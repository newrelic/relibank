#!/bin/bash
# ============================================================================
# run-banking-load.sh
#
# Launches sustained banking load directly against the MSSQL pod for New Relic
# Query Performance Monitoring demo purposes.
#
# What it does:
#   1. Kills any leftover workers from a previous run
#   2. Verifies Merchants (50K) and BankTransactions (2M) exist; seeds if missing
#   3. Launches N slow-query workers (spending_velocity) — each run takes ~25s,
#      giving NRDOT (10s sample interval) 2-3 captures per execution
#   4. Launches a blocking worker that holds an UPDLOCK on flagged high-risk
#      transactions for BLOCK_HOLD_SECONDS, then a contending UPDATE worker
#   5. Prints a status summary and how to stop everything
#
# Usage:
#   bash run-banking-load.sh [--workers N] [--block-hold SECONDS] [--no-block]
#
# Defaults:
#   --workers    4      number of parallel slow-query workers
#   --block-hold 120    seconds the blocker holds its lock (>= NR ingest lag ~90s)
#   --no-block         skip the blocking scenario
# ============================================================================

set -uo pipefail   # note: no -e, SQL errors are non-fatal

# ── defaults ────────────────────────────────────────────────────────────────
NAMESPACE="relibank"
POD="mssql-0"
SA_PASS="YourStrong@Password!"
DB="RelibankDB"
NUM_WORKERS=4
BLOCK_HOLD=120
RUN_BLOCKING=true

# ── argument parsing ─────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --workers)    NUM_WORKERS="$2"; shift 2 ;;
        --block-hold) BLOCK_HOLD="$2";  shift 2 ;;
        --no-block)   RUN_BLOCKING=false; shift ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
done

# Single sqlcmd invocation: kubectl exec into pod, run query, suppress stderr
run_sql() {
    kubectl exec -n "$NAMESPACE" "$POD" -- \
        /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P "$SA_PASS" -d "$DB" -C \
        -Q "$1" 2>/dev/null || true
}

# Get a scalar integer from SQL (strips headers/whitespace)
count_sql() {
    kubectl exec -n "$NAMESPACE" "$POD" -- \
        /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P "$SA_PASS" -d "$DB" -C \
        -h -1 -W -Q "SET NOCOUNT ON; $1" 2>/dev/null \
    | tr -d ' \r' | grep -E '^[0-9]+$' | head -1 || echo "0"
}

# ── helpers ──────────────────────────────────────────────────────────────────
banner() { echo ""; echo "══════════════════════════════════════════════"; echo "  $*"; echo "══════════════════════════════════════════════"; }

# ── 1. clean up old workers ──────────────────────────────────────────────────
banner "Step 1: Cleaning up old workers"
kubectl exec -n "$NAMESPACE" "$POD" -- bash -c "
    pkill -f 'sustain_banking' 2>/dev/null || true
    pkill -f 'block_banking'   2>/dev/null || true
    pkill -f 'banking_slow'    2>/dev/null || true
    # Kill any lingering sqlcmd sessions except the current one
    sleep 1
    echo 'cleanup done'
" 2>/dev/null || true

# Also kill any open MSSQL blocker sessions
run_sql "
DECLARE @spid INT;
DECLARE kill_cur CURSOR FOR
    SELECT session_id FROM sys.dm_exec_requests
    WHERE session_id > 50 AND wait_type LIKE 'LCK%';
OPEN kill_cur;
FETCH NEXT FROM kill_cur INTO @spid;
WHILE @@FETCH_STATUS = 0 BEGIN
    EXEC('KILL ' + @spid);
    FETCH NEXT FROM kill_cur INTO @spid;
END;
CLOSE kill_cur; DEALLOCATE kill_cur;
PRINT 'stale lock sessions cleared';
" || true

echo "Old workers cleared."

# ── 2. verify / seed tables ──────────────────────────────────────────────────
banner "Step 2: Verifying data tables"

MERCHANT_COUNT=$(count_sql "SELECT COUNT(*) FROM Merchants;")
TXNS_COUNT=$(count_sql "SELECT COUNT(*) FROM BankTransactions;")

echo "  Merchants:        ${MERCHANT_COUNT:-0} rows"
echo "  BankTransactions: ${TXNS_COUNT:-0} rows"

