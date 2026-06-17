import { useCallback, useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import { getPublicSettings } from '@/api/admin';
import { getErrorMessage } from '@/api/errors';
import { addPaperFromSearch } from '@/api/ingestion';
import { searchPapers } from '@/api/search';
import type { TranslationKey } from '@/i18n/translations';
import { useTranslation } from '@/i18n/useTranslation';
import { useWorkspaceStore } from '@/store/workspaceStore';
import type { ProjectPaper } from '@/types/document';
import type { PaperResult, SearchResponse } from '@/types/search';
import { DocumentList } from './DocumentList';
import { IngestionProgress } from './IngestionProgress';
import styles from './LibraryTab.module.css';
import { UploadModal } from './UploadModal';

interface LibraryTabProps {
  projectId: string | null;
}

export function LibraryTab({ projectId }: LibraryTabProps) {
  const { t } = useTranslation();
  const isUploadModalOpen = useWorkspaceStore((s) => s.isUploadModalOpen);
  const setUploadModalOpen = useWorkspaceStore((s) => s.setUploadModalOpen);
  const setDocumentCount = useWorkspaceStore((s) => s.setDocumentCount);
  const [query, setQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [searchResult, setSearchResult] = useState<SearchResponse | null>(null);
  // Theo dõi NHIỀU tài liệu đang ingest song song (upload + add-from-search liên tiếp),
  // tránh việc tài liệu thêm sau ghi đè mất theo dõi tài liệu trước.
  const [processingDocumentIds, setProcessingDocumentIds] = useState<string[]>([]);
  const [docRefreshTrigger, setDocRefreshTrigger] = useState(0);
  const [addingPapers, setAddingPapers] = useState<Set<string>>(new Set());
  const [papers, setPapers] = useState<ProjectPaper[]>([]);
  const [maxPapers, setMaxPapers] = useState(15);
  const searchIdRef = useRef(0);

  useEffect(() => {
    setDocumentCount(papers.length);
  }, [papers.length, setDocumentCount]);

  // Reset trạng thái theo project khi đổi project — tránh documentCount và
  // upload modal của project cũ rò rỉ sang project mới (suggestions sai context,
  // modal upload bật nhầm). DocumentList sẽ nạp lại papers cho project mới.
  useEffect(() => {
    setPapers([]);
    setUploadModalOpen(false);
  }, [projectId, setUploadModalOpen]);

  useEffect(() => {
    getPublicSettings()
      .then((s) => setMaxPapers(s.maxPapersPerProject))
      .catch(() => {
        // Giữ mặc định 15 nếu không lấy được cấu hình
      });
  }, []);

  const isAtLimit = papers.length >= maxPapers;

  const startProcessing = useCallback((documentId: string) => {
    setProcessingDocumentIds((prev) => (prev.includes(documentId) ? prev : [...prev, documentId]));
  }, []);

  const stopProcessing = useCallback((documentId: string) => {
    setProcessingDocumentIds((prev) => prev.filter((d) => d !== documentId));
  }, []);

  const handleIngestionComplete = useCallback(
    (documentId: string) => {
      toast.success(t('ingestion.done'));
      stopProcessing(documentId);
      setDocRefreshTrigger((n) => n + 1); // DocumentList refetch → onPapersLoad update isAtLimit
    },
    [t, stopProcessing],
  );

  const handleIngestionError = useCallback(
    (documentId: string) => {
      toast.error(t('ingestion.failed'));
      stopProcessing(documentId);
    },
    [t, stopProcessing],
  );

  const handleIngestionTimeout = useCallback(
    (documentId: string) => {
      toast.warning(t('ingestion.timeout'));
      stopProcessing(documentId);
      setDocRefreshTrigger((n) => n + 1);
    },
    [t, stopProcessing],
  );

  async function handleAddFromSearch(paper: PaperResult) {
    if (!projectId) return;
    const key = paper.doi ?? paper.arxivId ?? paper.title;
    setAddingPapers((prev) => new Set(prev).add(key));
    try {
      const res = await addPaperFromSearch({
        projectId,
        title: paper.title,
        authors: paper.authors,
        abstract: paper.abstract,
        year: paper.year,
        doi: paper.doi,
        arxivId: paper.arxivId,
        url: paper.url,
        pdfUrl: paper.pdfUrl,
        source: paper.source,
      });
      startProcessing(res.documentId);
      setDocRefreshTrigger((n) => n + 1);
      toast.success(t('search.addSuccess'));
    } catch (err: unknown) {
      // Hiển thị đúng message từ server cho 403 (giới hạn tài liệu), không dùng fallback generic
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      const serverDetail = axiosErr?.response?.data?.detail;
      toast.error(serverDetail ?? getErrorMessage(err, t('search.addError')));
    } finally {
      setAddingPapers((prev) => {
        const s = new Set(prev);
        s.delete(key);
        return s;
      });
    }
  }

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

  async function handleSuggestionClick(suggestion: string) {
    setQuery(suggestion);
    const currentId = ++searchIdRef.current;
    setIsSearching(true);
    setSearchResult(null);
    try {
      const result = await searchPapers(suggestion, 10);
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
        {projectId && (
          <button
            type="button"
            className={styles.uploadButton}
            onClick={() => setUploadModalOpen(true)}
            disabled={isAtLimit}
            title={isAtLimit ? t('library.uploadDisabledLimit') : undefined}
          >
            {t('upload.button')}
          </button>
        )}
      </div>

      {isAtLimit && projectId && (
        <div className={styles.limitAlert}>
          {t('library.limitReached').replace('{limit}', String(maxPapers))}
        </div>
      )}

      {isUploadModalOpen && projectId && (
        <UploadModal
          projectId={projectId}
          onClose={() => setUploadModalOpen(false)}
          onSuccess={(documentId) => {
            setUploadModalOpen(false);
            startProcessing(documentId);
          }}
        />
      )}

      {processingDocumentIds.map((id) => (
        <IngestionProgress
          key={id}
          documentId={id}
          onComplete={() => handleIngestionComplete(id)}
          onError={() => handleIngestionError(id)}
          onTimeout={() => handleIngestionTimeout(id)}
        />
      ))}

      {searchResult?.isBroadQuery && searchResult.suggestions.length > 0 && (
        <BroadQuerySuggestions
          suggestions={searchResult.suggestions}
          onSelect={handleSuggestionClick}
          t={t}
        />
      )}

      {isSearching && <div className={styles.loading}>{t('search.loading')}</div>}

      {searchResult && !isSearching && (
        <>
          {searchResult.results.length === 0 ? (
            <div className={styles.empty}>{t('search.noResults')}</div>
          ) : (
            <div className={styles.resultList}>
              {searchResult.results.map((paper, index) => {
                const key = paper.doi ?? paper.arxivId ?? paper.title;
                return (
                  <PaperCard
                    key={paper.doi ?? paper.arxivId ?? index}
                    paper={paper}
                    t={t}
                    canAdd={projectId !== null && !isAtLimit}
                    isAdding={addingPapers.has(key)}
                    onAddToProject={handleAddFromSearch}
                  />
                );
              })}
            </div>
          )}
        </>
      )}

      {projectId && (
        <DocumentList
          projectId={projectId}
          refreshTrigger={docRefreshTrigger}
          onPapersLoad={setPapers}
          onDeleteSuccess={() => setDocRefreshTrigger((n) => n + 1)}
        />
      )}
    </div>
  );
}

interface BroadQuerySuggestionsProps {
  suggestions: string[];
  onSelect: (suggestion: string) => void;
  t: (key: TranslationKey) => string;
}

function BroadQuerySuggestions({ suggestions, onSelect, t }: BroadQuerySuggestionsProps) {
  if (suggestions.length === 0) return null;
  return (
    <div
      className={styles.suggestionsBar}
      role="group"
      aria-label={t('search.suggestionAriaLabel')}
    >
      {suggestions.map((s) => (
        <button key={s} type="button" className={styles.suggestionChip} onClick={() => onSelect(s)}>
          {s}
        </button>
      ))}
    </div>
  );
}

interface PaperCardProps {
  paper: PaperResult;
  t: (key: TranslationKey) => string;
  canAdd: boolean;
  isAdding: boolean;
  onAddToProject: (paper: PaperResult) => void;
}

function PaperCard({ paper, t, canAdd, isAdding, onAddToProject }: PaperCardProps) {
  const authorStr =
    paper.authors.slice(0, 3).join(', ') + (paper.authors.length > 3 ? ' et al.' : '');
  const abstractSnippet =
    paper.abstract.length > 200 ? paper.abstract.slice(0, 200) + '...' : paper.abstract;

  return (
    <div className={styles.card}>
      <div className={styles.cardHeader}>
        <a href={paper.url} target="_blank" rel="noopener noreferrer" className={styles.paperTitle}>
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
          disabled={!canAdd || isAdding}
          onClick={() => onAddToProject(paper)}
          type="button"
        >
          {isAdding ? t('search.addingToProject') : t('search.addToProject')}
        </button>
      </div>
    </div>
  );
}
