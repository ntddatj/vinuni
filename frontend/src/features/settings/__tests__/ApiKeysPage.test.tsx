import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { ApiKeysPage } from '../ApiKeysPage';
import * as credApi from '@/api/userCredentials';

vi.mock('@/api/userCredentials');

function renderPage() {
  return render(
    <MemoryRouter>
      <ApiKeysPage />
    </MemoryRouter>
  );
}

describe('ApiKeysPage', () => {
  beforeEach(() => {
    vi.mocked(credApi.getApiKeys).mockResolvedValue([
      { provider: 'gemini', maskedKey: '••••••••a1b2', isValid: true, lastTestedAt: null },
    ]);
  });

  it('hiển thị provider Gemini với masked key', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText('Gemini (Google AI)')).toBeInTheDocument());
    expect(screen.getByText('••••••••a1b2')).toBeInTheDocument();
  });

  it('click ✏️ hiển thị input nhập key', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText('••••••••a1b2')).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: /sửa api key/i }));
    await waitFor(() =>
      expect(screen.getByPlaceholderText(/nhập api key mới/i)).toBeInTheDocument()
    );
  });

  it('click Huỷ ẩn input', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText('••••••••a1b2')).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: /sửa api key/i }));
    await waitFor(() => expect(screen.getByPlaceholderText(/nhập api key mới/i)).toBeInTheDocument());
    fireEvent.click(screen.getByText('Huỷ'));
    await waitFor(() =>
      expect(screen.queryByPlaceholderText(/nhập api key mới/i)).not.toBeInTheDocument()
    );
  });

  it('lưu key gọi saveApiKey và reload', async () => {
    vi.mocked(credApi.saveApiKey).mockResolvedValue(undefined);
    renderPage();
    await waitFor(() => expect(screen.getByText('••••••••a1b2')).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: /sửa api key/i }));
    await waitFor(() => expect(screen.getByPlaceholderText(/nhập api key mới/i)).toBeInTheDocument());
    const input = screen.getByPlaceholderText(/nhập api key mới/i);
    fireEvent.change(input, { target: { value: 'new-key-xyz' } });
    fireEvent.click(screen.getByText('Lưu'));
    await waitFor(() =>
      expect(vi.mocked(credApi.saveApiKey)).toHaveBeenCalledWith('gemini', { apiKey: 'new-key-xyz' })
    );
  });

  it('Test Connection hiển thị Testing... trong khi chờ', async () => {
    vi.mocked(credApi.testApiKey).mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve({ status: 'connected' }), 100))
    );
    renderPage();
    await waitFor(() => expect(screen.getByText('Test Connection')).toBeInTheDocument());
    fireEvent.click(screen.getByText('Test Connection'));
    await waitFor(() => expect(screen.getByText(/testing/i)).toBeInTheDocument());
  });

  it('chưa cấu hình key hiển thị Not configured', async () => {
    vi.mocked(credApi.getApiKeys).mockResolvedValue([
      { provider: 'gemini', maskedKey: null, isValid: null, lastTestedAt: null },
    ]);
    renderPage();
    await waitFor(() => expect(screen.getByText('Chưa cấu hình')).toBeInTheDocument());
    expect(screen.queryByText('Test Connection')).not.toBeInTheDocument();
  });
});
