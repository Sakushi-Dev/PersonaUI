// ── Overlay Header ──

import CloseButton from '../CloseButton/CloseButton';
import styles from './Overlay.module.css';

export default function OverlayHeader({ title, onClose, children }) {
  return (
    <div className={styles.header}>
      <h2 className={styles.title}>{title}</h2>
      {children}
      {onClose && <CloseButton onClick={onClose} />}
    </div>
  );
}
