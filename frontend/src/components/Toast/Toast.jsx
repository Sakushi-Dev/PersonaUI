// ── Single Toast ──

import styles from './Toast.module.css';

export default function Toast({ message, type = 'info', onClose }) {
  return (
    <div className={`${styles.toast} ${styles[type]}`} onClick={onClose}>
      <span className={styles.message}>{message}</span>
      <button className={styles.close} onClick={onClose}>×</button>
    </div>
  );
}
