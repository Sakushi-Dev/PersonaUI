// ── ColorPicker Component ──

import styles from './ColorPicker.module.css';

export default function ColorPicker({ label, value, onChange }) {
  return (
    <div className={styles.wrapper}>
      {label && <label className={styles.label}>{label}</label>}
      <div className={styles.picker}>
        <input
          type="color"
          value={value || '#000000'}
          onChange={(e) => onChange?.(e.target.value)}
          className={styles.input}
        />
        <span className={styles.value}>{value}</span>
      </div>
    </div>
  );
}
