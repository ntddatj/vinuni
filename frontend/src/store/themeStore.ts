import { create } from 'zustand';

type Theme = 'light' | 'dark';

interface ThemeState {
  theme: Theme;
  toggleTheme: () => void;
}

export const useThemeStore = create<ThemeState>()((set, get) => ({
  theme: 'light',
  toggleTheme: () => {
    const next: Theme = get().theme === 'light' ? 'dark' : 'light';
    set({ theme: next });
    document.documentElement.classList.toggle('dark', next === 'dark');
    localStorage.setItem('theme', next);
  },
}));

export function initTheme() {
  const saved = localStorage.getItem('theme') as Theme | null;
  if (saved === 'dark') {
    document.documentElement.classList.add('dark');
    useThemeStore.setState({ theme: 'dark' });
  }
}
