// ── Step: Context (3/6) ──

import { useLanguage } from '../../../hooks/useLanguage';
import styles from './Steps.module.css';

function getRange(value) {
  const n = parseInt(value, 10);
  if (n <= 125) return 'low';
  if (n <= 275) return 'medium';
  return 'high';
}

export default function StepContext({ data, onChange, onNext, onBack }) {
  const { t } = useLanguage();
  const s = t('onboardingContext');
  const c = t('onboardingCommon');

  const update = (field, value) => {
    onChange((prev) => ({ ...prev, [field]: value }));
  };

  const range = getRange(data.contextLimit);
  const rangeInfo = { low: s.rangeLow, medium: s.rangeMedium, high: s.rangeHigh };
  const info = rangeInfo[range];

  return (
    <div className={styles.card}>
      <div className={styles.cardHeader}>
        <span className={styles.cardStep}>3 / 6</span>
        <h2>{s.title}</h2>
        <p className={styles.cardDesc}>{s.desc}</p>
      </div>
      <div className={styles.cardBody}>

        {/* Intro */}
        <div className={styles.featureIntro}>
          <p dangerouslySetInnerHTML={{ __html: s.introP1 }} />
          <p>{s.introP2}</p>
        </div>

        {/* How it affects things */}
        <div className={styles.featureHighlights}>
          <div className={styles.feature}>
            <span className={styles.featureTag}>01</span>
            <div className={styles.featureText}>
              <strong>{s.feature1Title}</strong>
              <span className={styles.featureTyped}>{s.feature1Desc}</span>
            </div>
          </div>
          <div className={styles.feature}>
            <span className={styles.featureTag}>02</span>
            <div className={styles.featureText}>
              <strong>{s.feature2Title}</strong>
              <span className={styles.featureTyped}>{s.feature2Desc}</span>
            </div>
          </div>
          <div className={styles.feature}>
            <span className={styles.featureTag}>03</span>
            <div className={styles.featureText}>
              <strong>{s.feature3Title}</strong>
              <span className={styles.featureTyped}>{s.feature3Desc}</span>
            </div>
          </div>
        </div>

        {/* Slider */}
        <div className={styles.fieldGroup}>
          <label className={styles.label}>
            {s.sliderLabel} <strong>{data.contextLimit}</strong> {s.sliderUnit}
          </label>
          <input
            type="range"
            className={styles.slider}
            min={50}
            max={400}
            step={5}
            value={parseInt(data.contextLimit, 10)}
            onChange={(e) => update('contextLimit', e.target.value)}
          />
          <div className={styles.sliderLabels}>
            <span>50</span>
            <span className={styles.sliderRec}>{s.sliderRec}</span>
            <span>400</span>
          </div>

          {/* Dynamic Info based on range */}
          <div className={`${styles.infoBox} ${styles.infoBoxCompact}`}>
            <span className={styles.infoIcon}></span>
            <span>
              {info}
              {' '}{s.adjustAnytime}
            </span>
          </div>
        </div>

      </div>
      <div className={styles.cardFooter}>
        <button className={styles.btnGhost} onClick={onBack}>{c.back}</button>
        <button className={styles.btnPrimary} onClick={onNext}>{c.next}</button>
      </div>
    </div>
  );
}
