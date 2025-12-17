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

// --- NEW MONEY TRANSFER CARD COMPONENT ---
const TransferCard = ({ userData, setUserData, transactions, setTransactions }) => {
  const [fromAccount, setFromAccount] = useState('checking');
  const [toAccount, setToAccount] = useState('savings');
  const [amount, setAmount] = useState('');
  const [message, setMessage] = useState('');
  const [isError, setIsError] = useState(false);

  const checking = userData.find(acc => acc.account_type === 'checking');
  const savings = userData.find(acc => acc.account_type === 'savings');
  
  // Guard clause in case accounts are missing (e.g. initial load error)
  if (!checking || !savings) {
    return (
      <Card sx={{ p: 3 }}>
        <Typography variant="h6">Transfer Funds</Typography>
        <Alert severity="warning" sx={{ mt: 2 }}>Account data is not available for transfers.</Alert>
      </Card>
    );
  }

  const handleTransfer = async (event) => {
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

    const sourceAccount = fromAccount === 'checking' ? checking : savings;

    if (transferAmount > sourceAccount.balance) {
      const errorDetails = {
        accountType: sourceAccount.account_type,
        requestedAmount: transferAmount,
        availableBalance: sourceAccount.balance
      };

      console.error('Transfer failed: Insufficient funds', errorDetails);

      // Report error to New Relic Browser
      if (typeof window !== 'undefined' && window.newrelic) {
        window.newrelic.noticeError(
          new Error(`Insufficient funds in ${sourceAccount.account_type} account`),
          errorDetails
        );
      }

      setIsError(true);
      setMessage(`Insufficient funds in ${sourceAccount.account_type} account.`);
      return;
    }

    // ==========================================================
    try {
        const response = await fetch('/bill-pay-service/recurring', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                "billId": "BILL-RECUR-002",
                "amount": 150.00,
                "currency": "EUR",
                "fromAccountId": 12345,
                "toAccountId": 56789,
                "frequency": "monthly",
                "startDate": "2025-08-01"
            }),
        });

        if (!response.ok) {
            // Note: In a real app, you would read the error message from the response body.
            // For this hardcoded example, we'll just throw a generic error for the catch block.
            throw new Error(`API returned status ${response.status}`);
        }

        // Simulate a small delay for network call effect
        await new Promise(resolve => setTimeout(resolve, 500));

    } catch (error) {
        console.error('Transfer API error:', error);

        // Report API error to New Relic Browser
        if (typeof window !== 'undefined' && window.newrelic) {
          window.newrelic.noticeError(error, {
            component: 'TransferFunds',
            endpoint: '/bill-pay-service/recurring',
            amount: transferAmount,
            fromAccount: fromAccount,
            toAccount: toAccount
          });
        }

        // We'll proceed with the mock UI update for demo purposes even if the API fails,
        // but set a warning message. In a real app, you'd halt execution here.
        setIsError(true);
        setMessage(`API Warning: The transfer logic executed, but the call to /recurring failed or returned an error: ${error.message}`);
        // return; // Uncomment this in a production app to stop the transfer
    }
    // ==========================================================


    // Perform the mock transfer (This logic runs after the simulated API call)
    const newCheckingBalance = fromAccount === 'checking' ? checking.balance - transferAmount : checking.balance + transferAmount;
    const newSavingsBalance = fromAccount === 'savings' ? savings.balance - transferAmount : savings.balance + transferAmount;
    
    const newUserData = userData.map(acc => {
      if (acc.account_type === 'checking') {
        // Ensure not to introduce negative zero
        return { ...acc, balance: parseFloat(newCheckingBalance.toFixed(2)) };
      }
      if (acc.account_type === 'savings') {
        return { ...acc, balance: parseFloat(newSavingsBalance.toFixed(2)) };
      }
      return acc;
    });

    // Update parent user state
    setUserData(newUserData);
    
    // Create new mock transactions for the list
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
    
    // Update parent transactions state to show new transactions first
    setTransactions([newSourceTx, newTargetTx, ...transactions]);

    // Only show success if no error was set in the API block (or if we intentionally ignored the API error)
    if (!isError) {
      setMessage(`Successfully transferred $${transferAmount.toFixed(2)} from ${fromAccount} to ${toAccount}.`);
    }
    
    // Reset form
    setAmount('');
    
    // Update sessionStorage for persistence across mock app pages
    if (typeof window !== 'undefined') {
        sessionStorage.setItem('userData', JSON.stringify(newUserData));
    }
  };

  return (
    <Card sx={{ 
      p: 3, 
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

        <Grid container spacing={2}>
            <Grid item xs={6}>
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
            </Grid>
            <Grid item xs={6}>
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
            </Grid>
        </Grid>

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
// --- END NEW MONEY TRANSFER CARD COMPONENT ---

// Dashboard Page
const DashboardPage = () => {
  // Use a combination of demo data (initial state) and sessionStorage (post-login)
  const [userData, setUserData] = useState(demoUserData);
  const [additionalAccountData, setAdditionalAccountData] = useState(null);
  // NEW: Add transactions to state to allow updates from the TransferCard
  const [transactions, setTransactions] = useState(mockTransactions);
  // NEW: Loading state for the additional, client-side fetch
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);

  // 1. Initial Load: Check sessionStorage for authenticated user data
  useEffect(() => {
    console.info('Dashboard page loaded');
    if (typeof window !== 'undefined') {
      const storedUserData = sessionStorage.getItem('userData');
      if (storedUserData) {
        console.info('Loading user data from session storage');
        setUserData(JSON.parse(storedUserData));
      }
    }
  }, []);

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
                // In a real app, you might set an error state here
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
        
        {/* --- ADDED TRANSFER CARD (Full width) --- */}
        <Grid item size={{ xs: 12 }}>
            <TransferCard 
                userData={userData}
                setUserData={setUserData}
                transactions={transactions}
                setTransactions={setTransactions}
            />
        </Grid>
        {/* --- END ADDED TRANSFER CARD --- */}

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
