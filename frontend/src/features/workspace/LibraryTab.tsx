import { useRef, useState } from 'react';
import { toast } from 'sonner';
import { getErrorMessage } from '@/api/errors';
import { searchPapers } from '@/api/search';
import type { TranslationKey } from '@/i18n/translations';
import { useTranslation } from '@/i18n/useTranslation';
import type { PaperResult, SearchResponse } from '@/types/search';
import styles from './LibraryTab.module.css';

export function LibraryTab() {
  const { t } = useTranslation();
  const [query, setQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [searchResult, setSearchResult] = useState<SearchResponse | null>(null);
  const searchIdRef = useRef(0);

  async function handleSearch() {
    const trimmed = query.trim();
    if (!trimmed) return;

    const currentId = ++searchIdRef.current;
    setIsSearching(true);
    setSearchResult(null);

    try {
      const result = await searchPapers(trimmed, 10);
      if (currentId !== searchIdRef.current) return;

      setSearchResult(result);

      if (result.warnings.length >= 2) {
        toast.error(t('search.bothSourcesFailed'));
      } else if (result.warnings.length === 1) {
        toast.warning(t('search.partialResults'));
      }
    } catch (err) {
      if (currentId !== searchIdRef.current) return;
      toast.error(getErrorMessage(err, t('search.searchError')));
    } finally {
      if (currentId === searchIdRef.current) {
        setIsSearching(false);
      }
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') {
      handleSearch();
    }
  }

  return (
    <div className={styles.container}>
      <div className={styles.searchBar}>
        <input
          type="text"
          className={styles.searchInput}
          placeholder={t('search.placeholder')}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          aria-label={t('search.placeholder')}
        />
        <button
          className={styles.searchButton}
          onClick={handleSearch}
          disabled={isSearching || !query.trim()}
          type="button"
        >
          {isSearching ? t('search.searching') : t('search.searchButton')}
        </button>
      </div>

      {isSearching && (
        <div className={styles.loading}>{t('search.loading')}</div>
      )}

      {searchResult && !isSearching && (
        <>
          {searchResult.results.length === 0 ? (
            <div className={styles.empty}>{t('search.noResults')}</div>
          ) : (
            <div className={styles.resultList}>
              {searchResult.results.map((paper, index) => (
                <PaperCard key={paper.doi ?? paper.arxivId ?? index} paper={paper} t={t} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

interface PaperCardProps {
  paper: PaperResult;
  t: (key: TranslationKey) => string;
}

function PaperCard({ paper, t }: PaperCardProps) {
  const authorStr =
    paper.authors.slice(0, 3).join(', ') + (paper.authors.length > 3 ? ' et al.' : '');
  const abstractSnippet =
    paper.abstract.length > 200 ? paper.abstract.slice(0, 200) + '...' : paper.abstract;

  return (
    <div className={styles.card}>
      <div className={styles.cardHeader}>
        <a
          href={paper.url}
          target="_blank"
          rel="noopener noreferrer"
          className={styles.paperTitle}
        >
          {paper.title}
        </a>
        <div className={styles.badges}>
          <span className={styles.sourceBadge} data-source={paper.source}>
            {paper.source === 'arxiv' ? 'arXiv' : 'Semantic Scholar'}
          </span>
          {paper.pdfUrl && (
            <a
              href={paper.pdfUrl}
              target="_blank"
              rel="noopener noreferrer"
              className={styles.pdfBadge}
              aria-label="PDF"
            >
              PDF
            </a>
          )}
        </div>
      </div>
      <div className={styles.cardMeta}>
        <span className={styles.authors}>{authorStr}</span>
        {paper.year && <span className={styles.year}>{paper.year}</span>}
      </div>
      <p className={styles.abstract}>{abstractSnippet}</p>
      <div className={styles.cardActions}>
        <button
          className={styles.addButton}
          disabled
          title={t('search.addComingSoon')}
          type="button"
        >
          {t('search.addToProject')}
        </button>
      </div>
    </div>
  );
}
