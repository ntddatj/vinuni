import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { getAdminSettings, updateAdminSetting } from '@/api/admin';
import { getErrorMessage } from '@/api/errors';
import { useTranslation } from '@/i18n/useTranslation';
import { useAuthStore } from '@/store/authStore';
import styles from './AdminSettingsPage.module.css';

export function AdminSettingsPage() {
  const { t } = useTranslation();
  const { user } = useAuthStore();
  const [maxPapers, setMaxPapers] = useState('15');
  const [broadQueryThreshold, setBroadQueryThreshold] = useState('50');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getAdminSettings()
      .then((settings) => {
        const maxP = settings.find((s) => s.key === 'MAX_PAPERS_PER_PROJECT');
        const bqt = settings.find((s) => s.key === 'BROAD_QUERY_THRESHOLD');
        if (maxP) setMaxPapers(maxP.value);
        if (bqt) setBroadQueryThreshold(bqt.value);
      })
      .catch(() => {
        // Nếu không phải admin thì API trả 403 — chỉ hiển thị giá trị mặc định
      });
  }, []);

  if (!user || user.role !== 'admin') {
    return (
      <div className={styles.container}>
        <p className={styles.forbidden}>403 — Chỉ Admin mới có quyền truy cập trang này.</p>
      </div>
    );
  }

  async function handleSave() {
    setSaving(true);
    try {
      await Promise.all([
        updateAdminSetting('MAX_PAPERS_PER_PROJECT', maxPapers),
        updateAdminSetting('BROAD_QUERY_THRESHOLD', broadQueryThreshold),
      ]);
      toast.success(t('admin.settings.saveSuccess'));
    } catch (err) {
      toast.error(getErrorMessage(err, t('admin.settings.saveError')));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className={styles.container}>
      <h1 className={styles.title}>{t('admin.settings.title')}</h1>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>{t('admin.settings.systemLimits')}</h2>

        <div className={styles.field}>
          <label className={styles.label} htmlFor="max-papers">
            {t('admin.settings.maxPapers')}
          </label>
          <input
            id="max-papers"
            type="number"
            min={1}
            className={styles.input}
            value={maxPapers}
            onChange={(e) => setMaxPapers(e.target.value)}
          />
        </div>

        <div className={styles.field}>
          <label className={styles.label} htmlFor="broad-query-threshold">
            {t('admin.settings.broadQueryThreshold')}
          </label>
          <input
            id="broad-query-threshold"
            type="number"
            min={1}
            className={styles.input}
            value={broadQueryThreshold}
            onChange={(e) => setBroadQueryThreshold(e.target.value)}
          />
        </div>

        <button
          type="button"
          className={styles.saveButton}
          onClick={handleSave}
          disabled={saving}
        >
          {saving ? '...' : t('admin.settings.save')}
        </button>
      </section>
    </div>
  );
}
