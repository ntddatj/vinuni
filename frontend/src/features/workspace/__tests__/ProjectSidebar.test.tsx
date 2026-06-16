import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ProjectSidebar } from '../ProjectSidebar';
import { useProjectStore } from '@/store/projectStore';
import * as projectsApi from '@/api/projects';
import type { ProjectResponse } from '@/types/project';

vi.mock('@/api/projects');
vi.mock('sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() } }));

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate };
});

const mockProject: ProjectResponse = {
  id: 'proj-1',
  name: 'Nghiên cứu NLP',
  userId: 'user-1',
  createdAt: '2026-01-01T00:00:00Z',
  updatedAt: '2026-01-01T00:00:00Z',
};

const mockProject2: ProjectResponse = {
  id: 'proj-2',
  name: 'Dự án RAG',
  userId: 'user-1',
  createdAt: '2026-01-02T00:00:00Z',
  updatedAt: '2026-01-02T00:00:00Z',
};

function renderSidebar() {
  return render(
    <MemoryRouter>
      <ProjectSidebar />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  useProjectStore.getState().setProjects([]);
});

describe('ProjectSidebar', () => {
  it('hiển thị danh sách projects từ store', () => {
    useProjectStore.getState().setProjects([mockProject, mockProject2]);
    renderSidebar();

    expect(screen.getByText('Nghiên cứu NLP')).toBeInTheDocument();
    expect(screen.getByText('Dự án RAG')).toBeInTheDocument();
  });

  it('hiển thị nút "+ Tạo dự án mới"', () => {
    renderSidebar();
    expect(screen.getByRole('button', { name: /tạo dự án mới/i })).toBeInTheDocument();
  });

  it('click "+ Tạo dự án mới" → mở CreateProjectModal', () => {
    renderSidebar();
    fireEvent.click(screen.getByRole('button', { name: /tạo dự án mới/i }));
    expect(screen.getByText('Tạo dự án mới')).toBeInTheDocument();
  });

  it('hiển thị "Xem tất cả" link', () => {
    renderSidebar();
    expect(screen.getByText(/xem tất cả/i)).toBeInTheDocument();
  });

  it('tạo project thành công → store được cập nhật', async () => {
    const newProject: ProjectResponse = {
      id: 'new-proj',
      name: 'Dự án Mới',
      userId: 'user-1',
      createdAt: '2026-06-16T00:00:00Z',
      updatedAt: '2026-06-16T00:00:00Z',
    };
    vi.mocked(projectsApi.createProject).mockResolvedValue(newProject);

    renderSidebar();
    fireEvent.click(screen.getByRole('button', { name: /tạo dự án mới/i }));

    const nameInput = screen.getByPlaceholderText(/nhập tên dự án/i);
    fireEvent.change(nameInput, { target: { value: 'Dự án Mới' } });
    // Click submit button in the modal (exact text "Tạo dự án")
    const submitBtn = screen.getByRole('button', { name: /^tạo dự án$/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(projectsApi.createProject).toHaveBeenCalledWith('Dự án Mới', undefined);
    });

    await waitFor(() => {
      const store = useProjectStore.getState();
      expect(store.projects.find((p) => p.id === 'new-proj')).toBeDefined();
    });
  });

  it('xóa project với confirm → store được cập nhật', async () => {
    useProjectStore.getState().setProjects([mockProject]);
    vi.mocked(projectsApi.deleteProject).mockResolvedValue(undefined);

    renderSidebar();

    // Hover trên project row để hiện nút xóa
    const row = screen.getByText('Nghiên cứu NLP').closest('li')!;
    fireEvent.mouseEnter(row);

    const deleteBtn = row.querySelector('button[title="Xóa"]') as HTMLButtonElement;
    fireEvent.click(deleteBtn);

    // Modal xác nhận xuất hiện
    expect(screen.getByText(/bạn có chắc muốn xóa/i)).toBeInTheDocument();

    // Xác nhận xóa
    fireEvent.click(screen.getByRole('button', { name: /xóa dự án/i }));

    await waitFor(() => {
      expect(projectsApi.deleteProject).toHaveBeenCalledWith('proj-1');
    });

    await waitFor(() => {
      const store = useProjectStore.getState();
      expect(store.projects.find((p) => p.id === 'proj-1')).toBeUndefined();
    });
  });
});
