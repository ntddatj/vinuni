import { useThemeStore, initTheme } from '../themeStore';
import { act } from '@testing-library/react';

describe('themeStore', () => {
  beforeEach(() => {
    useThemeStore.setState({ theme: 'light' });
    document.documentElement.classList.remove('dark');
    localStorage.clear();
  });

  it('starts with light theme', () => {
    expect(useThemeStore.getState().theme).toBe('light');
  });

  it('toggleTheme switches to dark', () => {
    const { toggleTheme } = useThemeStore.getState();
    act(() => toggleTheme());
    expect(useThemeStore.getState().theme).toBe('dark');
  });

  it('toggleTheme adds dark class to documentElement', () => {
    const { toggleTheme } = useThemeStore.getState();
    act(() => toggleTheme());
    expect(document.documentElement.classList.contains('dark')).toBe(true);
  });

  it('toggleTheme saves to localStorage', () => {
    const { toggleTheme } = useThemeStore.getState();
    act(() => toggleTheme());
    expect(localStorage.getItem('theme')).toBe('dark');
  });

  it('toggleTheme switches back to light', () => {
    act(() => {
      useThemeStore.setState({ theme: 'dark' });
      document.documentElement.classList.add('dark');
    });
    const { toggleTheme } = useThemeStore.getState();
    act(() => toggleTheme());
    expect(useThemeStore.getState().theme).toBe('light');
    expect(document.documentElement.classList.contains('dark')).toBe(false);
    expect(localStorage.getItem('theme')).toBe('light');
  });
});

describe('initTheme', () => {
  beforeEach(() => {
    useThemeStore.setState({ theme: 'light' });
    document.documentElement.classList.remove('dark');
    localStorage.clear();
  });

  it('applies dark theme from localStorage on init', () => {
    localStorage.setItem('theme', 'dark');
    initTheme();
    expect(document.documentElement.classList.contains('dark')).toBe(true);
    expect(useThemeStore.getState().theme).toBe('dark');
  });

  it('does nothing when localStorage has no theme', () => {
    initTheme();
    expect(document.documentElement.classList.contains('dark')).toBe(false);
    expect(useThemeStore.getState().theme).toBe('light');
  });
});
