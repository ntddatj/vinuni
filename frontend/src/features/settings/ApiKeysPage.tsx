import { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { getApiKeys, saveApiKey, testApiKey } from '@/api/userCredentials';
import { getErrorMessage } from '@/api/errors';
import { useTranslation } from '@/i18n/useTranslation';
import type { ApiKeyStatus } from '@/types/userCredential';
import styles from './ApiKeysPage.module.css';

const PROVIDERS = [{ key: 'gemini', label: 'Gemini (Google AI)' }] as const;

const ERROR_CODE_KEYS = {
  timeout: 'apiKeys.errorTimeout',
  connection_failed: 'apiKeys.errorConnectionFailed',
} as const;

function formatLastTested(iso: string, justNowLabel: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return '';
  const diffSec = Math.floor((Date.now() - d.getTime()) / 1000);
  if (diffSec < 60) return justNowLabel;
  return d.toLocaleString();
}

export function ApiKeysPage() {
  const { t } = useTranslation();
  const [apiKeys, setApiKeys] = useState<ApiKeyStatus[]>([]);
  const [editingProvider, setEditingProvider] = useState<string | null>(null);
  const [inputValue, setInputValue] = useState('');
  const [isSaving, setIsSaving] = useState<Record<string, boolean>>({});
  const [isTesting, setIsTesting] = useState<Record<string, boolean>>({});
  const [testErrors, setTestErrors] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(true);

  const loadApiKeys = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await getApiKeys();
      setApiKeys(data);
    } catch (err) {
      toast.error(getErrorMessage(err, t('apiKeys.loadError')));
    } finally {
      setIsLoading(false);
    }
  }, [t]);

  useEffect(() => {
    loadApiKeys();
  }, [loadApiKeys]);

  async function handleSave(provider: string) {
    if (!inputValue.trim()) {
      toast.error(t('apiKeys.emptyKey'));
      return;
    }
    setIsSaving((prev) => ({ ...prev, [provider]: true }));
    try {
      await saveApiKey(provider, { apiKey: inputValue.trim() });
      toast.success(t('apiKeys.saveSuccess'));
      setEditingProvider(null);
      setInputValue('');
      await loadApiKeys();
    } catch (err) {
      toast.error(getErrorMessage(err, t('apiKeys.saveError')));
    } finally {
      setIsSaving((prev) => ({ ...prev, [provider]: false }));
    }
  }

  async function handleTest(provider: string) {
    setIsTesting((prev) => ({ ...prev, [provider]: true }));
    try {
      const result = await testApiKey(provider);
      if (result.status === 'connected') {
        toast.success(t('apiKeys.testSuccess'));
        setTestErrors((prev) => ({ ...prev, [provider]: '' }));
      } else {
        const errMsg = result.errorCode
          ? t(ERROR_CODE_KEYS[result.errorCode])
          : t('apiKeys.testFailed');
        toast.error(`${t('apiKeys.testFailed')}: ${errMsg}`);
        setTestErrors((prev) => ({ ...prev, [provider]: errMsg }));
      }
      await loadApiKeys();
    } catch (err) {
      const errMsg = getErrorMessage(err, t('apiKeys.testError'));
      toast.error(errMsg);
      setTestErrors((prev) => ({ ...prev, [provider]: errMsg }));
    } finally {
      setIsTesting((prev) => ({ ...prev, [provider]: false }));
    }
  }

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>{t('apiKeys.title')}</h1>
      <p className={styles.subtitle}>{t('apiKeys.subtitle')}</p>

      {isLoading ? (
        <div className={styles.loading}>{t('apiKeys.loading')}</div>
      ) : (
        <div className={styles.providerList}>
          {PROVIDERS.map(({ key: provider, label }) => {
            const status = apiKeys.find((k) => k.provider === provider);
            const isEditing = editingProvider === provider;
            const testing = isTesting[provider] ?? false;
            const saving = isSaving[provider] ?? false;
            const inlineError = testErrors[provider];

            return (
              <div key={provider} className={styles.providerCard}>
                <div className={styles.cardHeader}>
                  <span className={styles.providerName}>{label}</span>
                  <span
                    className={styles.statusBadge}
                    data-valid={status?.isValid ?? null}
                  >
                    {status?.isValid === true
                      ? '🟢 Connected'
                      : status?.isValid === false
                      ? '🔴 Failed'
                      : '⚪ Not configured'}
                  </span>
                </div>

                {status?.isValid === false && inlineError && (
                  <span className={styles.inlineError}>{inlineError}</span>
                )}

                {isEditing ? (
                  <div className={styles.editRow}>
                    <input
                      type="password"
                      className={styles.keyInput}
                      placeholder={t('apiKeys.inputPlaceholder')}
                      value={inputValue}
                      onChange={(e) => setInputValue(e.target.value)}
                      autoFocus
                    />
                    <button
                      className={styles.saveBtn}
                      onClick={() => handleSave(provider)}
                      disabled={saving}
                    >
                      {t('apiKeys.save')}
                    </button>
                    <button
                      className={styles.cancelBtn}
                      onClick={() => {
                        setEditingProvider(null);
                        setInputValue('');
                      }}
                    >
                      {t('apiKeys.cancel')}
                    </button>
                  </div>
                ) : (
                  <div className={styles.displayRow}>
                    <span className={styles.maskedKey}>
                      {status?.maskedKey ?? t('apiKeys.notSet')}
                    </span>
                    <button
                      className={styles.editBtn}
                      onClick={() => setEditingProvider(provider)}
                      aria-label={t('apiKeys.editAriaLabel')}
                    >
                      ✏️
                    </button>
                  </div>
                )}

                {status?.maskedKey && !isEditing && (
                  <button
                    className={styles.testBtn}
                    onClick={() => handleTest(provider)}
                    disabled={testing}
                    aria-label={t('apiKeys.testAriaLabel')}
                  >
                    {testing ? `⏳ ${t('apiKeys.testing')}` : t('apiKeys.testConnection')}
                  </button>
                )}

                {status?.lastTestedAt && formatLastTested(status.lastTestedAt, t('apiKeys.justNow')) && (
                  <span className={styles.lastTested}>
                    {t('apiKeys.lastTested')}: {formatLastTested(status.lastTestedAt, t('apiKeys.justNow'))}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