if [[ "${MERCHANT_COUNT:-0}" -lt 50000 ]]; then
    echo "  Seeding Merchants (50K)..."
    run_sql "TRUNCATE TABLE Merchants;" 2>/dev/null || run_sql "DROP TABLE IF EXISTS Merchants;"
    run_sql "
    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Merchants')
    BEGIN
        CREATE TABLE Merchants (
            MerchantID INT PRIMARY KEY, MerchantName VARCHAR(100) NOT NULL,
            Category VARCHAR(50) NOT NULL, Region VARCHAR(30) NOT NULL,
            RiskTier TINYINT NOT NULL DEFAULT 1, AnnualVolume DECIMAL(14,2), IsActive BIT NOT NULL DEFAULT 1
        );
        CREATE INDEX IX_Merchants_Category ON Merchants (Category);
        CREATE INDEX IX_Merchants_Region   ON Merchants (Region);
        CREATE INDEX IX_Merchants_Risk     ON Merchants (RiskTier);
    END;
    WITH Numbers AS (SELECT TOP 50000 ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS n FROM sys.all_columns a CROSS JOIN sys.all_columns b)
    INSERT INTO Merchants (MerchantID, MerchantName, Category, Region, RiskTier, AnnualVolume, IsActive)
    SELECT n, 'Merchant '+CAST(n AS VARCHAR(10)),
        CASE (n%8) WHEN 0 THEN 'Retail' WHEN 1 THEN 'Restaurant' WHEN 2 THEN 'Travel' WHEN 3 THEN 'Healthcare' WHEN 4 THEN 'Gas & Auto' WHEN 5 THEN 'Online' WHEN 6 THEN 'Grocery' ELSE 'Entertainment' END,
        CASE (n%6) WHEN 0 THEN 'Northeast' WHEN 1 THEN 'Southeast' WHEN 2 THEN 'Midwest' WHEN 3 THEN 'Southwest' WHEN 4 THEN 'West' ELSE 'Central' END,
        CASE WHEN n%20=0 THEN 3 WHEN n%7=0 THEN 2 ELSE 1 END,
        ((n%9000)+1000)*100.00,
        CASE WHEN n%15=0 THEN 0 ELSE 1 END
    FROM Numbers;
    UPDATE STATISTICS Merchants WITH FULLSCAN;
    PRINT 'Merchants seeded';
    "
fi

if [[ "${TXNS_COUNT:-0}" -lt 2000000 ]]; then
    echo "  Seeding BankTransactions (2M) — this takes ~30s..."
    run_sql "TRUNCATE TABLE BankTransactions;" 2>/dev/null || run_sql "DROP TABLE IF EXISTS BankTransactions;"
    run_sql "
    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'BankTransactions')
    BEGIN
        CREATE TABLE BankTransactions (
            TxnID INT PRIMARY KEY, AccountID INT NOT NULL, MerchantID INT NOT NULL,
            Amount DECIMAL(10,2) NOT NULL, TxnDate DATETIME NOT NULL,
            TxnType VARCHAR(20) NOT NULL, Status VARCHAR(15) NOT NULL, Channel VARCHAR(15) NOT NULL
        );
        CREATE INDEX IX_BankTxn_Account  ON BankTransactions (AccountID);
        CREATE INDEX IX_BankTxn_Merchant ON BankTransactions (MerchantID);
        CREATE INDEX IX_BankTxn_Date     ON BankTransactions (TxnDate);
    END;
    " 2>/dev/null || true

    run_sql "
    SET NOCOUNT ON;
    WITH Numbers AS (SELECT TOP 1000000 ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS n FROM sys.all_columns a CROSS JOIN sys.all_columns b CROSS JOIN sys.all_columns c)
    INSERT INTO BankTransactions (TxnID,AccountID,MerchantID,Amount,TxnDate,TxnType,Status,Channel)
    SELECT n,(n%10000)+10001,(n%50000)+1,CAST(((n%49900)+100) AS DECIMAL(10,2))/100.0,
        DATEADD(SECOND,-(n*31),GETDATE()),
        CASE (n%4) WHEN 0 THEN 'Purchase' WHEN 1 THEN 'Refund' WHEN 2 THEN 'Transfer' ELSE 'ATM' END,
        CASE WHEN n%50=0 THEN 'Flagged' WHEN n%15=0 THEN 'Declined' ELSE 'Approved' END,
        CASE (n%4) WHEN 0 THEN 'Online' WHEN 1 THEN 'InStore' WHEN 2 THEN 'Mobile' ELSE 'ATM' END
    FROM Numbers;
    " 2>/dev/null || true

    run_sql "
    SET NOCOUNT ON;
    WITH Numbers AS (SELECT TOP 1000000 ROW_NUMBER() OVER (ORDER BY (SELECT NULL))+1000000 AS n FROM sys.all_columns a CROSS JOIN sys.all_columns b CROSS JOIN sys.all_columns c)
    INSERT INTO BankTransactions (TxnID,AccountID,MerchantID,Amount,TxnDate,TxnType,Status,Channel)
    SELECT n,(n%10000)+10001,(n%50000)+1,CAST(((n%49900)+100) AS DECIMAL(10,2))/100.0,
        DATEADD(SECOND,-(n*31),GETDATE()),
        CASE (n%4) WHEN 0 THEN 'Purchase' WHEN 1 THEN 'Refund' WHEN 2 THEN 'Transfer' ELSE 'ATM' END,
        CASE WHEN n%50=0 THEN 'Flagged' WHEN n%15=0 THEN 'Declined' ELSE 'Approved' END,
        CASE (n%4) WHEN 0 THEN 'Online' WHEN 1 THEN 'InStore' WHEN 2 THEN 'Mobile' ELSE 'ATM' END
    FROM Numbers;
    UPDATE STATISTICS BankTransactions WITH FULLSCAN;
    DBCC FREEPROCCACHE;
    PRINT 'BankTransactions seeded';
    " 2>/dev/null || true
