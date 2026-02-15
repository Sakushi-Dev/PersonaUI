// ── DynamicBackground Component ──

import { useTheme } from '../../../../hooks/useTheme';
import styles from './DynamicBackground.module.css';

export default function DynamicBackground() {
  const { dynamicBackground } = useTheme();

  if (!dynamicBackground) return null;

  return (
    <div className={styles.background}>
      <div className={`${styles.blob} ${styles.blob1}`} />
      <div className={`${styles.blob} ${styles.blob2}`} />
      <div className={`${styles.blob} ${styles.blob3}`} />
    </div>
  );
}
