import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { Toaster } from 'sonner';
import { LibraryTab } from '../LibraryTab';
import * as searchApi from '@/api/search';
import * as ingestionApi from '@/api/ingestion';
import * as adminApi from '@/api/admin';
import { useWorkspaceStore } from '@/store/workspaceStore';

vi.mock('@/api/search');
vi.mock('@/api/ingestion');
vi.mock('@/api/admin');

const SAMPLE_PROJECT_PAPER = {
  id: 'doc-new',
  title: 'Attention Is All You Need',
  authors: ['Vaswani, A.'],
  year: 2017,
  source: 'arxiv' as const,
  status: 'indexed' as const,
  createdAt: '2026-06-22T00:00:00Z',
  abstract: null,
  hasFile: false,
  pdfUrl: null,
  url: 'https://arxiv.org/abs/1706.03762',
};

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
  isBroadQuery: false,
  suggestions: [],
};

function renderTab(projectId: string | null = null) {
  return render(
    <MemoryRouter>
      <Toaster />
      <LibraryTab projectId={projectId} />
    </MemoryRouter>,
  );
}

describe('LibraryTab', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(ingestionApi.getPapersByProject).mockResolvedValue([]);
    // Mặc định giới hạn cao để các test khác không chạm trần; test counter sẽ override = 1.
    vi.mocked(adminApi.getPublicSettings).mockResolvedValue({ maxPapersPerProject: 15 } as never);
    // Store zustand là singleton — reset sub-tab về mặc định để test không phụ thuộc thứ tự.
    useWorkspaceStore.setState({ librarySubTab: 'documents', isUploadModalOpen: false });
  });

  it('hiển thị 2 tab con segmented control', () => {
    renderTab();
    expect(screen.getByRole('button', { name: /tài liệu trong dự án/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /tìm kiếm báo cáo/i })).toBeInTheDocument();
  });

  it('mặc định tab con "Tài liệu trong dự án" active', () => {
    renderTab('proj-1');
    const docsBtn = screen.getByRole('button', { name: /tài liệu trong dự án/i });
    expect(docsBtn.className).toContain('subTabActive');
  });

  it('chuyển sang tab con Tìm kiếm khi click', async () => {
    renderTab();
    const searchBtn = screen.getByRole('button', { name: /tìm kiếm báo cáo/i });
    fireEvent.click(searchBtn);
    expect(searchBtn.className).toContain('subTabActive');
    // Ô tìm kiếm xuất hiện (SearchSubTab render)
    expect(screen.getByPlaceholderText(/tìm kiếm bài báo/i)).toBeInTheDocument();
  });

  it('ô tìm kiếm và nút Tìm kiếm có trong tab Tìm kiếm', () => {
    renderTab();
    fireEvent.click(screen.getByRole('button', { name: /tìm kiếm báo cáo/i }));
    expect(screen.getByPlaceholderText(/tìm kiếm bài báo/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^tìm kiếm$/i })).toBeInTheDocument();
  });

  it('nút Tìm kiếm disabled khi input rỗng', () => {
    renderTab();
    fireEvent.click(screen.getByRole('button', { name: /tìm kiếm báo cáo/i }));
    const btn = screen.getByRole('button', { name: /^tìm kiếm$/i });
    expect(btn).toBeDisabled();
  });

  it('hiển thị kết quả sau khi tìm kiếm thành công trong tab Tìm kiếm', async () => {
    vi.mocked(searchApi.searchPapers).mockResolvedValue(MOCK_RESULT);
    renderTab('proj-1');

    fireEvent.click(screen.getByRole('button', { name: /tìm kiếm báo cáo/i }));
    const input = screen.getByPlaceholderText(/tìm kiếm bài báo/i);
    fireEvent.change(input, { target: { value: 'transformer' } });
    fireEvent.click(screen.getByRole('button', { name: /^tìm kiếm$/i }));

    await waitFor(() => expect(screen.getByText('Attention Is All You Need')).toBeInTheDocument());
    expect(screen.getByText(/Vaswani/)).toBeInTheDocument();
    expect(screen.getByText('2017')).toBeInTheDocument();
  });

  it('Enter key kích hoạt tìm kiếm trong SearchSubTab', async () => {
    vi.mocked(searchApi.searchPapers).mockResolvedValue(MOCK_RESULT);
    renderTab();

    fireEvent.click(screen.getByRole('button', { name: /tìm kiếm báo cáo/i }));
    const input = screen.getByPlaceholderText(/tìm kiếm bài báo/i);
    fireEvent.change(input, { target: { value: 'transformer' } });
    fireEvent.keyDown(input, { key: 'Enter' });

    await waitFor(() =>
      expect(vi.mocked(searchApi.searchPapers)).toHaveBeenCalledWith('transformer', 10),
    );
  });

  it('nút "Thêm vào dự án" disabled khi không có projectId', async () => {
    vi.mocked(searchApi.searchPapers).mockResolvedValue(MOCK_RESULT);
    renderTab();

    fireEvent.click(screen.getByRole('button', { name: /tìm kiếm báo cáo/i }));
    const input = screen.getByPlaceholderText(/tìm kiếm bài báo/i);
    fireEvent.change(input, { target: { value: 'transformer' } });
    fireEvent.click(screen.getByRole('button', { name: /^tìm kiếm$/i }));

    await waitFor(() => screen.getByText('Attention Is All You Need'));
    const addBtn = screen.getByRole('button', { name: /thêm vào dự án/i });
    expect(addBtn).toBeDisabled();
  });

  it('nút "Thêm vào dự án" được enable khi có projectId', async () => {
    vi.mocked(searchApi.searchPapers).mockResolvedValue(MOCK_RESULT);
    renderTab('proj-1');

    fireEvent.click(screen.getByRole('button', { name: /tìm kiếm báo cáo/i }));
    const input = screen.getByPlaceholderText(/tìm kiếm bài báo/i);
    fireEvent.change(input, { target: { value: 'transformer' } });
    fireEvent.click(screen.getByRole('button', { name: /^tìm kiếm$/i }));

    await waitFor(() => screen.getByText('Attention Is All You Need'));
    const addBtn = screen.getByRole('button', { name: /thêm vào dự án/i });
    expect(addBtn).not.toBeDisabled();
  });

  it('hiển thị DocumentList trong tab Tài liệu khi projectId không null', async () => {
    renderTab('proj-1');
    await waitFor(() =>
      expect(vi.mocked(ingestionApi.getPapersByProject)).toHaveBeenCalledWith('proj-1'),
    );
    expect(screen.getAllByText(/tài liệu trong dự án/i).length).toBeGreaterThanOrEqual(1);
  });

  it('không gọi getPapersByProject khi projectId null', () => {
    renderTab(null);
    expect(vi.mocked(ingestionApi.getPapersByProject)).not.toHaveBeenCalled();
  });

  it('hiển thị chip gợi ý khi isBroadQuery = true', async () => {
    vi.mocked(searchApi.searchPapers).mockResolvedValue({
      results: [],
      warnings: [],
      isBroadQuery: true,
      suggestions: ['Natural Language Processing', 'Computer Vision'],
    });
    renderTab();

    fireEvent.click(screen.getByRole('button', { name: /tìm kiếm báo cáo/i }));
    const input = screen.getByPlaceholderText(/tìm kiếm bài báo/i);
    fireEvent.change(input, { target: { value: 'AI' } });
    fireEvent.click(screen.getByRole('button', { name: /^tìm kiếm$/i }));

    await waitFor(() =>
      expect(screen.getByText('Natural Language Processing')).toBeInTheDocument(),
    );
    expect(screen.getByText('Computer Vision')).toBeInTheDocument();
  });

  it('counter dùng chung — add-from-search ở tab Tìm kiếm làm tab Tài liệu đạt giới hạn', async () => {
    // AC#5 (rủi ro chính): papers/isAtLimit ở component CHA — nguồn sự thật duy nhất.
    // Thêm tài liệu từ tab "Tìm kiếm" phải phản ánh sang counter/giới hạn của tab "Tài liệu";
    // nếu mỗi tab con giữ bản sao riêng thì counter sẽ lệch và test này fail.
    vi.mocked(adminApi.getPublicSettings).mockResolvedValue({ maxPapersPerProject: 1 } as never);
    vi.mocked(searchApi.searchPapers).mockResolvedValue(MOCK_RESULT);
    vi.mocked(ingestionApi.addPaperFromSearch).mockResolvedValue({ documentId: 'doc-new', message: 'ok' });
    // Mount DocumentList → rỗng (chưa đạt giới hạn). Sau khi add → refetch trả 1 paper → đạt giới hạn 1.
    vi.mocked(ingestionApi.getPapersByProject)
      .mockResolvedValueOnce([])
      .mockResolvedValue([SAMPLE_PROJECT_PAPER]);

    renderTab('proj-1');
    await waitFor(() => expect(ingestionApi.getPapersByProject).toHaveBeenCalledWith('proj-1'));
    // Trước khi add: chưa có cảnh báo giới hạn
    expect(screen.queryByText(/đã đạt giới hạn/i)).not.toBeInTheDocument();

    // Sang tab Tìm kiếm, tìm và thêm 1 paper
    fireEvent.click(screen.getByRole('button', { name: /tìm kiếm báo cáo/i }));
    fireEvent.change(screen.getByPlaceholderText(/tìm kiếm bài báo/i), { target: { value: 'transformer' } });
    fireEvent.click(screen.getByRole('button', { name: /^tìm kiếm$/i }));
    await waitFor(() => screen.getByText('Attention Is All You Need'));
    fireEvent.click(screen.getByRole('button', { name: /thêm vào dự án/i }));
    await waitFor(() => expect(ingestionApi.addPaperFromSearch).toHaveBeenCalled());

    // Counter dùng chung cập nhật → quay lại tab Tài liệu thấy cảnh báo đạt giới hạn
    fireEvent.click(screen.getByRole('button', { name: /tài liệu trong dự án/i }));
    await waitFor(() => expect(screen.getByText(/đã đạt giới hạn/i)).toBeInTheDocument());
  });
});
