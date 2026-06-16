import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { RegisterPage } from '../RegisterPage';
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
  email: 'new@b.com',
  role: 'user' as const,
  isActive: true,
  createdAt: '',
  updatedAt: '',
};

beforeEach(() => {
  vi.clearAllMocks();
});

function renderRegister() {
  return render(
    <MemoryRouter>
      <RegisterPage />
    </MemoryRouter>,
  );
}

describe('RegisterPage', () => {
  it('registers then auto-logs in and redirects to /onboarding when no projects', async () => {
    vi.mocked(authApi.registerUser).mockResolvedValue(mockUser);
    vi.mocked(authApi.loginUser).mockResolvedValue(mockUser);
    vi.mocked(projectsApi.listProjects).mockResolvedValue([]);

    renderRegister();

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'new@b.com' } });
    fireEvent.change(screen.getByLabelText(/mật khẩu/i), { target: { value: 'password1' } });
    fireEvent.click(screen.getByRole('button', { name: /đăng ký/i }));

    await waitFor(() =>
      expect(authApi.registerUser).toHaveBeenCalledWith('new@b.com', 'password1'),
    );
    await waitFor(() => expect(authApi.loginUser).toHaveBeenCalledWith('new@b.com', 'password1'));
    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/onboarding'));
  });

  it('shows toast error when email already exists', async () => {
    const { toast } = await import('sonner');
    vi.mocked(authApi.registerUser).mockRejectedValue({
      response: { data: { detail: 'Email đã tồn tại' } },
    });

    renderRegister();

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'dup@b.com' } });
    fireEvent.change(screen.getByLabelText(/mật khẩu/i), { target: { value: 'password1' } });
    fireEvent.click(screen.getByRole('button', { name: /đăng ký/i }));

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Email đã tồn tại'));
  });

  it('shows toast error when password exceeds 72 chars', async () => {
    const { toast } = await import('sonner');

    renderRegister();

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'a@b.com' } });
    fireEvent.change(screen.getByLabelText(/mật khẩu/i), {
      target: { value: 'a'.repeat(73) },
    });
    fireEvent.click(screen.getByRole('button', { name: /đăng ký/i }));

    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith('Mật khẩu không được vượt quá 72 ký tự'),
    );
  });
});
