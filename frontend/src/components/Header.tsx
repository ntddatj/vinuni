import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';
import { logoutUser } from '@/api/auth';
import { useThemeStore } from '@/store/themeStore';
import { useLanguageStore } from '@/store/languageStore';
import { useTranslation } from '@/i18n/useTranslation';
import { useProjectStore } from '@/store/projectStore';
import styles from './Header.module.css';

export function Header() {
  const { user, setUser } = useAuthStore();
  const navigate = useNavigate();
  const { theme, toggleTheme } = useThemeStore();
  const { toggleLang } = useLanguageStore();
  const { t, lang } = useTranslation();
  const activeProjectId = useProjectStore((s) => s.activeProjectId);
  const projects = useProjectStore((s) => s.projects);
  const activeProject = projects.find((p) => p.id === activeProjectId);

  async function handleLogout() {
    try {
      await logoutUser();
    } finally {
      setUser(null);
      navigate('/login');
    }
  }

  return (
    <header className={styles.header}>
      <div className={styles.brand}>
        <span className={styles.logo}>{t('header.brand')}</span>
        {activeProject && (
          <span className={styles.badge}>{activeProject.name}</span>
        )}
      </div>
      <div className={styles.actions}>
        {user?.role === 'admin' && (
          <button
            className={`${styles.iconButton} ${styles.adminButton}`}
            type="button"
            onClick={() => navigate('/admin/settings')}
          >
            ⚙️ {t('header.settings')}
          </button>
        )}
        <button
          className={styles.iconButton}
          type="button"
          onClick={() => navigate('/settings/api-keys')}
        >
          {t('header.apiKeys')}
        </button>
        <button className={styles.toggle} type="button" onClick={toggleTheme}>
          {theme === 'light' ? '🌙' : '☀️'}
        </button>
        <button className={styles.toggle} type="button" onClick={toggleLang}>
          {lang === 'vi' ? 'VI | EN' : 'EN | VI'}
        </button>
        <button className={styles.iconButton} type="button" onClick={handleLogout}>
          🚪 {t('header.logout')}
        </button>
      </div>
    </header>
  );
}
