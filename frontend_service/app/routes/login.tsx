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
});

const LoginPage = () => {
    const [username, setUsername] = useState('demo');
    const [password, setPassword] = useState('password');
    const [showPassword, setShowPassword] = useState(false);
    const [loginError, setLoginError] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const { isAuthenticated, handleLogin } = useContext(LoginContext);
    const navigate = useNavigate();

    // if (isAuthenticated) {
    //     return <Navigate to="/dashboard" replace />;
    // }

    const handleLoginClick = async (event: { preventDefault: () => void; }) => {
        event.preventDefault();
        setIsSubmitting(true);
        setLoginError('');

        // Simulate a network request. In a real application, you would replace this with a real API call.
        try {
            const response = await fetch('http://localhost:5002/accounts/alice.j@relibank.com');

            if (!response.ok) {
                throw new Error('Login failed. Please check your credentials.');
            }

            const userData = await response.json();
            console.log('API Response:', userData);
            
            // On success, call handleLogin to set state and initiate navigation (via useEffect in root.tsx)
            handleLogin(userData);
            
            // DO NOT set isSubmitting(false) here. The spinner stays until the page unmounts.
        } catch (error) {
            console.error('Login error:', error);
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
                            <Lock color="primary" sx={{ fontSize: 48, mb: 1 }} />
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
                                    Don't have an account? <Link href="#" style={{ color: theme.palette.primary.main }}>Sign Up</Link>
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
