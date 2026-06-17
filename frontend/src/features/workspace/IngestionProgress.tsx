import { useEffect, useRef, useState } from 'react';
import { getSSETicket } from '@/api/ingestion';
import { useTranslation } from '@/i18n/useTranslation';
import styles from './IngestionProgress.module.css';

interface Props {
  documentId: string;
  onComplete: () => void;
  onError: () => void;
  onTimeout?: () => void;
}

interface ProgressState {
  percent: number;
  message: string;
  status: 'connecting' | 'running' | 'done' | 'error';
}

export function IngestionProgress({ documentId, onComplete, onError, onTimeout }: Props) {
  const { t } = useTranslation();
  const [state, setState] = useState<ProgressState>({
    percent: 0,
    message: t('ingestion.processing'),
    status: 'connecting',
  });
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function connect() {
      try {
        const { ticket } = await getSSETicket(documentId);
        if (cancelled) return;

        const es = new EventSource(
          `/api/ingestion/sse/stream?ticket=${encodeURIComponent(ticket)}`,
        );
        esRef.current = es;

        es.onmessage = (evt) => {
          if (cancelled) return;
          try {
            const data = JSON.parse(evt.data);
            if (data.event === 'progress') {
              setState({ percent: data.percent, message: data.message, status: 'running' });
            } else if (data.event === 'completed') {
              setState({ percent: 100, message: t('ingestion.done'), status: 'done' });
              es.close();
              onComplete();
            } else if (data.event === 'error') {
              setState({ percent: 0, message: data.message, status: 'error' });
              es.close();
              onError();
            } else if (data.event === 'timeout') {
              // Stream im lặng quá lâu (worker còn xếp hàng/đang chạy) — dừng theo dõi,
              // không báo lỗi thật; DocumentList sẽ phản ánh trạng thái cuối cùng.
              setState({ percent: 0, message: t('ingestion.timeout'), status: 'error' });
              es.close();
              (onTimeout ?? onError)();
            }
          } catch {
            // bỏ qua lỗi parse
          }
        };

        es.onerror = () => {
          if (cancelled) return;
          // EventSource tự reconnect khi rớt mạng tạm thời (readyState === CONNECTING) — ticket
          // còn hiệu lực trong TTL nên stream sẽ nối lại. Chỉ coi là lỗi khi đã đóng hẳn (CLOSED),
          // tránh toast "thất bại" sai trong khi worker vẫn đang xử lý.
          if (es.readyState === EventSource.CLOSED) {
            onError();
          }
        };
      } catch {
        if (!cancelled) onError();
      }
    }

    connect();
    return () => {
      cancelled = true;
      esRef.current?.close();
    };
    // onComplete/onError nên ổn định (useCallback ở parent); chỉ re-run khi documentId đổi
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documentId]);

  if (state.status === 'done' || state.status === 'error') return null;

  return (
    <div className={styles.container} role="status" aria-live="polite">
      <div className={styles.bar}>
        <div className={styles.fill} style={{ width: `${state.percent}%` }} />
      </div>
      <div className={styles.footer}>
        <span className={styles.message}>{state.message}</span>
        <span className={styles.percent}>{state.percent}%</span>
      </div>
    </div>
  );
}
