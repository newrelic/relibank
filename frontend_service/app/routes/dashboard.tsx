import { useState, createContext, useContext, useEffect } from 'react';
import { Link, useLocation, useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Card,
  CardHeader,
  CardContent,
  TableContainer,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  Button,
  Skeleton,
  Typography,
  Grid,
  Paper,
  IconButton,
} from '@mui/material';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import CreditCardIcon from '@mui/icons-material/CreditCard';
import MonetizationOnIcon from '@mui/icons-material/MonetizationOn';
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward';
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import { PageContext } from "../root"; // Re-import PageContext from root

// Overview Card component
const OverviewCard = ({ title, value, icon }) => (
  <Card sx={{
    display: 'flex',
    flexDirection: 'column',
    borderRadius: '12px',
    border: '1px solid #e5e7eb',
    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)'
  }}>
    <CardHeader
      title={<Typography variant="subtitle1" sx={{ fontWeight: 'medium', fontSize: '0.875rem' }}>{title}</Typography>}
      action={icon}
      sx={{ pb: 1, pt: 2, pr: 2 }}
    />
    <CardContent>
      <Typography variant="h4" sx={{ fontWeight: 'bold' }}>
        ${value.toFixed(2)}
      </Typography>
    </CardContent>
  </Card>
);

// Spending Chart Card component
const SpendingChart = ({ data }) => (
  <Card sx={{ p: 3 }}>
    <Typography variant="h6" sx={{ mb: 2 }}>Spending over last 6 months</Typography>
    <Box sx={{ height: 300 }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="name" />
          <YAxis />
          <RechartsTooltip />
          <Legend />
          <Line type="monotone" dataKey="value" stroke="#8884d8" activeDot={{ r: 8 }} />
        </LineChart>
      </ResponsiveContainer>
    </Box>
  </Card>
);

// Recent Transactions component
const RecentTransactions = ({ transactions }) => {
  const [showAll, setShowAll] = useState(false);
  const displayTransactions = showAll ? transactions : transactions.slice(0, 3);
  return (
    <Card sx={{ p: 3 }}>
      <Typography variant="h6" sx={{ mb: 2 }}>Recent Transactions</Typography>
      <TableContainer>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontWeight: 'bold' }}>Transaction</TableCell>
              <TableCell sx={{ fontWeight: 'bold' }}>Date</TableCell>
              <TableCell align="right" sx={{ fontWeight: 'bold' }}>Amount</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {displayTransactions.map((tx) => (
              <TableRow key={tx.id}>
                <TableCell>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Box sx={{ p: 1, bgcolor: '#f3f4f6', borderRadius: '50%' }}>
                      {tx.amount > 0 ? <ArrowUpwardIcon color="success" /> : <ArrowDownwardIcon color="error" />}
                    </Box>
                    <Typography variant="body1" sx={{ fontWeight: 'medium' }}>{tx.name}</Typography>
                  </Box>
                </TableCell>
                <TableCell>
                  <Typography variant="body2" sx={{ color: 'text.secondary' }}>{tx.date}</Typography>
                </TableCell>
                <TableCell align="right">
                  <Typography variant="body1" sx={{ fontWeight: 'medium', color: tx.amount > 0 ? 'success.main' : 'error.main' }}>
                    {tx.amount > 0 ? '+' : ''}${Math.abs(tx.amount).toFixed(2)}
                  </Typography>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      {transactions.length > 3 && (
        <Box sx={{ textAlign: 'center', mt: 2 }}>
          <Button
            onClick={() => setShowAll(!showAll)}
            endIcon={showAll ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          >
            {showAll ? 'Show Less' : 'Show All'}
          </Button>
        </Box>
      )}
    </Card>
  );
};

// Spending Categories Chart
const SpendingCategories = ({ data }) => (
  <Card sx={{ p: 3 }}>
    <Typography variant="h6" sx={{ mb: 2 }}>Spending over last 6 months</Typography>
    <Box sx={{ height: 300 }}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            labelLine={false}
            outerRadius={100}
            dataKey="value"
            label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <RechartsTooltip />
        </PieChart>
      </ResponsiveContainer>
    </Box>
  </Card>
);

// Dashboard Page
export const DashboardPage = () => {
  const { summaryData, spendingData, mockTransactions, pieData } = useContext(PageContext);

  if (!summaryData) {
    return (
      <Box sx={{ flexGrow: 1, p: 3 }}>
        <Typography variant="h6">Data not available.</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ flexGrow: 1, p: 3 }}>
      <Grid container spacing={4}>
        {/* Overview Cards */}
        <Grid item size={{ xs: 12, md: 4 }}>
          <OverviewCard
            title="Total Balance"
            value={summaryData.totalBalance}
            icon={<MonetizationOnIcon color="disabled" />}
          />
        </Grid>
        <Grid item size={{ xs: 12, md: 4 }}>
          <OverviewCard
            title="Checking"
            value={summaryData.checking}
            icon={<CreditCardIcon color="disabled" />}
          />
        </Grid>
        <Grid item size={{ xs: 12, md: 4 }}>
          <OverviewCard
            title="Savings"
            value={summaryData.savings}
            icon={<MonetizationOnIcon color="disabled" />}
          />
        </Grid>

        {/* Charts */}
        <Grid item size={{ xs: 12, md: 6 }}>
          <SpendingChart data={spendingData} />
        </Grid>

        <Grid item size={{ xs: 12, md: 6 }}>
          <SpendingCategories data={pieData} />
        </Grid>

        {/* Recent Transactions */}
        <Grid item size={{ xs: 12 }}>
          <RecentTransactions transactions={mockTransactions.filter(tx => ['checking', 'savings'].includes(tx.accountId))} />
        </Grid>
      </Grid>
    </Box>
  );
};

// Accounts Page
export const AccountsPage = () => {
  const { mockAccounts } = useContext(PageContext);

  if (!mockAccounts) {
    return (
      <Box sx={{ flexGrow: 1, p: 3 }}>
        <Typography variant="h6">Data not available.</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ flexGrow: 1, p: 3 }}>
      <Typography variant="h4" sx={{ fontWeight: 'bold', mb: 2 }}>Your Accounts</Typography>
      <Grid container spacing={2}>
        {mockAccounts.map((account) => (
          <Grid item size={{ xs: 12, sm: 6, md: 4 }} key={account.id}>
            <Card>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="center">
                  <Box>
                    <Typography variant="h6">{account.name}</Typography>
                    <Typography variant="subtitle2" color="text.secondary">{account.number}</Typography>
                  </Box>
                  <MonetizationOnIcon sx={{ color: 'primary.main', fontSize: 40 }} />
                </Box>
                <Typography variant="h5" sx={{ my: 2 }}>${account.balance.toFixed(2)}</Typography>
                <Button
                  component={Link}
                  to={`/accounts/${account.id}`}
                  variant="contained"
                  fullWidth
                >
                  View Details
                </Button>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
};

// Account Details Page
export const AccountDetailsPage = () => {
  const { accountId } = useParams();
  const navigate = useNavigate();
  const { mockAccounts, mockTransactions } = useContext(PageContext);

  const account = mockAccounts.find(acc => acc.id === accountId);
  const transactions = mockTransactions.filter(tx => tx.accountId === accountId);

  if (!account || !transactions) {
    return (
      <Box sx={{ flexGrow: 1, p: 3 }}>
        <Typography variant="h6">Account not found or data not available.</Typography>
        <Button onClick={() => navigate('/accounts')} startIcon={<ArrowBackIcon />}>
          Back to Accounts
        </Button>
      </Box>
    );
  }

  return (
    <Box sx={{ flexGrow: 1, p: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <IconButton onClick={() => navigate('/accounts')}>
          <ArrowBackIcon />
        </IconButton>
        <Typography variant="h4" sx={{ fontWeight: 'bold', ml: 1 }}>{account.name}</Typography>
      </Box>
      <Grid container spacing={3} mb={3}>
        <Grid item size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="subtitle1" color="text.secondary">Current Balance</Typography>
              <Typography variant="h3" sx={{ fontWeight: 'bold' }}>${account.balance.toFixed(2)}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="subtitle1" color="text.secondary">Account Number</Typography>
              <Typography variant="h4" sx={{ fontWeight: 'bold' }}>{account.number}</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
      <Paper sx={{ p: 3 }}>
        <Typography variant="h5" sx={{ fontWeight: 'bold', mb: 2 }}>All Transactions</Typography>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 'bold' }}>Date</TableCell>
                <TableCell sx={{ fontWeight: 'bold' }}>Description</TableCell>
                <TableCell align="right" sx={{ fontWeight: 'bold' }}>Amount</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {transactions.map((tx) => (
                <TableRow key={tx.id}>
                  <TableCell>{tx.date}</TableCell>
                  <TableCell>{tx.name}</TableCell>
                  <TableCell align="right">
                    <Typography variant="body1" sx={{ fontWeight: 'medium', color: tx.amount > 0 ? 'success.main' : 'error.main' }}>
                      {tx.amount > 0 ? '+' : ''}${Math.abs(tx.amount).toFixed(2)}
                    </Typography>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>
    </Box>
  );
};

// Settings Page (placeholder)
export const SettingsPage = () => (
  <Box sx={{ flexGrow: 1, p: 3 }}>
    <Typography variant="h4" sx={{ fontWeight: 'bold', mb: 2 }}>Settings</Typography>
    <Paper sx={{ p: 3 }}>
      <Typography>This is a placeholder for the Settings page.</Typography>
    </Paper>
  </Box>
);

export default DashboardPage;
