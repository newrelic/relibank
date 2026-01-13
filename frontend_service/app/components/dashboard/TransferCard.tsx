import { useState, useContext } from 'react';
import { LoginContext } from '~/root';
import {
  Box,
  Typography,
  Card,
  Button,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Alert,
  InputAdornment,
} from '@mui/material';

interface TransferCardProps {
  transactions: any[];
  setTransactions: (transactions: any[]) => void;
}

export const TransferCard = ({ transactions, setTransactions }: TransferCardProps) => {
  // Use context directly instead of receiving as props
  const { userData, setUserData } = useContext(LoginContext);

  const [fromAccount, setFromAccount] = useState('checking');
  const [toAccount, setToAccount] = useState('savings');
  const [amount, setAmount] = useState('');
  const [message, setMessage] = useState('');
  const [isError, setIsError] = useState(false);

  // Guard clause: userData should be an array of accounts
  if (!userData || !Array.isArray(userData)) {
    return (
      <Card sx={{ p: 3 }}>
        <Typography variant="h6">Transfer Funds</Typography>
        <Alert severity="warning" sx={{ mt: 2 }}>Account data is not available for transfers.</Alert>
      </Card>
    );
  }

  const checking = userData.find(acc => acc.account_type === 'checking');
  const savings = userData.find(acc => acc.account_type === 'savings');

  // Guard clause in case accounts are missing
  if (!checking || !savings) {
    return (
      <Card sx={{ p: 3 }}>
        <Typography variant="h6">Transfer Funds</Typography>
        <Alert severity="warning" sx={{ mt: 2 }}>Account data is not available for transfers.</Alert>
      </Card>
    );
  }

  const handleTransfer = async (event: React.FormEvent) => {
    event.preventDefault();
    setMessage('');
    setIsError(false);

    const transferAmount = parseFloat(amount);
    if (isNaN(transferAmount) || transferAmount <= 0) {
      setIsError(true);
      setMessage('Please enter a valid amount.');
      return;
    }

    if (fromAccount === toAccount) {
      setIsError(true);
      setMessage('Cannot transfer to the same account.');
      return;
    }

    // ==========================================================================
    // DEMO APP: No overdraft validation on frontend
    //
    // Users can transfer more than their balance (e.g., $10,000 from $100 account).
    // This is intentional to demonstrate:
    // - Backend validation errors
    // - New Relic error telemetry
    // - Visual impact of failed transfers with incorrect balances
    //
    // Do not add balance checks here unless updating demo scenarios.
    // ==========================================================================

    const sourceAccount = fromAccount === 'checking' ? checking : savings;
    const destinationAccount = toAccount === 'checking' ? checking : savings;

    // Calculate new balances
    const newCheckingBalance = fromAccount === 'checking'
      ? checking.balance - transferAmount
      : checking.balance + transferAmount;
    const newSavingsBalance = fromAccount === 'savings'
      ? savings.balance - transferAmount
      : savings.balance + transferAmount;

    const newUserData = userData.map(acc => {
      if (acc.account_type === 'checking') {
        return { ...acc, balance: parseFloat(newCheckingBalance.toFixed(2)) };
      }
      if (acc.account_type === 'savings') {
        return { ...acc, balance: parseFloat(newSavingsBalance.toFixed(2)) };
      }
      return acc;
    });

    // Create new transactions
    const transactionDate = new Date().toISOString().slice(0, 10);
    const newSourceTx = {
      id: transactions.length + 1,
      name: `Transfer to ${toAccount.charAt(0).toUpperCase() + toAccount.slice(1)}`,
      date: transactionDate,
      amount: -transferAmount,
      accountId: fromAccount,
      type: 'debit'
    };
    const newTargetTx = {
      id: transactions.length + 2,
      name: `Transfer from ${fromAccount.charAt(0).toUpperCase() + fromAccount.slice(1)}`,
      date: transactionDate,
      amount: transferAmount,
      accountId: toAccount,
      type: 'credit'
    };

    // ==========================================================================
    // OPTIMISTIC UPDATE: Update UI immediately (before API call)
    //
    // NOTE FOR DEMO APP: We intentionally DO NOT rollback on error.
    // This allows the UI to show incorrect balances when transfers fail,
    // demonstrating the visual impact of errors for New Relic telemetry demos.
    //
    // In a production app, you would rollback to original state on error.
    // Do not change this behavior unless explicitly updating demo scenarios.
    // ==========================================================================
    setUserData(newUserData);
    setTransactions([newSourceTx, newTargetTx, ...transactions]);

    // Call API
    try {
      const paymentData = {
        "billId": "BILL-RECUR-002",
        "amount": transferAmount,
        "currency": "USD",
        "fromAccountId": sourceAccount.account_type === 'checking' ? 12345 : 56789,
        "toAccountId": destinationAccount.account_type === 'checking' ? 12345 : 56789,
        "frequency": "one-time",
        "startDate": new Date().toISOString().split('T')[0],
        "currentBalance": sourceAccount.balance,
        "accountType": sourceAccount.account_type
      };

      console.log('[DEBUG] Sending payment request:', paymentData);

      const response = await fetch('/bill-pay-service/recurring', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(paymentData),
      });

      if (!response.ok) {
        let errorMessage = `API returned status ${response.status}`;
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorData.message || errorMessage;
        } catch (e) {
          console.warn('Could not parse error response as JSON');
        }
        throw new Error(errorMessage);
      }

      // Success - show success message
      setMessage(`Successfully transferred $${transferAmount.toFixed(2)} from ${fromAccount} to ${toAccount}.`);
      setAmount('');

    } catch (error: any) {
      console.error('Transfer API error:', error);

      // ==========================================================================
      // INTENTIONAL: NO ROLLBACK ON ERROR (Demo App Behavior)
      //
      // The incorrect balance remains visible to demonstrate error impact.
      // This helps with New Relic demos by showing corrupted UI state.
      //
      // In production: You would rollback userData and transactions here.
      // ==========================================================================

      // Report error to New Relic Browser
      if (typeof window !== 'undefined' && (window as any).newrelic) {
        console.log('[DEBUG] Reporting API error to New Relic Browser');
        (window as any).newrelic.noticeError(error, {
          component: 'TransferFunds',
          endpoint: '/bill-pay-service/recurring',
          amount: transferAmount,
          fromAccount: fromAccount,
          toAccount: toAccount
        });
        console.log('[DEBUG] API error reported to New Relic');
      } else {
        console.warn('[DEBUG] New Relic Browser agent not available for API error');
      }

      setIsError(true);
      setMessage(error.message || 'Transfer failed. Please try again.');
    }
  };

  return (
    <Card sx={{
      p: 3,
      height: '100%',
      width: '100%',
      display: 'flex',
      flexDirection: 'column',
      borderRadius: '12px',
      border: '1px solid #e5e7eb',
      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)'
    }}>
      <Typography variant="h6" sx={{ mb: 2 }}>Transfer Funds</Typography>
      {message && (
        <Alert severity={isError ? "error" : "success"} sx={{ width: '100%', mb: 2 }}>
          {message}
        </Alert>
      )}
      <Box component="form" onSubmit={handleTransfer} noValidate sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        <TextField
          label="Amount"
          type="number"
          variant="outlined"
          fullWidth
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          inputProps={{ step: "0.01", min: "0.01" }}
          InputProps={{
            startAdornment: <InputAdornment position="start">$</InputAdornment>,
          }}
        />

        <FormControl fullWidth variant="outlined">
          <InputLabel id="from-account-label">From</InputLabel>
          <Select
            labelId="from-account-label"
            id="from-account-select"
            value={fromAccount}
            label="From"
            onChange={(e) => {
              setFromAccount(e.target.value);
              if (e.target.value === toAccount) {
                setToAccount(e.target.value === 'checking' ? 'savings' : 'checking');
              }
            }}
          >
            <MenuItem value="checking">
              Checking (${checking.balance.toFixed(2)})
            </MenuItem>
            <MenuItem value="savings">
              Savings (${savings.balance.toFixed(2)})
            </MenuItem>
          </Select>
        </FormControl>

        <FormControl fullWidth variant="outlined">
          <InputLabel id="to-account-label">To</InputLabel>
          <Select
            labelId="to-account-label"
            id="to-account-select"
            value={toAccount}
            label="To"
            onChange={(e) => {
              setToAccount(e.target.value);
              if (e.target.value === fromAccount) {
                setFromAccount(e.target.value === 'checking' ? 'savings' : 'checking');
              }
            }}
          >
            <MenuItem value="checking">
              Checking (${checking.balance.toFixed(2)})
            </MenuItem>
            <MenuItem value="savings">
              Savings (${savings.balance.toFixed(2)})
            </MenuItem>
          </Select>
        </FormControl>

        <Button
          type="submit"
          variant="contained"
          color="primary"
          fullWidth
          sx={{ py: 1.5 }}
          disabled={fromAccount === toAccount || isNaN(parseFloat(amount)) || parseFloat(amount) <= 0}
        >
          Complete Transfer
        </Button>
      </Box>
    </Card>
  );
};
