import { useCallback } from 'react';
import { useLanguageStore } from '@/store/languageStore';
import { translations, type TranslationKey } from './translations';

export function useTranslation() {
  const lang = useLanguageStore((s) => s.lang);
  const t = useCallback((key: TranslationKey): string => {
    return translations[key][lang];
  }, [lang]);
  return { t, lang };
}
