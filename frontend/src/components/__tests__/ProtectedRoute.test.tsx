import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ProtectedRoute } from '../ProtectedRoute';
import * as authApi from '@/api/auth';
import { useAuthStore } from '@/store/authStore';

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate };
});

vi.mock('@/api/auth');

const mockUser = {
  id: '1',
  email: 'u@b.com',
  role: 'user' as const,
  isActive: true,
  createdAt: '',
  updatedAt: '',
};

beforeEach(() => {
  vi.clearAllMocks();
  useAuthStore.setState({ user: null, isLoading: true });
});

describe('ProtectedRoute', () => {
  it('renders children when /me returns valid session', async () => {
    vi.mocked(authApi.getCurrentUser).mockResolvedValue(mockUser);

    render(
      <MemoryRouter>
        <ProtectedRoute>
          <div>Protected Content</div>
        </ProtectedRoute>
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.getByText('Protected Content')).toBeInTheDocument());
  });

  it('redirects to /login when /me returns 401', async () => {
    vi.mocked(authApi.getCurrentUser).mockRejectedValue({ response: { status: 401 } });

    render(
      <MemoryRouter>
        <ProtectedRoute>
          <div>Protected Content</div>
        </ProtectedRoute>
      </MemoryRouter>,
    );

    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/login', { replace: true }));
  });
});
