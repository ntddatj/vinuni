import { useEffect, useRef } from 'react';
import { useChatStore } from '@/store/chatStore';
import { useTranslation } from '@/i18n/useTranslation';
import { listThreads, getThreadMessages } from '@/api/chat';
import type { ChatThread } from '@/types/chat';
import { toast } from 'sonner';
import styles from './ChatHistoryPopover.module.css';

interface Props {
  projectId: string;
  onClose: () => void;
}

export function ChatHistoryPopover({ projectId, onClose }: Props) {
  const { t } = useTranslation();
  const threads = useChatStore((s) => s.threads);
  const isLoading = useChatStore((s) => s.isLoadingThreads);
  const setThreads = useChatStore((s) => s.setThreads);
  const setLoadingThreads = useChatStore((s) => s.setLoadingThreads);
  const setActiveThreadId = useChatStore((s) => s.setActiveThreadId);
  const setMessages = useChatStore((s) => s.setMessages);
  const setLoadingMessages = useChatStore((s) => s.setLoadingMessages);
  const popoverRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setLoadingThreads(true);
    listThreads(projectId)
      .then(setThreads)
      .finally(() => setLoadingThreads(false));
  }, [projectId]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        onClose();
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [onClose]);

  async function handleSelectThread(thread: ChatThread) {
    setActiveThreadId(thread.id);
    setLoadingMessages(true);
    onClose();
    try {
      const msgs = await getThreadMessages(thread.id);
      setMessages(msgs);
    } catch {
      setMessages([]);
      toast.error('Không thể tải tin nhắn của cuộc trò chuyện');
    } finally {
      setLoadingMessages(false);
    }
  }

  return (
    <div
      ref={popoverRef}
      className={styles.popover}
      role="dialog"
      aria-label={t('chat.historyTitle')}
    >
      <div className={styles.header}>{t('chat.historyTitle')}</div>
      {isLoading ? (
        <div className={styles.loading}>…</div>
      ) : threads.length === 0 ? (
        <div className={styles.empty}>{t('chat.historyEmpty')}</div>
      ) : (
        <ul className={styles.list}>
          {threads.map((thread) => (
            <li key={thread.id}>
              <button
                className={styles.threadItem}
                onClick={() => handleSelectThread(thread)}
                type="button"
              >
                <span className={styles.threadTitle}>{thread.title}</span>
                <span className={styles.threadDate}>
                  {new Date(thread.updatedAt).toLocaleDateString('vi-VN')}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
