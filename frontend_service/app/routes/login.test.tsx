import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import LoginPage from './login';
import { LoginContext } from '../root';

// Mock fetch globally
global.fetch = vi.fn();

const mockLoginContext = {
  isAuthenticated: false,
  handleLogin: vi.fn(),
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
  });

  it('submits login form with credentials', async () => {
    const mockUserData = {
      id: 'alice.j@relibank.com',
      name: 'Alice Johnson',
      email: 'alice.j@relibank.com',
    };

    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockUserData,
    });

    renderLogin();

    const submitButton = screen.getByRole('button', { name: /sign in/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith('/accounts-service/accounts/alice.j@relibank.com');
      expect(mockLoginContext.handleLogin).toHaveBeenCalledWith(mockUserData);
    });
  });

  it('shows error message on failed login', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
    });

    renderLogin();

    const submitButton = screen.getByRole('button', { name: /sign in/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/login failed/i)).toBeInTheDocument();
    });
  });

  it('updates username field on input', () => {
    renderLogin();

    const usernameField = screen.getByLabelText(/username/i);
    fireEvent.change(usernameField, { target: { value: 'testuser' } });

    expect(usernameField).toHaveValue('testuser');
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
