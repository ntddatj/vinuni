import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';
import { MessageContent } from '../MessageContent';

vi.mock('../CitationBadge', () => ({
  CitationBadge: ({ label }: { label: string }) => (
    <span data-testid="citation-badge">{label}</span>
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

  it('renders multiple citation badges', () => {
    render(<MessageContent content="Xem [1] và [2] để biết thêm." />);
    const badges = screen.getAllByTestId('citation-badge');
    expect(badges).toHaveLength(2);
    expect(badges[0]).toHaveTextContent('[1]');
    expect(badges[1]).toHaveTextContent('[2]');
  });

  it('preserves text segments between citations', () => {
    render(<MessageContent content="A [1] B [2] C" />);
    const noNorm = { normalizer: (text: string) => text };
    expect(screen.getByText('A ', noNorm)).toBeInTheDocument();
    expect(screen.getByText(' B ', noNorm)).toBeInTheDocument();
    expect(screen.getByText(' C', noNorm)).toBeInTheDocument();
  });

  it('handles content with no text between citations', () => {
    render(<MessageContent content="[1][2]" />);
    const badges = screen.getAllByTestId('citation-badge');
    expect(badges).toHaveLength(2);
  });
});
