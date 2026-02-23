// ── DropdownItem Component ──

import styles from './Dropdown.module.css';

export default function DropdownItem({ onClick, icon, label, danger = false, children }) {
  return (
    <button
      type="button"
      className={`${styles.item} ${danger ? styles.danger : ''}`}
      onClick={onClick}
    >
      {icon && <span className={styles.icon}>{icon}</span>}
      <span>{label || children}</span>
    </button>
  );
}
