// ── Global Confirm Dialog ──

import { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import styles from './ConfirmDialog.module.css';

/**
 * Minimalist confirmation popup.
 *
 * @param {boolean}  open       – whether the dialog is visible
 * @param {string}   message    – dynamic text shown in the dialog
 * @param {function} onConfirm  – called when user clicks "Ja"
 * @param {function} onCancel   – called when user clicks "Nein" or presses Escape
 * @param {string}   [confirmLabel='Ja']
 * @param {string}   [cancelLabel='Nein']
 */
export default function ConfirmDialog({
  open,
  message,
  onConfirm,
  onCancel,
  confirmLabel = 'Ja',
  cancelLabel = 'Nein',
}) {
  const confirmRef = useRef(null);

  // Focus the confirm button when opened & handle Escape
  useEffect(() => {
    if (!open) return;

    confirmRef.current?.focus();

    const handleKey = (e) => {
      if (e.key === 'Escape') onCancel?.();
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [open, onCancel]);

  if (!open) return null;

  return createPortal(
    <div className={styles.backdrop} onClick={onCancel}>
      <div className={styles.dialog} onClick={(e) => e.stopPropagation()}>
        <p className={styles.message}>{message}</p>
        <div className={styles.actions}>
          <button
            ref={confirmRef}
            className={styles.confirmBtn}
            onClick={onConfirm}
          >
            {confirmLabel}
          </button>
          <button className={styles.cancelBtn} onClick={onCancel}>
            {cancelLabel}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
