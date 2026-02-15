// ── DynamicBackground Component ──
// Shared component used in Chat and Onboarding.
// Colors are driven by CSS vars set in ThemeContext,
// so switching dark mode updates immediately.

import { useTheme } from '../../hooks/useTheme';
import styles from './DynamicBackground.module.css';

export default function DynamicBackground() {
  const { dynamicBackground } = useTheme();

  if (!dynamicBackground) return null;

  return (
    <div className={styles.background}>
      {/* Deep / far layer — large, very blurred, slow */}
      <div className={`${styles.blob} ${styles.blobDeep1}`} />
      <div className={`${styles.blob} ${styles.blobDeep2}`} />

      {/* Mid layer — medium blobs, moderate blur */}
      <div className={`${styles.blob} ${styles.blobMid1}`} />
      <div className={`${styles.blob} ${styles.blobMid2}`} />
      <div className={`${styles.blob} ${styles.blobMid3}`} />

      {/* Accent — small highlight, subtle */}
      <div className={`${styles.blob} ${styles.blobAccent}`} />

      {/* Noise grain overlay for texture */}
      <div className={styles.noise} />
    </div>
  );
}
