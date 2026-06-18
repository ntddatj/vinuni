import { act, render, screen, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { KnowledgeMapTab } from '../KnowledgeMapTab';
import * as graphApi from '@/api/graph';

const mocks = vi.hoisted(() => {
  let activeTab = 'graph';
  const elementCollection = {
    length: 0,
    remove: vi.fn(),
    show: vi.fn(),
    hide: vi.fn(),
    style: vi.fn(),
    map: vi.fn().mockReturnValue([]),
    lock: vi.fn(),
    unlock: vi.fn(),
    filter: vi.fn().mockReturnValue({
      layout: vi.fn().mockReturnValue({ run: vi.fn() }),
    }),
    layout: vi.fn().mockReturnValue({ run: vi.fn() }),
  };
  const cy = {
    add: vi.fn().mockReturnThis(),
    elements: vi.fn().mockReturnValue(elementCollection),
    nodes: vi.fn().mockReturnValue(elementCollection),
    edges: vi.fn().mockReturnValue(elementCollection),
    on: vi.fn(),
    off: vi.fn(),
    layout: vi.fn().mockReturnValue({ run: vi.fn() }),
    fit: vi.fn(),
    resize: vi.fn(),
    destroy: vi.fn(),
  };

  return {
    cy,
    getActiveTab: () => activeTab,
    setActiveTab: (tab: string) => { activeTab = tab; },
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
});
