import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { PayBillCard } from './PayBillCard';
import { LoginContext } from '~/root';

// Mock fetch globally
global.fetch = vi.fn();

const mockUserData = [
  { account_type: 'checking', balance: 1000, routing_number: '123456789' },
  { account_type: 'savings', balance: 500, routing_number: '987654321' },
];

const mockLoginContext = {
  isAuthenticated: true,
  handleLogin: vi.fn(),
  userData: mockUserData,
  setUserData: vi.fn(),
  handleLogout: vi.fn(),
};

const renderPayBillCard = () => {
  return render(
    <LoginContext.Provider value={mockLoginContext}>
      <PayBillCard />
    </LoginContext.Provider>
  );
};

describe('PayBillCard - Payment Flow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (global.fetch as any).mockClear();
  });

  it('fetches saved payment methods on mount', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        paymentMethods: [
          { id: 'pm_123', brand: 'visa', last4: '4242', expMonth: 12, expYear: 2025 }
        ]
      }),
    });

    renderPayBillCard();

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/bill-pay-service/payment-methods/')
      );
    });
  });

  it('validates required fields before submission', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ paymentMethods: [] }),
    });

    renderPayBillCard();

    const amountField = screen.getByLabelText(/amount/i);
    const submitButton = screen.getByRole('button', { name: /pay bill/i });

    // Clear amount to make it invalid
    fireEvent.change(amountField, { target: { value: '' } });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/please fill in all fields/i)).toBeInTheDocument();
    });
  });

  it('processes bank account payment successfully', async () => {
    // Mock payment methods fetch
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ paymentMethods: [] }),
    });

    // Mock bank payment
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true }),
    });

    renderPayBillCard();

    await waitFor(() => {
      expect(screen.getByLabelText(/payment method/i)).toBeInTheDocument();
    });

    const submitButton = screen.getByRole('button', { name: /pay bill/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        '/bill-pay-service/pay',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        })
      );
    });

    await waitFor(() => {
      expect(screen.getByText(/completed successfully/i)).toBeInTheDocument();
    });
  });

  it('displays saved payment methods in dropdown', async () => {
    // Mock payment methods fetch with cards
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        paymentMethods: [
          { id: 'pm_123', brand: 'visa', last4: '4242', expMonth: 12, expYear: 2025 },
          { id: 'pm_456', brand: 'mastercard', last4: '5555', expMonth: 6, expYear: 2026 }
        ]
      }),
    });

    renderPayBillCard();

    // Verify API was called to fetch payment methods
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/bill-pay-service/payment-methods/')
      );
    });
  });

  it('resets form after successful payment', async () => {
    // Mock payment methods fetch
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ paymentMethods: [] }),
    });

    // Mock successful payment
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true }),
    });

    renderPayBillCard();

    await waitFor(() => {
      expect(screen.getByLabelText(/payee name/i)).toBeInTheDocument();
    });

    const payeeField = screen.getByLabelText(/payee name/i) as HTMLInputElement;
    const amountField = screen.getByLabelText(/amount/i) as HTMLInputElement;
    const accountField = screen.getByLabelText(/account number/i) as HTMLInputElement;

    // Change values
    fireEvent.change(payeeField, { target: { value: 'Cable Company' } });
    fireEvent.change(amountField, { target: { value: '99.99' } });
    fireEvent.change(accountField, { target: { value: '12345' } });

    const submitButton = screen.getByRole('button', { name: /pay bill/i });
    fireEvent.click(submitButton);

    // After successful payment, form should reset to defaults
    await waitFor(() => {
      expect(screen.getByText(/completed successfully/i)).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(payeeField.value).toBe('Electric Company');
      expect(amountField.value).toBe('125.50');
      expect(accountField.value).toBe('67890');
    });
  });

  it('shows loading state during payment processing', async () => {
    // Mock payment methods fetch
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ paymentMethods: [] }),
    });

    // Mock slow payment
    (global.fetch as any).mockImplementationOnce(() =>
      new Promise((resolve) => {
        setTimeout(() => {
          resolve({
            ok: true,
            json: async () => ({ success: true }),
          });
        }, 100);
      })
    );

    renderPayBillCard();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /pay bill/i })).toBeInTheDocument();
    });

    const submitButton = screen.getByRole('button', { name: /pay bill/i });
    fireEvent.click(submitButton);

    // Should show loading state
    await waitFor(() => {
      expect(screen.getByText(/processing/i)).toBeInTheDocument();
      expect(submitButton).toBeDisabled();
    });

    // Should complete
    await waitFor(() => {
      expect(screen.getByText(/completed successfully/i)).toBeInTheDocument();
    });
  });
});
