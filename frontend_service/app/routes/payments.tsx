import { useContext } from 'react';
import { LoginContext } from '~/root';
import { Box, Typography, Grid } from '@mui/material';
import { PayBillCard } from '~/components/payments/PayBillCard';
import { RecurringPaymentsCard } from '~/components/payments/RecurringPaymentsCard';
import { PaymentMethodsCard } from '~/components/payments/PaymentMethodsCard';
import { RecentPaymentsCard } from '~/components/payments/RecentPaymentsCard';

// Main Payments Page Component
const PaymentsPage = () => {
  const { userData } = useContext(LoginContext);

  return (
    <Box sx={{ flexGrow: 1 }}>
      {/* Hero Section */}
      <Box sx={{
        bgcolor: 'white',
        py: 2,
        mb: 3
      }}>
        <Box sx={{ px: 32 }}>
          <Typography variant="h4" component="h1" gutterBottom>
            Bill Pay & Payments
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Manage your bills, set up recurring payments, and track your payment history
          </Typography>
        </Box>
      </Box>

      {/* Main Content */}
      <Box sx={{ px: 32, pb: 3 }}>
        <Grid container spacing={4}>

          {/* Row 1: Pay Bill Card + Payment Methods (6-6) */}
          <Grid item size={{ xs: 12, md: 6 }}>
            <PayBillCard />
          </Grid>

          <Grid item size={{ xs: 12, md: 6 }}>
            <PaymentMethodsCard />
          </Grid>

          {/* Row 2: Recurring Payments (12 - full width) */}
          <Grid item size={{ xs: 12 }}>
            <RecurringPaymentsCard />
          </Grid>

          {/* Row 3: Recent Payments (12 - full width) */}
          <Grid item size={{ xs: 12 }}>
            <RecentPaymentsCard />
          </Grid>

        </Grid>
      </Box>
    </Box>
  );
};

export default PaymentsPage;
