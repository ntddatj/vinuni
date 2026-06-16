import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';
import { getCurrentUser } from '@/api/auth';
import { Header } from './Header';

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading, setUser, setLoading } = useAuthStore();
  const navigate = useNavigate();

  useEffect(() => {
    if (user) {
      setLoading(false);
      return;
    }
    setLoading(true);
    getCurrentUser()
      .then((u) => {
        setUser(u);
        setLoading(false);
      })
      .catch(() => {
        navigate('/login', { replace: true });
      });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Render children only once a verified user exists — guards against flashing
  // protected content when re-entering a route while isLoading is stale false.
  if (isLoading || !user) return <div className="spinner" />;
  return (
    <>
      <Header />
      {children}
    </>
  );
}
