// ── Overlay Footer ──

import styles from './Overlay.module.css';

export default function OverlayFooter({ className = '', children }) {
  return (
    <div className={`${styles.footer} ${className}`}>
      {children}
    </div>
  );
}
