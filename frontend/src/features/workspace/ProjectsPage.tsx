import { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { getProjects } from '@/api/projects';
import { getErrorMessage } from '@/api/errors';
import type { ProjectResponse } from '@/types/project';
import { CreateProjectModal } from './CreateProjectModal';
import { DeleteProjectModal } from './DeleteProjectModal';
import styles from './ProjectsPage.module.css';

const PAGE_SIZE = 10;

export function ProjectsPage() {
  const [projects, setProjects] = useState<ProjectResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
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

  useEffect(() => {
    loadProjects(page, searchQuery);
  }, [page, searchQuery, loadProjects]);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  function handleSearch(e: React.ChangeEvent<HTMLInputElement>) {
    setSearchQuery(e.target.value);
    setPage(0);
  }

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>Quản lý Dự án</h1>
        <button className={styles.createButton} onClick={() => setShowCreateModal(true)}>
          + Tạo dự án mới
        </button>
      </div>

      <input
        className={styles.searchInput}
        type="search"
        placeholder="Tìm kiếm theo tên dự án..."
        value={searchQuery}
        onChange={handleSearch}
      />

      {isLoading ? (
        <div className={styles.empty}>Đang tải...</div>
      ) : projects.length === 0 ? (
        <div className={styles.empty}>
          {searchQuery ? 'Không tìm thấy dự án nào.' : 'Chưa có dự án nào. Hãy tạo dự án đầu tiên!'}
        </div>
      ) : (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Tên dự án</th>
              <th>Mô tả</th>
              <th>Ngày tạo</th>
              <th>Hành động</th>
            </tr>
          </thead>
          <tbody>
            {projects.map((project) => (
              <tr key={project.id}>
                <td>{project.name}</td>
                <td>{project.description ?? '—'}</td>
                <td>{new Date(project.createdAt).toLocaleDateString('vi-VN')}</td>
                <td>
                  <button
                    className={styles.deleteBtn}
                    onClick={() => setDeleteTarget({ id: project.id, name: project.name })}
                  >
                    Xóa
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
            ← Trước
          </button>
          <span className={styles.pageInfo}>
            Trang {page + 1} / {totalPages}
          </span>
          <button
            className={styles.pageBtn}
            disabled={page >= totalPages - 1}
            onClick={() => setPage((p) => p + 1)}
          >
            Tiếp →
          </button>
        </div>
      )}

      {showCreateModal && (
        <CreateProjectModal
          onClose={() => setShowCreateModal(false)}
          onSuccess={() => loadProjects(page, searchQuery)}
        />
      )}
      {deleteTarget && (
        <DeleteProjectModal
          projectId={deleteTarget.id}
          projectName={deleteTarget.name}
          onClose={() => setDeleteTarget(null)}
          onSuccess={() => loadProjects(page, searchQuery)}
        />
      )}
    </div>
  );
}
