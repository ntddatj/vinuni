import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ChatBar } from '../ChatBar';

// Mutable mock state điều khiển được theo từng test (vi.mock bị hoist lên đầu module).
const h = vi.hoisted(() => ({
  projectState: { activeProjectId: null as string | null },
  chat: {
    activeThreadId: null as string | null,
    isStreaming: false,
    setActiveThreadId: vi.fn(),
    setStreaming: vi.fn(),
    appendChunk: vi.fn(),
    beginStreaming: vi.fn(),
    commitStreamingMessage: vi.fn(),
    addOptimisticUserMessage: vi.fn(() => 'optimistic-id'),
    removeMessage: vi.fn(),
    setThinkingStatus: vi.fn(),
    reset: vi.fn(),
  },
  sendMessage: vi.fn(),
  createThread: vi.fn(),
  getSuggestions: vi.fn(() => Promise.resolve([])),
}));

vi.mock('@/store/languageStore', () => ({
  useLanguageStore: (selector: (s: { lang: 'vi' }) => unknown) => selector({ lang: 'vi' }),
}));

vi.mock('@/store/chatStore', () => ({
  useChatStore: () => h.chat,
}));

vi.mock('@/store/projectStore', () => ({
  useProjectStore: (selector: (s: { activeProjectId: string | null }) => unknown) =>
    selector(h.projectState),
}));

vi.mock('@/store/workspaceStore', () => ({
  useWorkspaceStore: (selector: (s: {
    activeTab: string;
    documentCount: number;
    setActiveTab: () => void;
    setUploadModalOpen: () => void;
    pendingChatInput: null;
    setPendingChatInput: () => void;
  }) => unknown) =>
    selector({
      activeTab: 'library',
      documentCount: 0,
      setActiveTab: () => {},
      setUploadModalOpen: () => {},
      pendingChatInput: null,
      setPendingChatInput: () => {},
    }),
}));

vi.mock('@/api/chat', () => ({
  getSuggestions: h.getSuggestions,
  sendMessage: h.sendMessage,
  createThread: h.createThread,
}));

// jsdom không có EventSource — stub tối thiểu để handleSend không ném lỗi.
class FakeEventSource {
  static CLOSED = 2;
  onmessage: ((e: MessageEvent) => void) | null = null;
  onerror: ((e: Event) => void) | null = null;
  readyState = 1;
  url: string;
  constructor(url: string) {
    this.url = url;
  }
  close() {
    this.readyState = FakeEventSource.CLOSED;
  }
}

beforeEach(() => {
  vi.clearAllMocks();
  h.projectState.activeProjectId = null;
  h.chat.activeThreadId = null;
  h.chat.isStreaming = false;
  h.chat.addOptimisticUserMessage.mockReturnValue('optimistic-id');
  h.getSuggestions.mockResolvedValue([]);
  vi.stubGlobal('EventSource', FakeEventSource);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('ChatBar', () => {
  it('renders input field', () => {
    render(<ChatBar />);
    expect(screen.getByPlaceholderText('Chọn dự án để chat...')).toBeInTheDocument();
  });

  it('renders Gửi button', () => {
    render(<ChatBar />);
    expect(screen.getByText('Gửi')).toBeInTheDocument();
  });

  it('input is disabled when no project selected', () => {
    render(<ChatBar />);
    const input = screen.getByPlaceholderText('Chọn dự án để chat...');
    expect(input).toBeDisabled();
  });

  it('Gửi button is disabled when no project selected', () => {
    render(<ChatBar />);
    expect(screen.getByText('Gửi')).toBeDisabled();
  });

  it('routes a send through the chat API and begins streaming (AC#6)', async () => {
    h.projectState.activeProjectId = 'p1';
    h.chat.activeThreadId = 't1';
    h.sendMessage.mockResolvedValue({ runId: 'r1' });

    render(<ChatBar />);
    const input = screen.getByPlaceholderText('Bạn cần tôi hỗ trợ gì...');
    fireEvent.change(input, { target: { value: 'xin chào' } });
    fireEvent.click(screen.getByText('Gửi'));

    await waitFor(() => expect(h.sendMessage).toHaveBeenCalledWith('t1', 'xin chào'));
    expect(h.chat.addOptimisticUserMessage).toHaveBeenCalledWith('xin chào');
    expect(h.chat.beginStreaming).toHaveBeenCalled();
    // Không có activeThreadId trước đó? Ở đây đã có 't1' nên không tạo thread mới.
    expect(h.createThread).not.toHaveBeenCalled();
  });

  it('lazily creates a thread when none exists before sending (AC#6)', async () => {
    h.projectState.activeProjectId = 'p1';
    h.chat.activeThreadId = null;
    h.createThread.mockResolvedValue({ id: 't-new' });
    h.sendMessage.mockResolvedValue({ runId: 'r2' });

    render(<ChatBar />);
    const input = screen.getByPlaceholderText('Bạn cần tôi hỗ trợ gì...');
    fireEvent.change(input, { target: { value: 'câu hỏi' } });
    fireEvent.click(screen.getByText('Gửi'));

    await waitFor(() => expect(h.createThread).toHaveBeenCalledWith('p1'));
    await waitFor(() => expect(h.sendMessage).toHaveBeenCalledWith('t-new', 'câu hỏi'));
  });
});
