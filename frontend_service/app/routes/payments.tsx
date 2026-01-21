import { useContext, useState } from 'react';
import { LoginContext } from '~/root';
import { Box, Typography, Grid } from '@mui/material';
import { PayBillCard } from '~/components/payments/PayBillCard';
import { RecurringPaymentsCard } from '~/components/payments/RecurringPaymentsCard';
import { PaymentMethodsCard } from '~/components/payments/PaymentMethodsCard';
import { RecentPaymentsCard } from '~/components/payments/RecentPaymentsCard';

// Main Payments Page Component
const PaymentsPage = () => {
  const { userData } = useContext(LoginContext);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  // Callback to trigger refresh of recent payments
  const handlePaymentSuccess = () => {
    setRefreshTrigger(prev => prev + 1);
  };

  return (
    <Box sx={{ flexGrow: 1 }}>
      {/* Hero Section */}
      <Box sx={{
        background: 'linear-gradient(135deg, #fef7e9 0%, #fffcf7 50%, #ffffff 100%)',
        py: 2,
        mb: 3
      }}>
        <Box sx={{ px: { xs: 2, sm: 4, md: 8, lg: 16, xl: 32 } }}>
          <Typography variant="h4" component="h1" gutterBottom sx={{ fontSize: { xs: '1.75rem', sm: '2rem', md: '2.125rem' } }}>
            Bill Pay & Payments
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ fontSize: { xs: '0.875rem', sm: '1rem' } }}>
            Manage your bills, set up recurring payments, and track your payment history
          </Typography>
        </Box>
      </Box>

      {/* Main Content */}
      <Box sx={{ px: { xs: 2, sm: 4, md: 8, lg: 16, xl: 32 }, pb: 3 }}>
        <Grid container spacing={{ xs: 2, sm: 3, md: 4 }}>

          {/* Row 1: Pay Bill Card + Payment Methods (6-6) */}
          <Grid item size={{ xs: 12, lg: 6 }} sx={{ height: { xs: 'auto', lg: '500px' } }}>
            <PayBillCard onPaymentSuccess={handlePaymentSuccess} />
          </Grid>

          <Grid item size={{ xs: 12, lg: 6 }} sx={{ height: { xs: 'auto', lg: '500px' } }}>
            <PaymentMethodsCard />
          </Grid>

          {/* Row 2: Recurring Payments (12 - full width) */}
          <Grid item size={{ xs: 12 }}>
            <RecurringPaymentsCard />
          </Grid>

          {/* Row 3: Recent Payments (12 - full width) */}
          <Grid item size={{ xs: 12 }}>
            <RecentPaymentsCard refreshTrigger={refreshTrigger} />
          </Grid>

        </Grid>
      </Box>
    </Box>
  );
};

export default PaymentsPage;
