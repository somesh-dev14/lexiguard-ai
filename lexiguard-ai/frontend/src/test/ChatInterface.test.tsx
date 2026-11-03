import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { ChatInterface } from '../components/chat/ChatInterface';
import { api } from '../services/api';

vi.mock('../services/api', () => ({
  api: {
    chatWithDocument: vi.fn(),
  },
}));

describe('ChatInterface Component Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('prompts user if no documentId is provided', async () => {
    render(<ChatInterface />);
    expect(screen.getByText(/No document is loaded/i)).toBeInTheDocument();

    const input = screen.getByPlaceholderText(/Ask a question about this contract/i);
    fireEvent.change(input, { target: { value: 'What are the payment terms?' } });
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

    await waitFor(() => {
      expect(screen.getByText(/Please navigate to an uploaded document to ask questions/i)).toBeInTheDocument();
    });
    expect(api.chatWithDocument).not.toHaveBeenCalled();
  });

  it('queries backend chat API with the exact documentId and filters out-of-bounds citations', async () => {
    vi.mocked(api.chatWithDocument).mockResolvedValue({
      answer: 'Payment is INR 120,000 due within 30 days of invoice.',
      sources: [
        { page: 1, excerpt: 'Payment clause: INR 120,000' },
        { page: 4, excerpt: 'Invalid out of bounds page' }, // should be filtered since pageCount is 2
      ],
      demo_mode: false,
    });

    render(
      <ChatInterface
        documentId="doc_12345"
        pageCount={2}
        pages={[
          { page_number: 1, text: 'Page 1', word_count: 50, char_count: 300 },
          { page_number: 2, text: 'Page 2', word_count: 50, char_count: 300 },
        ]}
      />
    );

    const input = screen.getByPlaceholderText(/Ask a question about this contract/i);
    fireEvent.change(input, { target: { value: 'What are the payment terms and penalties for late payment?' } });
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

    await waitFor(() => {
      expect(api.chatWithDocument).toHaveBeenCalledWith(
        'doc_12345',
        'What are the payment terms and penalties for late payment?'
      );
    });

    await waitFor(() => {
      expect(screen.getByText('Payment is INR 120,000 due within 30 days of invoice.')).toBeInTheDocument();
    });

    // Valid source on page 1 should be rendered
    expect(screen.getByText(/Page 1/)).toBeInTheDocument();

    // Out of bounds page 4 should NOT be rendered
    expect(screen.queryByText(/Page 4/)).not.toBeInTheDocument();

    // Demo Mode badge should NOT be displayed when demo_mode is false
    expect(screen.queryByText(/Demo Mode/i)).not.toBeInTheDocument();
  });

  it('renders Demo Mode badge only when backend explicitly returns demo_mode: true', async () => {
    vi.mocked(api.chatWithDocument).mockResolvedValue({
      answer: 'This is a demo answer.',
      sources: [{ page: 1, excerpt: 'Demo excerpt' }],
      demo_mode: true,
    });

    render(<ChatInterface documentId="doc_demo_doc" pageCount={1} />);

    const input = screen.getByPlaceholderText(/Ask a question about this contract/i);
    fireEvent.change(input, { target: { value: 'Hello' } });
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

    await waitFor(() => {
      expect(screen.getByText('This is a demo answer.')).toBeInTheDocument();
    });

    expect(screen.getByText('Demo Mode')).toBeInTheDocument();
  });
});
