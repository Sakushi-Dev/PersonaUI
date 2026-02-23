// ── Spinner Component ──

import styles from './Spinner.module.css';

export default function Spinner({ fullScreen = false, className = '' }) {
  if (fullScreen) {
    return (
      <div className={styles.fullScreen}>
        <div className={styles.dots}>
          <span className={styles.dot} />
          <span className={styles.dot} />
          <span className={styles.dot} />
        </div>
      </div>
    );
  }

  return (
    <div className={`${styles.spinner} ${className}`}>
      <span className={styles.dot} />
      <span className={styles.dot} />
      <span className={styles.dot} />
    </div>
  );
}
