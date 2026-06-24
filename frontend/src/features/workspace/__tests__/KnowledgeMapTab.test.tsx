import { act, render, screen, waitFor, fireEvent } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { KnowledgeMapTab } from '../KnowledgeMapTab';
import * as graphApi from '@/api/graph';

const mocks = vi.hoisted(() => {
  let activeTab = 'graph';
  let gapFocusRequest: { paperId: string } | null = null;
  const clearGapFocus = vi.fn();
  const elementCollection = {
    length: 0,
    remove: vi.fn(),
    show: vi.fn(),
    hide: vi.fn(),
    style: vi.fn(),
    removeStyle: vi.fn(),
    map: vi.fn().mockReturnValue([]),
    lock: vi.fn(),
    unlock: vi.fn(),
    filter: vi.fn().mockReturnValue({
      layout: vi.fn().mockReturnValue({ run: vi.fn() }),
    }),
    layout: vi.fn().mockReturnValue({ run: vi.fn() }),
  };
  const addClassMock = vi.fn();
  const selectMock = vi.fn();
  const nodeElement = {
    addClass: addClassMock,
    removeClass: vi.fn(),
    select: selectMock,
    length: 1,
  };
  const cy = {
    add: vi.fn().mockReturnThis(),
    elements: vi.fn().mockReturnValue({ ...elementCollection, removeClass: vi.fn() }),
    nodes: vi.fn().mockReturnValue(elementCollection),
    edges: vi.fn().mockReturnValue(elementCollection),
    getElementById: vi.fn().mockReturnValue(nodeElement),
    on: vi.fn(),
    off: vi.fn(),
    layout: vi.fn().mockReturnValue({ run: vi.fn() }),
    fit: vi.fn(),
    resize: vi.fn(),
    animate: vi.fn(),
    destroy: vi.fn(),
  };

  return {
    cy,
    addClassMock,
    selectMock,
    clearGapFocus,
    getActiveTab: () => activeTab,
    setActiveTab: (tab: string) => { activeTab = tab; },
    getGapFocusRequest: () => gapFocusRequest,
    setGapFocusRequest: (r: { paperId: string } | null) => { gapFocusRequest = r; },
  };
});

// Cytoscape crashes in jsdom because there's no real DOM canvas — mock it
vi.mock('cytoscape', () => {
  const CytoscapeMock = vi.fn().mockReturnValue(mocks.cy);
  (CytoscapeMock as unknown as { use: typeof vi.fn }).use = vi.fn();
  return { default: CytoscapeMock };
});

vi.mock('cytoscape-fcose', () => ({ default: {} }));

vi.mock('@/api/graph');

vi.mock('@/store/workspaceStore', () => ({
  useWorkspaceStore: (selector: (s: Record<string, unknown>) => unknown) =>
    selector({
      activeTab: mocks.getActiveTab(),
      setPendingChatInput: vi.fn(),
      setActiveTab: vi.fn(),
      gapFocusRequest: mocks.getGapFocusRequest(),
      clearGapFocus: mocks.clearGapFocus,
    }),
}));

vi.mock('@/store/languageStore', () => ({
  useLanguageStore: (selector: (s: { lang: 'vi' }) => unknown) => selector({ lang: 'vi' }),
}));

const EMPTY_GRAPH = { nodes: [], edges: [], has_more: false };
const GRAPH_WITH_DATA = {
  nodes: [
    {
      id: 'paper-1',
      label: 'paper' as const,
      title: 'GraphRAG under Fire',
      authors: [],
      year: 2025,
      abstract: null,
      state: 'full_text' as const,
      project_id: 'proj-1',
    },
    {
      id: 'proj-1:author',
      label: 'author' as const,
      title: 'Jiacheng Liang',
      authors: [],
      year: null,
      abstract: null,
      state: null,
      project_id: 'proj-1',
    },
  ],
  edges: [
    {
      id: 'edge-1',
      source: 'paper-1',
      target: 'proj-1:author',
      type: 'AUTHORED_BY',
    },
  ],
  has_more: false,
};

