import { useTranslation } from '@/i18n/useTranslation';
import styles from './GraphLegend.module.css';

export function GraphLegend() {
  const { t } = useTranslation();
  return (
    <div className={styles.legend}>
      <p className={styles.title}>{t('graph.legendTitle')}</p>
      <ul className={styles.list}>
        <li>
          <span className={`${styles.dot} ${styles.dotFullText}`} />
          {t('graph.legendFullText')}
        </li>
        <li>
          <span className={`${styles.dot} ${styles.dotMetaOnly}`} />
          {t('graph.legendMetaOnly')}
        </li>
        <li>
          <span className={`${styles.diamond} ${styles.diamondAuthor}`} />
          {t('graph.legendAuthor')}
        </li>
        <li>
          <span className={`${styles.line} ${styles.lineCites}`} />
          {t('graph.legendCites')}
        </li>
        <li>
          <span className={`${styles.line} ${styles.lineAuthoredBy}`} />
          {t('graph.legendAuthoredBy')}
        </li>
      </ul>
    </div>
  );
}
