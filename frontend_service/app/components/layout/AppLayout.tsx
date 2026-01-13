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

export const AppLayout = ({ children }: { children: React.ReactNode }) => {
  const { isAuthenticated } = useContext(LoginContext);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{
        display: 'flex',
        height: '100vh',
        bgcolor: '#f8f9fa'
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
