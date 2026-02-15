// ── Overlay Shell ──

import { useEffect, useRef } from 'react';
import styles from './Overlay.module.css';

export default function Overlay({ open, onClose, className = '', width, children }) {
  const overlayRef = useRef(null);

  // Close on Escape key
  useEffect(() => {
    if (!open) return;
    const handleKey = (e) => {
      if (e.key === 'Escape') onClose?.();
    };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [open, onClose]);

  // Close on backdrop click
  const handleBackdropClick = (e) => {
    if (e.target === overlayRef.current) {
      onClose?.();
    }
  };

  if (!open) return null;

  return (
    <div
      ref={overlayRef}
      className={styles.backdrop}
      onClick={handleBackdropClick}
    >
      <div
        className={`${styles.panel} ${className}`}
        style={width ? { maxWidth: width } : undefined}
      >
        {children}
      </div>
    </div>
  );
}
