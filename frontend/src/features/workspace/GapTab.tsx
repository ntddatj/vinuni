import { useEffect, useState } from 'react';
import { fetchGapsDetailed } from '@/api/graph';
import type { TranslationKey } from '@/i18n/translations';
import { useTranslation } from '@/i18n/useTranslation';
import { useWorkspaceStore } from '@/store/workspaceStore';
import type { GapDetailItem } from '@/types/graph';
import styles from './GapTab.module.css';

// Nhãn i18n cho từng khoá evidence (backend chỉ phát số liệu, không lộ id nội bộ).
const EVIDENCE_LABEL_KEYS: Record<string, TranslationKey> = {
  finding_count: 'gapTab.evidenceFindings',
  paper_count: 'gapTab.evidencePapers',
  neighbor_count: 'gapTab.evidenceNeighbors',
  filler_count: 'gapTab.evidenceFillers',
};

// Khử trùng paper theo paper_id — mâu thuẫn nội tại (cùng 1 bài) trả [p, p] trùng id.
function dedupePapers(papers: GapDetailItem['papers']): GapDetailItem['papers'] {
  const seen = new Set<string>();
  return papers.filter((p) => {
    if (seen.has(p.paper_id)) return false;
    seen.add(p.paper_id);
    return true;
  });
}

function formatEvidence(
  evidence: GapDetailItem['evidence'],
  t: ReturnType<typeof useTranslation>['t'],
): string {
  return Object.entries(evidence)
    // Chỉ render giá trị vô hướng — tránh "[object Object]" nếu evidence chứa object/array.
    .filter(([, v]) => typeof v === 'string' || typeof v === 'number' || typeof v === 'boolean')
    .map(([k, v]) => {
      const labelKey = EVIDENCE_LABEL_KEYS[k];
      return labelKey ? `${t(labelKey)}: ${v}` : `${k}: ${String(v)}`;
    })
    .join(' · ');
}

interface GapTabProps {
  projectId: string | null;
}

type GapType = 'contradiction' | 'unfilled_limitation' | 'isolated_cluster';

const GAP_GROUPS: { type: GapType; labelKey: 'gapTab.typeContradiction' | 'gapTab.typeUnfilled' | 'gapTab.typeIsolated' }[] = [
  { type: 'contradiction', labelKey: 'gapTab.typeContradiction' },
  { type: 'unfilled_limitation', labelKey: 'gapTab.typeUnfilled' },
  { type: 'isolated_cluster', labelKey: 'gapTab.typeIsolated' },
];

const BADGE_CLASS: Record<GapType, string> = {
  contradiction: styles.badgeContradiction,
  unfilled_limitation: styles.badgeUnfilled,
  isolated_cluster: styles.badgeIsolated,
};

const CARD_CLASS: Record<GapType, string> = {
  contradiction: styles.cardContradiction,
  unfilled_limitation: styles.cardUnfilled,
  isolated_cluster: styles.cardIsolated,
};

export function GapTab({ projectId }: GapTabProps) {
  const { t } = useTranslation();
  const activeTab = useWorkspaceStore((s) => s.activeTab);
  const setActiveTab = useWorkspaceStore((s) => s.setActiveTab);
  const requestGapFocus = useWorkspaceStore((s) => s.requestGapFocus);
  const setPendingChatInput = useWorkspaceStore((s) => s.setPendingChatInput);

  const [items, setItems] = useState<GapDetailItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  // Fetch khi tab active & có projectId
  useEffect(() => {
    if (activeTab !== 'gaps' || !projectId) return;
    let cancelled = false;
    setLoading(true);
    setError(false);
    fetchGapsDetailed(projectId)
      .then((data) => {
        if (cancelled) return;
        setItems(data.items);
      })
      .catch(() => {
        if (cancelled) return;
        setError(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [activeTab, projectId]);

  if (!projectId) {
    return <div className={styles.noProject}>{t('gapTab.noProject')}</div>;
  }

  if (loading) {
    return <div className={styles.loading}>{t('gapTab.loading')}</div>;
  }

  if (error) {
    return <div className={styles.error}>{t('gapTab.error')}</div>;
  }

  if (items.length === 0) {
    return <div className={styles.empty}>{t('gapTab.empty')}</div>;
  }

  return (
    <div className={styles.container}>
      {GAP_GROUPS.map(({ type, labelKey }) => {
        const groupItems = items.filter((item) => item.type === type);
        if (groupItems.length === 0) return null;
        return (
          <div key={type} className={styles.group}>
            <div className={styles.groupTitle}>
              {t(labelKey)}
              <span className={styles.groupCount}>{groupItems.length}</span>
            </div>
            <div className={styles.cardList}>
              {groupItems.map((item) => (
                <GapCard
                  key={item.id}
                  item={item}
                  onOpenOnMap={() => {
                    const paperId = item.papers[0]?.paper_id;
                    setActiveTab('graph');
                    if (paperId) requestGapFocus(paperId);
                  }}
                  onExplain={() => {
                    const names = dedupePapers(item.papers)
                      .map((p) => `"${p.title}"`)
                      .join(', ');
                    setPendingChatInput(
                      `Giải thích khoảng trống nghiên cứu: "${item.title}"` +
                        (names ? ` (liên quan: ${names})` : '') +
                        `. ${item.description}`,
                    );
                  }}
                  t={t}
                />
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── GapCard ───────────────────────────────────────────────────────────────────

interface GapCardProps {
  item: GapDetailItem;
  onOpenOnMap: () => void;
  onExplain: () => void;
  t: ReturnType<typeof useTranslation>['t'];
}

function GapCard({ item, onOpenOnMap, onExplain, t }: GapCardProps) {
  const type = item.type as GapType;
  const badgeClass = BADGE_CLASS[type] ?? '';
  const cardClass = CARD_CLASS[type] ?? '';

  const labelKey = type === 'contradiction'
    ? 'gapTab.typeContradiction'
    : type === 'unfilled_limitation'
      ? 'gapTab.typeUnfilled'
      : 'gapTab.typeIsolated';

  return (
    <div className={`${styles.card} ${cardClass}`}>
      <div className={styles.cardHeader}>
        <div className={styles.cardTitle}>{item.title}</div>
        <span className={`${styles.badge} ${badgeClass}`}>{t(labelKey)}</span>
      </div>

      {item.description && (
        <p className={styles.cardDescription}>{item.description}</p>
      )}

      {(() => {
        const papers = dedupePapers(item.papers);
        return papers.length > 0 ? (
          <div className={styles.papersLine}>
            <span className={styles.papersLabel}>{t('gapTab.relatedPapers')}:</span>{' '}
            {papers.map((p) => `“${p.title}”`).join(', ')}
          </div>
        ) : null;
      })()}

      {(() => {
        const evidenceText = formatEvidence(item.evidence, t);
        return evidenceText ? (
          <div className={styles.evidenceLine}>
            {t('gapTab.evidence')}: {evidenceText}
          </div>
        ) : null;
      })()}

      <div className={styles.cardActions}>
        <button type="button" className={styles.btnSecondary} onClick={onOpenOnMap}>
          {t('gapTab.openOnMap')}
        </button>
        <button type="button" className={styles.btnPrimary} onClick={onExplain}>
          {t('gapTab.explainGap')}
        </button>
      </div>
    </div>
  );
}
