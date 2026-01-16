import { useContext, useEffect, useState } from 'react';
import { LoginContext } from '~/root';
import { useLocation } from 'react-router-dom';
import {
  Box,
  Typography,
  Avatar,
  IconButton,
  Tooltip,
  Divider,
  Button,
} from '@mui/material';
import NotificationsIcon from '@mui/icons-material/Notifications';
import LogoutIcon from '@mui/icons-material/Logout';
import Brightness4Icon from '@mui/icons-material/Brightness4';

export const Header = () => {
  const { userData, handleLogout } = useContext(LoginContext);
  const location = useLocation();

  // CRITICAL: Force re-render when userData changes
  const [, forceUpdate] = useState({});
  useEffect(() => {
    console.log('[Header] userData changed:', userData);
    console.log('[Header] userData type:', typeof userData);
    console.log('[Header] userData is array:', Array.isArray(userData));
    if (userData && Array.isArray(userData)) {
      console.log('[Header] userData length:', userData.length);
      console.log('[Header] First account:', userData[0]);
    }
    forceUpdate({});
  }, [userData]);

  let pageTitle = 'Dashboard';
  if (location.pathname.startsWith('/accounts')) {
    pageTitle = 'Accounts';
  } else if (location.pathname === '/payments') {
    pageTitle = 'Payments';
  } else if (location.pathname === '/settings') {
    pageTitle = 'Settings';
  } else if (location.pathname === '/support') {
    pageTitle = 'Support';
  }

  // Extract user name from userData (which is an array of accounts)
  const userName = userData && Array.isArray(userData) && userData.length > 0
    ? userData[0].name.split(' ')[0]  // Get first name from "Alice Checking"
    : null;

  // ==========================================================================
  // DEMO APP: Intentionally broken theme toggle button
  //
  // This button throws a JavaScript error to demonstrate:
  // - Frontend error tracking with New Relic Browser
  // - Error boundaries and error handling
  // - Impact of client-side errors on user experience
  //
  // Do not fix this unless explicitly updating demo scenarios.
  // ==========================================================================
  const handleThemeToggle = () => {
    const error = new Error('Theme toggle is not implemented');

    // Report error to New Relic Browser
    if (typeof window !== 'undefined' && (window as any).newrelic) {
      console.log('[DEBUG] Reporting theme toggle error to New Relic Browser');
      (window as any).newrelic.noticeError(error, {
        component: 'Header',
        feature: 'ThemeToggle',
        action: 'click'
      });
      console.log('[DEBUG] Theme toggle error reported to New Relic');
    } else {
      console.warn('[DEBUG] New Relic Browser agent not available for theme error');
    }

    // Intentionally throw error to demonstrate frontend error handling
    throw error;
  };

  return (
    <Box sx={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      px: 32,
      py: 2,
      backgroundColor: 'white',
      borderBottom: '1px solid #e5e7eb',
      borderRadius: '0 12px 12px 0'
    }}>
      <Typography variant="h5" sx={{ fontWeight: 'semibold', color: 'text.primary' }}>
        {pageTitle}
      </Typography>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        <Tooltip title="Notifications">
          <IconButton id="header-notifications-btn">
            <NotificationsIcon sx={{ color: 'text.secondary' }} />
          </IconButton>
        </Tooltip>
        <Tooltip title="Toggle theme">
          <IconButton id="header-theme-toggle-btn" onClick={handleThemeToggle}>
            <Brightness4Icon sx={{ color: 'text.secondary' }} />
          </IconButton>
        </Tooltip>
        <Divider orientation="vertical" flexItem sx={{ mx: 1 }} />
        {userName ? (
          <>
            <Avatar>{userName.charAt(0)}</Avatar>
            <Typography variant="subtitle1" sx={{ fontWeight: 'medium' }}>
              {userName}
            </Typography>
            <Tooltip title="Logout">
              <IconButton id="header-logout-btn" onClick={handleLogout} sx={{ ml: 1 }}>
                <LogoutIcon sx={{ color: 'text.secondary' }} />
              </IconButton>
            </Tooltip>
          </>
        ) : (
          <Typography variant="subtitle1" sx={{ fontWeight: 'medium', color: 'text.secondary' }}>
            Loading...
          </Typography>
        )}
      </Box>
    </Box>
  );
};
