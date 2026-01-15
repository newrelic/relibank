import { useState, useEffect, useContext } from 'react';
import { LoginContext } from '~/root';
import {
  Box,
  Typography,
  Card,
  Button,
  Alert,
  Chip,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Collapse,
} from '@mui/material';
import {
  CreditCard as CreditCardIcon,
  Add as AddIcon,
  AccountBalance as AccountBalanceIcon,
} from '@mui/icons-material';

interface PaymentMethod {
  id: string;
  brand: string;
  last4: string;
  expMonth: number;
  expYear: number;
}

interface BankAccount {
  account_type: string;
  balance: number;
  routing_number: string;
  name?: string;
}

export const PaymentMethodsCard = () => {
  const { userData } = useContext(LoginContext);
  const [methods, setMethods] = useState<PaymentMethod[]>([]);
  const [customerId, setCustomerId] = useState<string>('');
  const [showAddForm, setShowAddForm] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isAdding, setIsAdding] = useState(false);
  const [message, setMessage] = useState('');
  const [isError, setIsError] = useState(false);

  // Form state (pre-filled with test card)
  const [selectedCard, setSelectedCard] = useState('pm_card_mastercard');

  const testCards = [
    { value: 'pm_card_visa', label: 'Visa Test Card' },
    { value: 'pm_card_mastercard', label: 'Mastercard Test Card' },
    { value: 'pm_card_amex', label: 'American Express Test Card' },
  ];

  // Fetch payment methods on mount
  useEffect(() => {
    fetchPaymentMethods();
  }, []);

  const fetchPaymentMethods = async () => {
    try {
      setIsLoading(true);

      // TODO: Get customer ID dynamically from backend
      // For now, hardcode Alice's customer ID since it's created on service startup
      // In production, we'd need an endpoint to lookup customer by email
      const aliceCustomerId = 'cus_TkCwwRJbjMVQZ4';
      setCustomerId(aliceCustomerId);

      const response = await fetch(`/bill-pay-service/payment-methods/${aliceCustomerId}`);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || data.message || 'Failed to fetch payment methods');
      }

      setMethods(data.paymentMethods || []);
    } catch (error: any) {
      console.error('Error fetching payment methods:', error);
      setIsError(true);
      setMessage('Failed to load payment methods. Using demo data.');
      // Fall back to empty array on error
      setMethods([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAddPaymentMethod = async (event: React.FormEvent) => {
    event.preventDefault();
    setMessage('');
    setIsError(false);
    setIsAdding(true);

    try {
      const response = await fetch('/bill-pay-service/payment-method', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          paymentMethodToken: selectedCard,
          customerEmail: 'alice.j@relibank.com',
          customerId: customerId || undefined,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || data.message || 'Failed to add payment method');
      }

      // Update customer ID if we got it back
      if (data.customerId) {
        setCustomerId(data.customerId);
      }

      // Success - refresh the list
      setIsError(false);
      setMessage(`${data.cardBrand} ending in ${data.cardLast4} added successfully!`);
      setShowAddForm(false);

      // Refresh payment methods list
      await fetchPaymentMethods();

      // Reset form
      setSelectedCard('pm_card_mastercard');
    } catch (error: any) {
      setIsError(true);
      setMessage(error.message || 'Failed to add payment method. Please try again.');
      console.error('Add payment method error:', error);
    } finally {
      setIsAdding(false);
    }
  };

  const getCardIcon = () => {
    return <CreditCardIcon />;
  };

  const getBankIcon = () => {
    return <AccountBalanceIcon />;
  };

  const formatCardBrand = (brand: string) => {
    return brand.charAt(0).toUpperCase() + brand.slice(1);
  };

  const formatAccountType = (type: string) => {
    return type.charAt(0).toUpperCase() + type.slice(1) + ' Account';
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
          <CreditCardIcon color="primary" sx={{ mr: 1 }} />
          <Typography variant="h6">Payment Methods</Typography>
        </Box>
        <Button
          id="payment-method-add-card-btn"
          variant="outlined"
          size="small"
          startIcon={<AddIcon />}
          onClick={() => setShowAddForm(!showAddForm)}
        >
          {showAddForm ? 'Cancel' : 'Add Card'}
        </Button>
      </Box>

      {message && (
        <Alert severity={isError ? "error" : "success"} sx={{ mb: 2 }} onClose={() => setMessage('')}>
          {message}
        </Alert>
      )}

      <Collapse in={showAddForm}>
        <Box component="form" onSubmit={handleAddPaymentMethod} sx={{ mb: 3, p: 2, bgcolor: '#f9fafb', borderRadius: '8px' }}>
          <Typography variant="subtitle2" sx={{ mb: 2, fontWeight: 'bold' }}>
            Add Test Payment Card
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <FormControl fullWidth variant="outlined" size="small">
              <InputLabel id="test-card-label">Select Test Card</InputLabel>
              <Select
                id="payment-method-card-select"
                labelId="test-card-label"
                value={selectedCard}
                label="Select Test Card"
                onChange={(e) => setSelectedCard(e.target.value)}
              >
                {testCards.map((card) => (
                  <MenuItem key={card.value} value={card.value}>
                    {card.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <Alert severity="info" sx={{ fontSize: '0.875rem' }}>
              These are Stripe test cards for demo purposes
            </Alert>

            <Button
              id="payment-method-submit-btn"
              type="submit"
              variant="contained"
              color="primary"
              disabled={isAdding}
              sx={{ py: 1 }}
            >
              {isAdding ? (
                <>
                  <CircularProgress size={18} sx={{ mr: 1 }} color="inherit" />
                  Adding...
                </>
              ) : (
                'Add Payment Method'
              )}
            </Button>
          </Box>
        </Box>
      </Collapse>

      {isLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress />
        </Box>
      ) : (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {/* Bank Accounts */}
          {userData?.map((account: BankAccount) => (
            <Card key={account.routing_number} variant="outlined" sx={{ p: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  {getBankIcon()}
                  <Box>
                    <Typography variant="body1" sx={{ fontWeight: 'medium' }}>
                      {formatAccountType(account.account_type)} •••• {account.routing_number.slice(-4)}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Balance: ${account.balance.toFixed(2)}
                    </Typography>
                  </Box>
                </Box>
                <Chip label="Bank Account" size="small" color="success" variant="outlined" />
              </Box>
            </Card>
          ))}

          {/* Stripe Cards */}
          {methods.map((method) => (
            <Card key={method.id} variant="outlined" sx={{ p: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  {getCardIcon()}
                  <Box>
                    <Typography variant="body1" sx={{ fontWeight: 'medium' }}>
                      {formatCardBrand(method.brand)} •••• {method.last4}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Expires {String(method.expMonth).padStart(2, '0')}/{method.expYear}
                    </Typography>
                  </Box>
                </Box>
                <Chip label="Stripe Test" size="small" color="primary" variant="outlined" />
              </Box>
            </Card>
          ))}
        </Box>
      )}

      {!isLoading && methods.length === 0 && !userData?.length && (
        <Box sx={{ textAlign: 'center', py: 4 }}>
          <Typography variant="body2" color="text.secondary">
            No payment methods saved yet
          </Typography>
        </Box>
      )}
    </Card>
  );
};
