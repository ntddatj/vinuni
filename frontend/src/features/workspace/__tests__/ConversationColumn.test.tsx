import { render, screen, fireEvent } from '@testing-library/react';
import { ConversationColumn } from '../ConversationColumn';

vi.mock('@/store/languageStore', () => ({
  useLanguageStore: (selector: (s: { lang: 'vi' }) => unknown) => selector({ lang: 'vi' }),
}));

vi.mock('@/store/chatStore', () => ({
  useChatStore: () => ({
    messages: [],
    isStreaming: false,
    streamingContent: '',
    isLoadingMessages: false,
    thinkingStatus: null,
    setActiveThreadId: () => {},
    setMessages: () => {},
  }),
}));

vi.mock('@/store/projectStore', () => ({
  useProjectStore: (selector: (s: { activeProjectId: null }) => unknown) =>
    selector({ activeProjectId: null }),
}));

describe('ConversationColumn', () => {
  it('renders conversation title', () => {
    render(<ConversationColumn />);
    expect(screen.getByText('Nội dung trò chuyện')).toBeInTheDocument();
  });

  it('renders resize handle', () => {
    render(<ConversationColumn />);
    const handle = document.querySelector('[role="separator"]');
    expect(handle).not.toBeNull();
  });

  it('collapses when collapse button clicked', () => {
    render(<ConversationColumn />);
    const collapseBtn = screen.getByTitle('Ẩn Chat');
    fireEvent.click(collapseBtn);
    expect(screen.queryByText('Nội dung trò chuyện')).not.toBeInTheDocument();
    expect(screen.getByTitle('Hiện Chat')).toBeInTheDocument();
  });

  it('expands back after collapse', () => {
    render(<ConversationColumn />);
    fireEvent.click(screen.getByTitle('Ẩn Chat'));
    fireEvent.click(screen.getByTitle('Hiện Chat'));
    expect(screen.getByText('Nội dung trò chuyện')).toBeInTheDocument();
  });

  it('resets width to default on double click of resize handle', () => {
    render(<ConversationColumn />);
    const handle = document.querySelector('[role="separator"]');
    expect(handle).not.toBeNull();
    fireEvent.doubleClick(handle!);
    const col = document.querySelector('[data-role="conv-column"]') as HTMLElement;
    expect(col?.style.width).toBe('340px');
  });
});
