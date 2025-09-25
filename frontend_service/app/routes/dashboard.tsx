import { useState, createContext, useContext, useEffect } from 'react';
import { Link, useLocation, useParams, useNavigate, useLoaderData } from 'react-router-dom';
import {
  Box,
  CssBaseline,
  ThemeProvider,
  createTheme,
  Typography,
  Grid,
  Paper,
  Divider,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Avatar,
  IconButton,
  Tooltip,
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
  CircularProgress
} from '@mui/material';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import DashboardIcon from '@mui/icons-material/Dashboard';
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet';
import SettingsIcon from '@mui/icons-material/Settings';
import NotificationsIcon from '@mui/icons-material/Notifications';
import PersonIcon from '@mui/icons-material/Person';
import CreditCardIcon from '@mui/icons-material/CreditCard';
import BusinessIcon from '@mui/icons-material/Business';
import MonetizationOnIcon from '@mui/icons-material/MonetizationOn';
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward';
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import AttachMoneyIcon from '@mui/icons-material/AttachMoney';
import CalendarMonthIcon from '@mui/icons-material/CalendarMonth';
import { LoginContext } from '../root';


// This is the loader function for the dashboard route. It will be called by React Router
// and its data will be available to the DashboardPage component via useLoaderData.
export const loader = async () => {
  const mockSummaryData = {
    totalBalance: 12500.75,
    checking: 8500.25,
    savings: 4000.25,
  };

  const mockTransactions = [
    { id: 1, name: "Amazon", date: "2023-10-25", amount: -54.99, accountId: 'checking', type: 'debit' },
    { id: 2, name: "Paycheck", date: "2023-10-24", amount: 2500.00, accountId: 'checking', type: 'credit' },
    { id: 3, name: "Starbucks", date: "2023-10-23", amount: -5.75, accountId: 'checking', type: 'debit' },
    { id: 4, name: "Spotify", date: "2023-10-22", amount: -10.99, accountId: 'checking', type: 'debit' },
    { id: 5, name: "Grocery Store", date: "2023-10-21", amount: -120.50, accountId: 'checking', type: 'debit' },
    { id: 6, name: "Deposit", date: "2023-10-20", amount: 1000.00, accountId: 'savings', type: 'credit' },
    { id: 7, name: "Transfer to Checking", date: "2023-10-19", amount: -200.00, accountId: 'savings', type: 'debit' },
    { id: 8, name: "Interest", date: "2023-10-18", amount: 0.25, accountId: 'savings', type: 'credit' },
    { id: 9, name: "Gas Station", date: "2023-10-17", amount: -45.00, accountId: 'checking', type: 'debit' },
  ];

  const mockSpendingData = [
    { name: 'Jan', value: 4000 },
    { name: 'Feb', value: 3000 },
    { name: 'Mar', value: 2000 },
    { name: 'Apr', value: 2780 },
    { name: 'May', value: 1890 },
    { name: 'Jun', value: 2390 },
    { name: 'Jul', value: 3490 },
  ];

  const mockPieData = [
    { name: 'Shopping', value: 300, color: '#f87171' },
    { name: 'Food', value: 200, color: '#facc15' },
    { name: 'Groceries', value: 150, color: '#34d399' },
    { name: 'Utilities', value: 100, color: '#60a5fa' },
    { name: 'Other', value: 50, color: '#c084fc' },
  ];

  // Simulate a network delay
  await new Promise(resolve => setTimeout(resolve, 1000));

  return {
    summaryData: mockSummaryData,
    transactions: mockTransactions,
    spendingData: mockSpendingData,
    pieData: mockPieData,
  };
};

// Overview Card component
const OverviewCard = ({ title, value, icon, info }) => (
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
    <CardContent sx={{ minHeight: '80px' }}>
      <Typography variant="h4" sx={{ fontWeight: 'bold' }}>
        ${value.toFixed(2)}
      </Typography>
      {info && (
        <Typography variant="body2" sx={{ color: 'text.secondary', mt: 1 }}>
          {info}
        </Typography>
      )}
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
const DashboardPage = () => {
  const loaderData = useLoaderData();
  const [userData, setUserData] = useState(null);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const storedUserData = sessionStorage.getItem('userData');
      if (storedUserData) {
        setUserData(JSON.parse(storedUserData));
      }
    }
  }, []);

  if (!userData || !loaderData) {
    return <CircularProgress />;
  }

  const { summaryData, spendingData, transactions, pieData } = loaderData;
  const checkingAccount = userData.find(acc => acc.account_type === 'checking');
  const savingsAccount = userData.find(acc => acc.account_type === 'savings');

  const totalBalance = (checkingAccount?.balance || 0) + (savingsAccount?.balance || 0);
  const checkingBalance = checkingAccount?.balance || 0;
  const savingsBalance = savingsAccount?.balance || 0;
  const checkingRouting = checkingAccount?.routing_number || 'Not available';
  const savingsRouting = savingsAccount?.routing_number || 'Not available';

  return (
    <Box sx={{ flexGrow: 1, p: 3 }}>
      <Grid container spacing={4}>
        {/* Overview Cards */}
        <Grid size={{ xs: 12, md: 4 }}>
          <OverviewCard
            title="Total Balance"
            value={totalBalance}
            icon={<MonetizationOnIcon color="disabled" />}
            info="&nbsp;"
          />
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <OverviewCard
            title="Checking"
            value={checkingBalance}
            icon={<CreditCardIcon color="disabled" />}
            info={`Routing: ${checkingRouting}`}
          />
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <OverviewCard
            title="Savings"
            value={savingsBalance}
            icon={<AccountBalanceWalletIcon color="disabled" />}
            info={`Routing: ${savingsRouting}`}
          />
        </Grid>

        {/* Spending Chart */}
        <Grid item size={{ xs: 12, md: 6 }}>
          <SpendingChart data={loaderData.spendingData} />
        </Grid>

        {/* Spending Categories Pie Chart */}
        <Grid item size={{ xs: 12, md: 6 }}>
          <SpendingCategories data={loaderData.pieData} />
        </Grid>

        {/* Recent Transactions */}
        <Grid item size={{ xs: 12 }}>
          <RecentTransactions transactions={loaderData.transactions.filter(tx => ['checking', 'savings'].includes(tx.accountId))} />
        </Grid>
      </Grid>
    </Box>
  );
};

export default DashboardPage;
