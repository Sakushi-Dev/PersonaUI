// ── Overlay Shell ──

import { useEffect, useRef } from 'react';
import styles from './Overlay.module.css';

export default function Overlay({ open, onClose, className = '', width, stacked, children }) {
  const overlayRef = useRef(null);
  const mouseDownOnBackdrop = useRef(false);

  // Close on Escape key
  useEffect(() => {
    if (!open) return;
    const handleKey = (e) => {
      if (e.key === 'Escape') onClose?.();
    };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [open, onClose]);

  // Only close when both mousedown AND mouseup happen on the backdrop
  const handleMouseDown = (e) => {
    mouseDownOnBackdrop.current = e.target === overlayRef.current;
  };

  const handleMouseUp = (e) => {
    if (mouseDownOnBackdrop.current && e.target === overlayRef.current) {
      onClose?.();
    }
    mouseDownOnBackdrop.current = false;
  };

  if (!open) return null;

  return (
    <div
      ref={overlayRef}
      className={`${styles.backdrop} ${stacked ? styles.stacked : ''}`}
      onMouseDown={handleMouseDown}
      onMouseUp={handleMouseUp}
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
