import { useEffect, useState } from 'react';
import { getPapersByProject } from '@/api/ingestion';
import type { TranslationKey } from '@/i18n/translations';
import { useTranslation } from '@/i18n/useTranslation';
import type { ProjectPaper } from '@/types/document';
import styles from './DocumentList.module.css';

interface Props {
  projectId: string;
  refreshTrigger: number;
  onPapersLoad?: (papers: ProjectPaper[]) => void;
}

const STATUS_LABEL_KEY: Record<ProjectPaper['status'], TranslationKey> = {
  pending: 'library.status.pending',
  processing: 'library.status.processing',
  indexed: 'library.status.indexed',
  failed: 'library.status.failed',
};

export function DocumentList({ projectId, refreshTrigger, onPapersLoad }: Props) {
  const { t } = useTranslation();
  const [papers, setPapers] = useState<ProjectPaper[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(false);
      try {
        const data = await getPapersByProject(projectId);
        if (!cancelled) {
          setPapers(data);
          onPapersLoad?.(data);
        }
      } catch {
        if (!cancelled) setError(true);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [projectId, refreshTrigger]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className={styles.container}>
      <h3 className={styles.heading}>{t('library.documents')}</h3>
      {loading && <div className={styles.message}>{t('projects.loading')}</div>}
      {!loading && error && <div className={styles.message}>{t('library.loadError')}</div>}
      {!loading && !error && papers.length === 0 && (
        <div className={styles.message}>{t('library.emptyDocs')}</div>
      )}
      {!loading && !error && papers.length > 0 && (
        <ul className={styles.list}>
          {papers.map((paper) => (
            <DocumentRow key={paper.id} paper={paper} t={t} />
          ))}
        </ul>
      )}
    </div>
  );
}

interface RowProps {
  paper: ProjectPaper;
  t: (key: TranslationKey) => string;
}

function DocumentRow({ paper, t }: RowProps) {
  const authorStr =
    paper.authors.slice(0, 2).join(', ') + (paper.authors.length > 2 ? ' et al.' : '');

  return (
    <li className={styles.row}>
      <div className={styles.main}>
        <span className={styles.title}>{paper.title}</span>
        <div className={styles.meta}>
          {authorStr && <span className={styles.authors}>{authorStr}</span>}
          {paper.year && <span className={styles.year}>{paper.year}</span>}
          <span className={styles.sourceBadge} data-source={paper.source}>
            {paper.source === 'arxiv'
              ? 'arXiv'
              : paper.source === 'semantic_scholar'
                ? 'Semantic Scholar'
                : 'Upload'}
          </span>
        </div>
      </div>
      <span className={styles.statusBadge} data-status={paper.status}>
        {t(STATUS_LABEL_KEY[paper.status])}
      </span>
    </li>
  );
}
