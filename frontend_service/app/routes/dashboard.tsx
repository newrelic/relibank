import { useState, useContext, useEffect } from 'react';
import { Link } from 'react-router-dom';
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
  CircularProgress,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Alert,
  InputAdornment
} from '@mui/material';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import {
    Dashboard as DashboardIcon,
    AccountBalanceWallet as AccountBalanceWalletIcon,
    Settings as SettingsIcon,
    Notifications as NotificationsIcon,
    Person as PersonIcon,
    CreditCard as CreditCardIcon,
    Business as BusinessIcon,
    MonetizationOn as MonetizationOnIcon,
    ArrowUpward as ArrowUpwardIcon,
    ArrowDownward as ArrowDownwardIcon,
    ExpandMore as ExpandMoreIcon,
    ExpandLess as ExpandLessIcon,
    ArrowBack as ArrowBackIcon,
    AttachMoney as AttachMoneyIcon,
    CalendarMonth as CalendarMonthIcon
} from '@mui/icons-material';
import { LoginContext } from '~/root';
import { TransferCard } from '~/components/dashboard/TransferCard';

// --- MOCK APPLICATION DATA (Replaces Loader) ---

const mockSummaryData = {
    totalBalance: 12500.75,
    checking: 8500.25,
    savings: 4000.25,
};

// NOTE: This array is now only for initial state and must be imported by useState below
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

// --- MOCK USER ACCOUNT DATA (Used for calculations and initial display) ---
const demoUserData = [
  { account_type: 'checking', balance: 8500.25, routing_number: '123456789' },
  { account_type: 'savings', balance: 4000.25, routing_number: '987654321' },
];


