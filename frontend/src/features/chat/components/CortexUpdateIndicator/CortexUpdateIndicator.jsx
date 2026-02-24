// ── CortexUpdateIndicator ──
// Subtle notification above the input area when a background cortex update is running

import { useLanguage } from '../../../../hooks/useLanguage';
import styles from './CortexUpdateIndicator.module.css';

export default function CortexUpdateIndicator() {
  const { t } = useLanguage();
  const s = t('chat');

  return (
    <div className={styles.wrapper}>
      <div className={styles.indicator}>
        <span className={styles.dot} />
        <span className={styles.text}>{s.cortexUpdating}</span>
      </div>
    </div>
  );
}
