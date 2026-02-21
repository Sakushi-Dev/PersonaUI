// ── Step: Cortex (4/6) ──

import { t } from '../useTranslation';
import styles from './Steps.module.css';

export default function StepCortex({ data, onChange, onNext, onBack, language }) {
  const s = t(language, 'cortex');
  const c = t(language, 'common');

  const FREQUENCY_OPTIONS = [
    { value: 'frequent', label: s.freqFrequent,  percent: 50 },
    { value: 'medium',   label: s.freqMedium,    percent: 75 },
    { value: 'rare',     label: s.freqRare,      percent: 95 },
  ];

  const FREQUENCY_INFO = {
    frequent: s.freqInfoFrequent,
    medium:   s.freqInfoMedium,
    rare:     s.freqInfoRare,
  };

  const update = (field, value) => {
    onChange((prev) => ({ ...prev, [field]: value }));
  };

  return (
    <div className={styles.card}>
      <div className={styles.cardHeader}>
        <span className={styles.cardStep}>4 / 6</span>
        <h2>{s.title}</h2>
        <p className={styles.cardDesc}>{s.desc}</p>
      </div>
      <div className={styles.cardBody}>

        {/* Intro Text */}
        <div className={styles.featureIntro}>
          <p dangerouslySetInnerHTML={{ __html: s.introP1 }} />
          <p>{s.introP2}</p>
        </div>

        {/* Cortex drei Bereiche */}
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

        {/* Enable/Disable */}
        <div className={styles.fieldGroup}>
          <label className={styles.label}>{s.enableLabel}</label>
          <div className={styles.modeSwitch}>
            <span className={styles.modeLabel}>{s.off}</span>
            <label className={styles.toggle}>
              <input
                type="checkbox"
                checked={data.cortexEnabled}
                onChange={() => update('cortexEnabled', !data.cortexEnabled)}
              />
              <span className={styles.toggleSlider} />
            </label>
            <span className={styles.modeLabel}>{s.on}</span>
          </div>
          {!data.cortexEnabled && (
            <div className={`${styles.infoBox} ${styles.infoBoxCompact}`}>
              <span className={styles.infoIcon}></span>
              <span>{s.disabledInfo}</span>
            </div>
          )}
        </div>

        {/* Frequency */}
        {data.cortexEnabled && (
          <div className={styles.fieldGroup}>
            <label className={styles.label}>{s.frequencyLabel}</label>
            <span className={styles.hint} style={{ marginBottom: 10 }}>
              {s.frequencyHint}
            </span>
            <div className={styles.typeGrid} style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
              {FREQUENCY_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  className={`${styles.typeChip} ${styles.typeChipTall} ${data.cortexFrequency === opt.value ? styles.chipActive : ''}`}
                  onClick={() => update('cortexFrequency', opt.value)}
                >
                  <span>{opt.label}</span>
                  <span className={styles.chipSub}>{opt.percent}%</span>
                </button>
              ))}
            </div>
            <div className={`${styles.infoBox} ${styles.infoBoxCompact}`}>
              <span className={styles.infoIcon}></span>
              <span>
                {FREQUENCY_INFO[data.cortexFrequency]}
                {' '}{s.autoInfo}
              </span>
            </div>
          </div>
        )}

      </div>
      <div className={styles.cardFooter}>
        <button className={styles.btnGhost} onClick={onBack}>{c.back}</button>
        <button className={styles.btnPrimary} onClick={onNext}>{c.next}</button>
      </div>
    </div>
  );
}
