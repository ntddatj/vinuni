import { useEffect, useRef, useState } from 'react';
import { useTranslation } from '@/i18n/useTranslation';
import styles from './ChatbotPanel.module.css';

const DEFAULT_WIDTH = 25;
const MIN_WIDTH = 20;
const MAX_WIDTH = 40;

export function ChatbotPanel() {
  const [width, setWidth] = useState(DEFAULT_WIDTH);
  const [collapsed, setCollapsed] = useState(false);
  const [lastWidth, setLastWidth] = useState(DEFAULT_WIDTH);
  const isDragging = useRef(false);
  const cleanupDragRef = useRef<(() => void) | null>(null);
  const { t } = useTranslation();

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
          <div className={styles.header}>
            <h3 className={styles.title}>{t('chat.title')}</h3>
          </div>

          <div className={styles.messages}>
            <p className={styles.emptyHint}>{t('chat.comingSoon')}</p>
          </div>

          <div className={styles.inputArea}>
            <input
              className={styles.input}
              placeholder={t('chat.placeholder')}
              disabled
              type="text"
            />
          </div>
        </div>
      </div>
    </>
  );
}
