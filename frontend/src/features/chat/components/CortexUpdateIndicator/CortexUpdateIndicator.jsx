// ── CortexUpdateIndicator ──
// Subtle notification when a background cortex update is running

import { useLanguage } from '../../../../hooks/useLanguage';
import styles from './CortexUpdateIndicator.module.css';

export default function CortexUpdateIndicator() {
  const { t } = useLanguage();
  const s = t('chat');

  return (
    <div className={styles.indicator}>
      <span className={styles.icon}>🧠</span>
      <span className={styles.text}>{s.cortexUpdating}</span>
    </div>
  );
}
