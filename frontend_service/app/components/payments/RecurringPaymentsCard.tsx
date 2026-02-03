import { useState, useContext, useEffect } from 'react';
import { LoginContext } from '~/root';
import {
  Box,
  Typography,
  Card,
  Button,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
  Tooltip,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  InputAdornment,
  CircularProgress,
  Collapse,
} from '@mui/material';
import {
  CalendarMonth as CalendarMonthIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Add as AddIcon,
} from '@mui/icons-material';

// Mock data for scheduled/recurring payments
const mockScheduledPayments = [
  { id: 'mock-1', billId: 'BILL-ELECTRIC-001', payee: 'Electric Company', amount: 125.50, frequency: 'monthly', nextDate: '2024-02-01', status: 'active', toAccountId: 10001 },
  { id: 'mock-2', billId: 'BILL-INTERNET-002', payee: 'Internet Service', amount: 79.99, frequency: 'monthly', nextDate: '2024-02-05', status: 'active', toAccountId: 10001 },
  { id: 'mock-3', billId: 'BILL-WATER-003', payee: 'Water Utility', amount: 45.00, frequency: 'monthly', nextDate: '2024-02-10', status: 'active', toAccountId: 10001 },
];

interface RecurringScheduleAPI {
  ScheduleID: number;
  BillID: string;
  AccountID: number;
  Amount: number;
  Currency: string;
  Frequency: string;
  StartDate: string;
  Timestamp: number;
  CancellationUserID?: string;
  CancellationTimestamp?: number;
}

