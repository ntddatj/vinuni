import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';
import { logoutUser } from '@/api/auth';
import styles from './Header.module.css';

export function Header() {
  const { user, setUser } = useAuthStore();
  const navigate = useNavigate();

  async function handleLogout() {
    try {
      await logoutUser();
    } finally {
      setUser(null);
      navigate('/login');
    }
  }

  function toggleDarkMode() {
    document.documentElement.classList.toggle('dark');
  }

  return (
    <header className={styles.header}>
      <span className={styles.logo}>C2 Research</span>
      <div className={styles.actions}>
        {user?.role === 'admin' && (
          <button className={`${styles.iconButton} ${styles.adminButton}`} type="button">
            ⚙️ Cài đặt Hệ thống
          </button>
        )}
        <button className={styles.toggle} type="button" onClick={toggleDarkMode}>
          🌙 Dark
        </button>
        <button className={styles.toggle} type="button">
          VI | EN
        </button>
        <button className={styles.iconButton} type="button" onClick={handleLogout}>
          🚪 Đăng xuất
        </button>
      </div>
    </header>
  );
}
