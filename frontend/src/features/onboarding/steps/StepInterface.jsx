// ── Step: Interface (2/4) ──

import InterfacePreview from '../../../components/InterfacePreview/InterfacePreview';
import { NONVERBAL_PRESETS } from '../../../utils/constants';
import styles from './Steps.module.css';

export default function StepInterface({ data, onChange, onDarkModeChange, onNext, onBack }) {
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
        <h2>Interface</h2>
        <p className={styles.cardDesc}>Customize the look to your taste.</p>
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
          <label className={styles.label}>Design Mode</label>
          <div className={styles.modeSwitch}>
            <span className={styles.modeLabel}>Light</span>
            <label className={styles.toggle}>
              <input
                type="checkbox"
                checked={data.darkMode}
                onChange={handleDarkToggle}
              />
              <span className={styles.toggleSlider} />
            </label>
            <span className={styles.modeLabel}>Dark</span>
          </div>
        </div>

        {/* Nonverbal Color Presets */}
        <div className={styles.fieldGroup}>
          <label className={styles.label}>Nonverbal Text Color</label>
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
          <span className={styles.hint}>Color for text between asterisks (*nonverbal*) – e.g. actions, emotions</span>
        </div>

        <div className={styles.infoBox}>
          <span className={styles.infoIcon}></span>
          <span>More interface settings like colors, font, and size can be found later under <strong>Settings</strong>.</span>
        </div>
      </div>
      <div className={styles.cardFooter}>
        <button className={styles.btnGhost} onClick={onBack}>Back</button>
        <button className={styles.btnPrimary} onClick={onNext}>Next</button>
      </div>
    </div>
  );
}
