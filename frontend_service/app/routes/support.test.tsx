import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import SupportPage from './support';

// Mock fetch globally
global.fetch = vi.fn();

describe('Support Chat Flow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (global.fetch as any).mockClear();
  });

  it('displays initial welcome message from bot', () => {
    render(<SupportPage />);

    expect(screen.getByText(/Hello! I'm ReliBot/i)).toBeInTheDocument();
    expect(screen.getByText(/How can I help you today/i)).toBeInTheDocument();
  });

  it('sends user message and receives bot response', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ response: 'I can help you with your account balance.' }),
    });

    render(<SupportPage />);

    const input = screen.getByPlaceholderText(/Type your message/i);
    const sendButton = screen.getByRole('button', { name: /send/i });

    // Type message
    fireEvent.change(input, { target: { value: 'What is my account balance?' } });
    expect(input).toHaveValue('What is my account balance?');

    // Send message
    fireEvent.click(sendButton);

    // User message should appear
    await waitFor(() => {
      expect(screen.getByText('What is my account balance?')).toBeInTheDocument();
    });

    // Bot response should appear
    await waitFor(() => {
      expect(screen.getByText(/I can help you with your account balance/i)).toBeInTheDocument();
    });

    // API should have been called
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/chatbot-service/chat?prompt='),
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      })
    );
  });

  it('calls API with correct URL when sending message', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ response: 'Response' }),
    });

    render(<SupportPage />);

    const input = screen.getByPlaceholderText(/Type your message/i);
    const sendButton = screen.getByRole('button', { name: /send/i });

    fireEvent.change(input, { target: { value: 'Test question' } });
    fireEvent.click(sendButton);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('Test%20question'),
        expect.any(Object)
      );
    });
  });

  it('prevents sending empty messages', () => {
    render(<SupportPage />);

    const sendButton = screen.getByRole('button', { name: /send/i });

    // Button should be disabled when input is empty
    expect(sendButton).toBeDisabled();

    const input = screen.getByPlaceholderText(/Type your message/i);
    fireEvent.change(input, { target: { value: '   ' } }); // Only whitespace

    // Button should still be disabled
    expect(sendButton).toBeDisabled();
  });

  it('clears input field after sending message', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ response: 'Got it!' }),
    });

    render(<SupportPage />);

    const input = screen.getByPlaceholderText(/Type your message/i);
    const sendButton = screen.getByRole('button', { name: /send/i });

    fireEvent.change(input, { target: { value: 'Test' } });
    fireEvent.click(sendButton);

    // Input should be cleared immediately
    expect(input).toHaveValue('');
  });
});
