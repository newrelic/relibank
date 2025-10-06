import process from 'node:process';
import {
  Links,
  Meta,
  Outlet,
  Scripts,
  ScrollRestoration,
} from "react-router";

import { useState, createContext, useContext, useEffect } from 'react';
import { Link, useLocation, Navigate, useNavigate } from 'react-router-dom';
import {
  Box,
  CssBaseline,
  ThemeProvider,
  createTheme,
  Typography,
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
import SupportAgentIcon from '@mui/icons-material/SupportAgent';

import nrScriptTemplate from "./nr.js?raw";

const NEW_RELIC_CONFIG = {
    // These values are hardcoded in nr.js
    // We'll use placeholders in the template and replace them here.
  ACCOUNT_ID: import.meta.env.VITE_NEW_RELIC_ACCOUNT_ID,
  BROWSER_APPLICATION_ID: import.meta.env.VITE_NEW_RELIC_BROWSER_APPLICATION_ID,
  LICENSE_KEY: import.meta.env.VITE_NEW_RELIC_LICENSE_KEY,
};

const generateNrScript = () => {
    let script = nrScriptTemplate;

    script = script.replace(/accountID:"__ACCOUNT_ID__"/g, `accountID:"${NEW_RELIC_CONFIG.ACCOUNT_ID}"`);
    script = script.replace(/licenseKey:"__LICENSE_KEY__"/g, `licenseKey:"${NEW_RELIC_CONFIG.LICENSE_KEY}"`);
    script = script.replace(/applicationID:"__APPLICATION_ID__"/g, `applicationID:"${NEW_RELIC_CONFIG.BROWSER_APPLICATION_ID}"`);

    return script;
};


// Create a context for login data
export const LoginContext = createContext({});

// Create a context for the page data
export const PageContext = createContext({});


// Mock data for the dashboard
const mockUserData = {
  name: "John Doe",
  avatar: "https://placehold.co/40x40/60a5fa/ffffff?text=JD",
};

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
  const { userData } = useContext(LoginContext);
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
        {/* <ListItem disablePadding sx={{ mb: 1, borderRadius: '8px' }}>
          <ListItemButton component={Link} to="/accounts" selected={activePage.startsWith('/accounts')} sx={{ borderRadius: '8px', '&:hover': { backgroundColor: '#f3f4f6' } }}>
            <ListItemIcon>
              <AccountBalanceWalletIcon sx={{ color: activePage.startsWith('/accounts') ? 'primary.main' : 'secondary.main' }} />
            </ListItemIcon>
            <ListItemText primary="Accounts" />
          </ListItemButton>
        </ListItem> */}
        <ListItem disablePadding sx={{ mb: 1, borderRadius: '8px' }}>
          <ListItemButton component={Link} to="/support" selected={activePage === '/support'} sx={{ borderRadius: '8px', '&:hover': { backgroundColor: '#f3f4f6' } }}>
            <ListItemIcon>
              <SupportAgentIcon sx={{ color: activePage === '/support' ? 'primary.main' : 'secondary.main' }} />
            </ListItemIcon>
            <ListItemText primary="Support" />
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
  const { userData } = useContext(LoginContext);
  const location = useLocation();
  let pageTitle = 'Dashboard';
  if (location.pathname.startsWith('/accounts')) {
    pageTitle = 'Accounts';
  } else if (location.pathname === '/settings') {
    pageTitle = 'Settings';
  } else if (location.pathname === '/support') {
    pageTitle = 'Support';
  }

  // Fallback for userData in case it's not available yet
  const user = userData || mockUserData;

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
        <Avatar src={user.avatar} alt={user.name} />
        <Typography variant="subtitle1" sx={{ fontWeight: 'medium' }}>
          {user.name}
        </Typography>
      </Box>
    </Box>
  );
};

// Main Layout component
export const AppLayout = ({ children }) => {
  const { isAuthenticated } = useContext(LoginContext);

  // If not authenticated, redirect to the login page. This handles direct navigation to protected routes.
  // if (!isAuthenticated) {
  //   return <Navigate to="/" replace />;
  // }

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
          <PageContext.Provider value={{}}>
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
  const isLoginPage = location.pathname === '/'; 

  const dynamicNrScriptContent = generateNrScript();

  // The login page is a separate layout
  if (isLoginPage) {
    return (
      <html lang="en">
        <head>
          <script dangerouslySetInnerHTML={{ __html: dynamicNrScriptContent }}></script>
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
        <script dangerouslySetInnerHTML={{ __html: dynamicNrScriptContent }}></script>
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
  const [isAuthenticated, setIsAuthenticated] = useState(() => {
    if (typeof window !== 'undefined') {
      console.log(`sessionStorage.getItem('isAuthenticated'): ${sessionStorage.getItem('isAuthenticated')}`)
      return sessionStorage.getItem('isAuthenticated') === 'true';
    }
    return false;
  });
  const [userData, setUserData] = useState(() => {
    if (typeof window !== 'undefined') {
      const storedUserData = sessionStorage.getItem('userData');
      return storedUserData ? JSON.parse(storedUserData) : null;
    }
    return null;
  });
  const navigate = useNavigate();

  const handleLogin = (data) => {
    console.log("we're actually setting data");
    setIsAuthenticated(true);
    setUserData(data);
    if (typeof window !== 'undefined') {
      sessionStorage.setItem('isAuthenticated', 'true');
      sessionStorage.setItem('userData', JSON.stringify(data));
    }
    // navigate('/dashboard');
    // if (isAuthenticated) {
    //   navigate('/dashboard');
    // }
  };
  
  const handleLogout = () => {
    setIsAuthenticated(false);
    setUserData(null);
    if (typeof window !== 'undefined') {
      sessionStorage.removeItem('isAuthenticated');
      sessionStorage.removeItem('userData');
    }
  };
  // Use useEffect to see the updated userData after a render
  useEffect(() => {
    console.log("userData:", userData);
    console.log("isAuthenticated:", isAuthenticated);
    if (isAuthenticated) {
      navigate('/dashboard');
    }
  }, [userData, isAuthenticated, navigate]);

  return (
    <LoginContext.Provider value={{ isAuthenticated, handleLogin, userData }}>
      <Outlet />
    </LoginContext.Provider>
  );
}