export const RecurringPaymentsCard = () => {
  const { userData } = useContext(LoginContext);
  const [payments, setPayments] = useState(mockScheduledPayments);
  const [isLoadingSchedules, setIsLoadingSchedules] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);

  // Form state (pre-filled with test values)
  const [payee, setPayee] = useState('Netflix');
  const [amount, setAmount] = useState('149.99');
  const [accountNumber, setAccountNumber] = useState('10001');
  const [fromAccount, setFromAccount] = useState('checking');
  const [frequency, setFrequency] = useState('monthly');
  const [startDate, setStartDate] = useState('2024-03-01');

  const [message, setMessage] = useState('');
  const [isError, setIsError] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    fetchRecurringSchedules();
  }, []);

  // Helper: Parse bill_id into readable payee name
  const parseBillIdToPayee = (billId: string): string => {
    const cleaned = billId.replace(/^BILL-/i, '').replace(/-\d+$/, '');
    return cleaned
      .split(/[-_]/)
      .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(' ');
  };

  const fetchRecurringSchedules = async () => {
    try {
      setIsLoadingSchedules(true);
      const response = await fetch('/transaction-service/recurring-payments');
      const data: RecurringScheduleAPI[] = await response.json();

      if (!response.ok) {
        throw new Error('Failed to fetch recurring schedules');
      }

      // Transform API data to display format
      const realSchedules = data
        .filter(schedule => !schedule.CancellationTimestamp) // Only show active schedules
        .map(schedule => ({
          id: schedule.ScheduleID,
          billId: schedule.BillID,
          payee: parseBillIdToPayee(schedule.BillID),
          amount: schedule.Amount,
          frequency: schedule.Frequency.toLowerCase(),
          nextDate: schedule.StartDate,
          status: 'active',
          toAccountId: schedule.AccountID,
        }));

      // Combine mock data with real schedules
      const allSchedules = [...mockScheduledPayments, ...realSchedules];
      setPayments(allSchedules);
    } catch (error: any) {
      console.error('Error fetching recurring schedules:', error);
      // On error, show mock data
      setPayments(mockScheduledPayments);
    } finally {
      setIsLoadingSchedules(false);
    }
  };

  const handleAddRecurring = async (event: React.FormEvent) => {
    event.preventDefault();
    setMessage('');
    setIsError(false);

    // Basic validation
    const paymentAmount = parseFloat(amount);
    if (!payee || isNaN(paymentAmount) || paymentAmount <= 0 || !accountNumber || !startDate) {
      setIsError(true);
      setMessage('Please fill in all fields with valid values.');
      return;
    }

    // Get the fromAccountId based on selected account type
    const fromAccountData = userData?.find(acc => acc.account_type === fromAccount);
    if (!fromAccountData) {
      setIsError(true);
      setMessage('Unable to find source account. Please try again.');
      return;
    }

    const fromAccountId = parseInt(fromAccountData.routing_number);

    setIsLoading(true);

    try {
      // Call the bill-pay-service recurring API
      const response = await fetch('/bill-pay-service/recurring', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          billId: `BILL-${payee.toUpperCase().replace(/\s+/g, '-')}-${Date.now()}`,
          amount: paymentAmount,
          currency: 'USD',
          fromAccountId: fromAccountId,
          toAccountId: parseInt(accountNumber),
          frequency: frequency,
          startDate: startDate,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || data.message || 'Failed to set up recurring payment');
      }

      // Success
      setIsError(false);
      setMessage(`Recurring payment to ${payee} set up successfully!`);

      // Refresh the list from backend
      await fetchRecurringSchedules();

      // Reset form to defaults
      setPayee('Netflix');
      setAmount('149.99');
      setAccountNumber('10001');
      setStartDate('2024-03-01');
      setShowAddForm(false);
    } catch (error: any) {
      setIsError(true);
      setMessage(error.message || 'Failed to set up recurring payment. Please try again.');
      console.error('Recurring payment error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancelPayment = async (billId: string) => {
    try {
      // Call the cancel API
      const response = await fetch(`/bill-pay-service/cancel/${billId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: 'solaire.a@sunlight.com', // TODO: get from user context
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || data.message || 'Failed to cancel payment');
      }

      // Success - refresh from backend
      await fetchRecurringSchedules();
      setMessage('Payment cancelled successfully');
      setIsError(false);
    } catch (error: any) {
      setIsError(true);
      setMessage(error.message || 'Failed to cancel payment. Please try again.');
      console.error('Cancel payment error:', error);
    }
  };

  return (
    <Card sx={{
      p: 3,
      height: '100%',
      borderRadius: '12px',
      border: '1px solid #e5e7eb',
      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)'
    }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <CalendarMonthIcon color="primary" sx={{ mr: 1 }} />
          <Typography variant="h6">Recurring Payments</Typography>
        </Box>
        <Button
          id="recurring-payment-add-btn"
          variant="outlined"
          size="small"
          startIcon={<AddIcon />}
          onClick={() => setShowAddForm(!showAddForm)}
        >
          {showAddForm ? 'Cancel' : 'Add New'}
        </Button>
      </Box>

      {message && (
        <Alert severity={isError ? "error" : "success"} sx={{ mb: 2 }} onClose={() => setMessage('')}>
          {message}
        </Alert>
      )}

      <Collapse in={showAddForm}>
        <Box component="form" onSubmit={handleAddRecurring} sx={{ mb: 3, p: 2, bgcolor: '#f9fafb', borderRadius: '8px' }}>
          <Typography variant="subtitle2" sx={{ mb: 2, fontWeight: 'bold' }}>
            Set Up Recurring Payment
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              id="recurring-payment-payee"
              label="Payee Name"
              variant="outlined"
              fullWidth
              size="small"
              value={payee}
              onChange={(e) => setPayee(e.target.value)}
              placeholder="Netflix"
            />

            <TextField
              id="recurring-payment-account-number"
              label="Account Number"
              variant="outlined"
              fullWidth
              size="small"
              value={accountNumber}
              onChange={(e) => setAccountNumber(e.target.value)}
              placeholder="10001"
            />

            <TextField
              id="recurring-payment-amount"
              label="Amount"
              type="number"
              variant="outlined"
              fullWidth
              size="small"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              inputProps={{ step: "0.01", min: "0.01" }}
              placeholder="149.99"
              slotProps={{
                input: {
                  startAdornment: <InputAdornment position="start">$</InputAdornment>,
                }
              }}
            />

            <TextField
              id="recurring-payment-start-date"
              label="Start Date"
              type="date"
              variant="outlined"
              fullWidth
              size="small"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              slotProps={{
                inputLabel: { shrink: true }
              }}
            />

            <FormControl fullWidth variant="outlined" size="small">
              <InputLabel id="frequency-label">Frequency</InputLabel>
              <Select
                id="recurring-payment-frequency"
                labelId="frequency-label"
                value={frequency}
                label="Frequency"
                onChange={(e) => setFrequency(e.target.value)}
              >
                <MenuItem value="weekly">Weekly</MenuItem>
                <MenuItem value="monthly">Monthly</MenuItem>
                <MenuItem value="quarterly">Quarterly</MenuItem>
                <MenuItem value="annually">Annually</MenuItem>
              </Select>
            </FormControl>

            <FormControl fullWidth variant="outlined" size="small">
              <InputLabel id="from-account-recurring-label">Pay From</InputLabel>
              <Select
                id="recurring-payment-from-account"
                labelId="from-account-recurring-label"
                value={fromAccount}
                label="Pay From"
                onChange={(e) => setFromAccount(e.target.value)}
              >
                <MenuItem value="checking">Checking Account</MenuItem>
                <MenuItem value="savings">Savings Account</MenuItem>
              </Select>
            </FormControl>

            <Button
              id="recurring-payment-submit-btn"
              type="submit"
              variant="contained"
              color="primary"
              disabled={isLoading}
              sx={{ py: 1 }}
            >
              {isLoading ? (
                <>
                  <CircularProgress size={18} sx={{ mr: 1 }} color="inherit" />
                  Setting up...
                </>
              ) : (
                'Set Up Recurring Payment'
              )}
            </Button>
          </Box>
        </Box>
      </Collapse>

      <TableContainer>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontWeight: 'bold' }}>Payee</TableCell>
              <TableCell align="right" sx={{ fontWeight: 'bold' }}>Amount</TableCell>
              <TableCell sx={{ fontWeight: 'bold' }}>Frequency</TableCell>
              <TableCell sx={{ fontWeight: 'bold' }}>Next Date</TableCell>
              <TableCell sx={{ fontWeight: 'bold' }}>Status</TableCell>
              <TableCell align="right" sx={{ fontWeight: 'bold' }}>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {payments.map((payment) => (
              <TableRow key={payment.id}>
                <TableCell>{payment.payee}</TableCell>
                <TableCell align="right">${payment.amount.toFixed(2)}</TableCell>
                <TableCell>
                  <Chip label={payment.frequency} size="small" color="primary" variant="outlined" />
                </TableCell>
                <TableCell>{payment.nextDate}</TableCell>
                <TableCell>
                  <Chip
                    label={payment.status}
                    size="small"
                    color={payment.status === 'active' ? 'success' : 'default'}
                  />
                </TableCell>
                <TableCell align="right">
                  <Tooltip title="Edit">
                    <IconButton size="small" color="primary">
                      <EditIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Cancel">
                    <IconButton
                      size="small"
                      color="error"
                      onClick={() => handleCancelPayment(payment.billId)}
                    >
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {payments.length === 0 && (
        <Box sx={{ textAlign: 'center', py: 4 }}>
          <Typography variant="body2" color="text.secondary">
            No recurring payments set up yet
          </Typography>
        </Box>
      )}
    </Card>
  );
};
