import { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { getProjects } from '@/api/projects';
import { getErrorMessage } from '@/api/errors';
import { useTranslation } from '@/i18n/useTranslation';
import type { ProjectResponse } from '@/types/project';
import { CreateProjectModal } from './CreateProjectModal';
import { DeleteProjectModal } from './DeleteProjectModal';
import styles from './ProjectsPage.module.css';

const PAGE_SIZE = 10;

function formatDate(dateStr: string | null | undefined, locale: string): string {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return '—';
  return d.toLocaleDateString(locale);
}

export function ProjectsPage() {
  const { t, lang } = useTranslation();
  const [projects, setProjects] = useState<ProjectResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [page, setPage] = useState(0);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; name: string } | null>(null);

  const loadProjects = useCallback(async (currentPage: number, search: string) => {
    setIsLoading(true);
    try {
      const { items, total: t } = await getProjects(PAGE_SIZE, currentPage * PAGE_SIZE, search || undefined);
      setProjects(items);
      setTotal(t);
    } catch (err) {
      toast.error(getErrorMessage(err, 'Không thể tải danh sách dự án'));
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Debounce: delay search 300ms
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchQuery), 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Load khi page hoặc debouncedSearch thay đổi
  useEffect(() => {
    loadProjects(page, debouncedSearch);
  }, [page, debouncedSearch, loadProjects]);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  function handleSearch(e: React.ChangeEvent<HTMLInputElement>) {
    setSearchQuery(e.target.value);
    setPage(0);
  }

  const handleDeleteSuccess = useCallback(() => {
    if (projects.length === 1 && page > 0) {
      setPage((p) => p - 1);
    } else {
      loadProjects(page, debouncedSearch);
    }
  }, [projects.length, page, debouncedSearch, loadProjects]);

  const locale = lang === 'vi' ? 'vi-VN' : 'en-US';

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>{t('projects.title')}</h1>
        <button className={styles.createButton} onClick={() => setShowCreateModal(true)}>
          {t('projects.createButton')}
        </button>
      </div>

      <input
        className={styles.searchInput}
        type="search"
        placeholder={t('projects.searchPlaceholder')}
        value={searchQuery}
        onChange={handleSearch}
      />

      {isLoading ? (
        <div className={styles.empty}>{t('projects.loading')}</div>
      ) : projects.length === 0 ? (
        <div className={styles.empty}>
          {debouncedSearch ? t('projects.noResults') : t('projects.empty')}
        </div>
      ) : (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>{t('projects.colName')}</th>
              <th>{t('projects.colDesc')}</th>
              <th>{t('projects.colDate')}</th>
              <th>{t('projects.colAction')}</th>
            </tr>
          </thead>
          <tbody>
            {projects.map((project) => (
              <tr key={project.id}>
                <td>{project.name}</td>
                <td>{project.description ?? '—'}</td>
                <td>{formatDate(project.createdAt, locale)}</td>
                <td>
                  <button
                    className={styles.deleteBtn}
                    onClick={() => setDeleteTarget({ id: project.id, name: project.name })}
                    title={t('sidebar.delete')}
                    aria-label={t('sidebar.delete')}
                  >
                    🗑
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {totalPages > 1 && (
        <div className={styles.pagination}>
          <button
            className={styles.pageBtn}
            disabled={page === 0}
            onClick={() => setPage((p) => p - 1)}
          >
            {t('projects.pagePrev')}
          </button>
          <span className={styles.pageInfo}>
            {page + 1} / {totalPages}
          </span>
          <button
            className={styles.pageBtn}
            disabled={page >= totalPages - 1}
            onClick={() => setPage((p) => p + 1)}
          >
            {t('projects.pageNext')}
          </button>
        </div>
      )}

      {showCreateModal && (
        <CreateProjectModal
          onClose={() => setShowCreateModal(false)}
          onSuccess={() => loadProjects(page, debouncedSearch)}
        />
      )}
      {deleteTarget && (
        <DeleteProjectModal
          projectId={deleteTarget.id}
          projectName={deleteTarget.name}
          onClose={() => setDeleteTarget(null)}
          onSuccess={handleDeleteSuccess}
        />
      )}
    </div>
  );
}
