import { act, render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { ProjectsPage } from '../ProjectsPage';
import * as projectsApi from '@/api/projects';

vi.mock('@/api/projects');
vi.mock('sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() } }));

const mockProjects = [
  { id: '1', name: 'Dự án Alpha', description: 'Mô tả A', userId: 'u1', createdAt: '2026-01-15T00:00:00Z', updatedAt: '2026-01-15T00:00:00Z' },
  { id: '2', name: 'Dự án Beta', description: undefined, userId: 'u1', createdAt: '', updatedAt: '' },
];

function renderPage() {
  return render(
    <MemoryRouter>
      <ProjectsPage />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(projectsApi.getProjects).mockResolvedValue({ items: mockProjects, total: 2 });
});

afterEach(() => {
  vi.useRealTimers();
});

describe('ProjectsPage', () => {
  it('hiển thị bảng với dữ liệu mock', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText('Dự án Alpha')).toBeInTheDocument());
    expect(screen.getByText('Dự án Beta')).toBeInTheDocument();
    expect(screen.getByText('Mô tả A')).toBeInTheDocument();
  });

  it('hiển thị tiêu đề cột đúng', async () => {
    renderPage();
    await waitFor(() => screen.getByText('Dự án Alpha'));
    expect(screen.getByText('Tên dự án')).toBeInTheDocument();
    expect(screen.getByText('Mô tả')).toBeInTheDocument();
    expect(screen.getByText('Ngày tạo')).toBeInTheDocument();
    expect(screen.getByText('Hành động')).toBeInTheDocument();
  });

  it('createdAt rỗng hiển thị —', async () => {
    renderPage();
    await waitFor(() => screen.getByText('Dự án Beta'));
    const dashes = screen.getAllByText('—');
    expect(dashes.length).toBeGreaterThan(0);
  });

  it('click icon 🗑 mở DeleteProjectModal với đúng tên dự án', async () => {
    renderPage();
    await waitFor(() => screen.getByText('Dự án Alpha'));
    const trashBtns = screen.getAllByTitle('Xóa');
    fireEvent.click(trashBtns[0]);
    expect(screen.getByText(/Bạn có chắc muốn xóa/i)).toBeInTheDocument();
    // tên dự án xuất hiện trong modal (trong <strong>)
    const allAlpha = screen.getAllByText(/Dự án Alpha/);
    expect(allAlpha.length).toBeGreaterThanOrEqual(2); // cả trong bảng lẫn trong modal
  });

  it('debounce: search gọi API sau 300ms', async () => {
    vi.useFakeTimers();
    renderPage();

    // Chờ initial debounce 300ms + flush promise API
    await act(async () => {
      vi.advanceTimersByTime(300);
    });
    await act(async () => {});

    vi.clearAllMocks();
    vi.mocked(projectsApi.getProjects).mockResolvedValue({ items: [], total: 0 });

    const input = screen.getByRole('searchbox');
    await act(async () => {
      fireEvent.change(input, { target: { value: 'Alpha' } });
    });

    // Chưa đủ 300ms → chưa gọi API
    expect(vi.mocked(projectsApi.getProjects)).not.toHaveBeenCalled();

    // Advance qua debounce
    await act(async () => {
      vi.advanceTimersByTime(300);
    });
    await act(async () => {});

    expect(vi.mocked(projectsApi.getProjects)).toHaveBeenCalledWith(10, 0, 'Alpha');
  });

  it('phân trang: hiện nút prev/next khi total > PAGE_SIZE', async () => {
    vi.mocked(projectsApi.getProjects).mockResolvedValue({ items: mockProjects, total: 25 });
    renderPage();
    await waitFor(() => screen.getByText('Dự án Alpha'));
    expect(screen.getByText('← Trước')).toBeInTheDocument();
    expect(screen.getByText('Tiếp →')).toBeInTheDocument();
  });

  it('không hiện phân trang khi total <= PAGE_SIZE', async () => {
    renderPage();
    await waitFor(() => screen.getByText('Dự án Alpha'));
    expect(screen.queryByText('← Trước')).not.toBeInTheDocument();
  });

  it('AC#3: gõ tìm kiếm từ trang 2 reset về trang 1', async () => {
    vi.useFakeTimers();
    vi.mocked(projectsApi.getProjects).mockResolvedValue({ items: mockProjects, total: 25 });
    renderPage();

    // Flush mount debounce + initial load
    await act(async () => { vi.advanceTimersByTime(300); });
    await act(async () => {});

    // Chuyển sang trang 2
    const nextBtn = screen.getByText('Tiếp →');
    await act(async () => { fireEvent.click(nextBtn); });
    await act(async () => {});

    vi.clearAllMocks();
    vi.mocked(projectsApi.getProjects).mockResolvedValue({ items: [], total: 0 });

    // Gõ tìm kiếm
    const input = screen.getByRole('searchbox');
    await act(async () => { fireEvent.change(input, { target: { value: 'xyz' } }); });

    // Flush debounce
    await act(async () => { vi.advanceTimersByTime(300); });
    await act(async () => {});

    // API phải được gọi với offset=0 (trang 1)
    expect(vi.mocked(projectsApi.getProjects)).toHaveBeenCalledWith(10, 0, 'xyz');
  });

  it('AC#4: xóa item cuối trên trang > 0 → tự lùi về trang trước', async () => {
    const singleItem = [mockProjects[0]];
    // Setup: tổng 21 dự án → 3 trang; đang ở trang 2 (index 1) có 1 item
    vi.mocked(projectsApi.getProjects)
      .mockResolvedValueOnce({ items: singleItem, total: 21 }) // lần load đầu (mount trang 1)
      .mockResolvedValueOnce({ items: singleItem, total: 21 }) // sau khi nhấn Tiếp → (trang 2)
      .mockResolvedValue({ items: mockProjects, total: 21 });  // sau khi lùi về trang 1
    vi.mocked(projectsApi.deleteProject).mockResolvedValue(undefined);
    renderPage();
    await waitFor(() => screen.getByText('Dự án Alpha'));

    // Chuyển sang trang 2 (index 1) — page indicator "2 / 3"
    await act(async () => { fireEvent.click(screen.getByText('Tiếp →')); });
    await waitFor(() => screen.getByText('2 / 3'));

    // Mở modal xóa và xác nhận
    await act(async () => { fireEvent.click(screen.getAllByLabelText('Xóa')[0]); });
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: /xóa dự án/i })); });

    // handleDeleteSuccess: projects.length===1 && page>0 → setPage(0) → lùi về "1 / 3"
    await waitFor(() => expect(screen.getByText('1 / 3')).toBeInTheDocument());
  });
});
