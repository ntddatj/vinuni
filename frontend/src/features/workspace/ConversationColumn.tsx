import { useEffect, useRef, useState } from 'react';
import { useTranslation } from '@/i18n/useTranslation';
import { useChatStore } from '@/store/chatStore';
import { useProjectStore } from '@/store/projectStore';
import { createThread } from '@/api/chat';
import { ChatHistoryPopover } from './ChatHistoryPopover';
import { ChatBar } from './ChatBar';
import { MessageContent } from '@/components/MessageContent';
import { toast } from 'sonner';
import styles from './ConversationColumn.module.css';

const DEFAULT_WIDTH_PX = 340;
const MIN_WIDTH_PX = 220;
const MAX_WIDTH_PX = 640;

export function ConversationColumn() {
  const [width, setWidth] = useState(DEFAULT_WIDTH_PX);
  const [collapsed, setCollapsed] = useState(false);
  const [lastWidth, setLastWidth] = useState(DEFAULT_WIDTH_PX);
  const [showHistory, setShowHistory] = useState(false);
  const isDragging = useRef(false);
  const cleanupDragRef = useRef<(() => void) | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { t } = useTranslation();

  const activeProjectId = useProjectStore((s) => s.activeProjectId);
  const {
    messages,
    isStreaming,
    streamingContent,
    isLoadingMessages,
    thinkingStatus,
    setActiveThreadId,
    setMessages,
  } = useChatStore();

  // collapsed phụ thuộc deps để re-scroll khi mở lại cột.
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent, collapsed]);

  // Khi bắt đầu stream (người dùng gửi từ ChatBar) mà cột đang thu gọn → tự mở lại
  // để hội thoại không bị "mất" sau ô chat độc lập (AC#4/#6).
  useEffect(() => {
    if (isStreaming && collapsed) setCollapsed(false);
  }, [isStreaming, collapsed]);

  function handleMouseDown(e: React.MouseEvent) {
    e.preventDefault();
    isDragging.current = true;
    document.body.style.userSelect = 'none';
    document.body.style.cursor = 'col-resize';

    // Cột nằm NGOÀI CÙNG BÊN PHẢI, thanh kéo ở mép TRÁI: đo width = mép phải cột - clientX.
    // Mép phải cột cố định trong suốt thao tác kéo nên chỉ cần lấy một lần ở mousedown.
    const columnEl = (e.currentTarget as HTMLElement).closest(
      '[data-role="conv-column"]',
    ) as HTMLElement | null;
    const columnRight = columnEl?.getBoundingClientRect().right ?? window.innerWidth;
    // Chừa tối thiểu ~320px cho cột 3 tab ở giữa để không bóp nghẹt CenterWorkspace
    // trên màn hình hẹp (clamp px tuyệt đối thôi là chưa đủ).
    const maxWidth = Math.min(MAX_WIDTH_PX, columnRight - 320);

    function onMouseMove(ev: MouseEvent) {
      if (!isDragging.current) return;
      const newWidth = columnRight - ev.clientX;
      setWidth(Math.max(MIN_WIDTH_PX, Math.min(maxWidth, newWidth)));
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
    setWidth(DEFAULT_WIDTH_PX);
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
    // Chặn tạo chat mới khi đang stream: EventSource thuộc về ChatBar, component này
    // không đóng được → chunk của câu trả lời cũ sẽ rò vào thread vừa tạo (state desync).
    if (!activeProjectId || isStreaming) return;
    try {
      const thread = await createThread(activeProjectId);
      setActiveThreadId(thread.id);
      setMessages([]);
    } catch {
      toast.error('Không thể tạo cuộc trò chuyện mới');
    }
  }

  useEffect(() => {
    return () => {
      cleanupDragRef.current?.();
    };
  }, []);

  return (
    <div
      data-role="conv-column"
      className={`${styles.column} ${collapsed ? styles.columnCollapsed : ''}`}
      style={{ width: collapsed ? 0 : width }}
    >
      {!collapsed && (
        <>
          <div
            className={styles.resizeHandle}
            onMouseDown={handleMouseDown}
            onDoubleClick={handleDblClick}
            role="separator"
            aria-orientation="vertical"
          />
          <div className={styles.content}>
            <div className={styles.header}>
              <h3 className={styles.title}>{t('chat.conversationTitle')}</h3>
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
                  disabled={!activeProjectId || isStreaming}
                >
                  ✏️
                </button>
                <button
                  onClick={toggleCollapse}
                  title={t('chat.hide')}
                  type="button"
                  className={styles.collapseBtn}
                >
                  ›
                </button>
              </div>
              {showHistory && activeProjectId && (
                <ChatHistoryPopover
                  projectId={activeProjectId}
                  onClose={() => setShowHistory(false)}
                />
              )}
            </div>

            <ChatBar />

            <div className={styles.messages}>
              {!activeProjectId && <p className={styles.hint}>{t('chat.noProject')}</p>}
              {isLoadingMessages && <p className={styles.hint}>Đang tải tin nhắn...</p>}
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`${styles.bubble} ${msg.role === 'user' ? styles.userBubble : styles.aiBubble}`}
                >
                  {msg.role === 'assistant' ? (
                    <MessageContent content={msg.content} citationMap={msg.citationMap} />
                  ) : (
                    msg.content
                  )}
                </div>
              ))}
              {isStreaming && (
                <div className={`${styles.bubble} ${styles.aiBubble}`}>
                  {streamingContent === '' ? (
                    <span className={styles.thinking}>
                      {thinkingStatus
                        ? t(`chat.thinking.${thinkingStatus}` as any) || t('chat.thinking')
                        : t('chat.thinking')}
                    </span>
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
          </div>
        </>
      )}
      {collapsed && (
        <button
          className={styles.expandBtn}
          onClick={toggleCollapse}
          title={t('chat.show')}
          type="button"
        >
          ‹
        </button>
      )}
    </div>
  );
}
