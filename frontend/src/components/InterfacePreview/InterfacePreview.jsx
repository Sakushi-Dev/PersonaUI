// ── InterfacePreview ──
// Shared mini-preview showing dynamic background with chat bubble.
// Used in onboarding StepInterface & InterfaceSettingsOverlay.

import styles from './InterfacePreview.module.css';

/**
 * @param {Object} props
 * @param {boolean} props.isDark - Whether dark mode is active
 * @param {string}  props.nonverbalColor - Color for nonverbal text
 * @param {string}  [props.bgColor] - Background color override (falls back to theme default)
 * @param {string}  [props.gradient1] - Blob 1 color override
 * @param {string}  [props.gradient2] - Blob 2 color override
 */
export default function InterfacePreview({
  isDark,
  nonverbalColor = '#e4ba00',
  bgColor,
  gradient1,
  gradient2,
}) {
  // Fallback to theme defaults if no override provided
  const bg = bgColor ?? (isDark ? '#1a2332' : '#a3baff');
  const g1 = gradient1 ?? (isDark ? '#2a3f5f' : '#66cfff');
  const g2 = gradient2 ?? (isDark ? '#3d4f66' : '#fd91ee');

  return (
    <div className={styles.previewBox}>
      <div className={styles.previewBg} style={{ background: bg }}>
        <div
          className={`${styles.previewBlob} ${styles.blob1}`}
          style={{ background: g1 }}
        />
        <div
          className={`${styles.previewBlob} ${styles.blob2}`}
          style={{ background: g2 }}
        />
      </div>
      <div className={`${styles.previewBubble} ${isDark ? styles.bubbleDark : ''}`}>
        Das ist eine Vorschau.{' '}
        <span className={styles.nonverbal} style={{ color: nonverbalColor }}>
          *lächelt sanft*
        </span>{' '}
        So sieht dein Chat aus.
      </div>
    </div>
  );
}
