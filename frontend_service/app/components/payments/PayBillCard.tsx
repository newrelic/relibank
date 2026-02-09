import { useState, useContext, useEffect } from 'react';
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
  CircularProgress,
} from '@mui/material';
import { Receipt as ReceiptIcon } from '@mui/icons-material';

interface PaymentMethod {
  id: string;
  brand: string;
  last4: string;
  expMonth: number;
  expYear: number;
}

interface PayeeAccount {
  id: string;
  name: string;
  accountNumber: string;
}

// Available accounts from the database
const AVAILABLE_PAYEES: PayeeAccount[] = [
  { id: '12345', name: 'Alice Checking', accountNumber: '12345' },
  { id: '56789', name: 'Alice Savings', accountNumber: '56789' },
  { id: '67890', name: 'Charlie Checking', accountNumber: '67890' },
  { id: '98765', name: 'Bob Credit Card', accountNumber: '98765' },
  { id: '10111', name: 'Charlie Credit Card', accountNumber: '10111' },
];

interface PayBillCardProps {
  onPaymentSuccess?: () => void;
}

export const PayBillCard = ({ onPaymentSuccess }: PayBillCardProps) => {
  const { userData } = useContext(LoginContext);

  // Form state - use account ID as the single source of truth
  const [selectedAccountId, setSelectedAccountId] = useState('67890');
  const [amount, setAmount] = useState('125.50');

  // Payment method selection - unified dropdown
  const [selectedPaymentMethod, setSelectedPaymentMethod] = useState('checking');

  // Card data
  const [savedCards, setSavedCards] = useState<PaymentMethod[]>([]);
  const [customerId] = useState('cus_TkCwwRJbjMVQZ4');
  const [isLoadingCards, setIsLoadingCards] = useState(false);

  // UI state
  const [message, setMessage] = useState('');
  const [isError, setIsError] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // Fetch saved payment methods on mount
  useEffect(() => {
    fetchPaymentMethods();
  }, []);

  const fetchPaymentMethods = async () => {
    try {
      setIsLoadingCards(true);
      const response = await fetch(`/bill-pay-service/payment-methods/${customerId}`);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || data.message || 'Failed to fetch payment methods');
      }

      const cards = data.paymentMethods || [];
      setSavedCards(cards);
    } catch (error: any) {
      console.error('Error fetching payment methods:', error);
      setSavedCards([]);
    } finally {
      setIsLoadingCards(false);
    }
  };

  const handleBankPayment = async (paymentAmount: number, accountType: string, selectedAccount: PayeeAccount) => {
    // Get the fromAccountId based on selected account type
    const fromAccountData = userData?.find((acc: any) => acc.account_type === accountType);
    if (!fromAccountData) {
      setIsError(true);
      setMessage('Unable to find source account. Please try again.');
      return;
    }

    const fromAccountId = parseInt(fromAccountData.routing_number);

    const response = await fetch('/bill-pay-service/pay', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        billId: `BILL-${selectedAccount.name.toUpperCase().replace(/\s+/g, '-')}-${Date.now()}`,
        amount: paymentAmount,
        currency: 'USD',
        fromAccountId: fromAccountId,
        toAccountId: parseInt(selectedAccount.accountNumber),
      }),
    });

    if (!response.ok) {
      let errorMessage = 'Payment failed';
      try {
        const data = await response.json();
        errorMessage = data.detail || data.message || errorMessage;
      } catch (e) {
        errorMessage = `Payment failed with status ${response.status}`;
      }
      throw new Error(errorMessage);
    }

    const data = await response.json();

    const accountDisplay = accountType.charAt(0).toUpperCase() + accountType.slice(1);
    setIsError(false);

    setMessage(`Payment of $${paymentAmount.toFixed(2)} to ${selectedAccount.name} completed successfully using ${accountDisplay} account!`);

    // Reset form to defaults
    setSelectedAccountId('67890');
    setAmount('125.50');

    // Trigger refresh of recent payments
    if (onPaymentSuccess) {
      onPaymentSuccess();
    }
  };

  const handleCardPayment = async (paymentAmount: number, cardId: string, selectedAccount: PayeeAccount) => {
    const response = await fetch('/bill-pay-service/card-payment', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        billId: `BILL-${selectedAccount.name.toUpperCase().replace(/\s+/g, '-')}-${Date.now()}`,
        amount: paymentAmount,
        currency: 'USD',
        paymentMethodId: cardId,
        customerId: customerId,
        saveCard: false, // Card is already saved
      }),
    });

    if (!response.ok) {
      let errorMessage = 'Card payment failed';
      try {
        const data = await response.json();
        // Handle card-specific errors
        if (response.status === 402) {
          errorMessage = data.detail || 'Card declined by issuer. Please try a different card or contact your bank.';
        } else if (response.status === 504) {
          errorMessage = 'Payment gateway timeout. Please try again later.';
        } else {
          errorMessage = data.detail || data.message || errorMessage;
        }
      } catch (e) {
        errorMessage = `Card payment failed with status ${response.status}`;
      }
      throw new Error(errorMessage);
    }

    const data = await response.json();

    const selectedCardData = savedCards.find(c => c.id === cardId);
    const cardDisplay = selectedCardData
      ? `${selectedCardData.brand} ****${selectedCardData.last4}`
      : 'card';

    setIsError(false);
    setMessage(`Card payment of $${paymentAmount.toFixed(2)} to ${selectedAccount.name} processed successfully using ${cardDisplay}! (Payment ID: ${data.paymentIntentId})`);

    // Reset form to defaults
    setSelectedAccountId('67890');
    setAmount('125.50');

    // Trigger refresh of recent payments
    if (onPaymentSuccess) {
      onPaymentSuccess();
    }
  };

  const handlePayBill = async (event: React.FormEvent) => {
    event.preventDefault();
    setMessage('');
    setIsError(false);

    // Get the selected payee account
    const selectedAccount = AVAILABLE_PAYEES.find(acc => acc.accountNumber === selectedAccountId);
    if (!selectedAccount) {
      setIsError(true);
      setMessage('Please select a valid payee.');
      return;
    }

    // Basic validation
    const paymentAmount = parseFloat(amount);
    if (isNaN(paymentAmount) || paymentAmount <= 0) {
      setIsError(true);
      setMessage('Please enter a valid payment amount.');
      return;
    }

    setIsLoading(true);

    try {
      // Determine if selected payment method is a bank account or card
      if (selectedPaymentMethod === 'checking' || selectedPaymentMethod === 'savings') {
        // Bank account payment
        await handleBankPayment(paymentAmount, selectedPaymentMethod, selectedAccount);
      } else {
        // Card payment - selectedPaymentMethod is the card ID (pm_xxxx)
        await handleCardPayment(paymentAmount, selectedPaymentMethod, selectedAccount);
      }
    } catch (error: any) {
      setIsError(true);
      setMessage(error.message || 'Failed to process payment. Please try again.');
      console.error('Payment error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const formatCardBrand = (brand: string) => {
    return brand.charAt(0).toUpperCase() + brand.slice(1);
  };

  return (
    <Card sx={{
      p: 3,
      height: '100%',
      borderRadius: '12px',
      border: '1px solid #e5e7eb',
      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)'
    }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
        <ReceiptIcon color="primary" sx={{ mr: 1 }} />
        <Typography variant="h6">Pay a Bill</Typography>
      </Box>

      {message && (
        <Alert severity={isError ? "error" : "success"} sx={{ mb: 2 }} onClose={() => setMessage('')}>
          {message}
        </Alert>
      )}

      <Box component="form" onSubmit={handlePayBill} noValidate sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        <FormControl fullWidth variant="outlined">
          <InputLabel id="payee-label">Payee</InputLabel>
          <Select
            id="pay-bill-payee"
            labelId="payee-label"
            value={selectedAccountId}
            label="Payee"
            onChange={(e) => setSelectedAccountId(e.target.value)}
          >
            {AVAILABLE_PAYEES.map((account) => (
              <MenuItem key={account.id} value={account.accountNumber}>
                {account.name} - {account.accountNumber}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <TextField
          id="pay-bill-amount"
          label="Amount"
          type="number"
          variant="outlined"
          fullWidth
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          placeholder="125.50"
          slotProps={{
            htmlInput: { step: "0.01", min: "0.01" },
            input: {
              startAdornment: <InputAdornment position="start">$</InputAdornment>,
            }
          }}
        />

        {/* Unified Payment Method Selector */}
        {isLoadingCards ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
            <CircularProgress size={20} />
          </Box>
        ) : (
          <FormControl fullWidth variant="outlined">
            <InputLabel id="payment-method-label">Payment Method</InputLabel>
            <Select
              id="pay-bill-payment-method"
              labelId="payment-method-label"
              value={selectedPaymentMethod}
              label="Payment Method"
              onChange={(e) => setSelectedPaymentMethod(e.target.value)}
            >
              {/* Bank Accounts */}
              {userData?.map((account: any) => (
                <MenuItem key={account.account_type} value={account.account_type}>
                  {account.account_type.charAt(0).toUpperCase() + account.account_type.slice(1)} •••• {account.routing_number.slice(-4)}
                </MenuItem>
              ))}

              {/* Credit/Debit Cards */}
              {savedCards.map((card) => (
                <MenuItem key={card.id} value={card.id}>
                  {formatCardBrand(card.brand)} •••• {card.last4}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        )}

        <Button
          id="pay-bill-submit-btn"
          type="submit"
          variant="contained"
          color="primary"
          fullWidth
          disabled={isLoading}
          sx={{ py: 1.5 }}
        >
          {isLoading ? (
            <>
              <CircularProgress size={20} sx={{ mr: 1 }} color="inherit" />
              Processing...
            </>
          ) : (
            'Pay Bill'
          )}
        </Button>
      </Box>
    </Card>
  );
};
