// ── ContextBar ──
// Stacked progress bars: context usage (top) + cortex progress (bottom), right-aligned

import { useMemo, useEffect, useState } from 'react';
import { useSession } from '../../../../hooks/useSession';
import { useSettings } from '../../../../hooks/useSettings';
import { getCortexProgress } from '../../../../services/cortexApi';
import styles from './ContextBar.module.css';

export default function ContextBar({ cortexProgress: liveCortexProgress }) {
  const { totalMessageCount, sessionId, personaId } = useSession();
  const { get } = useSettings();

  const contextLimit = parseInt(get('contextLimit', 100), 10);
  const rawCortexEnabled = get('cortexEnabled', true);
  const cortexEnabled = rawCortexEnabled === true || rawCortexEnabled === 'true';

  // Initial cortex progress loaded from API
  const [initialCortexProgress, setInitialCortexProgress] = useState(null);

  // Fetch cortex progress on mount / session change
  useEffect(() => {
    if (!cortexEnabled || !sessionId) return;

    getCortexProgress(sessionId, personaId)
      .then((res) => {
        if (res.success && res.progress) {
          setInitialCortexProgress({ ...res.progress, frequency: res.frequency });
        }
      })
      .catch(() => {/* silent */});
  }, [sessionId, personaId, cortexEnabled]);

  // Live data overrides initial
  const cortexProgress = liveCortexProgress || initialCortexProgress;

  const { percentage, usedCount, level } = useMemo(() => {
    const used = Math.min(totalMessageCount, contextLimit);
    const pct = contextLimit > 0 ? Math.round((used / contextLimit) * 100) : 0;

    let lvl = 'low';
    if (pct >= 100) lvl = 'full';
    else if (pct >= 70) lvl = 'high';
    else if (pct >= 45) lvl = 'medium';

    return { percentage: pct, usedCount: used, level: lvl };
  }, [totalMessageCount, contextLimit]);

  const cortexPct = cortexProgress?.progress_percent ?? 0;
  const cortexSince = cortexProgress?.messages_since_reset ?? 0;
  const cortexThreshold = cortexProgress?.threshold ?? 0;
  const showCortex = cortexEnabled && cortexProgress != null;
  const showContext = totalMessageCount > 0;

  // Don't render if neither bar has data
  if (!showContext && !showCortex) return null;

  return (
    <div className={styles.contextBar}>
      {/* Context row */}
      {showContext && (
        <div className={styles.row}>
          <span className={styles.prefix}>C</span>
          <span className={`${styles.stats} ${styles[level]}`}>
            {percentage}%
            <span className={styles.detail}>
              {' '}· {usedCount}/{contextLimit}
            </span>
          </span>
          <div className={styles.track}>
            <div
              className={`${styles.fill} ${styles[level]}`}
              style={{ width: `${percentage}%` }}
            />
          </div>
        </div>
      )}

      {/* Cortex row */}
      {showCortex && (
        <div className={styles.row}>
          <span className={`${styles.prefix} ${styles.cortexPrefix}`}>X</span>
          <span className={`${styles.stats} ${styles.cortexLabel}`}>
            {Math.round(cortexPct)}%
            <span className={styles.detail}>
              {' '}· {cortexSince}/{cortexThreshold}
            </span>
          </span>
          <div className={`${styles.track} ${styles.cortexTrack}`}>
            <div
              className={`${styles.fill} ${styles.cortex} ${cortexPct === 0 ? styles.cortexReset : ''}`}
              style={{ width: `${Math.min(cortexPct, 100)}%` }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
