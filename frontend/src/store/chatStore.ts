import { create } from 'zustand';
import type { ChatThread, ChatMessage } from '@/types/chat';

interface ChatState {
  threads: ChatThread[];
  activeThreadId: string | null;
  messages: ChatMessage[];
  isLoadingThreads: boolean;
  isLoadingMessages: boolean;
  isStreaming: boolean;
  streamingContent: string;
  thinkingStatus: string | null;

  setThreads: (threads: ChatThread[]) => void;
  updateThreadTitle: (id: string, title: string) => void;
  removeThread: (id: string) => void;
  setActiveThreadId: (id: string | null) => void;
  setMessages: (messages: ChatMessage[]) => void;
  appendChunk: (chunk: string) => void;
  beginStreaming: () => void;
  commitStreamingMessage: (cleanedContent?: string, citationMap?: Record<string, string>) => void;
  setLoadingThreads: (v: boolean) => void;
  setLoadingMessages: (v: boolean) => void;
  setStreaming: (v: boolean) => void;
  setThinkingStatus: (status: string | null) => void;
  addOptimisticUserMessage: (content: string) => string;
  removeMessage: (id: string) => void;
  reset: () => void;
}

const INIT: Pick<
  ChatState,
  | 'threads'
  | 'activeThreadId'
  | 'messages'
  | 'isLoadingThreads'
  | 'isLoadingMessages'
  | 'isStreaming'
  | 'streamingContent'
  | 'thinkingStatus'
> = {
  threads: [],
  activeThreadId: null,
  messages: [],
  isLoadingThreads: false,
  isLoadingMessages: false,
  isStreaming: false,
  streamingContent: '',
  thinkingStatus: null,
};

export const useChatStore = create<ChatState>()((set, get) => ({
  ...INIT,

  setThreads: (threads) => set({ threads }),
  updateThreadTitle: (id, title) =>
    set((s) => ({ threads: s.threads.map((t) => (t.id === id ? { ...t, title } : t)) })),
  removeThread: (id) => set((s) => ({ threads: s.threads.filter((t) => t.id !== id) })),
  setActiveThreadId: (id) => set({ activeThreadId: id }),
  setMessages: (messages) => set({ messages }),
  setLoadingThreads: (v) => set({ isLoadingThreads: v }),
  setLoadingMessages: (v) => set({ isLoadingMessages: v }),
  setStreaming: (v) => set({ isStreaming: v }),
  setThinkingStatus: (status) => set({ thinkingStatus: status }),

  appendChunk: (chunk) => set((s) => ({ streamingContent: s.streamingContent + chunk })),

  beginStreaming: () => set({ isStreaming: true, streamingContent: '', thinkingStatus: null }),

  commitStreamingMessage: (cleanedContent?: string, citationMap?: Record<string, string>) => {
    // Dùng cleanedContent từ SSE done event (đã qua guardrail) nếu có,
    // fallback về streamingContent (bản chưa clean) cho backward compat
    const content = cleanedContent ?? get().streamingContent;
    // Luôn reset trạng thái streaming kể cả khi content rỗng,
    // nếu không isStreaming sẽ kẹt true và khoá input vĩnh viễn.
    if (!content) {
      set({ streamingContent: '', isStreaming: false });
      return;
    }
    const assistantMsg: ChatMessage = {
      id: `stream-${Date.now()}`,
      threadId: get().activeThreadId ?? '',
      role: 'assistant',
      content,
      createdAt: new Date().toISOString(),
      citationMap,
    };
    set((s) => ({
      messages: [...s.messages, assistantMsg],
      streamingContent: '',
      isStreaming: false,
    }));
  },

  addOptimisticUserMessage: (content) => {
    const id = `optimistic-${Date.now()}`;
    const msg: ChatMessage = {
      id,
      threadId: get().activeThreadId ?? '',
      role: 'user',
      content,
      createdAt: new Date().toISOString(),
    };
    set((s) => ({ messages: [...s.messages, msg] }));
    return id;
  },

  removeMessage: (id) => set((s) => ({ messages: s.messages.filter((m) => m.id !== id) })),

  reset: () => set(INIT),
}));
