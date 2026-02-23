// ── TagButton Component ──

import styles from './TagSelector.module.css';

export default function TagButton({ label, selected, disabled, onClick }) {
  return (
    <button
      type="button"
      className={`${styles.tag} ${selected ? styles.tagActive : ''}`}
      onClick={onClick}
      disabled={disabled}
    >
      {label}
    </button>
  );
}
