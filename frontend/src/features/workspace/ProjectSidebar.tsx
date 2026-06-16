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

export function ProjectSidebar() {
  const navigate = useNavigate();
  const { projects, updateProject: storeUpdateProject, setActiveProjectId } = useProjectStore();
  const { t } = useTranslation();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; name: string } | null>(null);
  const [renameTarget, setRenameTarget] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');
  // Guards against double-fire from Enter→blur and Escape→blur
  const isCommittingRef = useRef(false);
  const isCancelledRef = useRef(false);

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
      <aside className={styles.sidebar}>
        <button className={styles.createButton} onClick={() => setShowCreateModal(true)}>
          {t('sidebar.createProject')}
        </button>

        <span className={styles.listTitle}>{t('sidebar.projectList')}</span>

        <ul className={styles.projectList}>
          {projects.map((project) => (
            <li key={project.id} className={styles.projectRow}>
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
                    onClick={() => {
                      setActiveProjectId(project.id);
                      navigate(`/dashboard?projectId=${project.id}`);
                    }}
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
          ))}
        </ul>

        <a href="/projects" className={styles.viewAllLink} onClick={(e) => { e.preventDefault(); navigate('/projects'); }}>
          {t('sidebar.viewAll')}
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
