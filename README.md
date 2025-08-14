# relibank

TODOs

DB interface python with endpoints for auth service
placeholder for posts/puts, so we can implement adding new accounts later

In Transactions, add a DB table that stores outstanding balance on a loan/credit account, amount on a checking/savings account

In Bill Pay, add from/to account
Enforce uniqueness on BillIDs
Check that to/fromaccount is valid, check balance on each before initiating payment or cancel if it's impossible

Convert logging.info calls to json instead of flat logs

## Ledger details and decision log

Get Ledger/loan/credit card payment history
    {
        "TransactionID": 1,
        "EventType": "BillPaymentInitiated",
        "BillID": "BILL-TEST-068",
        "Amount": 76.0,
        "Currency": "USD",
        "ToAccount": 873657890,
        "FromAccount": 872347890,
        "Timestamp": 1755028460.4713438,
        "CancellationUserID": null,
        "CancellationTimestamp": null
    },

    For toaccount, query database and reduce total by amount
    for fromaccount, query database and reduce total by amount

    Querying account 1234
    display ledger for current total
    query transaction database for every transaction with to or from containing the account 1234

    Venmo example
    You paid x $3.50
    x paid you $4.50

    Debit acct example
    Payment to AmEx -$x.xx
    To **xx-444 -$x.xx
    DIVIDEND

    Credit acct example
    Pending
    Active - VendorName -$x.xx

    Activity
    Credit Card Payment +$x.xx
    Vendor -$x.xx

    Account balance in debit is reduced by $76
    {
        "TransactionID": 1,
        "EventType": "BillPaidToAccount",
        "BillID": "BILL-TEST-068",
        "Amount": 76.0,
        "Currency": "USD",
        "Account": 873657890,
        "Timestamp": 1755028460.4713438,
        "CancellationUserID": null,
        "CancellationTimestamp": null
    },


    Loan principal is reduced by $76
    {
        "TransactionID": 1,
        "EventType": "BillPaidFromAccount",
        "BillID": "BILL-TEST-068",
        "Amount": 76.0,
        "Currency": "USD",
        "Account": 873657890,
        "Timestamp": 1755028460.4713438,
        "CancellationUserID": null,
        "CancellationTimestamp": null
    },
    Get eventtype
    edit DB for Account 1234
    Reduce total by Amount