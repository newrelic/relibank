import { useContext } from 'react';
import { LoginContext } from '~/root';
import { useLocation, Link } from 'react-router-dom';
import {
  Box,
  Typography,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
} from '@mui/material';
import DashboardIcon from '@mui/icons-material/Dashboard';
import SettingsIcon from '@mui/icons-material/Settings';
import SupportAgentIcon from '@mui/icons-material/SupportAgent';
import BusinessIcon from '@mui/icons-material/Business';

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
