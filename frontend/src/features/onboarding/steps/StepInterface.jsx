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
        <p className={styles.cardDesc}>Passe das Aussehen an deinen Geschmack an.</p>
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
          <label className={styles.label}>Design-Modus</label>
          <div className={styles.modeSwitch}>
            <span className={styles.modeLabel}>☀️ Hell</span>
            <label className={styles.toggle}>
              <input
                type="checkbox"
                checked={data.darkMode}
                onChange={handleDarkToggle}
              />
              <span className={styles.toggleSlider} />
            </label>
            <span className={styles.modeLabel}>🌙 Dunkel</span>
          </div>
        </div>

        {/* Nonverbal Color Presets */}
        <div className={styles.fieldGroup}>
          <label className={styles.label}>Nonverbale Text-Farbe</label>
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
          <span className={styles.hint}>Farbe für Text zwischen Sternchen (*nonverbal*) – z.B. Aktionen, Emotionen</span>
        </div>

        <div className={styles.infoBox}>
          <span className={styles.infoIcon}>ℹ️</span>
          <span>Weitere Interface-Einstellungen wie Farben, Schriftart und -größe findest du später unter <strong>Einstellungen</strong>.</span>
        </div>
      </div>
      <div className={styles.cardFooter}>
        <button className={styles.btnGhost} onClick={onBack}>Zurück</button>
        <button className={styles.btnPrimary} onClick={onNext}>Weiter</button>
      </div>
    </div>
  );
}
