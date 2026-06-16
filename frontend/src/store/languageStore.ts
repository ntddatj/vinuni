import { create } from 'zustand';

type Lang = 'vi' | 'en';

interface LanguageState {
  lang: Lang;
  setLang: (lang: Lang) => void;
  toggleLang: () => void;
}

export const useLanguageStore = create<LanguageState>()((set, get) => ({
  lang: 'vi',
  setLang: (lang) => set({ lang }),
  toggleLang: () => set({ lang: get().lang === 'vi' ? 'en' : 'vi' }),
}));
