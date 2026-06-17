import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import { CitationBadge } from '../CitationBadge';

vi.mock('@/api/citations', () => ({
  getCitationDetail: vi.fn(),
}));

import { getCitationDetail } from '@/api/citations';

const mockGet = getCitationDetail as ReturnType<typeof vi.fn>;

describe('CitationBadge', () => {
  beforeEach(() => {
    mockGet.mockReset();
  });

  it('renders badge with label', () => {
    render(<CitationBadge citationId="1" label="[1]" />);
    expect(screen.getByText('[1]')).toBeInTheDocument();
  });

  it('shows loading on hover', async () => {
    mockGet.mockReturnValue(new Promise(() => {})); // never resolves
    render(<CitationBadge citationId="1" label="[1]" />);
    await userEvent.hover(screen.getByText('[1]'));
    expect(screen.getByText('Đang tải...')).toBeInTheDocument();
  });

  it('shows citation data after successful fetch', async () => {
    mockGet.mockResolvedValue({ title: 'Paper A', text: 'Apple color is red...' });
    render(<CitationBadge citationId="1" label="[1]" />);
    await userEvent.hover(screen.getByText('[1]'));
    await waitFor(() => expect(screen.getByText('Paper A')).toBeInTheDocument());
    expect(screen.getByText('Apple color is red...')).toBeInTheDocument();
  });

  it('shows error message on API failure', async () => {
    mockGet.mockRejectedValue(new Error('404'));
    render(<CitationBadge citationId="999" label="[999]" />);
    await userEvent.hover(screen.getByText('[999]'));
    await waitFor(() =>
      expect(screen.getByText('Không tìm thấy thông tin trích dẫn')).toBeInTheDocument()
    );
  });

  it('hides tooltip on mouse leave', async () => {
    mockGet.mockResolvedValue({ title: 'Paper A', text: 'content' });
    render(<CitationBadge citationId="1" label="[1]" />);
    const badge = screen.getByText('[1]');
    await userEvent.hover(badge);
    await userEvent.unhover(badge);
    expect(screen.queryByText('Đang tải...')).not.toBeInTheDocument();
  });

  it('does not show tooltip when fetch resolves after mouse already left', async () => {
    let resolveFetch: (v: { title: string; text: string }) => void = () => {};
    mockGet.mockReturnValue(
      new Promise((resolve) => {
        resolveFetch = resolve;
      }),
    );
    render(<CitationBadge citationId="1" label="[1]" />);
    const badge = screen.getByText('[1]');
    await userEvent.hover(badge);
    await userEvent.unhover(badge); // leave before the API responds
    resolveFetch({ title: 'Paper A', text: 'stale content' });
    await waitFor(() =>
      expect(screen.queryByText('Đang tải...')).not.toBeInTheDocument(),
    );
    // Stale response must not resurrect the tooltip after the user left.
    expect(screen.queryByText('Paper A')).not.toBeInTheDocument();
    expect(screen.queryByText('stale content')).not.toBeInTheDocument();
  });
});
