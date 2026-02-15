// ── ProgressBar ──

import styles from './ProgressBar.module.css';

export default function ProgressBar({ progress }) {
  return (
    <div className={styles.track}>
      <div
        className={styles.fill}
        style={{ width: `${Math.max(0, Math.min(100, progress))}%` }}
      />
    </div>
  );
}
