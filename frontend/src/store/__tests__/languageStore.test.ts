import { useLanguageStore } from '../languageStore';
import { useTranslation } from '@/i18n/useTranslation';
import { renderHook, act } from '@testing-library/react';

describe('languageStore', () => {
  beforeEach(() => {
    useLanguageStore.setState({ lang: 'vi' });
  });

  it('starts with Vietnamese as default', () => {
    const { lang } = useLanguageStore.getState();
    expect(lang).toBe('vi');
  });

  it('setLang changes language', () => {
    const { setLang } = useLanguageStore.getState();
    act(() => setLang('en'));
    expect(useLanguageStore.getState().lang).toBe('en');
  });

  it('toggleLang switches from vi to en', () => {
    const { toggleLang } = useLanguageStore.getState();
    act(() => toggleLang());
    expect(useLanguageStore.getState().lang).toBe('en');
  });

  it('toggleLang switches from en back to vi', () => {
    act(() => useLanguageStore.setState({ lang: 'en' }));
    const { toggleLang } = useLanguageStore.getState();
    act(() => toggleLang());
    expect(useLanguageStore.getState().lang).toBe('vi');
  });
});

describe('useTranslation hook', () => {
  beforeEach(() => {
    useLanguageStore.setState({ lang: 'vi' });
  });

  it('translates key to Vietnamese', () => {
    const { result } = renderHook(() => useTranslation());
    expect(result.current.t('tab.library')).toBe('Thư viện Tài liệu');
  });

  it('translates key to English when lang is en', () => {
    act(() => useLanguageStore.setState({ lang: 'en' }));
    const { result } = renderHook(() => useTranslation());
    expect(result.current.t('tab.library')).toBe('Document Library');
  });

  it('translates chat.title correctly', () => {
    const { result } = renderHook(() => useTranslation());
    expect(result.current.t('chat.title')).toBe('Trợ lý nghiên cứu');
  });
});
