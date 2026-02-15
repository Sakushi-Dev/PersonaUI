// ── CloseButton Component ──

import styles from './CloseButton.module.css';

export default function CloseButton({ onClick, className = '' }) {
  return (
    <button
      className={`${styles.closeButton} ${className}`}
      onClick={onClick}
      aria-label="Schließen"
      type="button"
    >
      ×
    </button>
  );
}
