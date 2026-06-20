import { useTranslation } from '@/i18n/useTranslation';
import type { GraphNode, GraphEdge } from '@/types/graph';
import { useWorkspaceStore } from '@/store/workspaceStore';
import styles from './NodeDetailCard.module.css';

interface NodeDetailCardProps {
  node: GraphNode;
  allNodes: GraphNode[];
  allEdges?: GraphEdge[];
  onClose: () => void;
  onExpand?: () => void;
  gapReason?: 'contradiction' | 'isolated' | 'unfilled_limitation' | null;
}

export function NodeDetailCard({ node, allNodes, allEdges = [], onClose, onExpand, gapReason }: NodeDetailCardProps) {
  const { t } = useTranslation();
  const setPendingChatInput = useWorkspaceStore((s) => s.setPendingChatInput);

  const handleAskAI = () => {
    // Chat sống trong ChatbotPanel (panel phải, luôn mounted) — chỉ cần prefill,
    // KHÔNG đổi tab center (trước đây switch sang 'library' làm ẩn đồ thị đang xem).
    setPendingChatInput(`Hãy phân tích bài báo: ${node.title}`);
  };

  const handleExplainGap = () => {
    const gapDesc = {
      contradiction: `mâu thuẫn học thuật trong nghiên cứu: ${node.title}`,
      isolated: `khoảng trống do thiếu liên kết trích dẫn: ${node.title}`,
      unfilled_limitation: `hạn chế chưa được giải quyết trong: ${node.title}`,
    }[gapReason ?? 'contradiction'] ?? `khoảng trống nghiên cứu liên quan đến: ${node.title}`;
    setPendingChatInput(`Phân tích ${gapDesc}. Hãy chỉ rõ mâu thuẫn, hạn chế và cơ hội nghiên cứu.`);
  };

  if (node.label === 'author') {
    // Tác giả là target của (paper)-[:AUTHORED_BY]->(author): lấy các paper nối tới author này.
    const paperIds = new Set(
      allEdges
        .filter((e) => e.type === 'AUTHORED_BY' && e.target === node.id)
        .map((e) => e.source),
    );
    const authoredPapers = allNodes.filter(
      (n) => n.label === 'paper' && paperIds.has(n.id),
    );

    return (
      <div className={styles.card}>
        <div className={styles.header}>
          <h3 className={styles.title}>{node.title}</h3>
          <button className={styles.closeBtn} onClick={onClose} type="button" aria-label="Đóng">
            ✕
          </button>
        </div>
        <p className={styles.sectionLabel}>{t('graph.authoredPapers')}</p>
        <ul className={styles.paperList}>
          {authoredPapers.length > 0
            ? authoredPapers.map((p) => <li key={p.id}>{p.title}</li>)
            : <li className={styles.meta}>—</li>
          }
        </ul>
      </div>
    );
  }

  // Tác giả của paper: ưu tiên suy ra từ cạnh AUTHORED_BY (Neo4j không lưu p.authors),
  // fallback về node.authors nếu có sẵn.
  const authorIds = new Set(
    allEdges
      .filter((e) => e.type === 'AUTHORED_BY' && e.source === node.id)
      .map((e) => e.target),
  );
  const derivedAuthors = allNodes
    .filter((n) => n.label === 'author' && authorIds.has(n.id))
    .map((n) => n.title);
  const authorNames = derivedAuthors.length > 0 ? derivedAuthors : (node.authors ?? []);

  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <h3 className={styles.title}>{node.title}</h3>
        <button className={styles.closeBtn} onClick={onClose} type="button" aria-label="Đóng">
          ✕
        </button>
      </div>

      {(authorNames.length > 0 || node.year != null) && (
        <p className={styles.meta}>
          {authorNames.join(', ')}{node.year != null ? ` (${node.year})` : ''}
        </p>
      )}

      {node.abstract && (
        <p className={styles.abstract}>{node.abstract}</p>
      )}

      <div className={styles.actions}>
        <button className={styles.askAIBtn} onClick={handleAskAI} type="button">
          {t('graph.askAI')}
        </button>
        {onExpand && (
          <button className={styles.expandBtn} onClick={onExpand} type="button">
            {t('graph.expand')}
          </button>
        )}
        {gapReason && (
          <button className={styles.explainGapBtn} onClick={handleExplainGap} type="button">
            {t('graph.explainGap')}
          </button>
        )}
      </div>
    </div>
  );
}
