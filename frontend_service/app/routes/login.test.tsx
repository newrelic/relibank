import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import LoginPage from './login';
import { LoginContext } from '../root';

// Mock fetch globally
global.fetch = vi.fn();

// Mock sessionStorage
const sessionStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => { store[key] = value; },
    removeItem: (key: string) => { delete store[key]; },
    clear: () => { store = {}; }
  };
})();

Object.defineProperty(window, 'sessionStorage', {
  value: sessionStorageMock
});

const mockLoginContext = {
  isAuthenticated: false,
  handleLogin: vi.fn(),
  handleLogout: vi.fn(),
  userData: null,
  setUserData: vi.fn(),
};

const renderLogin = () => {
  return render(
    <BrowserRouter>
      <LoginContext.Provider value={mockLoginContext}>
        <LoginPage />
      </LoginContext.Provider>
    </BrowserRouter>
  );
};

describe('Login Flow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (global.fetch as any).mockClear();
    sessionStorageMock.clear();
  });

  it('submits login form with credentials', async () => {
    const mockAuthData = {
      token: 'mock-jwt-token-12345',
      email: 'alice.j@relibank.com',
      user_id: 'alice.j@relibank.com'
    };

    const mockAccountData = [
      {
        id: 12345,
        name: 'Primary Checking',
        balance: 1500.50,
        account_type: 'checking'
      }
    ];

    // Mock auth-service/login response
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockAuthData,
    });

    // Mock accounts-service response
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockAccountData,
    });

    renderLogin();

    const submitButton = screen.getByRole('button', { name: /sign in/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      // First call: auth-service login
      expect(global.fetch).toHaveBeenNthCalledWith(1, '/auth-service/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: 'alice.j@relibank.com',
          password: 'aJ7#kQ9mP2wX'
        })
      });

      // Second call: accounts-service with authenticated email
      expect(global.fetch).toHaveBeenNthCalledWith(
        2,
        '/accounts-service/accounts/alice.j@relibank.com'
      );

      // Verify sessionStorage stores token
      expect(sessionStorage.getItem('authToken')).toBe(mockAuthData.token);

      // Verify handleLogin called with account data
      expect(mockLoginContext.handleLogin).toHaveBeenCalledWith(mockAccountData);
    });
  });

  it('shows error message on failed login', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: async () => ({ detail: 'Invalid email or password' }),
    });

    renderLogin();

    const submitButton = screen.getByRole('button', { name: /sign in/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/invalid email or password/i)).toBeInTheDocument();
    });
  });

  it('updates username field on input', () => {
    renderLogin();

    const usernameField = screen.getByLabelText(/email/i);
    fireEvent.change(usernameField, { target: { value: 'testuser@example.com' } });

    expect(usernameField).toHaveValue('testuser@example.com');
  });

  it('toggles password visibility', () => {
    renderLogin();

    const passwordField = screen.getByLabelText(/password/i);
    expect(passwordField).toHaveAttribute('type', 'password');

    const toggleButton = screen.getByRole('button', { name: '' }); // IconButton has no text
    fireEvent.click(toggleButton);

    expect(passwordField).toHaveAttribute('type', 'text');
  });
});
