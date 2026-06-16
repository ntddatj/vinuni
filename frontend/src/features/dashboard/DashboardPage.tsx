import { useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { toast } from 'sonner';
import { getProjects } from '@/api/projects';
import { getErrorMessage } from '@/api/errors';
import { useProjectStore } from '@/store/projectStore';
import { ProjectSidebar } from '@/features/workspace/ProjectSidebar';
import { CenterWorkspace } from '@/features/workspace/CenterWorkspace';
import { ChatbotPanel } from '@/features/workspace/ChatbotPanel';
import styles from './DashboardPage.module.css';

export function DashboardPage() {
  const [searchParams] = useSearchParams();
  const { setProjects, setActiveProjectId } = useProjectStore();

  useEffect(() => {
    const projectId = searchParams.get('projectId');
    if (projectId) setActiveProjectId(projectId);

    getProjects(10, 0)
      .then(({ items }) => setProjects(items))
      .catch((err) => toast.error(getErrorMessage(err, 'Không thể tải dự án')));
  }, [searchParams, setProjects, setActiveProjectId]);

  return (
    <div className={styles.layout}>
      <ProjectSidebar />
      <CenterWorkspace />
      <ChatbotPanel />
    </div>
  );
}
