import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { GapTab } from '../GapTab';
import * as graphApi from '@/api/graph';

vi.mock('@/api/graph');

const mockSetActiveTab = vi.fn();
const mockRequestGapFocus = vi.fn();
const mockSetPendingChatInput = vi.fn();

vi.mock('@/store/workspaceStore', () => ({
  useWorkspaceStore: (selector: (s: Record<string, unknown>) => unknown) =>
    selector({
      activeTab: 'gaps',
      setActiveTab: mockSetActiveTab,
      requestGapFocus: mockRequestGapFocus,
      setPendingChatInput: mockSetPendingChatInput,
    }),
}));

vi.mock('@/store/languageStore', () => ({
  useLanguageStore: (selector: (s: { lang: 'vi' }) => unknown) => selector({ lang: 'vi' }),
}));

const GAP_ITEMS = [
  {
    id: 'f1_f2',
    type: 'contradiction' as const,
    reason: 'contradiction',
    title: 'Hai nghiên cứu đưa ra kết luận trái ngược nhau',
    description: 'Finding 1 / Finding 2',
    papers: [
      { paper_id: 'p1', title: 'Paper A' },
      { paper_id: 'p2', title: 'Paper B' },
    ],
    evidence: { finding_count: 2, paper_count: 2 },
  },
  {
    id: 'lim-1',
    type: 'unfilled_limitation' as const,
    reason: 'unfilled_limitation',
    title: 'Hạn chế nghiên cứu chưa được giải quyết',
    description: 'Phương pháp chưa được kiểm chứng',
    papers: [{ paper_id: 'p3', title: 'Paper C' }],
    evidence: { filler_count: 0 },
  },
  {
    id: 'p-iso',
    type: 'isolated_cluster' as const,
    reason: 'isolated_cluster',
    title: 'Nghiên cứu chưa có liên kết trích dẫn',
    description: 'Bài báo không có cạnh CITES',
    papers: [{ paper_id: 'p-iso', title: 'Isolated Paper' }],
    evidence: { neighbor_count: 0 },
  },
];

