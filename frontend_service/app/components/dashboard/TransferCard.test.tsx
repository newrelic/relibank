import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { TransferCard } from './TransferCard';
import { LoginContext } from '~/root';

// Mock fetch globally
global.fetch = vi.fn();

const mockUserData = [
  { account_type: 'checking', balance: 1000, routing_number: '123456789' },
  { account_type: 'savings', balance: 500, routing_number: '987654321' },
];

const mockTransactions = [];
const mockSetTransactions = vi.fn();
const mockSetUserData = vi.fn();

const mockLoginContext = {
  isAuthenticated: true,
  handleLogin: vi.fn(),
  userData: mockUserData,
  setUserData: mockSetUserData,
};

const renderTransferCard = () => {
  return render(
    <LoginContext.Provider value={mockLoginContext}>
      <TransferCard
        transactions={mockTransactions}
        setTransactions={mockSetTransactions}
      />
    </LoginContext.Provider>
  );
};

describe('Transfer Flow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (global.fetch as any).mockClear();
  });

  it('validates transfer amount is positive', async () => {
    renderTransferCard();

    const amountField = screen.getByLabelText(/amount/i);
    const form = screen.getByRole('button', { name: /complete transfer/i }).closest('form');

    fireEvent.change(amountField, { target: { value: '-50' } });
    fireEvent.submit(form!);

    await waitFor(() => {
      expect(screen.getByText(/please enter a valid amount/i)).toBeInTheDocument();
    });
  });


  it('submits valid transfer request', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true }),
    });

    renderTransferCard();

    const amountField = screen.getByLabelText(/amount/i);
    const submitButton = screen.getByRole('button', { name: /complete transfer/i });

    fireEvent.change(amountField, { target: { value: '100' } });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        '/bill-pay-service/recurring',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        })
      );
    });
  });

  it('updates account balances after transfer', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true }),
    });

    renderTransferCard();

    const amountField = screen.getByLabelText(/amount/i);
    const submitButton = screen.getByRole('button', { name: /complete transfer/i });

    // Transfer $100 from checking to savings
    fireEvent.change(amountField, { target: { value: '100' } });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockSetUserData).toHaveBeenCalledWith(
        expect.arrayContaining([
          expect.objectContaining({ account_type: 'checking', balance: 900 }),
          expect.objectContaining({ account_type: 'savings', balance: 600 }),
        ])
      );
    });
  });

  it('shows error message on failed transfer', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({ detail: 'Insufficient funds' }),
    });

    renderTransferCard();

    const amountField = screen.getByLabelText(/amount/i);
    const submitButton = screen.getByRole('button', { name: /complete transfer/i });

    fireEvent.change(amountField, { target: { value: '5000' } });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/insufficient funds/i)).toBeInTheDocument();
    });
  });

  it('adds transaction records after transfer', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true }),
    });

    renderTransferCard();

    const amountField = screen.getByLabelText(/amount/i);
    const submitButton = screen.getByRole('button', { name: /complete transfer/i });

    fireEvent.change(amountField, { target: { value: '100' } });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockSetTransactions).toHaveBeenCalledWith(
        expect.arrayContaining([
          expect.objectContaining({
            amount: -100,
            accountId: 'checking',
            type: 'debit',
          }),
          expect.objectContaining({
            amount: 100,
            accountId: 'savings',
            type: 'credit',
          }),
        ])
      );
    });
  });
});
