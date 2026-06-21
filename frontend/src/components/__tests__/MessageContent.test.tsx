import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';
import { MessageContent, injectCitations } from '../MessageContent';

// Mock react-markdown để render children trực tiếp — test logic citation, không test markdown parser
vi.mock('react-markdown', () => ({
  default: ({ children, components }: { children: string; components: Record<string, (props: { children: string }) => React.ReactNode> }) => {
    const PComponent = components?.p;
    if (PComponent) {
      return <div data-testid="markdown">{PComponent({ children })}</div>;
    }
    return <div data-testid="markdown">{children}</div>;
  },
}));

vi.mock('remark-gfm', () => ({ default: () => {} }));
vi.mock('rehype-sanitize', () => ({ default: () => {} }));

vi.mock('../CitationBadge', () => ({
  CitationBadge: ({ label, citationId }: { label: string; citationId: string }) => (
    <span data-testid="citation-badge" data-citation-id={citationId}>{label}</span>
  ),
}));

describe('MessageContent', () => {
  it('renders plain text without citations', () => {
    render(<MessageContent content="Đây là câu trả lời." />);
    expect(screen.getByText('Đây là câu trả lời.')).toBeInTheDocument();
    expect(screen.queryByTestId('citation-badge')).toBeNull();
  });

  it('renders citation badge for [N] pattern', () => {
    render(<MessageContent content="Nghiên cứu [1] xác nhận." />);
    const badge = screen.getByTestId('citation-badge');
    expect(badge).toHaveTextContent('[1]');
  });

  it('resolves ordinal to UUID via citationMap', () => {
    render(
      <MessageContent
        content="Xem [1] để biết thêm."
        citationMap={{ '1': 'uuid-abc-123' }}
      />,
    );
    const badge = screen.getByTestId('citation-badge');
    expect(badge).toHaveAttribute('data-citation-id', 'uuid-abc-123');
  });

  it('falls back to ordinal when citationMap missing', () => {
    render(<MessageContent content="Xem [1] để biết thêm." />);
    const badge = screen.getByTestId('citation-badge');
    expect(badge).toHaveAttribute('data-citation-id', '1');
  });

  it('renders multiple citation badges', () => {
    render(<MessageContent content="Xem [1] và [2] để biết thêm." />);
    const badges = screen.getAllByTestId('citation-badge');
    expect(badges).toHaveLength(2);
    expect(badges[0]).toHaveTextContent('[1]');
    expect(badges[1]).toHaveTextContent('[2]');
  });

  it('handles content with no text between citations', () => {
    render(<MessageContent content="[1][2]" />);
    const badges = screen.getAllByTestId('citation-badge');
    expect(badges).toHaveLength(2);
  });
});

// Test trực tiếp injectCitations: đây là nhánh đệ quy mà mock react-markdown
// (chỉ truyền string vào `p`) không chạm tới — citation nằm trong inline element
// (bold/italic/link) và quy tắc bỏ qua code. (AC#3)
describe('injectCitations (nested elements)', () => {
  function renderNode(node: React.ReactNode) {
    return render(<div>{node}</div>);
  }

  it('injects badge for [N] inside a bold element', () => {
    renderNode(injectCitations(<strong>báo cáo [1]</strong>, { '1': 'uuid-1' }));
    const badge = screen.getByTestId('citation-badge');
    expect(badge).toHaveTextContent('[1]');
    expect(badge).toHaveAttribute('data-citation-id', 'uuid-1');
  });

  it('injects badges across mixed string + element children', () => {
    renderNode(
      injectCitations(
        ['Theo ', <strong key="s">báo cáo [1]</strong>, ' thì [2] đúng.'],
        undefined,
      ),
    );
    const badges = screen.getAllByTestId('citation-badge');
    expect(badges).toHaveLength(2);
    expect(badges[0]).toHaveTextContent('[1]');
    expect(badges[1]).toHaveTextContent('[2]');
  });

  it('does NOT inject a badge inside a code element', () => {
    renderNode(injectCitations(<code>arr[1]</code>, undefined));
    expect(screen.queryByTestId('citation-badge')).toBeNull();
    expect(screen.getByText('arr[1]')).toBeInTheDocument();
  });
});
