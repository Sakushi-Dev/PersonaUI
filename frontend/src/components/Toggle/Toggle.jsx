// ── Toggle Switch ──

import styles from './Toggle.module.css';

export default function Toggle({ checked, onChange, label, id, disabled = false }) {
  const toggleId = id || `toggle-${label?.replace(/\s+/g, '-').toLowerCase()}`;

  return (
    <div className={styles.wrapper}>
      {label && <label htmlFor={toggleId} className={styles.label}>{label}</label>}
      <button
        id={toggleId}
        type="button"
        role="switch"
        aria-checked={checked}
        className={`${styles.toggle} ${checked ? styles.active : ''}`}
        onClick={() => !disabled && onChange?.(!checked)}
        disabled={disabled}
      >
        <span className={styles.thumb} />
      </button>
    </div>
  );
}
