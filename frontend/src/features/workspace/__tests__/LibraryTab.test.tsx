import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { Toaster } from 'sonner';
import { LibraryTab } from '../LibraryTab';
import * as searchApi from '@/api/search';

vi.mock('@/api/search');

const MOCK_RESULT = {
  results: [
    {
      title: 'Attention Is All You Need',
      authors: ['Vaswani, A.', 'Shazeer, N.'],
      year: 2017,
      abstract: 'The dominant sequence transduction models...',
      doi: '10.48550/arXiv.1706.03762',
      arxivId: '1706.03762',
      url: 'https://arxiv.org/abs/1706.03762',
      pdfUrl: 'https://arxiv.org/pdf/1706.03762',
      source: 'arxiv' as const,
    },
  ],
  warnings: [],
};

function renderTab() {
  return render(
    <MemoryRouter>
      <Toaster />
      <LibraryTab />
    </MemoryRouter>
  );
}

describe('LibraryTab', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('hiển thị ô tìm kiếm và nút Tìm kiếm', () => {
    renderTab();
    expect(screen.getByPlaceholderText(/tìm kiếm bài báo/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /tìm kiếm/i })).toBeInTheDocument();
  });

  it('nút Tìm kiếm disabled khi input rỗng', () => {
    renderTab();
    const btn = screen.getByRole('button', { name: /tìm kiếm/i });
    expect(btn).toBeDisabled();
  });

  it('hiển thị kết quả sau khi tìm kiếm thành công', async () => {
    vi.mocked(searchApi.searchPapers).mockResolvedValue(MOCK_RESULT);
    renderTab();

    const input = screen.getByPlaceholderText(/tìm kiếm bài báo/i);
    fireEvent.change(input, { target: { value: 'transformer' } });
    fireEvent.click(screen.getByRole('button', { name: /tìm kiếm/i }));

    await waitFor(() =>
      expect(screen.getByText('Attention Is All You Need')).toBeInTheDocument()
    );
    expect(screen.getByText(/Vaswani/)).toBeInTheDocument();
    expect(screen.getByText('2017')).toBeInTheDocument();
  });

  it('Enter key kích hoạt tìm kiếm', async () => {
    vi.mocked(searchApi.searchPapers).mockResolvedValue(MOCK_RESULT);
    renderTab();

    const input = screen.getByPlaceholderText(/tìm kiếm bài báo/i);
    fireEvent.change(input, { target: { value: 'transformer' } });
    fireEvent.keyDown(input, { key: 'Enter' });

    await waitFor(() =>
      expect(vi.mocked(searchApi.searchPapers)).toHaveBeenCalledWith('transformer', 10)
    );
  });

  it('hiển thị empty state khi không có kết quả', async () => {
    vi.mocked(searchApi.searchPapers).mockResolvedValue({ results: [], warnings: [] });
    renderTab();

    const input = screen.getByPlaceholderText(/tìm kiếm bài báo/i);
    fireEvent.change(input, { target: { value: 'xyznotfound' } });
    fireEvent.click(screen.getByRole('button', { name: /tìm kiếm/i }));

    await waitFor(() =>
      expect(screen.getByText(/không tìm thấy bài báo/i)).toBeInTheDocument()
    );
  });

  it('nút "Thêm vào dự án" disabled trên mỗi card', async () => {
    vi.mocked(searchApi.searchPapers).mockResolvedValue(MOCK_RESULT);
    renderTab();

    const input = screen.getByPlaceholderText(/tìm kiếm bài báo/i);
    fireEvent.change(input, { target: { value: 'transformer' } });
    fireEvent.click(screen.getByRole('button', { name: /tìm kiếm/i }));

    await waitFor(() => screen.getByText('Attention Is All You Need'));
    const addBtn = screen.getByRole('button', { name: /thêm vào dự án/i });
    expect(addBtn).toBeDisabled();
  });

  it('hiển thị PDF badge khi có pdfUrl', async () => {
    vi.mocked(searchApi.searchPapers).mockResolvedValue(MOCK_RESULT);
    renderTab();

    const input = screen.getByPlaceholderText(/tìm kiếm bài báo/i);
    fireEvent.change(input, { target: { value: 'transformer' } });
    fireEvent.click(screen.getByRole('button', { name: /tìm kiếm/i }));

    await waitFor(() => expect(screen.getByText('PDF')).toBeInTheDocument());
  });
});
