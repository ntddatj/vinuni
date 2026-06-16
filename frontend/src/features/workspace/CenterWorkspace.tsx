import { useState } from 'react';
import { useProjectStore } from '@/store/projectStore';
import { useTranslation } from '@/i18n/useTranslation';
import { LibraryTab } from './LibraryTab';
import styles from './CenterWorkspace.module.css';

type TabKey = 'library' | 'graph' | 'writing';

export function CenterWorkspace() {
  const [activeTab, setActiveTab] = useState<TabKey>('library');
  const activeProjectId = useProjectStore((s) => s.activeProjectId);
  const projects = useProjectStore((s) => s.projects);
  const { t } = useTranslation();

  const activeProject = projects.find((p) => p.id === activeProjectId);
  const projectTitle = activeProject?.name ?? t('workspace.selectProject');

  return (
    <div className={styles.workspace}>
      <div className={styles.tabBar}>
        <button
          className={`${styles.tab} ${activeTab === 'library' ? styles.tabActive : ''}`}
          onClick={() => setActiveTab('library')}
          type="button"
        >
          {t('tab.library')}
        </button>
        <button
          className={`${styles.tab} ${activeTab === 'graph' ? styles.tabActive : ''}`}
          onClick={() => setActiveTab('graph')}
          type="button"
        >
          {t('tab.graph')}
        </button>
        <button
          className={`${styles.tab} ${activeTab === 'writing' ? styles.tabActive : ''}`}
          onClick={() => setActiveTab('writing')}
          type="button"
        >
          {t('tab.writing')}
        </button>
      </div>

      <div className={styles.projectHeader}>
        <h2 className={styles.projectTitle}>{projectTitle}</h2>
      </div>

      <div className={styles.tabContent}>
        <div style={{ display: activeTab === 'library' ? 'block' : 'none' }}>
          <LibraryTab />
        </div>
        <div style={{ display: activeTab === 'graph' ? 'block' : 'none' }}>
          <p className={styles.placeholder}>{t('tab.graph')}</p>
        </div>
        <div style={{ display: activeTab === 'writing' ? 'block' : 'none' }}>
          <p className={styles.placeholder}>{t('tab.writing')}</p>
        </div>
      </div>
    </div>
  );
}
