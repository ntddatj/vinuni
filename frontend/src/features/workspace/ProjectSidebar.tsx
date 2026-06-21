import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { updateProject } from '@/api/projects';
import { getErrorMessage } from '@/api/errors';
import { useProjectStore } from '@/store/projectStore';
import { useTranslation } from '@/i18n/useTranslation';
import { CreateProjectModal } from './CreateProjectModal';
import { DeleteProjectModal } from './DeleteProjectModal';
import styles from './ProjectSidebar.module.css';

const COLLAPSED_KEY = 'sidebar.collapsed';

function projectInitial(name: string): string {
  return name.trim().charAt(0).toUpperCase() || '?';
}

export function ProjectSidebar() {
  const navigate = useNavigate();
  const {
    projects,
    updateProject: storeUpdateProject,
    setActiveProjectId,
    activeProjectId,
  } = useProjectStore();
  const { t } = useTranslation();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; name: string } | null>(null);
  const [renameTarget, setRenameTarget] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');
  // Trạng thái thu gọn được ghi nhớ qua localStorage để giữ nguyên sau khi tải lại.
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    try {
      return localStorage.getItem(COLLAPSED_KEY) === '1';
    } catch {
      return false;
    }
  });
  // Guards against double-fire from Enter→blur and Escape→blur
  const isCommittingRef = useRef(false);
  const isCancelledRef = useRef(false);

  function toggleCollapse() {
    setCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem(COLLAPSED_KEY, next ? '1' : '0');
      } catch {
        /* localStorage không khả dụng — bỏ qua, state vẫn đổi trong phiên này */
      }
      return next;
    });
  }

  function openProject(id: string) {
    setActiveProjectId(id);
    navigate(`/dashboard?projectId=${id}`);
  }

  function startRename(id: string, currentName: string) {
    isCommittingRef.current = false;
    isCancelledRef.current = false;
    setRenameTarget(id);
    setRenameValue(currentName);
  }

  async function commitRename(id: string) {
    if (isCommittingRef.current || isCancelledRef.current) return;
    isCommittingRef.current = true;
    const trimmed = renameValue.trim();
    if (!trimmed) {
      isCommittingRef.current = false;
      setRenameTarget(null);
      return;
    }
    try {
      const updated = await updateProject(id, trimmed);
      storeUpdateProject(updated);
      toast.success('Đã đổi tên dự án');
    } catch (err) {
      toast.error(getErrorMessage(err, 'Không thể đổi tên dự án'));
    } finally {
      isCommittingRef.current = false;
      setRenameTarget(null);
    }
  }

  function handleRenameKeyDown(e: React.KeyboardEvent, id: string) {
    if (e.key === 'Enter') {
      e.preventDefault();
      commitRename(id);
    }
    if (e.key === 'Escape') {
      isCancelledRef.current = true;
      setRenameTarget(null);
    }
  }

  return (
    <>
      <aside className={`${styles.sidebar} ${collapsed ? styles.sidebarCollapsed : ''}`}>
        <div className={styles.topBar}>
          <button
            className={styles.toggleBtn}
            onClick={toggleCollapse}
            title={collapsed ? t('sidebar.expand') : t('sidebar.collapse')}
            aria-label={collapsed ? t('sidebar.expand') : t('sidebar.collapse')}
            aria-expanded={!collapsed}
            type="button"
          >
            {collapsed ? '☰' : '«'}
          </button>
        </div>

        <button
          className={styles.createButton}
          onClick={() => setShowCreateModal(true)}
          title={t('sidebar.createProject')}
        >
          {collapsed ? '+' : t('sidebar.createProject')}
        </button>

        {!collapsed && <span className={styles.listTitle}>{t('sidebar.projectList')}</span>}

        <ul className={styles.projectList}>
          {projects.map((project) => {
            const isActive = project.id === activeProjectId;
            const rowClass = `${styles.projectRow} ${isActive ? styles.active : ''}`;

            if (collapsed) {
              return (
                <li key={project.id} className={rowClass}>
                  <button
                    className={styles.avatar}
                    title={project.name}
                    aria-label={project.name}
                    onClick={() => openProject(project.id)}
                    type="button"
                  >
                    {projectInitial(project.name)}
                  </button>
                </li>
              );
            }

            return (
              <li key={project.id} className={rowClass}>
                {renameTarget === project.id ? (
                  <input
                    className={styles.renameInput}
                    value={renameValue}
                    autoFocus
                    onChange={(e) => setRenameValue(e.target.value)}
                    onBlur={() => commitRename(project.id)}
                    onKeyDown={(e) => handleRenameKeyDown(e, project.id)}
                    maxLength={255}
                  />
                ) : (
                  <>
                    <span
                      className={styles.projectName}
                      onClick={() => openProject(project.id)}
                      title={project.name}
                    >
                      {project.name}
                    </span>
                    <span className={styles.actions}>
                      <button
                        className={styles.actionBtn}
                        title={t('sidebar.rename')}
                        onClick={(e) => {
                          e.stopPropagation();
                          startRename(project.id, project.name);
                        }}
                      >
                        ✏️
                      </button>
                      <button
                        className={styles.actionBtn}
                        title={t('sidebar.delete')}
                        onClick={(e) => {
                          e.stopPropagation();
                          setDeleteTarget({ id: project.id, name: project.name });
                        }}
                      >
                        🗑️
                      </button>
                    </span>
                  </>
                )}
              </li>
            );
          })}
        </ul>

        <a
          href="/projects"
          className={styles.viewAllLink}
          title={t('sidebar.viewAll')}
          onClick={(e) => {
            e.preventDefault();
            navigate('/projects');
          }}
        >
          {collapsed ? '→' : t('sidebar.viewAll')}
        </a>
      </aside>

      {showCreateModal && <CreateProjectModal onClose={() => setShowCreateModal(false)} />}
      {deleteTarget && (
        <DeleteProjectModal
          projectId={deleteTarget.id}
          projectName={deleteTarget.name}
          onClose={() => setDeleteTarget(null)}
        />
      )}
    </>
  );
}
