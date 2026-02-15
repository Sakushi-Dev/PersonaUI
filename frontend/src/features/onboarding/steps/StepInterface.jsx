// ── Step: Interface (2/4) – Legacy 1:1 ──

import InterfacePreview from '../../../components/InterfacePreview/InterfacePreview';
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

  const handleColorInput = (e) => {
    update('nonverbalColor', e.target.value);
  };

  const handleColorText = (e) => {
    const v = e.target.value;
    if (/^#[0-9a-fA-F]{6}$/.test(v)) {
      update('nonverbalColor', v);
    }
    // Always update the text field
    e.target.value = v;
  };

  return (
    <div className={styles.card}>
      <div className={styles.cardHeader}>
        <span className={styles.cardStep}>2 / 4</span>
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

        {/* Nonverbal Color */}
        <div className={styles.fieldGroup}>
          <label className={styles.label}>Nonverbale Text-Farbe</label>
          <div className={styles.colorRow}>
            <input
              type="color"
              className={styles.colorInput}
              value={data.nonverbalColor}
              onChange={handleColorInput}
            />
            <input
              type="text"
              className={`${styles.input} ${styles.colorText}`}
              value={data.nonverbalColor}
              onChange={handleColorText}
              placeholder="#e4ba00"
            />
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
