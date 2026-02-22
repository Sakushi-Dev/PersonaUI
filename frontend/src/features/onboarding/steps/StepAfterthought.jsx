// ── Step: Afterthought (5/6) ──

import { useLanguage } from '../../../hooks/useLanguage';
import styles from './Steps.module.css';

export default function StepAfterthought({ data, onChange, onNext, onBack }) {
  const { t } = useLanguage();
  const s = t('onboardingAfterthought');
  const c = t('onboardingCommon');

  const MODES = [
    { value: 'off',    label: s.modeOff },
    { value: 'selten', label: s.modeRare },
    { value: 'mittel', label: s.modeMedium },
    { value: 'hoch',   label: s.modeHigh },
  ];

  const MODE_INFO = {
    off:    { text: s.modeInfoOff,    extra: null },
    selten: { text: s.modeInfoRare,   extra: s.modeInfoRareExtra },
    mittel: { text: s.modeInfoMedium, extra: s.modeInfoMediumExtra },
    hoch:   { text: s.modeInfoHigh,   extra: s.modeInfoHighExtra },
  };

  const update = (field, value) => {
    onChange((prev) => ({ ...prev, [field]: value }));
  };

  const currentMode = MODE_INFO[data.nachgedankeMode] || MODE_INFO.off;

  return (
    <div className={styles.card}>
      <div className={styles.cardHeader}>
        <span className={styles.cardStep}>5 / 6</span>
        <h2>{s.title}</h2>
        <p className={styles.cardDesc}>{s.desc}</p>
      </div>
      <div className={styles.cardBody}>

        {/* Intro */}
        <div className={styles.featureIntro}>
          <p dangerouslySetInnerHTML={{ __html: s.introP1 }} />
          <p>{s.introP2}</p>
        </div>

        {/* How it works */}
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

        {/* Mode Selector */}
        <div className={styles.fieldGroup}>
          <label className={styles.label}>{s.frequencyLabel} <span className={styles.betaBadge}>Beta</span></label>
          <div className={styles.typeGrid} style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
            {MODES.map((opt) => (
              <button
                key={opt.value}
                type="button"
                className={`${styles.typeChip} ${data.nachgedankeMode === opt.value ? styles.chipActive : ''}`}
                onClick={() => update('nachgedankeMode', opt.value)}
              >
                {opt.label}
              </button>
            ))}
          </div>

          {/* Dynamic Info per Mode */}
          <div className={`${styles.infoBox} ${styles.infoBoxCompact}`}>
            <span className={styles.infoIcon}></span>
            <span>
              {currentMode.text}
              {currentMode.extra && (
                <>
                  <br /><strong>{currentMode.extra}</strong>
                </>
              )}
              {data.nachgedankeMode !== 'off' && (
                <>
                  {' '}{s.apiNote}
                </>
              )}
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
