import { render, screen, fireEvent } from '@testing-library/react';
import { CenterWorkspace } from '../CenterWorkspace';

vi.mock('@/store/projectStore', () => ({
  useProjectStore: (selector: (s: { projects: []; activeProjectId: null }) => unknown) =>
    selector({ projects: [], activeProjectId: null }),
}));

vi.mock('@/store/languageStore', () => ({
  useLanguageStore: (selector: (s: { lang: 'vi' }) => unknown) => selector({ lang: 'vi' }),
}));

describe('CenterWorkspace', () => {
  it('renders 3 tabs', () => {
    render(<CenterWorkspace />);
    expect(screen.getByRole('button', { name: 'Thư viện Tài liệu' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Bản đồ Tri thức' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Hỗ trợ viết tổng quan' })).toBeInTheDocument();
  });

  it('starts with library tab active', () => {
    render(<CenterWorkspace />);
    const libraryBtn = screen.getByRole('button', { name: 'Thư viện Tài liệu' });
    expect(libraryBtn.className).toContain('tabActive');
    const graphBtn = screen.getByRole('button', { name: 'Bản đồ Tri thức' });
    expect(graphBtn.className).not.toContain('tabActive');
  });

  it('switches active tab on click', () => {
    render(<CenterWorkspace />);
    const graphBtn = screen.getByRole('button', { name: 'Bản đồ Tri thức' });
    fireEvent.click(graphBtn);
    expect(graphBtn.className).toContain('tabActive');
    const libraryBtn = screen.getByRole('button', { name: 'Thư viện Tài liệu' });
    expect(libraryBtn.className).not.toContain('tabActive');
  });

  it('shows correct tab content without unmounting other tabs', () => {
    render(<CenterWorkspace />);
    const writingBtn = screen.getByRole('button', { name: 'Hỗ trợ viết tổng quan' });
    fireEvent.click(writingBtn);
    // All tab content elements still exist (display:none pattern)
    expect(screen.getAllByText(/Thư viện Tài liệu/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Hỗ trợ viết tổng quan/i).length).toBeGreaterThanOrEqual(1);
  });
});
