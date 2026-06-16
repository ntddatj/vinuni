import { useLanguageStore } from '@/store/languageStore';
import { translations, type TranslationKey } from './translations';

export function useTranslation() {
  const lang = useLanguageStore((s) => s.lang);
  function t(key: TranslationKey): string {
    return translations[key][lang];
  }
  return { t, lang };
}
