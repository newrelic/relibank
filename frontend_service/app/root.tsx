import {
  Links,
  Meta,
  Outlet,
  Scripts,
  ScrollRestoration,
} from "react-router";

import { useState, createContext, useContext, useEffect } from 'react';
import { Link, useLocation, useParams, useNavigate } from 'react-router-dom';
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
  CircularProgress
} from '@mui/material';
import DashboardIcon from '@mui/icons-material/Dashboard';
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet';
import SettingsIcon from '@mui/icons-material/Settings';
import NotificationsIcon from '@mui/icons-material/Notifications';
import BusinessIcon from '@mui/icons-material/Business';
import { DashboardPage } from "./routes/dashboard";

// Create a context for the page data
export const PageContext = createContext({});

// Mock data for the dashboard
const mockUserData = {
  name: "John Doe",
  avatar: "https://placehold.co/40x40/60a5fa/ffffff?text=JD",
};

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

const mockAccounts = [
  { id: 'checking', name: 'Checking Account', balance: 8500.25, number: '**** 1234' },
  { id: 'savings', name: 'Savings Account', balance: 4000.25, number: '**** 5678' },
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

// Create a custom theme with Inter font and a subtle background
const theme = createTheme({
  typography: {
    fontFamily: ['Inter', 'sans-serif'].join(','),
  },
  palette: {
    background: {
      default: '#f8f9fa',
    },
    primary: {
      main: '#3b82f6',
    },
    secondary: {
      main: '#6b7280',
    },
  },
  components: {
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
        },
      },
    },
  },
});

// Footer component
export const Footer = () => (
  <Box component="footer" sx={{
    py: 3,
    px: 2,
    backgroundColor: 'white',
    borderTop: '1px solid #e5e7eb',
    textAlign: 'center',
    borderRadius: '0 0 12px 12px',
    color: 'text.secondary'
  }}>
    <Typography variant="body2">
      Is this bank real? Is your money? Are you? We’re only certain about the first one. Please recognize this is a demo.
    </Typography>
    <Typography variant="body2">
      © 2023 ReliBank. All rights reserved.
    </Typography>
  </Box>
);

// Sidebar component
export const Sidebar = () => {
  const location = useLocation();
  const activePage = location.pathname;

  return (
    <Box sx={{
      width: 256,
      backgroundColor: 'white',
      p: 2,
      height: '100%',
      borderRight: '1px solid #e5e7eb',
      display: 'flex',
      flexDirection: 'column',
      borderRadius: '12px 0 0 12px'
    }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 4 }}>
        <BusinessIcon color="primary" sx={{ mr: 1 }} />
        <Typography variant="h6" sx={{ fontWeight: 'bold' }}>ReliBank</Typography>
      </Box>
      <List sx={{ flexGrow: 1 }}>
        <ListItem disablePadding sx={{ mb: 1, borderRadius: '8px' }}>
          <ListItemButton component={Link} to="/dashboard" selected={activePage === '/dashboard'} sx={{ borderRadius: '8px', '&:hover': { backgroundColor: '#f3f4f6' } }}>
            <ListItemIcon>
              <DashboardIcon sx={{ color: activePage === '/dashboard' ? 'primary.main' : 'secondary.main' }} />
            </ListItemIcon>
            <ListItemText primary="Dashboard" />
          </ListItemButton>
        </ListItem>
        <ListItem disablePadding sx={{ mb: 1, borderRadius: '8px' }}>
          <ListItemButton component={Link} to="/accounts" selected={activePage.startsWith('/accounts')} sx={{ borderRadius: '8px', '&:hover': { backgroundColor: '#f3f4f6' } }}>
            <ListItemIcon>
              <AccountBalanceWalletIcon sx={{ color: activePage.startsWith('/accounts') ? 'primary.main' : 'secondary.main' }} />
            </ListItemIcon>
            <ListItemText primary="Accounts" />
          </ListItemButton>
        </ListItem>
        <ListItem disablePadding sx={{ mb: 1, borderRadius: '8px' }}>
          <ListItemButton component={Link} to="/settings" selected={activePage === '/settings'} sx={{ borderRadius: '8px', '&:hover': { backgroundColor: '#f3f4f6' } }}>
            <ListItemIcon>
              <SettingsIcon sx={{ color: activePage === '/settings' ? 'primary.main' : 'secondary.main' }} />
            </ListItemIcon>
            <ListItemText primary="Settings" />
          </ListItemButton>
        </ListItem>
      </List>
    </Box>
  );
};

// Header component
export const Header = () => {
  const { userData } = useContext(PageContext);
  const location = useLocation();
  let pageTitle = 'Dashboard';
  if (location.pathname.startsWith('/accounts')) {
    pageTitle = 'Accounts';
  } else if (location.pathname === '/settings') {
    pageTitle = 'Settings';
  }

  return (
    <Box sx={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      p: 2,
      backgroundColor: 'white',
      borderBottom: '1px solid #e5e7eb',
      borderRadius: '0 12px 12px 0'
    }}>
      <Typography variant="h5" sx={{ fontWeight: 'semibold', color: 'text.primary' }}>
        {pageTitle}
      </Typography>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        <Tooltip title="Notifications">
          <IconButton>
            <NotificationsIcon sx={{ color: 'text.secondary' }} />
          </IconButton>
        </Tooltip>
        <Divider orientation="vertical" flexItem sx={{ mx: 1 }} />
        <Avatar src={mockUserData.avatar} alt={mockUserData.name} />
        <Typography variant="subtitle1" sx={{ fontWeight: 'medium' }}>
          {mockUserData.name}
        </Typography>
      </Box>
    </Box>
  );
};

// Main Layout component
export const AppLayout = ({ children }) => {
  const sharedContext = {
    userData: mockUserData,
    summaryData: mockSummaryData,
    mockTransactions,
    mockAccounts,
    spendingData: mockSpendingData,
    pieData: mockPieData,
  };

  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsLoading(false);
    }, 1000);
    return () => clearTimeout(timer);
  }, []);

  if (isLoading) {
    return (
      <Box
        sx={{
          position: 'fixed',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 9999,
          color: 'white',
        }}
      >
        <CircularProgress color="inherit" />
      </Box>
    );
  }

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{
        display: 'flex',
        height: '100vh',
        bgcolor: '#f8f9fa',
        p: 4,
        borderRadius: '12px'
      }}>
        {/* Sidebar */}
        <Sidebar />

        {/* Main Content Area */}
        <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', borderRadius: '0 12px 12px 0' }}>
          <PageContext.Provider value={sharedContext}>
            {/* Header */}
            <Header />
            {/* Page Content */}
            <Box sx={{ flexGrow: 1, overflow: 'auto' }}>
              {children}
            </Box>
            <Footer />
          </PageContext.Provider>
        </Box>
      </Box>
    </ThemeProvider>
  );
};

export function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  // The login page doesn't need the full AppLayout, so we render it without the wrapper.
  const isLoginPage = location.pathname === '/'; 

  // The login page is a separate layout
  if (isLoginPage) {
    return (
      <html lang="en">
        <head>
          <meta charSet="utf-8" />
          <meta name="viewport" content="width=device-width, initial-scale=1" />
          <Meta />
          <Links />
        </head>
        <body>
          {children}
          <ScrollRestoration />
          <Scripts />
        </body>
      </html>
    );
  }

  // All other pages will use the AppLayout
  return (
    <html lang="en">
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <Meta />
        <Links />
      </head>
      <body>
        <AppLayout>
          {children}
        </AppLayout>
        <ScrollRestoration />
        <Scripts />
      </body>
    </html>
  );
};

export default function App() {
  return <Outlet />;
}
