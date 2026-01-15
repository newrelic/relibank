import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  CircularProgress,
} from '@mui/material';
import { Receipt as ReceiptIcon } from '@mui/icons-material';

// Mock data for recent payment history (always shown)
const mockPaymentHistory = [
  { id: 'mock-1', payee: 'Electric Company', amount: 125.50, date: '2024-01-01', status: 'completed', method: 'Bank Account' },
  { id: 'mock-2', payee: 'Internet Service', amount: 79.99, date: '2024-01-05', status: 'completed', method: 'Bank Account' },
  { id: 'mock-3', payee: 'Rent', amount: 1500.00, date: '2024-01-01', status: 'completed', method: 'Bank Account' },
  { id: 'mock-4', payee: 'Phone Bill', amount: 65.00, date: '2023-12-28', status: 'completed', method: 'Credit Card' },
];

interface TransactionRecord {
  transaction_id: number;
  event_type: string;
  bill_id: string;
  amount: number;
  currency: string;
  account_id: number;
  timestamp: number;
  cancellation_user_id?: string;
  cancellation_timestamp?: number;
}

interface PaymentDisplay {
  id: string;
  payee: string;
  amount: number;
  date: string;
  status: string;
  method: string;
}

export const RecentPaymentsCard = () => {
  const [payments, setPayments] = useState<PaymentDisplay[]>(mockPaymentHistory);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchTransactions();
  }, []);

  // Helper: Parse bill_id into readable payee name
  const parseBillIdToPayee = (billId: string): string => {
    // Remove "BILL-" prefix and convert dashes/underscores to spaces
    // Example: "BILL-ELECTRIC-COMPANY-123" -> "Electric Company"
    const cleaned = billId.replace(/^BILL-/i, '').replace(/-\d+$/, '');
    return cleaned
      .split(/[-_]/)
      .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(' ');
  };

  // Helper: Format Unix timestamp to date string
  const formatTimestamp = (timestamp: number): string => {
    const date = new Date(timestamp * 1000); // Convert seconds to milliseconds
    return date.toISOString().split('T')[0]; // Returns YYYY-MM-DD
  };

  // Helper: Derive status from cancellation fields
  const deriveStatus = (transaction: TransactionRecord): string => {
    if (transaction.cancellation_timestamp) {
      return 'cancelled';
    }
    return 'completed';
  };

  const fetchTransactions = async () => {
    try {
      setIsLoading(true);

      const response = await fetch('/transaction-service/transactions');
      const data: TransactionRecord[] = await response.json();

      if (!response.ok) {
        throw new Error('Failed to fetch transactions');
      }

      // Filter to only payment events
      const paymentTransactions = data.filter(tx => tx.event_type && tx.event_type.toLowerCase() === 'payment');

      // Transform transaction data to payment display format
      const realPayments: PaymentDisplay[] = paymentTransactions.map(tx => ({
        id: `tx-${tx.transaction_id}`,
        payee: parseBillIdToPayee(tx.bill_id),
        amount: tx.amount,
        date: formatTimestamp(tx.timestamp),
        status: deriveStatus(tx),
        method: 'Bank Account', // All payments from transaction service are bank transfers
      }));

      // Combine mock data with real transactions
      const allPayments = [...mockPaymentHistory, ...realPayments];

      // Sort by date (newest first) and limit to 10 most recent
      const sortedPayments = allPayments
        .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
        .slice(0, 10);

      setPayments(sortedPayments);
    } catch (error: any) {
      console.error('Error fetching transactions:', error);
      // On error, just show mock data
      setPayments(mockPaymentHistory);
    } finally {
      setIsLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'pending':
        return 'warning';
      case 'failed':
        return 'error';
      case 'cancelled':
        return 'default';
      default:
        return 'default';
    }
  };

  return (
    <Card sx={{
      p: 3,
      borderRadius: '12px',
      border: '1px solid #e5e7eb',
      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)'
    }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
        <ReceiptIcon color="primary" sx={{ mr: 1 }} />
        <Typography variant="h6">Recent Payments</Typography>
      </Box>

      {isLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress />
        </Box>
      ) : (
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 'bold' }}>Payee</TableCell>
                <TableCell align="right" sx={{ fontWeight: 'bold' }}>Amount</TableCell>
                <TableCell sx={{ fontWeight: 'bold' }}>Date</TableCell>
                <TableCell sx={{ fontWeight: 'bold' }}>Method</TableCell>
                <TableCell sx={{ fontWeight: 'bold' }}>Status</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {payments.map((payment) => (
                <TableRow key={payment.id}>
                  <TableCell>
                    <Typography variant="body1" sx={{ fontWeight: 'medium' }}>
                      {payment.payee}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography variant="body1" sx={{ fontWeight: 'medium' }}>
                      ${payment.amount.toFixed(2)}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" color="text.secondary">
                      {payment.date}
                    </Typography>
                  </TableCell>
                  <TableCell>{payment.method}</TableCell>
                  <TableCell>
                    <Chip
                      label={payment.status}
                      size="small"
                      color={getStatusColor(payment.status)}
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {!isLoading && payments.length === 0 && (
        <Box sx={{ textAlign: 'center', py: 4 }}>
          <Typography variant="body2" color="text.secondary">
            No payment history available
          </Typography>
        </Box>
      )}
    </Card>
  );
};
