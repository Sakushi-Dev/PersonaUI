// ── Step: Interface (2/4) ──

import Toggle from '../../../components/Toggle/Toggle';
import ColorPicker from '../../../components/ColorPicker/ColorPicker';
import Button from '../../../components/Button/Button';
import styles from './Steps.module.css';

export default function StepInterface({ data, onChange, onNext, onBack }) {
  const update = (field, value) => {
    onChange({ ...data, [field]: value });
  };

  const previewStyle = {
    background: data.darkMode
      ? 'linear-gradient(135deg, #1a2332, #2a3f5f)'
      : 'linear-gradient(135deg, #e8dff5, #c9b8ff)',
    color: data.darkMode ? '#fff' : '#1a1a1a',
    padding: '16px',
    borderRadius: '12px',
    marginBottom: '20px',
    fontSize: '16px',
    lineHeight: '1.6',
    transition: 'all 0.3s ease',
  };

  return (
    <div className={styles.step}>
      <h2 className={styles.title}>Interface <span className={styles.stepNum}>(2/4)</span></h2>
      <p className={styles.subtitle}>Passe das Erscheinungsbild an</p>

      {/* Preview */}
      <div style={previewStyle}>
        Hallo! So sieht dein Chat aus. <span style={{ color: data.nonverbalColor, fontStyle: 'italic' }}>*lächelt sanft*</span>
      </div>

      <div className={styles.settingRow}>
        <Toggle
          label={data.darkMode ? 'Dunkel' : 'Hell'}
          checked={data.darkMode}
          onChange={(v) => update('darkMode', v)}
          id="ob-dark-mode"
        />
        <span className={styles.label}>Darstellungsmodus</span>
      </div>

      <ColorPicker
        label="Nonverbal-Textfarbe"
        value={data.nonverbalColor}
        onChange={(v) => update('nonverbalColor', v)}
      />

      <div className={styles.infoBox}>
        <p>💡 Weitere Einstellungen wie Hintergrundfarben und Schriftart findest du später in den Interface-Einstellungen.</p>
      </div>

      <div className={styles.footer}>
        <Button variant="secondary" onClick={onBack}>Zurück</Button>
        <Button variant="primary" onClick={onNext}>Weiter</Button>
      </div>
    </div>
  );
}
