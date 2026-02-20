// ── CortexUpdateIndicator ──
// Subtle notification when a background cortex update is running

import styles from './CortexUpdateIndicator.module.css';

export default function CortexUpdateIndicator() {
  return (
    <div className={styles.indicator}>
      <span className={styles.icon}>🧠</span>
      <span className={styles.text}>Cortex aktualisiert sich…</span>
    </div>
  );
}