describe('KnowledgeMapTab', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();
    mocks.setActiveTab('graph');
    mocks.setGapFocusRequest(null);
    vi.mocked(graphApi.fetchGraph).mockResolvedValue(EMPTY_GRAPH);
    vi.mocked(graphApi.getSyncStatus).mockResolvedValue({ syncing: false });
  });

  it('hiển thị placeholder "Chọn một dự án" khi projectId là null', () => {
    render(<KnowledgeMapTab projectId={null} />);
    expect(screen.getByText(/chọn một dự án/i)).toBeInTheDocument();
  });

  it('không crash khi API trả empty graph', async () => {
    render(<KnowledgeMapTab projectId="proj-1" />);
    // No crash = test passes; fetchGraph called
    await waitFor(() => expect(graphApi.fetchGraph).toHaveBeenCalledWith('proj-1'));
  });

  it('tải graph khi tab chuyển từ library sang graph', async () => {
    mocks.setActiveTab('library');
    const { rerender } = render(<KnowledgeMapTab projectId="proj-1" />);

    await waitFor(() => expect(graphApi.fetchGraph).not.toHaveBeenCalled());

    mocks.setActiveTab('graph');
    rerender(<KnowledgeMapTab projectId="proj-1" />);

    await waitFor(() => expect(graphApi.fetchGraph).toHaveBeenCalledWith('proj-1'));
  });

  it('thêm graph elements và không hiện empty overlay khi API trả dữ liệu', async () => {
    vi.mocked(graphApi.fetchGraph).mockResolvedValue(GRAPH_WITH_DATA);

    render(<KnowledgeMapTab projectId="proj-1" />);

    await waitFor(() => expect(mocks.cy.add).toHaveBeenCalled());
    expect(screen.queryByText(/chưa có dữ liệu đồ thị/i)).not.toBeInTheDocument();
  });

  it('tải lại graph khi sync-status chuyển từ đang sync sang xong sync', async () => {
    const intervalCallbacks: Array<() => void> = [];
    const originalSetInterval = globalThis.setInterval;
    const originalClearInterval = globalThis.clearInterval;
    const setIntervalSpy = vi.spyOn(globalThis, 'setInterval').mockImplementation((callback, timeout, ...args) => {
      if (timeout === 10_000) {
        intervalCallbacks.push(callback as () => void);
        return originalSetInterval(() => undefined, timeout);
      }
      return originalSetInterval(callback, timeout, ...args);
    });
    const clearIntervalSpy = vi.spyOn(globalThis, 'clearInterval').mockImplementation((id) => {
      return originalClearInterval(id);
    });
    vi.mocked(graphApi.getSyncStatus)
      .mockResolvedValueOnce({ syncing: true })
      .mockResolvedValueOnce({ syncing: false });

    render(<KnowledgeMapTab projectId="proj-1" />);

    await waitFor(() => expect(graphApi.fetchGraph).toHaveBeenCalled());
    await screen.findByText(/đồ thị đang cập nhật/i);
    await waitFor(() => expect(intervalCallbacks.length).toBeGreaterThan(0));
    const fetchesBeforeSyncFinished = vi.mocked(graphApi.fetchGraph).mock.calls.length;

    await act(async () => {
      intervalCallbacks.at(-1)?.();
      await Promise.resolve();
    });

    await waitFor(() => expect(graphApi.getSyncStatus).toHaveBeenCalledTimes(2));
    await waitFor(() => {
      expect(vi.mocked(graphApi.fetchGraph).mock.calls.length).toBeGreaterThan(fetchesBeforeSyncFinished);
    });
    setIntervalSpy.mockRestore();
    clearIntervalSpy.mockRestore();
  });

  it('hiển thị toggle "Hiện tác giả"', async () => {
    render(<KnowledgeMapTab projectId="proj-1" />);
    expect(screen.getByText(/hiện tác giả/i)).toBeInTheDocument();
    await waitFor(() => expect(graphApi.fetchGraph).toHaveBeenCalledWith('proj-1'));
  });

  it('hiển thị nút reset view', async () => {
    render(<KnowledgeMapTab projectId="proj-1" />);
    expect(screen.getByText(/khôi phục góc nhìn/i)).toBeInTheDocument();
    await waitFor(() => expect(graphApi.fetchGraph).toHaveBeenCalledWith('proj-1'));
  });

  it('renders gap mode button', async () => {
    render(<KnowledgeMapTab projectId="proj-1" />);
    expect(screen.getByText(/tìm khoảng trống/i)).toBeInTheDocument();
    await waitFor(() => expect(graphApi.fetchGraph).toHaveBeenCalledWith('proj-1'));
  });

  it('toggles gap mode on click — fetchGaps called with projectId', async () => {
    vi.mocked(graphApi.fetchGaps).mockResolvedValue({ flagged_nodes: [], flagged_edges: [] });

    render(<KnowledgeMapTab projectId="proj-1" />);
    await waitFor(() => expect(graphApi.fetchGraph).toHaveBeenCalled());

    const gapBtn = screen.getByText(/tìm khoảng trống/i);
    fireEvent.click(gapBtn);

    await waitFor(() => expect(graphApi.fetchGaps).toHaveBeenCalledWith('proj-1'));
  });

  it('applies gap-contradiction class to contradiction nodes', async () => {
    vi.mocked(graphApi.fetchGaps).mockResolvedValue({
      flagged_nodes: [{ paper_id: 'p1', reason: 'has_contradiction' }],
      flagged_edges: [],
    });

    render(<KnowledgeMapTab projectId="proj-1" />);
    await waitFor(() => expect(graphApi.fetchGraph).toHaveBeenCalled());

    const gapBtn = screen.getByText(/tìm khoảng trống/i);
    fireEvent.click(gapBtn);

    await waitFor(() => expect(mocks.cy.getElementById).toHaveBeenCalledWith('p1'));
    await waitFor(() => expect(mocks.addClassMock).toHaveBeenCalledWith('gap-contradiction'));
  });

  it('removes gap classes on gap mode off', async () => {
    vi.mocked(graphApi.fetchGaps).mockResolvedValue({
      flagged_nodes: [{ paper_id: 'p1', reason: 'isolated_cluster' }],
      flagged_edges: [],
    });
    const removeClassMock = vi.fn();
    mocks.cy.elements.mockReturnValue({
      removeClass: removeClassMock,
      style: vi.fn(),
      removeStyle: vi.fn(),
      remove: vi.fn(),
      length: 0,
      map: vi.fn().mockReturnValue([]),
    });

    render(<KnowledgeMapTab projectId="proj-1" />);
    await waitFor(() => expect(graphApi.fetchGraph).toHaveBeenCalled());

    // Toggle ON
    fireEvent.click(screen.getByText(/tìm khoảng trống/i));
    await waitFor(() => expect(graphApi.fetchGaps).toHaveBeenCalled());

    // Toggle OFF — nút bây giờ đang hiện "Ẩn khoảng trống"
    fireEvent.click(screen.getByText(/ẩn khoảng trống/i));

    await waitFor(() => expect(removeClassMock).toHaveBeenCalledWith('gap-contradiction gap-unfilled gap-isolated'));
  });

  it('applies gap-unfilled class to has_unfilled_limitation nodes', async () => {
    vi.mocked(graphApi.fetchGaps).mockResolvedValue({
      flagged_nodes: [{ paper_id: 'p2', reason: 'has_unfilled_limitation' }],
      flagged_edges: [],
    });

    render(<KnowledgeMapTab projectId="proj-1" />);
    await waitFor(() => expect(graphApi.fetchGraph).toHaveBeenCalled());

    fireEvent.click(screen.getByText(/tìm khoảng trống/i));

    await waitFor(() => expect(mocks.cy.getElementById).toHaveBeenCalledWith('p2'));
    await waitFor(() => expect(mocks.addClassMock).toHaveBeenCalledWith('gap-unfilled'));
  });

  it('applies gap-isolated (blue) class to isolated_cluster nodes', async () => {
    vi.mocked(graphApi.fetchGaps).mockResolvedValue({
      flagged_nodes: [{ paper_id: 'p3', reason: 'isolated_cluster' }],
      flagged_edges: [],
    });

    render(<KnowledgeMapTab projectId="proj-1" />);
    await waitFor(() => expect(graphApi.fetchGraph).toHaveBeenCalled());

    fireEvent.click(screen.getByText(/tìm khoảng trống/i));

    await waitFor(() => expect(mocks.cy.getElementById).toHaveBeenCalledWith('p3'));
    await waitFor(() => expect(mocks.addClassMock).toHaveBeenCalledWith('gap-isolated'));
  });

  it('dedup: contradiction wins over unfilled for same paper', async () => {
    vi.mocked(graphApi.fetchGaps).mockResolvedValue({
      flagged_nodes: [
        { paper_id: 'p4', reason: 'has_contradiction' },
        { paper_id: 'p4', reason: 'has_unfilled_limitation' },
      ],
      flagged_edges: [],
    });

    render(<KnowledgeMapTab projectId="proj-1" />);
    await waitFor(() => expect(graphApi.fetchGraph).toHaveBeenCalled());

    fireEvent.click(screen.getByText(/tìm khoảng trống/i));

    await waitFor(() => expect(mocks.addClassMock).toHaveBeenCalledWith('gap-contradiction'));
    expect(mocks.addClassMock).not.toHaveBeenCalledWith('gap-unfilled');
  });

  it('passes gapMode to GraphLegend — gap legend items appear', async () => {
    vi.mocked(graphApi.fetchGaps).mockResolvedValue({ flagged_nodes: [], flagged_edges: [] });

    render(<KnowledgeMapTab projectId="proj-1" />);
    await waitFor(() => expect(graphApi.fetchGraph).toHaveBeenCalled());

    expect(screen.queryByText('Khoảng trống')).not.toBeInTheDocument();

    fireEvent.click(screen.getByText(/tìm khoảng trống/i));
    await waitFor(() => expect(graphApi.fetchGaps).toHaveBeenCalled());

    expect(screen.getByText('Khoảng trống')).toBeInTheDocument();
  });

  it('clears gap state when project is deselected mid-fetch — button not stuck disabled', async () => {
    // fetchGaps treo (chưa resolve) để mô phỏng cửa sổ in-flight
    let resolveGaps: (v: { flagged_nodes: never[]; flagged_edges: never[] }) => void = () => {};
    vi.mocked(graphApi.fetchGaps).mockReturnValue(
      new Promise((res) => {
        resolveGaps = res;
      }) as ReturnType<typeof graphApi.fetchGaps>,
    );

    const { rerender } = render(<KnowledgeMapTab projectId="proj-1" />);
    await waitFor(() => expect(graphApi.fetchGraph).toHaveBeenCalled());

    // Bật gap mode → fetchGaps in-flight, gapLoading = true
    fireEvent.click(screen.getByText(/tìm khoảng trống/i));
    await waitFor(() => expect(graphApi.fetchGaps).toHaveBeenCalledWith('proj-1'));

    // Bỏ chọn dự án khi fetch còn treo → effect chạy lại nhánh reset
    rerender(<KnowledgeMapTab projectId={null} />);

    // Resolve promise cũ (đã bị cancelled) — không được làm kẹt gapLoading
    await act(async () => {
      resolveGaps({ flagged_nodes: [], flagged_edges: [] });
    });

    // Legend gap đã ẩn (gapData cleared) → state đã được reset sạch
    expect(screen.queryByText('Khoảng trống')).not.toBeInTheDocument();
  });

  it('Gap→Map bridge: center + select node khi gapFocusRequest có & graph + gap data đã load', async () => {
    // gapFocusRequest set sẵn (mô phỏng GapTab bấm "Mở trên Bản đồ"). Khi graph load xong
    // (graphNodes>0) và gapData sẵn sàng → bật gap mode, select + center node, rồi clear signal.
    vi.mocked(graphApi.fetchGraph).mockResolvedValue(GRAPH_WITH_DATA);
    vi.mocked(graphApi.fetchGaps).mockResolvedValue({ flagged_nodes: [], flagged_edges: [] });
    mocks.setGapFocusRequest({ paperId: 'paper-1' });

    render(<KnowledgeMapTab projectId="proj-1" />);

    // gapMode bật do signal → fetchGaps được gọi
    await waitFor(() => expect(graphApi.fetchGaps).toHaveBeenCalledWith('proj-1'));
    // Node mục tiêu được lấy, select và center
    await waitFor(() => expect(mocks.cy.getElementById).toHaveBeenCalledWith('paper-1'));
    await waitFor(() => expect(mocks.selectMock).toHaveBeenCalled());
    await waitFor(() => expect(mocks.cy.animate).toHaveBeenCalled());
    // Signal một chiều được clear sau khi xử lý → không rò rỉ sang lần sau
    await waitFor(() => expect(mocks.clearGapFocus).toHaveBeenCalled());
  });

  it('Gap→Map bridge: KHÔNG center khi chưa ở tab graph (giữ signal, chưa clear)', async () => {
    // Ở tab khác (library): bridge không được chạy center/clear → signal vẫn còn để xử lý
    // khi người dùng thực sự sang tab Bản đồ.
    mocks.setActiveTab('library');
    vi.mocked(graphApi.fetchGraph).mockResolvedValue(GRAPH_WITH_DATA);
    mocks.setGapFocusRequest({ paperId: 'paper-1' });

    render(<KnowledgeMapTab projectId="proj-1" />);

    await waitFor(() => expect(graphApi.fetchGraph).not.toHaveBeenCalled());
    expect(mocks.selectMock).not.toHaveBeenCalled();
    expect(mocks.clearGapFocus).not.toHaveBeenCalled();
  });
});
