import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { loginUser } from '@/api/auth';
import { listProjects } from '@/api/projects';
import { getErrorMessage } from '@/api/errors';
import { useAuthStore } from '@/store/authStore';
import styles from './LoginPage.module.css';

export function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { setUser } = useAuthStore();
  const navigate = useNavigate();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const user = await loginUser(email, password);
      setUser(user);
      try {
        const projects = await listProjects();
        if (projects.length === 0) {
          navigate('/onboarding');
        } else {
          navigate('/dashboard');
        }
      } catch {
        navigate('/onboarding');
      }
    } catch (err: unknown) {
      toast.error(getErrorMessage(err, 'Đăng nhập thất bại'));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        <h1 className={styles.title}>Đăng nhập</h1>
        <form onSubmit={handleSubmit}>
          <div className={styles.field}>
            <label className={styles.label} htmlFor="email">
              Email
            </label>
            <input
              id="email"
              className={styles.input}
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div className={styles.field}>
            <label className={styles.label} htmlFor="password">
              Mật khẩu
            </label>
            <input
              id="password"
              className={styles.input}
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <button className={styles.button} type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Đang đăng nhập...' : 'Đăng nhập'}
          </button>
        </form>
        <Link className={styles.link} to="/register">
          Chưa có tài khoản? Đăng ký
        </Link>
      </div>
    </div>
  );
}
