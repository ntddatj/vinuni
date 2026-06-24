import { useEffect, useRef, useState } from 'react';
import { useTranslation } from '@/i18n/useTranslation';
import { useChatStore } from '@/store/chatStore';
import { useProjectStore } from '@/store/projectStore';
import { useWorkspaceStore } from '@/store/workspaceStore';
import { createThread, sendMessage, getSuggestions, type Suggestion } from '@/api/chat';
import { toast } from 'sonner';
import styles from './ChatBar.module.css';

export function ChatBar() {
  const [inputValue, setInputValue] = useState('');
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const chatInputRef = useRef<HTMLTextAreaElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const citationMapRef = useRef<Record<string, string>>({});
  const { t } = useTranslation();

  const activeProjectId = useProjectStore((s) => s.activeProjectId);
  const activeTab = useWorkspaceStore((s) => s.activeTab);
  const documentCount = useWorkspaceStore((s) => s.documentCount);
  const setActiveTab = useWorkspaceStore((s) => s.setActiveTab);
  const setUploadModalOpen = useWorkspaceStore((s) => s.setUploadModalOpen);
  const pendingChatInput = useWorkspaceStore((s) => s.pendingChatInput);
  const setPendingChatInput = useWorkspaceStore((s) => s.setPendingChatInput);

  const {
    activeThreadId,
    isStreaming,
    setActiveThreadId,
    setStreaming,
    appendChunk,
    beginStreaming,
    commitStreamingMessage,
    addOptimisticUserMessage,
    removeMessage,
    setThinkingStatus,
    reset,
  } = useChatStore();

  function closeStream() {
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
  }

  useEffect(() => {
    closeStream();
    citationMapRef.current = {};
    setThinkingStatus(null);
    reset();
  }, [activeProjectId]);

  // Graph→Chat bridge: khi có pendingChatInput → prefill input + focus
  useEffect(() => {
    if (!pendingChatInput) return;
    setInputValue(pendingChatInput);
    setPendingChatInput(null);
    setTimeout(() => chatInputRef.current?.focus(), 50);
  }, [pendingChatInput, setPendingChatInput]);

  // Auto-resize: textarea cao theo nội dung. height='auto' để scrollHeight phản ánh
  // đúng chiều cao thật, rồi gán = scrollHeight. CSS max-height (½ màn hình) + overflow-y
  // tự lo phần giới hạn và scroll khi nội dung quá dài.
  useEffect(() => {
    const el = chatInputRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${el.scrollHeight}px`;
  }, [inputValue]);

  useEffect(() => {
    if (!activeProjectId) {
      setSuggestions([]);
      return;
    }
    let cancelled = false;
    getSuggestions({ activeTab, documentCount, hasDraft: false })
      .then((data) => {
        if (!cancelled) setSuggestions(data);
      })
      .catch(() => {
        if (!cancelled) setSuggestions([]);
      });
    return () => {
      cancelled = true;
    };
  }, [activeProjectId, documentCount, activeTab]);

  function handleSuggestionClick(actionKey: string) {
    switch (actionKey) {
      case 'open_upload':
        setActiveTab('library');
        setUploadModalOpen(true);
        break;
      case 'navigate_library':
        setActiveTab('library');
        break;
      case 'navigate_graph':
        setActiveTab('graph');
        break;
      case 'navigate_writing':
        setActiveTab('writing');
        break;
      case 'focus_search':
        setActiveTab('library');
        break;
      default:
        break;
    }
  }

  useEffect(() => {
    return () => closeStream();
  }, []);

  async function handleSend() {
    if (!inputValue.trim() || !activeProjectId || isStreaming) return;

    let threadId = activeThreadId;
    if (!threadId) {
      try {
        const thread = await createThread(activeProjectId);
        setActiveThreadId(thread.id);
        threadId = thread.id;
      } catch {
        toast.error('Không thể tạo cuộc trò chuyện mới');
        return;
      }
    }

    const text = inputValue.trim();
    const optimisticId = addOptimisticUserMessage(text);
    setInputValue('');
    citationMapRef.current = {};
    beginStreaming();

    let runId: string;
    try {
      ({ runId } = await sendMessage(threadId, text));
    } catch {
      removeMessage(optimisticId);
      setStreaming(false);
      toast.error('Không thể gửi tin nhắn');
      return;
    }

    closeStream();
    const es = new EventSource(`/api/chat/stream?runId=${runId}`, { withCredentials: true });
    eventSourceRef.current = es;

    es.onmessage = (e) => {
      let data: {
        event?: string;
        chunk?: string;
        content?: string;
        data?: Record<string, string>;
        status?: string;
      };
      try {
        data = JSON.parse(e.data);
      } catch {
        return;
      }
      if (data.event === 'done') {
        setThinkingStatus(null);
        commitStreamingMessage(data.content, citationMapRef.current);
        citationMapRef.current = {};
        closeStream();
      } else if (data.event === 'citation_map') {
        citationMapRef.current = data.data ?? {};
      } else if (data.event === 'agent_thinking') {
        setThinkingStatus(data.status ?? null);
      } else if (typeof data.chunk === 'string') {
        setThinkingStatus(null);
        appendChunk(data.chunk);
      }
    };

    es.onerror = () => {
      if (es.readyState === EventSource.CLOSED) return;
      setStreaming(false);
      setThinkingStatus(null);
      closeStream();
      toast.error('Lỗi kết nối stream');
    };
  }

  return (
    <div className={styles.chatbar}>
      <div className={styles.inputRow}>
        <textarea
          ref={chatInputRef}
          className={styles.input}
          placeholder={activeProjectId ? t('chat.placeholder') : t('chat.inputDisabled')}
          disabled={!activeProjectId || isStreaming}
          value={inputValue}
          rows={1}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
        />
        <button
          className={styles.sendBtn}
          onClick={handleSend}
          disabled={!activeProjectId || isStreaming || !inputValue.trim()}
          type="button"
        >
          {t('chat.sendBtn')}
        </button>
      </div>
      {suggestions.length > 0 && !isStreaming && (
        <div className={styles.pills}>
          {suggestions.map((s) => (
            <button
              key={s.actionKey}
              className={styles.pill}
              onClick={() => handleSuggestionClick(s.actionKey)}
              type="button"
            >
              {s.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
