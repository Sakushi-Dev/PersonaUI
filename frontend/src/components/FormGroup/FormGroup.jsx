// ── FormGroup Component ──

import styles from './FormGroup.module.css';

export default function FormGroup({ label, hint, charCount, maxLength, children, className = '' }) {
  return (
    <div className={`${styles.group} ${className}`}>
      {(label || charCount !== undefined) && (
        <div className={styles.header}>
          {label && <label className={styles.label}>{label}</label>}
          {charCount !== undefined && maxLength && (
            <span className={`${styles.counter} ${charCount > maxLength ? styles.counterOver : ''}`}>
              {charCount}/{maxLength}
            </span>
          )}
        </div>
      )}
      {children}
      {hint && <p className={styles.hint}>{hint}</p>}
    </div>
  );
}
