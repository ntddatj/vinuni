import { useState, useRef } from 'react';
import { getCitationDetail, type CitationDetail } from '@/api/citations';
import styles from './CitationBadge.module.css';

interface Props {
  citationId: string;
  label: string;
}

type TooltipState =
  | { status: 'hidden' }
  | { status: 'loading' }
  | { status: 'loaded'; data: CitationDetail }
  | { status: 'error' };

const TOOLTIP_WIDTH = 300; // khớp với max-width trong CSS
const VIEWPORT_MARGIN = 8;

export function CitationBadge({ citationId, label }: Props) {
  const [tooltip, setTooltip] = useState<TooltipState>({ status: 'hidden' });
  const [coords, setCoords] = useState<{ left: number; bottom: number }>({
    left: 0,
    bottom: 0,
  });
  const hoveringRef = useRef(false);
  const badgeRef = useRef<HTMLSpanElement>(null);

  function positionTooltip() {
    const badge = badgeRef.current;
    if (!badge) return;
    const rect = badge.getBoundingClientRect();
    // Căn giữa trên badge, nhưng kẹp trong viewport để không bị tràn/che.
    let left = rect.left + rect.width / 2 - TOOLTIP_WIDTH / 2;
    left = Math.max(
      VIEWPORT_MARGIN,
      Math.min(left, window.innerWidth - TOOLTIP_WIDTH - VIEWPORT_MARGIN),
    );
    setCoords({ left, bottom: window.innerHeight - rect.top + 6 });
  }

  function handleMouseEnter() {
    hoveringRef.current = true;
    positionTooltip();
    setTooltip({ status: 'loading' });
    getCitationDetail(citationId)
      .then((data) => {
        if (hoveringRef.current) setTooltip({ status: 'loaded', data });
      })
      .catch(() => {
        if (hoveringRef.current) setTooltip({ status: 'error' });
      });
  }

  function handleMouseLeave() {
    hoveringRef.current = false;
    setTooltip({ status: 'hidden' });
  }

  return (
    <span
      ref={badgeRef}
      className={styles.wrapper}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <span className={styles.badge}>{label}</span>
      {tooltip.status !== 'hidden' && (
        <span
          className={styles.tooltip}
          style={{ left: coords.left, bottom: coords.bottom }}
        >
          {tooltip.status === 'loading' && (
            <span className={styles.loading}>Đang tải...</span>
          )}
          {tooltip.status === 'loaded' && (
            <>
              <span className={styles.tooltipTitle}>{tooltip.data.title}</span>
              <span className={styles.tooltipText}>{tooltip.data.text}</span>
            </>
          )}
          {tooltip.status === 'error' && (
            <span className={styles.error}>Không tìm thấy thông tin trích dẫn</span>
          )}
        </span>
      )}
    </span>
  );
}
