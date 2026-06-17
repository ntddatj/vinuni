import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { getErrorMessage } from '@/api/errors';
import { deletePaper, getPaperFileUrl, getPapersByProject, patchPaperMetadata } from '@/api/ingestion';
import type { TranslationKey } from '@/i18n/translations';
import { useTranslation } from '@/i18n/useTranslation';
import type { ProjectPaper } from '@/types/document';
import styles from './DocumentList.module.css';

interface Props {
  projectId: string;
  refreshTrigger: number;
  onPapersLoad?: (papers: ProjectPaper[]) => void;
  onDeleteSuccess?: () => void;
}

const STATUS_LABEL_KEY: Record<ProjectPaper['status'], TranslationKey> = {
  pending: 'library.status.pending',
  processing: 'library.status.processing',
  indexed: 'library.status.indexed',
  failed: 'library.status.failed',
};

export function DocumentList({ projectId, refreshTrigger, onPapersLoad, onDeleteSuccess }: Props) {
  const { t } = useTranslation();
  const [papers, setPapers] = useState<ProjectPaper[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

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
  }, [projectId, refreshTrigger, refreshKey]); // eslint-disable-line react-hooks/exhaustive-deps

  function handleItemDeleted() {
    setRefreshKey((k) => k + 1);
    onDeleteSuccess?.();
  }

  function handleItemEdited() {
    setRefreshKey((k) => k + 1);
  }

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
            <DocumentRow
              key={paper.id}
              paper={paper}
              projectId={projectId}
              t={t}
              onDeleted={handleItemDeleted}
              onEdited={handleItemEdited}
            />
          ))}
        </ul>
      )}
    </div>
  );
}

interface RowProps {
  paper: ProjectPaper;
  projectId: string;
  t: (key: TranslationKey) => string;
  onDeleted: () => void;
  onEdited: () => void;
}

function DocumentRow({ paper, projectId, t, onDeleted, onEdited }: RowProps) {
  const authorStr =
    paper.authors.slice(0, 2).join(', ') + (paper.authors.length > 2 ? ' et al.' : '');

  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [showEditForm, setShowEditForm] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [editTitle, setEditTitle] = useState(paper.title);
  const [editAuthors, setEditAuthors] = useState(paper.authors.join(', '));
  const [editAbstract, setEditAbstract] = useState(paper.abstract ?? '');
  const [editYear, setEditYear] = useState(String(paper.year ?? ''));

  async function handleDelete() {
    setIsDeleting(true);
    try {
      await deletePaper(projectId, paper.id);
      toast.success(t('library.deleteSuccess'));
      onDeleted();
    } catch (err) {
      toast.error(getErrorMessage(err, t('library.deleteError')));
    } finally {
      setIsDeleting(false);
      setShowDeleteConfirm(false);
    }
  }

  async function handleSaveEdit() {
    // Title là bắt buộc — chặn lưu rỗng để không "thành công thầm lặng" mà không đổi gì (backend bỏ qua None).
    const trimmedTitle = editTitle.trim();
    if (!trimmedTitle) {
      toast.error(t('library.titleRequired'));
      return;
    }
    // Year: chỉ gửi khi parse được số hợp lệ; tránh NaN/giá trị rác lọt xuống backend.
    let yearValue: number | undefined;
    if (editYear.trim()) {
      const parsed = Number(editYear);
      if (!Number.isInteger(parsed) || parsed < 1000 || parsed > 2100) {
        toast.error(t('library.yearInvalid'));
        return;
      }
      yearValue = parsed;
    }
    setIsSaving(true);
    try {
      await patchPaperMetadata(projectId, paper.id, {
        title: trimmedTitle,
        authors: editAuthors.split(',').map((a) => a.trim()).filter(Boolean),
        abstract: editAbstract.trim() || undefined,
        year: yearValue,
      });
      toast.success(t('library.editSuccess'));
      onEdited();
      setShowEditForm(false);
    } catch (err) {
      toast.error(getErrorMessage(err, t('library.editError')));
    } finally {
      setIsSaving(false);
    }
  }

  const fileUrl = getPaperFileUrl(projectId, paper.id);
  const hasLocalFile = paper.hasFile;
  const hasExternalLink = Boolean(paper.pdfUrl || paper.url);

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

      <div className={styles.rightSection}>
        <span className={styles.statusBadge} data-status={paper.status}>
          {t(STATUS_LABEL_KEY[paper.status])}
        </span>

        <div className={styles.actions}>
          {hasLocalFile ? (
            <a href={fileUrl} target="_blank" rel="noopener noreferrer" className={styles.viewFileBtn}>
              {t('library.viewSource')}
            </a>
          ) : hasExternalLink ? (
            <a
              href={(paper.pdfUrl ?? paper.url)!}
              target="_blank"
              rel="noopener noreferrer"
              className={styles.paywallLink}
            >
              {t('library.externalSource')}
            </a>
          ) : null}

          <button
            type="button"
            className={styles.editBtn}
            onClick={() => {
              setEditTitle(paper.title);
              setEditAuthors(paper.authors.join(', '));
              setEditAbstract(paper.abstract ?? '');
              setEditYear(String(paper.year ?? ''));
              setShowEditForm(true);
            }}
          >
            {t('library.edit')}
          </button>
          <button
            type="button"
            className={styles.deleteBtn}
            onClick={() => setShowDeleteConfirm(true)}
          >
            {t('library.delete')}
          </button>
        </div>
      </div>

      {showDeleteConfirm && (
        <div className={styles.confirmOverlay}>
          <div className={styles.confirmBox}>
            <p>{t('library.deleteConfirmMessage')}</p>
            <div className={styles.confirmActions}>
              <button
                type="button"
                onClick={handleDelete}
                disabled={isDeleting}
                className={styles.confirmDeleteBtn}
              >
                {isDeleting ? '...' : t('library.delete')}
              </button>
              <button
                type="button"
                onClick={() => setShowDeleteConfirm(false)}
                className={styles.cancelBtn}
              >
                {t('library.editCancel')}
              </button>
            </div>
          </div>
        </div>
      )}

      {showEditForm && (
        <div className={styles.editFormOverlay}>
          <div className={styles.editForm}>
            <h4 className={styles.editFormTitle}>{t('library.editTitle')}</h4>
            <label className={styles.editLabel}>
              {t('library.titleField')}
              <input
                className={styles.editInput}
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
              />
            </label>
            <label className={styles.editLabel}>
              {t('library.authorsField')}
              <input
                className={styles.editInput}
                value={editAuthors}
                onChange={(e) => setEditAuthors(e.target.value)}
              />
            </label>
            <label className={styles.editLabel}>
              {t('library.abstractField')}
              <textarea
                className={styles.editInput}
                rows={4}
                value={editAbstract}
                onChange={(e) => setEditAbstract(e.target.value)}
              />
            </label>
            <label className={styles.editLabel}>
              {t('library.yearField')}
              <input
                type="number"
                min={1000}
                max={2100}
                className={styles.editInput}
                value={editYear}
                onChange={(e) => setEditYear(e.target.value)}
              />
            </label>
            <div className={styles.editFormActions}>
              <button
                type="button"
                onClick={handleSaveEdit}
                disabled={isSaving}
                className={styles.confirmDeleteBtn}
              >
                {isSaving ? '...' : t('library.editSave')}
              </button>
              <button
                type="button"
                onClick={() => setShowEditForm(false)}
                className={styles.cancelBtn}
              >
                {t('library.editCancel')}
              </button>
            </div>
          </div>
        </div>
      )}
    </li>
  );
}
