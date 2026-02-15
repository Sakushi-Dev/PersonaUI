// ── Overlay Body ──

import styles from './Overlay.module.css';

export default function OverlayBody({ className = '', children }) {
  return (
    <div className={`${styles.body} ${className}`}>
      {children}
    </div>
  );
}
