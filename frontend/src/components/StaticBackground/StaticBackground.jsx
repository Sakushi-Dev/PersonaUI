// ── StaticBackground Component ──
// Solid color background with paper-grain texture.
// Shown when dynamic background is off.

import styles from './StaticBackground.module.css';

/**
 * @param {Object}  [props]
 * @param {string}  [props.bgColor]   - Base background color (fallback: --color-white)
 * @param {string}  [props.className] - Extra class name
 */
export default function StaticBackground({ bgColor, className = '' }) {
  const style = bgColor ? { '--sb-bg': bgColor } : undefined;

  return (
    <div className={`${styles.staticBg} ${className}`} style={style}>
      <div className={styles.grain} />
      <div className={styles.blur} />
    </div>
  );
}
