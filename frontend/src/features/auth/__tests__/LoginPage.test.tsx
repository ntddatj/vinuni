import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { LoginPage } from '../LoginPage';
import * as authApi from '@/api/auth';
import * as projectsApi from '@/api/projects';

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate };
});

vi.mock('@/api/auth');
vi.mock('@/api/projects');
vi.mock('sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() } }));

const mockUser = {
  id: '1',
  email: 'a@b.com',
  role: 'user' as const,
  isActive: true,
  createdAt: '',
  updatedAt: '',
};

beforeEach(() => {
  vi.clearAllMocks();
});

function renderLogin() {
  return render(
    <MemoryRouter>
      <LoginPage />
    </MemoryRouter>,
  );
}

describe('LoginPage', () => {
  it('redirects to /onboarding when login succeeds and no projects', async () => {
    vi.mocked(authApi.loginUser).mockResolvedValue(mockUser);
    vi.mocked(projectsApi.listProjects).mockResolvedValue([]);

    renderLogin();

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'a@b.com' } });
    fireEvent.change(screen.getByLabelText(/mật khẩu/i), { target: { value: 'pass1234' } });
    fireEvent.click(screen.getByRole('button', { name: /đăng nhập/i }));

    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/onboarding'));
  });

  it('redirects to /dashboard when login succeeds and has projects', async () => {
    vi.mocked(authApi.loginUser).mockResolvedValue(mockUser);
    vi.mocked(projectsApi.listProjects).mockResolvedValue([
      { id: 'p1', name: 'My Project', userId: '1', createdAt: '', updatedAt: '' },
    ]);

    renderLogin();

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'a@b.com' } });
    fireEvent.change(screen.getByLabelText(/mật khẩu/i), { target: { value: 'pass1234' } });
    fireEvent.click(screen.getByRole('button', { name: /đăng nhập/i }));

    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/dashboard'));
  });

  it('shows toast error on 401 wrong credentials', async () => {
    const { toast } = await import('sonner');
    vi.mocked(authApi.loginUser).mockRejectedValue({
      response: { data: { detail: 'Email hoặc mật khẩu không đúng' } },
    });

    renderLogin();

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'bad@b.com' } });
    fireEvent.change(screen.getByLabelText(/mật khẩu/i), { target: { value: 'wrongpw1' } });
    fireEvent.click(screen.getByRole('button', { name: /đăng nhập/i }));

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Email hoặc mật khẩu không đúng'));
  });
});
