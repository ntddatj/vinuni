import { useCallback } from 'react';
import { useLanguageStore } from '@/store/languageStore';
import { translations, type TranslationKey } from './translations';

export function useTranslation() {
  const lang = useLanguageStore((s) => s.lang);
  const t = useCallback((key: TranslationKey): string => {
    // Guard key không tồn tại: callers có thể truyền key động (vd
    // `chat.thinking.${status}` qua `as any`). Trả '' để không crash render và để
    // pattern `t(dynamicKey) || t(fallback)` hoạt động đúng thay vì ném TypeError.
    const entry = translations[key];
    return entry ? entry[lang] : '';
  }, [lang]);
  return { t, lang };
}
