// ── Overlay Shell ──
// Two modes:
//   normal  – backdrop + panel (desktop & non-swipeable overlays)
//   panelOnly – just the panel div, for use inside the swipe carousel

import { useEffect, useRef } from 'react';
import styles from './Overlay.module.css';

export default function Overlay({ open, onClose, className = '', width, stacked, panelOnly, children }) {
  const overlayRef = useRef(null);
  const mouseDownOnBackdrop = useRef(false);

  // Close on Escape key (normal mode only)
  useEffect(() => {
    if (!open || panelOnly) return;
    const handleKey = (e) => {
      if (e.key === 'Escape') onClose?.();
    };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [open, onClose, panelOnly]);

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

  // ── Panel-only mode: carousel panel without backdrop ──
  if (panelOnly) {
    const panelStyle = width ? { maxWidth: width } : {};
    return (
      <div className={`${styles.panel} ${styles.carouselPanel} ${className}`} style={panelStyle}>
        {children}
      </div>
    );
  }

  // ── Normal mode: backdrop + panel ──
  if (!open) return null;

  const backdropCls = [
    styles.backdrop,
    stacked ? styles.stacked : '',
  ].filter(Boolean).join(' ');

  const panelStyle = width ? { maxWidth: width } : {};

  return (
    <div
      ref={overlayRef}
      className={backdropCls}
      onMouseDown={handleMouseDown}
      onMouseUp={handleMouseUp}
    >
      <div className={`${styles.panel} ${className}`} style={panelStyle}>
        {children}
      </div>
    </div>
  );
}
