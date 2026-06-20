import { useTranslation } from '@/i18n/useTranslation';
import styles from './GraphLegend.module.css';

interface GraphLegendProps {
  gapMode?: boolean;
}

export function GraphLegend({ gapMode = false }: GraphLegendProps) {
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
      <p className={styles.gapSectionTitle}>{t('graph.legendEntitiesSection')}</p>
      <ul className={styles.list}>
        <li>
          <span className={`${styles.dotEntity} ${styles.dotFinding}`} />
          {t('graph.legendFinding')}
        </li>
        <li>
          <span className={`${styles.dotEntity} ${styles.dotMethod}`} />
          {t('graph.legendMethod')}
        </li>
        <li>
          <span className={`${styles.dotEntity} ${styles.dotDataset}`} />
          {t('graph.legendDataset')}
        </li>
        <li>
          <span className={`${styles.dotEntity} ${styles.dotTopic}`} />
          {t('graph.legendTopic')}
        </li>
        <li>
          <span className={`${styles.dotEntity} ${styles.dotLimitation}`} />
          {t('graph.legendLimitation')}
        </li>
        <li>
          <span className={`${styles.dotEntity} ${styles.dotProblem}`} />
          {t('graph.legendProblem')}
        </li>
      </ul>
      {gapMode && (
        <>
          <p className={styles.gapSectionTitle}>{t('graph.legendGapSection')}</p>
          <ul className={styles.list}>
            <li>
              <span className={`${styles.dotGap} ${styles.dotGapContradiction}`} />
              {t('graph.legendContradiction')}
            </li>
            <li>
              <span className={`${styles.dotGap} ${styles.dotGapUnfilled}`} />
              {t('graph.legendUnfilled')}
            </li>
            <li>
              <span className={`${styles.dotGap} ${styles.dotGapIsolated}`} />
              {t('graph.legendIsolated')}
            </li>
          </ul>
        </>
      )}
    </div>
  );
}
