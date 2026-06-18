import { render, screen, fireEvent } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { NodeDetailCard } from '../NodeDetailCard';
import type { GraphNode, GraphEdge } from '@/types/graph';

const mockSetPendingChatInput = vi.fn();
const mockSetActiveTab = vi.fn();

vi.mock('@/store/workspaceStore', () => ({
  useWorkspaceStore: (selector: (s: Record<string, unknown>) => unknown) =>
    selector({
      setPendingChatInput: mockSetPendingChatInput,
      setActiveTab: mockSetActiveTab,
    }),
}));

vi.mock('@/store/languageStore', () => ({
  useLanguageStore: (selector: (s: { lang: 'vi' }) => unknown) => selector({ lang: 'vi' }),
}));

const PAPER_NODE: GraphNode = {
  id: 'paper-1',
  label: 'paper',
  title: 'Attention Is All You Need',
  authors: ['Vaswani, A.'],
  year: 2017,
  abstract: 'The dominant sequence transduction models...',
  state: 'full_text',
  project_id: 'proj-1',
};

const AUTHOR_NODE: GraphNode = {
  id: 'author-1',
  label: 'author',
  title: 'Vaswani, A.',
  authors: [],
  year: null,
  abstract: null,
  state: null,
  project_id: 'proj-1',
};

describe('NodeDetailCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('hiển thị tiêu đề paper', () => {
    render(<NodeDetailCard node={PAPER_NODE} allNodes={[]} onClose={vi.fn()} />);
    expect(screen.getByText('Attention Is All You Need')).toBeInTheDocument();
  });

  it('nút "Hỏi AI" set pendingChatInput đúng và KHÔNG đổi tab', () => {
    render(<NodeDetailCard node={PAPER_NODE} allNodes={[]} onClose={vi.fn()} />);
    const btn = screen.getByText(/hỏi ai/i);
    fireEvent.click(btn);
    expect(mockSetPendingChatInput).toHaveBeenCalledWith(
      `Hãy phân tích bài báo: Attention Is All You Need`,
    );
    // Chat sống ở panel phải (luôn mounted) → không được switch tab center.
    expect(mockSetActiveTab).not.toHaveBeenCalled();
  });

  it('card paper hiển thị tác giả suy ra từ cạnh AUTHORED_BY', () => {
    const edges: GraphEdge[] = [
      { id: 'e1', source: 'paper-1', target: 'author-1', type: 'AUTHORED_BY' },
    ];
    render(
      <NodeDetailCard
        node={PAPER_NODE}
        allNodes={[PAPER_NODE, AUTHOR_NODE]}
        allEdges={edges}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByText(/Vaswani, A\. \(2017\)/)).toBeInTheDocument();
  });

  it('card author liệt kê paper qua cạnh AUTHORED_BY', () => {
    const edges: GraphEdge[] = [
      { id: 'e1', source: 'paper-1', target: 'author-1', type: 'AUTHORED_BY' },
    ];
    render(
      <NodeDetailCard
        node={AUTHOR_NODE}
        allNodes={[PAPER_NODE, AUTHOR_NODE]}
        allEdges={edges}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByText('Attention Is All You Need')).toBeInTheDocument();
  });

  it('nút đóng gọi onClose', () => {
    const onClose = vi.fn();
    render(<NodeDetailCard node={PAPER_NODE} allNodes={[]} onClose={onClose} />);
    fireEvent.click(screen.getByLabelText(/đóng/i));
    expect(onClose).toHaveBeenCalled();
  });

  it('card author hiển thị tên tác giả', () => {
    render(<NodeDetailCard node={AUTHOR_NODE} allNodes={[PAPER_NODE]} onClose={vi.fn()} />);
    expect(screen.getByText('Vaswani, A.')).toBeInTheDocument();
  });

  it('card author không có nút Hỏi AI', () => {
    render(<NodeDetailCard node={AUTHOR_NODE} allNodes={[]} onClose={vi.fn()} />);
    expect(screen.queryByText(/hỏi ai/i)).not.toBeInTheDocument();
  });
});
