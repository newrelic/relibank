import { useState, useContext, useEffect } from 'react';
import { useNavigate, Link, Navigate } from 'react-router-dom';
import {
    Box,
    Button,
    Container,
    CssBaseline,
    TextField,
    Typography,
    Alert,
    InputAdornment,
    IconButton,
    Paper,
    CircularProgress
} from '@mui/material';
import { Visibility, VisibilityOff, Lock, Person, ErrorOutline } from '@mui/icons-material';
import { createTheme, ThemeProvider } from '@mui/material/styles';
import { LoginContext } from '../root';

// Create a custom theme with Inter font and ReliBank green colors
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
            main: '#7a9b3e',      // Sage green
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
});

const LoginPage = () => {
    const [username, setUsername] = useState('demo');
    const [password, setPassword] = useState('lightm0deisthebest');
    const [showPassword, setShowPassword] = useState(false);
    const [loginError, setLoginError] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const { isAuthenticated, handleLogin } = useContext(LoginContext);
    const navigate = useNavigate();

    // Log when login page loads
    useEffect(() => {
        console.info('Login page loaded');
    }, []);

    // if (isAuthenticated) {
    //     return <Navigate to="/dashboard" replace />;
    // }

    const handleLoginClick = async (event: { preventDefault: () => void; }) => {
        event.preventDefault();
        setIsSubmitting(true);
        setLoginError('');

        console.info('Login attempt started', { username });

        // Simulate a network request. In a real application, you would replace this with a real API call.
        try {
            console.info('Fetching user account data from accounts service');
            const response = await fetch('/accounts-service/accounts/alice.j@relibank.com');

            if (!response.ok) {
                throw new Error('Login failed. Please check your credentials.');
            }

            const userData = await response.json();
            console.log('API Response:', userData);
            console.info('Login successful', { userId: userData.id, userName: userData.name });

            // On success, call handleLogin to set state and initiate navigation (via useEffect in root.tsx)
            handleLogin(userData);

            // DO NOT set isSubmitting(false) here. The spinner stays until the page unmounts.
        } catch (error) {
            console.error('Login error:', error);
            console.info('Login failed', { error: error.message });
            setLoginError(error.message);

            // On failure, hide the spinner so the user can try again
            setIsSubmitting(false);
        }
        // Removed the outer finally block to prevent prematurely setting isSubmitting(false)
    };

    return (
        <ThemeProvider theme={theme}>
            <CssBaseline />
            <Box
                sx={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    minHeight: '100vh',
                    bgcolor: 'background.default',
                }}
            >
                <Container component="main" maxWidth="sm">
                    <Paper
                        elevation={3}
                        sx={{
                            padding: 4,
                            display: 'flex',
                            flexDirection: 'column',
                            alignItems: 'center',
                            borderRadius: '12px',
                        }}
                    >
                        <Box sx={{ mb: 2, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                            <Box sx={{ width: '64px', height: '64px', display: 'flex', alignItems: 'center', justifyContent: 'center', mb: 1 }}>
                                <img src="/relibank.png" alt="ReliBank Logo" style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }} />
                            </Box>
                            <Typography component="h1" variant="h5" sx={{ fontWeight: 'bold' }}>
                                ReliBank Login
                            </Typography>
                        </Box>
                        {loginError && (
                            <Alert severity="error" sx={{ width: '100%', mb: 2 }}>
                                {loginError}
                            </Alert>
                        )}
                        <Box component="form" onSubmit={handleLoginClick} noValidate sx={{ mt: 1, width: '100%' }}>
                            <TextField
                                margin="normal"
                                required
                                fullWidth
                                id="username"
                                label="Username"
                                name="username"
                                autoComplete="username"
                                autoFocus
                                value={username}
                                onChange={(e: { target: { value: any; }; }) => setUsername(e.target.value)}
                                InputProps={{
                                    startAdornment: (
                                        <InputAdornment position="start">
                                            <Person />
                                        </InputAdornment>
                                    ),
                                }}
                            />
                            <TextField
                                margin="normal"
                                required
                                fullWidth
                                name="password"
                                label="Password"
                                type={showPassword ? 'text' : 'password'}
                                id="password"
                                autoComplete="current-password"
                                value={password}
                                onChange={(e: { target: { value: any; }; }) => setPassword(e.target.value)}
                                InputProps={{
                                    startAdornment: (
                                        <InputAdornment position="start">
                                            <Lock />
                                        </InputAdornment>
                                    ),
                                    endAdornment: (
                                        <InputAdornment position="end">
                                            <IconButton
                                                id="login-toggle-password-btn"
                                                onClick={() => setShowPassword(!showPassword)}
                                                onMouseDown={(e: { preventDefault: () => any; }) => e.preventDefault()}
                                                edge="end"
                                            >
                                                {showPassword ? <VisibilityOff /> : <Visibility />}
                                            </IconButton>
                                        </InputAdornment>
                                    ),
                                }}
                            />
                            <Button
                                id="login-submit-btn"
                                type="submit"
                                fullWidth
                                variant="contained"
                                sx={{ mt: 3, mb: 2, py: 1.5, borderRadius: '8px' }}
                                disabled={isSubmitting}
                            >
                                {isSubmitting ? <CircularProgress size={24} /> : 'Sign In'}
                            </Button>
                            <Box sx={{ mt: 2, textAlign: 'center' }}>
                                <Typography variant="body2" color="text.secondary">
                                    Don't have an account? <Link id="login-signup-link" href="#" style={{ color: theme.palette.primary.main }}>Sign Up</Link>
                                </Typography>
                            </Box>
                        </Box>
                    </Paper>
                </Container>
            </Box>
        </ThemeProvider>
    );
};

export default LoginPage;
