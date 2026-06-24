import { useEffect, useRef, useState } from 'react';
import { useChatStore } from '@/store/chatStore';
import { useTranslation } from '@/i18n/useTranslation';
import { listThreads, getThreadMessages, renameThread, deleteThread } from '@/api/chat';
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
  const activeThreadId = useChatStore((s) => s.activeThreadId);
  const setThreads = useChatStore((s) => s.setThreads);
  const setLoadingThreads = useChatStore((s) => s.setLoadingThreads);
  const setActiveThreadId = useChatStore((s) => s.setActiveThreadId);
  const setMessages = useChatStore((s) => s.setMessages);
  const setLoadingMessages = useChatStore((s) => s.setLoadingMessages);
  const updateThreadTitle = useChatStore((s) => s.updateThreadTitle);
  const removeThread = useChatStore((s) => s.removeThread);
  const popoverRef = useRef<HTMLDivElement>(null);

  // Trạng thái thao tác cục bộ trong popover.
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

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

  function startEdit(thread: ChatThread) {
    setConfirmDeleteId(null);
    setEditingId(thread.id);
    setEditValue(thread.title);
  }

  async function saveEdit(threadId: string) {
    const title = editValue.trim();
    if (!title) return;
    setBusyId(threadId);
    try {
      const updated = await renameThread(threadId, title);
      updateThreadTitle(threadId, updated.title);
      setEditingId(null);
    } catch {
      toast.error('Không thể đổi tên cuộc trò chuyện');
    } finally {
      setBusyId(null);
    }
  }

  async function confirmDelete(threadId: string) {
    setBusyId(threadId);
    try {
      await deleteThread(threadId);
      removeThread(threadId);
      // Đang xóa thread đang mở → dọn khung chat để không hiển thị tin nhắn mồ côi.
      if (threadId === activeThreadId) {
        setActiveThreadId(null);
        setMessages([]);
      }
      setConfirmDeleteId(null);
    } catch {
      toast.error('Không thể xóa cuộc trò chuyện');
    } finally {
      setBusyId(null);
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
            <li key={thread.id} className={styles.row}>
              {editingId === thread.id ? (
                <div className={styles.editRow}>
                  <input
                    className={styles.editInput}
                    value={editValue}
                    autoFocus
                    disabled={busyId === thread.id}
                    onChange={(e) => setEditValue(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') saveEdit(thread.id);
                      if (e.key === 'Escape') setEditingId(null);
                    }}
                  />
                  <button
                    className={styles.iconBtn}
                    onClick={() => saveEdit(thread.id)}
                    disabled={busyId === thread.id || !editValue.trim()}
                    title={t('chat.save')}
                    type="button"
                  >
                    ✓
                  </button>
                  <button
                    className={styles.iconBtn}
                    onClick={() => setEditingId(null)}
                    disabled={busyId === thread.id}
                    title={t('chat.cancel')}
                    type="button"
                  >
                    ✕
                  </button>
                </div>
              ) : confirmDeleteId === thread.id ? (
                <div className={styles.confirmRow}>
                  <span className={styles.confirmText}>{t('chat.deleteConfirm')}</span>
                  <button
                    className={`${styles.iconBtn} ${styles.danger}`}
                    onClick={() => confirmDelete(thread.id)}
                    disabled={busyId === thread.id}
                    title={t('chat.delete')}
                    type="button"
                  >
                    {t('chat.delete')}
                  </button>
                  <button
                    className={styles.iconBtn}
                    onClick={() => setConfirmDeleteId(null)}
                    disabled={busyId === thread.id}
                    title={t('chat.cancel')}
                    type="button"
                  >
                    {t('chat.cancel')}
                  </button>
                </div>
              ) : (
                <>
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
                  <div className={styles.actions}>
                    <button
                      className={styles.iconBtn}
                      onClick={() => startEdit(thread)}
                      title={t('chat.rename')}
                      type="button"
                    >
                      ✏️
                    </button>
                    <button
                      className={styles.iconBtn}
                      onClick={() => {
                        setEditingId(null);
                        setConfirmDeleteId(thread.id);
                      }}
                      title={t('chat.delete')}
                      type="button"
                    >
                      🗑️
                    </button>
                  </div>
                </>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
