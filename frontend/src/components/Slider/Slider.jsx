// ── Slider Component ──

import styles from './Slider.module.css';

export default function Slider({
  label,
  value,
  onChange,
  min = 0,
  max = 100,
  step = 1,
  displayValue,
  disabled = false,
}) {
  const display = displayValue !== undefined ? displayValue : value;

  return (
    <div className={styles.wrapper}>
      <div className={styles.header}>
        {label && <label className={styles.label}>{label}</label>}
        <span className={styles.value}>{display}</span>
      </div>
      <input
        type="range"
        className={styles.slider}
        value={value}
        onChange={(e) => onChange?.(parseFloat(e.target.value))}
        min={min}
        max={max}
        step={step}
        disabled={disabled}
      />
    </div>
  );
}
