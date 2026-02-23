// ── Overlay Header ──

import CloseButton from '../CloseButton/CloseButton';
import styles from './Overlay.module.css';

export default function OverlayHeader({ title, icon, onClose, children }) {
  return (
    <div className={styles.header}>
      <h2 className={styles.title}>
        {icon && <span className={styles.titleIcon}>{icon}</span>}
        {title}
      </h2>
      {children}
      {onClose && <CloseButton onClick={onClose} />}
    </div>
  );
}