fi

echo "  Tables ready."

# ── 3. write SQL files into pod ──────────────────────────────────────────────
banner "Step 3: Writing SQL and worker scripts to pod"

# Spending velocity slow query (~25s on 6 months / ~500K rows)
kubectl exec -n "$NAMESPACE" "$POD" -- bash -c "cat > /tmp/banking_slow.sql << 'EOF'
SELECT
    t.TxnID,
    t.AccountID,
    t.MerchantID,
    m.Category,
    m.Region,
    m.RiskTier,
    t.Amount,
    t.TxnDate,
    t.TxnType,
    t.Channel,
    ROW_NUMBER()  OVER (PARTITION BY t.AccountID ORDER BY t.TxnDate)
                                                    AS TxnSeq,
    SUM(t.Amount) OVER (PARTITION BY t.AccountID ORDER BY t.TxnDate
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
                                                    AS CumulativeSpend,
    AVG(t.Amount) OVER (PARTITION BY t.AccountID ORDER BY t.TxnDate
                        ROWS BETWEEN 99 PRECEDING AND CURRENT ROW)
                                                    AS MovingAvg100,
    RANK()        OVER (PARTITION BY m.Category ORDER BY t.Amount DESC)
                                                    AS GlobalAmountRank
FROM BankTransactions t WITH (INDEX(0))
INNER JOIN Merchants m WITH (INDEX(0)) ON m.MerchantID = t.MerchantID
WHERE t.TxnDate >= DATEADD(MONTH, -6, GETDATE())
ORDER BY t.AccountID, t.TxnDate
OPTION (MAXDOP 1);
EOF
echo 'banking_slow.sql written'"

# Blocker SQL: hold UPDLOCK on flagged high-risk rows for BLOCK_HOLD_SECONDS
kubectl exec -n "$NAMESPACE" "$POD" -- bash -c "cat > /tmp/banking_blocker.sql << EOF
BEGIN TRANSACTION;
SELECT TOP 100 t.TxnID, t.AccountID, t.Amount, m.Category, m.RiskTier
FROM BankTransactions t WITH (UPDLOCK, ROWLOCK, HOLDLOCK)
INNER JOIN Merchants m ON m.MerchantID = t.MerchantID
WHERE t.Status = 'Flagged' AND m.RiskTier = 3
ORDER BY t.Amount DESC;
UPDATE BankTransactions SET Amount = Amount WHERE TxnID IN (
    SELECT TOP 100 t.TxnID FROM BankTransactions t
    INNER JOIN Merchants m ON m.MerchantID = t.MerchantID
    WHERE t.Status = 'Flagged' AND m.RiskTier = 3 ORDER BY t.Amount DESC
);
WAITFOR DELAY '$(printf '%02d:%02d:%02d' $((BLOCK_HOLD/3600)) $(( (BLOCK_HOLD%3600)/60 )) $((BLOCK_HOLD%60)))';
COMMIT TRANSACTION;
EOF
echo 'banking_blocker.sql written'"

# Contender UPDATE: risk-adjusted amount recalculation over ~500K rows.
# Runs independently (no lock contention), produces a rich UPDATE plan:
# UPDATE STATEMENT -> Hash Match (join) -> Clustered Index Scan x2
# Takes ~15-25s so NRDOT catches it mid-execution.
kubectl exec -n "$NAMESPACE" "$POD" -- bash -c "cat > /tmp/banking_contender.sql << 'EOF'
UPDATE t
SET t.Amount = t.Amount * (1.0 + (CAST(m.RiskTier AS DECIMAL(5,4)) * 0.0001))
FROM BankTransactions t WITH (INDEX(0))
INNER JOIN Merchants m WITH (INDEX(0)) ON m.MerchantID = t.MerchantID
WHERE t.TxnDate >= DATEADD(MONTH, -6, GETDATE())
  AND t.Status = 'Approved'
  AND m.IsActive = 1
OPTION (MAXDOP 1);
EOF
echo 'banking_contender.sql written'"

# Slow-query worker loop
kubectl exec -n "$NAMESPACE" "$POD" -- bash -c "cat > /tmp/sustain_banking.sh << 'SCRIPT'
#!/bin/bash
while true; do
    /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P 'YourStrong@Password!' -d RelibankDB -C -i /tmp/banking_slow.sql 2>/dev/null
done
SCRIPT
chmod +x /tmp/sustain_banking.sh
echo 'sustain_banking.sh written'"

echo "SQL files written to pod."

# ── 4. launch slow-query workers ─────────────────────────────────────────────
banner "Step 4: Launching $NUM_WORKERS slow-query workers"

kubectl exec -n "$NAMESPACE" "$POD" -- bash -c "
for i in \$(seq 1 $NUM_WORKERS); do
    nohup /tmp/sustain_banking.sh > /tmp/worker_\${i}.log 2>&1 &
done
sleep 2
echo \"Workers launched: \$(ps aux | grep sustain_banking | grep -v grep | wc -l)\"
"

# ── 5. launch blocking scenario ───────────────────────────────────────────────
if $RUN_BLOCKING; then
    banner "Step 5: Launching blocking scenario (hold ${BLOCK_HOLD}s)"

    # Start blocker in background (holds lock for BLOCK_HOLD seconds)
    kubectl exec -n "$NAMESPACE" "$POD" -- bash -c "
    nohup /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P 'YourStrong@Password!' -d RelibankDB -C -i /tmp/banking_blocker.sql > /tmp/blocker.log 2>&1 &
    echo 'blocker started'
    " 2>/dev/null

    sleep 3

    # Start contender UPDATE loop (risk-adjusted recalculation, ~15-25s per run)
    kubectl exec -n "$NAMESPACE" "$POD" -- bash -c "
    cat > /tmp/sustain_contender.sh << 'SCRIPT'
#!/bin/bash
while true; do
    /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P 'YourStrong@Password!' -d RelibankDB -C -i /tmp/banking_contender.sql 2>/dev/null
done
SCRIPT
    chmod +x /tmp/sustain_contender.sh
    nohup /tmp/sustain_contender.sh > /tmp/contender.log 2>&1 &
    echo 'contender loop started'
    " 2>/dev/null

    echo "Blocking scenario launched."
fi

# ── 6. status summary ─────────────────────────────────────────────────────────
sleep 5
banner "Status"

echo ""
echo "Active MSSQL sessions:"
run_sql "
SELECT session_id,
       status,
       wait_type,
       wait_time/1000 AS wait_sec,
       blocking_session_id AS blocker,
       LEFT(sql_text.text, 70) AS query
FROM sys.dm_exec_requests r
CROSS APPLY sys.dm_exec_sql_text(r.sql_handle) AS sql_text
WHERE session_id > 50 AND session_id != @@SPID
ORDER BY wait_time DESC
"

echo ""
echo "Worker processes in pod:"
kubectl exec -n "$NAMESPACE" "$POD" -- bash -c "ps aux | grep -E '(sustain_banking|sqlcmd)' | grep -v grep | wc -l" 2>/dev/null
echo "  worker processes running"

echo ""
echo "══════════════════════════════════════════════"
echo "  Load generation running."
echo "  NRDOT scrapes every 10s → NR ingest ~60-90s"
echo "  Allow 2-3 minutes for Active Queries to populate."
echo ""
echo "  Stop workers:  kubectl exec -n $NAMESPACE $POD -- bash -c \"pkill -f sustain_banking; pkill -f sqlcmd\" 2>/dev/null || true"
echo "══════════════════════════════════════════════"
