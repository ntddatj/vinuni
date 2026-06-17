import { useEffect, useRef, useState } from 'react';
import { useTranslation } from '@/i18n/useTranslation';
import { useChatStore } from '@/store/chatStore';
import { useProjectStore } from '@/store/projectStore';
import { useWorkspaceStore } from '@/store/workspaceStore';
import { createThread, sendMessage, getSuggestions, type Suggestion } from '@/api/chat';
import { ChatHistoryPopover } from './ChatHistoryPopover';
import styles from './ChatbotPanel.module.css';
import { toast } from 'sonner';

const DEFAULT_WIDTH = 25;
const MIN_WIDTH = 20;
const MAX_WIDTH = 40;

export function ChatbotPanel() {
  const [width, setWidth] = useState(DEFAULT_WIDTH);
  const [collapsed, setCollapsed] = useState(false);
  const [lastWidth, setLastWidth] = useState(DEFAULT_WIDTH);
  const [showHistory, setShowHistory] = useState(false);
  const [inputValue, setInputValue] = useState('');
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const isDragging = useRef(false);
  const cleanupDragRef = useRef<(() => void) | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const { t } = useTranslation();

  const activeProjectId = useProjectStore((s) => s.activeProjectId);
  const activeTab = useWorkspaceStore((s) => s.activeTab);
  const documentCount = useWorkspaceStore((s) => s.documentCount);
  const setActiveTab = useWorkspaceStore((s) => s.setActiveTab);
  const setUploadModalOpen = useWorkspaceStore((s) => s.setUploadModalOpen);
  const {
    messages,
    activeThreadId,
    isStreaming,
    streamingContent,
    isLoadingMessages,
    setActiveThreadId,
    setMessages,
    setStreaming,
    appendChunk,
    beginStreaming,
    commitStreamingMessage,
    addOptimisticUserMessage,
    removeMessage,
    reset,
  } = useChatStore();

  function closeStream() {
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
  }

  // Reset chat when project changes — đóng luôn stream đang chạy để tránh
  // chunk của project cũ chèn vào hội thoại mới.
  useEffect(() => {
    closeStream();
    reset();
  }, [activeProjectId]);

  useEffect(() => {
    if (!activeProjectId) {
      setSuggestions([]);
      return;
    }
    // Guard chống race: nếu đổi project/tab nhanh, bỏ qua response cũ về sau
    // để không đè lên suggestions mới (giống pattern `cancelled` ở DocumentList).
    let cancelled = false;
    getSuggestions({
      activeTab,
      documentCount,
      hasDraft: false,
    })
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

  // Đóng EventSource khi unmount để tránh leak kết nối.
  useEffect(() => {
    return () => closeStream();
  }, []);

  // Auto-scroll to bottom on new messages or streaming chunks
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  function handleMouseDown(e: React.MouseEvent) {
    e.preventDefault();
    isDragging.current = true;
    document.body.style.userSelect = 'none';
    document.body.style.cursor = 'col-resize';

    function onMouseMove(ev: MouseEvent) {
      if (!isDragging.current) return;
      const vw = window.innerWidth;
      const newPct = ((vw - ev.clientX) / vw) * 100;
      setWidth(Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, newPct)));
    }

    function onMouseUp() {
      isDragging.current = false;
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
      cleanupDragRef.current = null;
      document.body.style.userSelect = '';
      document.body.style.cursor = '';
    }

    cleanupDragRef.current = () => {
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
      document.body.style.userSelect = '';
      document.body.style.cursor = '';
    };

    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  }

  function handleDblClick() {
    setWidth(DEFAULT_WIDTH);
  }

  function toggleCollapse() {
    if (collapsed) {
      setCollapsed(false);
      setWidth(lastWidth);
    } else {
      setLastWidth(width);
      setCollapsed(true);
    }
  }

  async function handleNewChat() {
    if (!activeProjectId) return;
    try {
      const thread = await createThread(activeProjectId);
      setActiveThreadId(thread.id);
      setMessages([]);
    } catch {
      toast.error('Không thể tạo cuộc trò chuyện mới');
    }
  }

  async function handleSend() {
    if (!inputValue.trim() || !activeThreadId || isStreaming) return;

    const text = inputValue.trim();
    const optimisticId = addOptimisticUserMessage(text);
    setInputValue('');
    beginStreaming(); // isStreaming=true + reset streamingContent

    let runId: string;
    try {
      ({ runId } = await sendMessage(activeThreadId, text));
    } catch {
      // POST thất bại → gỡ optimistic message để không hiển thị tin chưa gửi được.
      removeMessage(optimisticId);
      setStreaming(false);
      toast.error('Không thể gửi tin nhắn');
      return;
    }

    closeStream(); // đảm bảo không có stream cũ còn mở
    const es = new EventSource(`/api/chat/stream?runId=${runId}`, { withCredentials: true });
    eventSourceRef.current = es;

    es.onmessage = (e) => {
      let data: { event?: string; chunk?: string };
      try {
        data = JSON.parse(e.data);
      } catch {
        return; // bỏ qua frame không hợp lệ (vd: keep-alive comment)
      }
      if (data.event === 'done') {
        commitStreamingMessage();
        closeStream();
      } else if (typeof data.chunk === 'string') {
        appendChunk(data.chunk);
      }
    };

    es.onerror = () => {
      if (es.readyState === EventSource.CLOSED) return;
      setStreaming(false);
      closeStream();
      toast.error('Lỗi kết nối stream');
    };
  }

  useEffect(() => {
    return () => {
      cleanupDragRef.current?.();
    };
  }, []);

  return (
    <>
      <button
        className={`${styles.toggleBtn} ${collapsed ? styles.toggleBtnCollapsed : ''}`}
        onClick={toggleCollapse}
        type="button"
        title={collapsed ? t('chat.show') : t('chat.hide')}
        style={{ right: collapsed ? 0 : `calc(${width}vw - 12px)` }}
      >
        {collapsed ? '‹' : '›'}
      </button>

      <div
        className={`${styles.panel} ${collapsed ? styles.panelCollapsed : ''}`}
        style={{ width: collapsed ? 0 : `${width}vw` }}
      >
        <div
          className={styles.resizeHandle}
          onMouseDown={handleMouseDown}
          onDoubleClick={handleDblClick}
          role="separator"
          aria-orientation="vertical"
        />

        <div className={styles.content}>
          <div className={styles.chatHeader}>
            <h3 className={styles.title}>{t('chat.title')}</h3>
            <div className={styles.actions}>
              <button
                onClick={() => setShowHistory(!showHistory)}
                title={t('chat.historyBtn')}
                type="button"
                disabled={!activeProjectId}
              >
                🕐
              </button>
              <button
                onClick={handleNewChat}
                title={t('chat.newChatBtn')}
                type="button"
                disabled={!activeProjectId}
              >
                ✏️
              </button>
            </div>
            {showHistory && activeProjectId && (
              <ChatHistoryPopover
                projectId={activeProjectId}
                onClose={() => setShowHistory(false)}
              />
            )}
          </div>

          <div className={styles.messages}>
            {!activeProjectId && <p className={styles.hint}>{t('chat.noProject')}</p>}
            {isLoadingMessages && <p className={styles.hint}>Đang tải tin nhắn...</p>}
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`${styles.bubble} ${msg.role === 'user' ? styles.userBubble : styles.aiBubble}`}
              >
                {msg.content}
              </div>
            ))}
            {isStreaming && (
              <div className={`${styles.bubble} ${styles.aiBubble}`}>
                {streamingContent === '' ? (
                  <span className={styles.thinking}>{t('chat.thinking')}</span>
                ) : (
                  <>
                    {streamingContent}
                    <span className={styles.cursor}>▋</span>
                  </>
                )}
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {suggestions.length > 0 && !isStreaming && (
            <div className={styles.suggestions}>
              {suggestions.map((s) => (
                <button
                  key={s.actionKey}
                  className={styles.suggestionPill}
                  onClick={() => handleSuggestionClick(s.actionKey)}
                  type="button"
                >
                  {s.label}
                </button>
              ))}
            </div>
          )}

          <div className={styles.inputArea}>
            <input
              className={styles.input}
              placeholder={activeProjectId ? t('chat.placeholder') : t('chat.inputDisabled')}
              disabled={!activeProjectId || isStreaming}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              type="text"
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
        </div>
      </div>
    </>
  );
}
