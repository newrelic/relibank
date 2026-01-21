import { useContext } from 'react';
import { LoginContext, PageContext } from '~/root';
import { Box, CssBaseline, ThemeProvider, createTheme } from '@mui/material';
import { Header } from './Header';
import { Sidebar } from './Sidebar';
import { Footer } from './Footer';

const theme = createTheme({
  typography: {
    fontFamily: ['Inter', 'sans-serif'].join(','),
  },
  palette: {
    background: {
      default: '#f8faf8',
      paper: '#ffffff',
    },
    primary: {
      main: '#1a3d1a',      // Forest green from logo
      light: '#7a9b3e',     // Sage green
      dark: '#0f2610',      // Deeper green
    },
    secondary: {
      main: '#8db600',      // Lime accent from logo
      light: '#a8cc3a',
    },
    success: {
      main: '#7a9b3e',      // Sage green for positive actions
    },
    warning: {
      main: '#d97706',      // Amber gold (tertiary)
      light: '#fbbf24',     // Light gold
      dark: '#b45309',      // Deep amber
    },
    error: {
      main: '#dc2626',      // Red for errors
      light: '#f87171',
    },
    info: {
      main: '#7a9b3e',      // Sage green for info
    },
    text: {
      primary: '#2d3748',   // Charcoal
      secondary: '#6b7280',
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

export const AppLayout = ({ children }: { children: React.ReactNode }) => {
  const { isAuthenticated } = useContext(LoginContext);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{
        display: 'flex',
        height: '100vh',
        bgcolor: '#f8faf8'
      }}>
        <Sidebar />
        <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', borderRadius: '0 12px 12px 0' }}>
          <PageContext.Provider value={{}}>
            <Header />
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
