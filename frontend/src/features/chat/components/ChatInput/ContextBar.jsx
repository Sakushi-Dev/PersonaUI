// ── ContextBar ──
// Subtle context usage bar showing message count vs. context limit

import { useMemo } from 'react';
import { useSession } from '../../../../hooks/useSession';
import { useSettings } from '../../../../hooks/useSettings';
import styles from './ContextBar.module.css';

export default function ContextBar() {
  const { totalMessageCount } = useSession();
  const { get } = useSettings();

  const contextLimit = parseInt(get('contextLimit', 100), 10);

  const { percentage, usedCount, level } = useMemo(() => {
    const used = Math.min(totalMessageCount, contextLimit);
    const pct = contextLimit > 0 ? Math.round((used / contextLimit) * 100) : 0;

    let lvl = 'low';
    if (pct >= 90) lvl = 'critical';
    else if (pct >= 70) lvl = 'high';
    else if (pct >= 45) lvl = 'medium';

    return { percentage: pct, usedCount: used, level: lvl };
  }, [totalMessageCount, contextLimit]);

  // Don't render if no messages yet
  if (totalMessageCount === 0) return null;

  return (
    <div className={styles.contextBar}>
      <div className={styles.track}>
        <div
          className={`${styles.fill} ${styles[level]}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <span className={`${styles.label} ${styles[level]}`}>
        {percentage}%
        <span className={styles.detail}>
          {' '}· {usedCount}/{contextLimit}
        </span>
      </span>
    </div>
  );
}
