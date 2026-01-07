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
} from '@mui/material';
import NotificationsIcon from '@mui/icons-material/Notifications';

export const Header = () => {
  const { userData } = useContext(LoginContext);
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
  } else if (location.pathname === '/settings') {
    pageTitle = 'Settings';
  } else if (location.pathname === '/support') {
    pageTitle = 'Support';
  }

  // Extract user name from userData (which is an array of accounts)
  const userName = userData && Array.isArray(userData) && userData.length > 0
    ? userData[0].name.split(' ')[0]  // Get first name from "Alice Checking"
    : null;

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
        {userName ? (
          <>
            <Avatar>{userName.charAt(0)}</Avatar>
            <Typography variant="subtitle1" sx={{ fontWeight: 'medium' }}>
              {userName}
            </Typography>
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
