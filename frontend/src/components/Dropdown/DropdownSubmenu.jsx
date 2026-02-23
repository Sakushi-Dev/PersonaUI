// ── DropdownSubmenu Component ──

import { useState } from 'react';
import styles from './Dropdown.module.css';

export default function DropdownSubmenu({ label, icon, children }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className={styles.submenuWrapper}>
      <button
        type="button"
        className={styles.item}
        onClick={() => setIsOpen(!isOpen)}
      >
        {icon && <span className={styles.icon}>{icon}</span>}
        <span>{label}</span>
        <span className={`${styles.arrow} ${isOpen ? styles.arrowOpen : ''}`}>›</span>
      </button>
      {isOpen && <div className={styles.submenu}>{children}</div>}
    </div>
  );
}
