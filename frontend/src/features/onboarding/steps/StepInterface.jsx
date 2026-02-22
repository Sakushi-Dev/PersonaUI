// ── Step: Interface (2/6) ──

import InterfacePreview from '../../../components/InterfacePreview/InterfacePreview';
import { NONVERBAL_PRESETS } from '../../../utils/constants';
import { useLanguage } from '../../../hooks/useLanguage';
import styles from './Steps.module.css';

export default function StepInterface({ data, onChange, onDarkModeChange, onNext, onBack }) {
  const { t } = useLanguage();
  const s = t('onboardingInterface');
  const c = t('onboardingCommon');

  const update = (field, value) => {
    onChange((prev) => ({ ...prev, [field]: value }));
  };

  const handleDarkToggle = () => {
    const newVal = !data.darkMode;
    if (onDarkModeChange) {
      onDarkModeChange(newVal);
    } else {
      update('darkMode', newVal);
    }
  };

  return (
    <div className={styles.card}>
      <div className={styles.cardHeader}>
        <span className={styles.cardStep}>2 / 6</span>
        <h2>{s.title}</h2>
        <p className={styles.cardDesc}>{s.desc}</p>
      </div>
      <div className={styles.cardBody}>

        {/* Live Preview Box */}
        <div style={{ marginBottom: 20 }}>
          <InterfacePreview
            isDark={data.darkMode}
            nonverbalColor={data.nonverbalColor}
          />
        </div>

        {/* Dark/Light Toggle */}
        <div className={styles.fieldGroup}>
          <label className={styles.label}>{s.designMode}</label>
          <div className={styles.modeSwitch}>
            <span className={styles.modeLabel}>{s.light}</span>
            <label className={styles.toggle}>
              <input
                type="checkbox"
                checked={data.darkMode}
                onChange={handleDarkToggle}
              />
              <span className={styles.toggleSlider} />
            </label>
            <span className={styles.modeLabel}>{s.dark}</span>
          </div>
        </div>

        {/* Nonverbal Color Presets */}
        <div className={styles.fieldGroup}>
          <label className={styles.label}>{s.nonverbalColor}</label>
          <div className={styles.colorPresets}>
            {NONVERBAL_PRESETS.map((preset) => (
              <button
                key={preset.value}
                type="button"
                className={`${styles.colorSwatch} ${data.nonverbalColor === preset.value ? styles.colorSwatchActive : ''}`}
                style={{ background: preset.value }}
                onClick={() => update('nonverbalColor', preset.value)}
                title={preset.label}
              >
                {data.nonverbalColor === preset.value && <span className={styles.swatchCheck}>✓</span>}
              </button>
            ))}
          </div>
          <span className={styles.hint}>{s.nonverbalHint}</span>
        </div>

        <div className={styles.infoBox}>
          <span className={styles.infoIcon}></span>
          <span dangerouslySetInnerHTML={{ __html: s.infoText }} />
        </div>
      </div>
      <div className={styles.cardFooter}>
        <button className={styles.btnGhost} onClick={onBack}>{c.back}</button>
        <button className={styles.btnPrimary} onClick={onNext}>{c.next}</button>
      </div>
    </div>
  );
}