describe('GapTab', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('hiển thị thông báo chọn dự án khi projectId null', () => {
    render(<GapTab projectId={null} />);
    expect(screen.getByText(/chọn một dự án/i)).toBeInTheDocument();
  });

  it('hiển thị loading khi đang fetch', async () => {
    vi.mocked(graphApi.fetchGapsDetailed).mockReturnValue(new Promise(() => {}));
    render(<GapTab projectId="proj-1" />);
    await waitFor(() => expect(screen.getByText(/đang phân tích/i)).toBeInTheDocument());
  });

  it('hiển thị empty state khi không có gaps', async () => {
    vi.mocked(graphApi.fetchGapsDetailed).mockResolvedValue({ items: [] });
    render(<GapTab projectId="proj-1" />);
    await waitFor(() =>
      expect(screen.getByText(/chưa phát hiện khoảng trống/i)).toBeInTheDocument(),
    );
  });

  it('hiển thị lỗi khi fetch thất bại', async () => {
    vi.mocked(graphApi.fetchGapsDetailed).mockRejectedValue(new Error('Network error'));
    render(<GapTab projectId="proj-1" />);
    await waitFor(() =>
      expect(screen.getByText(/không thể tải danh sách khoảng trống/i)).toBeInTheDocument(),
    );
  });

  it('nhóm card theo 3 loại gap', async () => {
    vi.mocked(graphApi.fetchGapsDetailed).mockResolvedValue({ items: GAP_ITEMS });
    render(<GapTab projectId="proj-1" />);
    await waitFor(() => screen.getByText('Hai nghiên cứu đưa ra kết luận trái ngược nhau'));

    expect(screen.getAllByText(/^mâu thuẫn$/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/limitation chưa giải quyết/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/cụm cô lập/i).length).toBeGreaterThanOrEqual(1);
  });

  it('hiển thị đúng nội dung card contradiction', async () => {
    vi.mocked(graphApi.fetchGapsDetailed).mockResolvedValue({ items: [GAP_ITEMS[0]] });
    render(<GapTab projectId="proj-1" />);
    await waitFor(() => screen.getByText('Hai nghiên cứu đưa ra kết luận trái ngược nhau'));
    expect(screen.getByText('Finding 1 / Finding 2')).toBeInTheDocument();
    // Tên bài báo hiển thị ở dòng "Nghiên cứu liên quan" (không nhồi vào tiêu đề)
    expect(screen.getByText(/nghiên cứu liên quan/i)).toBeInTheDocument();
    expect(screen.getByText(/Paper A.*Paper B/)).toBeInTheDocument();
  });

  it('khử trùng tên bài báo ở dòng "Nghiên cứu liên quan" (mâu thuẫn nội tại cùng 1 bài)', async () => {
    const samePaperItem = {
      ...GAP_ITEMS[0],
      title: 'Hai kết luận trái ngược trong cùng một nghiên cứu',
      papers: [
        { paper_id: 'p1', title: 'Tổng quan ngô Bt' },
        { paper_id: 'p1', title: 'Tổng quan ngô Bt' },
      ],
    };
    vi.mocked(graphApi.fetchGapsDetailed).mockResolvedValue({ items: [samePaperItem] });
    render(<GapTab projectId="proj-1" />);
    await waitFor(() => screen.getByText('Hai kết luận trái ngược trong cùng một nghiên cứu'));
    // Tên bài chỉ xuất hiện 1 lần trong dòng (đã khử trùng theo paper_id), không lặp "X, X"
    const papersLine = screen.getByText(/nghiên cứu liên quan/i).parentElement;
    const occurrences = (papersLine?.textContent?.match(/Tổng quan ngô Bt/g) ?? []).length;
    expect(occurrences).toBe(1);
  });

  it('dòng bằng chứng dùng nhãn i18n, không lộ khoá/ID nội bộ', async () => {
    vi.mocked(graphApi.fetchGapsDetailed).mockResolvedValue({ items: [GAP_ITEMS[0]] });
    render(<GapTab projectId="proj-1" />);
    await waitFor(() => screen.getByText('Hai nghiên cứu đưa ra kết luận trái ngược nhau'));
    // Nhãn thân thiện thay vì "finding_count=2"
    expect(screen.getByText(/số phát hiện liên quan: 2/i)).toBeInTheDocument();
    expect(screen.queryByText(/finding_count=/i)).not.toBeInTheDocument();
  });

  it('nút "Mở trên Bản đồ Tri thức" gọi setActiveTab + requestGapFocus', async () => {
    vi.mocked(graphApi.fetchGapsDetailed).mockResolvedValue({ items: [GAP_ITEMS[0]] });
    render(<GapTab projectId="proj-1" />);
    await waitFor(() => screen.getByText('Hai nghiên cứu đưa ra kết luận trái ngược nhau'));

    const openBtn = screen.getAllByRole('button', { name: /mở trên bản đồ/i })[0];
    fireEvent.click(openBtn);

    expect(mockSetActiveTab).toHaveBeenCalledWith('graph');
    expect(mockRequestGapFocus).toHaveBeenCalledWith('p1');
  });

  it('nút "Giải thích khoảng trống này" gọi setPendingChatInput với title gap', async () => {
    vi.mocked(graphApi.fetchGapsDetailed).mockResolvedValue({ items: [GAP_ITEMS[0]] });
    render(<GapTab projectId="proj-1" />);
    await waitFor(() => screen.getByText('Hai nghiên cứu đưa ra kết luận trái ngược nhau'));

    const explainBtn = screen.getAllByRole('button', { name: /giải thích khoảng trống/i })[0];
    fireEvent.click(explainBtn);

    expect(mockSetPendingChatInput).toHaveBeenCalled();
    const callArg = mockSetPendingChatInput.mock.calls[0][0] as string;
    expect(callArg).toContain('Hai nghiên cứu đưa ra kết luận trái ngược nhau');
  });

  it('fetchGapsDetailed được gọi với projectId đúng', async () => {
    vi.mocked(graphApi.fetchGapsDetailed).mockResolvedValue({ items: [] });
    render(<GapTab projectId="proj-xyz" />);
    await waitFor(() => expect(graphApi.fetchGapsDetailed).toHaveBeenCalledWith('proj-xyz'));
  });
});