// Overview Card component
const OverviewCard = ({ title, value, icon, info }) => (
  <Card sx={{
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    borderRadius: '12px',
    border: '1px solid #e5e7eb',
    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)'
  }}>
    <CardHeader
      avatar={icon}
      title={<Typography variant="subtitle1" sx={{ fontWeight: 'medium', fontSize: '0.875rem' }}>{title}</Typography>}
      sx={{ pb: 1, pt: 2, pl: 2 }}
    />
    <CardContent sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
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
  <Card sx={{ p: 3, height: '100%', display: 'flex', flexDirection: 'column' }}>
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
  // Use filter on the passed transactions prop which is now stateful
  const filteredTransactions = transactions.filter(tx => ['checking', 'savings'].includes(tx.accountId)); 
  const displayTransactions = showAll ? filteredTransactions : filteredTransactions.slice(0, 3);
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
      {filteredTransactions.length > 3 && (
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
  <Card sx={{ p: 3, height: '100%', display: 'flex', flexDirection: 'column' }}>
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

// TransferCard component now imported from ~/components/dashboard/TransferCard

// Dashboard Page
const DashboardPage = () => {
  // Get userData from LoginContext instead of loading from sessionStorage
  const { userData: contextUserData, setUserData: contextSetUserData } = useContext(LoginContext);
  // Use demo data as fallback if not logged in (for development/demo purposes)
  const userData = contextUserData || demoUserData;
  const setUserData = contextSetUserData;

  const [additionalAccountData, setAdditionalAccountData] = useState(null);
  // NEW: Add transactions to state to allow updates from the TransferCard
  const [transactions, setTransactions] = useState(mockTransactions);
  // NEW: Loading state for the additional, client-side fetch
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);

  // 2. Secondary Fetch: Get additional account details after initial data is set
  useEffect(() => {
    // Only run if userData is available AND we haven't fetched the additional data yet
    if (userData && !additionalAccountData && !isLoadingDetails) {
        const fetchAccountDetails = async () => {
            setIsLoadingDetails(true); // START loading
            console.log('Simulating fetch for detailed account information with user data:', userData);

            const primaryAccountId = userData.find(acc => acc.account_type === 'checking')?.routing_number || '123456789';

            try {
                // --- Placeholder API Simulation: Delayed fetch to demonstrate re-rendering ---
                await new Promise(resolve => setTimeout(resolve, 1500)); 

                const mockDetailedData = {
                    '123456789': { 
                        checking: {
                            lastDeposit: '2023-10-24', 
                            interestRate: '0.05%'
                        },
                        savings: {
                            maturityDate: '2024-06-01', 
                            interestRate: '4.10%' 
                        }
                    }
                };
                
                const fetchedData = mockDetailedData[primaryAccountId] || {};
                
                setAdditionalAccountData(fetchedData);
                console.log('Fetched detailed account information:', fetchedData);
            } catch (error) {
                console.error("Error fetching additional details:", error);
            } finally {
                setIsLoadingDetails(false); // END loading
            }
        };

        fetchAccountDetails();
    }
  }, [userData, additionalAccountData, isLoadingDetails]); 

  // Data sourcing for the whole component
  const appData = {
      // summaryData: mockSummaryData, // Not needed since balance is calculated from userData state
      transactions: transactions, // Use state instead of mockTransactions constant
      spendingData: mockSpendingData,
      pieData: mockPieData,
  };

  if (!userData) { 
    return <CircularProgress />;
  }

  const { spendingData, pieData } = appData;
  const checkingAccount = userData.find(acc => acc.account_type === 'checking');
  const savingsAccount = userData.find(acc => acc.account_type === 'savings');

  const totalBalance = (checkingAccount?.balance || 0) + (savingsAccount?.balance || 0);
  const checkingBalance = checkingAccount?.balance || 0;
  const savingsBalance = savingsAccount?.balance || 0;
  
  const checkingRouting = checkingAccount?.routing_number || 'Not available';
  const savingsRouting = savingsAccount?.routing_number || 'Not available';

  // Logic to display loading message or fetched details
  const checkingExtraInfo = isLoadingDetails ? 
    `Routing: ${checkingRouting} (Loading details...)` :
    (additionalAccountData?.checking?.lastDeposit ? 
        `Routing: ${checkingRouting} | Last Deposit: ${additionalAccountData.checking.lastDeposit}` : 
        `Routing: ${checkingRouting}`
    );
    
  const savingsExtraInfo = isLoadingDetails ? 
    `Routing: ${savingsRouting} (Loading details...)` :
    (additionalAccountData?.savings?.interestRate ? 
        `Routing: ${savingsRouting} | Interest: ${additionalAccountData.savings.interestRate}` : 
        `Routing: ${savingsRouting}`
    );


  return (
    <Box sx={{ flexGrow: 1, p: 3 }}>
      <Grid container spacing={4}>
        {/* Overview Cards (3-column layout on medium screens and up) */}
        <Grid item size={{ xs:12, md: 4}}>
          <OverviewCard
            title="Total Balance"
            value={totalBalance}
            icon={<MonetizationOnIcon color="disabled" />}
            info=""
          />
        </Grid>
        <Grid item size={{ xs:12, md: 4}}>
          <OverviewCard
            title="Checking"
            value={checkingBalance}
            icon={<CreditCardIcon color="disabled" />}
            info={checkingExtraInfo}
          />
        </Grid>
        <Grid item size={{ xs:12, md: 4}}>
          <OverviewCard
            title="Savings"
            value={savingsBalance}
            icon={<AccountBalanceWalletIcon color="disabled" />}
            info={savingsExtraInfo}
          />
        </Grid>
        
        {/* Transfer Card (Full width) */}
        <Grid item size={{ xs: 12 }}>
            <TransferCard
                transactions={transactions}
                setTransactions={setTransactions}
            />
        </Grid>

        {/* Spending Chart (2-column layout on medium screens and up) */}
        <Grid item size={{ xs: 12, md: 6 }}>
          <SpendingChart data={appData.spendingData} />
        </Grid>

        {/* Spending Categories Pie Chart (2-column layout on medium screens and up) */}
        <Grid item size={{ xs: 12, md: 6 }}>
          <SpendingCategories data={appData.pieData} />
        </Grid>

        {/* Recent Transactions (full width) */}
        <Grid item size={{ xs: 12}}>
          <RecentTransactions transactions={appData.transactions} />
        </Grid>
      </Grid>
    </Box>
  );
};

export default DashboardPage;
