import { render, screen, fireEvent } from '@testing-library/react';
import { ChatbotPanel } from '../ChatbotPanel';

vi.mock('@/store/languageStore', () => ({
  useLanguageStore: (selector: (s: { lang: 'vi' }) => unknown) => selector({ lang: 'vi' }),
}));

describe('ChatbotPanel', () => {
  it('renders panel with default width 25vw', () => {
    render(<ChatbotPanel />);
    const panel = document.querySelector('[style*="25vw"]');
    expect(panel).not.toBeNull();
  });

  it('renders research assistant title', () => {
    render(<ChatbotPanel />);
    expect(screen.getByText('Trợ lý nghiên cứu')).toBeInTheDocument();
  });

  it('collapses panel when toggle button clicked', () => {
    render(<ChatbotPanel />);
    const toggleBtn = screen.getByTitle('Ẩn Chat');
    fireEvent.click(toggleBtn);
    const panel = document.querySelector('[style*="width: 0"]');
    expect(panel).not.toBeNull();
  });

  it('expands panel back after collapse', () => {
    render(<ChatbotPanel />);
    const hideBtn = screen.getByTitle('Ẩn Chat');
    fireEvent.click(hideBtn);
    const showBtn = screen.getByTitle('Hiện Chat');
    fireEvent.click(showBtn);
    const panel = document.querySelector('[style*="25vw"]');
    expect(panel).not.toBeNull();
  });

  it('resets width to 25% on double click of resize handle', () => {
    render(<ChatbotPanel />);
    const handle = document.querySelector('[role="separator"]');
    expect(handle).not.toBeNull();
    fireEvent.doubleClick(handle!);
    const panel = document.querySelector('[style*="25vw"]');
    expect(panel).not.toBeNull();
  });
});
