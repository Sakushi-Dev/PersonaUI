// ── ApiKeyOverlay ──
// API key input, test, and save flow
// Structured to match legacy SettingsManager API-Key Verwaltung

import { useState, useCallback, useRef } from 'react';
import Overlay from '../../components/Overlay/Overlay';
import OverlayHeader from '../../components/Overlay/OverlayHeader';
import { KeyIcon } from '../../components/Icons/Icons';
import OverlayBody from '../../components/Overlay/OverlayBody';
import OverlayFooter from '../../components/Overlay/OverlayFooter';
import FormGroup from '../../components/FormGroup/FormGroup';
import Button from '../../components/Button/Button';
import { testApiKey, saveApiKey, checkApiStatus } from '../../services/serverApi';
import { useSettings } from '../../hooks/useSettings';
import { useLanguage } from '../../hooks/useLanguage';
import styles from './Overlays.module.css';

export default function ApiKeyOverlay({ open, onClose }) {
  const [apiKey, setApiKey] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState(null); // { type: 'loading'|'success'|'error', message }
  const [testValid, setTestValid] = useState(false);
  const inputRef = useRef(null);
  const { get } = useSettings();
  const { t } = useLanguage();
  const s = t('apiKey');
  const sc = t('common');

  // ── Client-side validation (matches legacy SettingsManager.testApiKey) ──
  const handleTest = useCallback(async () => {
    const key = apiKey.trim();

    if (!key) {
      setStatus({ type: 'error', message: s.emptyError });
      setTestValid(false);
      return;
    }

    if (!key.startsWith('sk-ant-api')) {
      setStatus({ type: 'error', message: s.formatError });
      setTestValid(false);
      return;
    }

    setTesting(true);
    setStatus({ type: 'loading', message: s.testing });

    try {
      const apiModel = get('apiModel');
      const result = await testApiKey(key, apiModel);

      if (result.success) {
        setStatus({ type: 'success', message: s.valid });
        setTestValid(true);
      } else {
        setStatus({ type: 'error', message: `✗ ${result.error || 'API-Key ist ungültig'}` });
        setTestValid(false);
      }
    } catch (err) {
      setStatus({ type: 'error', message: s.connError });
      setTestValid(false);
    } finally {
      setTesting(false);
    }
  }, [apiKey, get]);

  // ── Save flow (matches legacy: status → wait → checkApiStatus → close → reload) ──
  const handleSave = useCallback(async () => {
    const key = apiKey.trim();
    if (!key) return;

    setSaving(true);
    setStatus({ type: 'loading', message: s.savingKey });

    try {
      const result = await saveApiKey(key);

      if (result.success) {
        setStatus({ type: 'success', message: s.saved });
        // Legacy: wait 1s, then checkApiStatus, close, reload
        setTimeout(async () => {
          try { await checkApiStatus(); } catch { /* ignore */ }
          onClose();
          window.location.reload();
        }, 1000);
      } else {
        setStatus({ type: 'error', message: `✗ ${result.error || s.saveError}` });
        setSaving(false);
      }
    } catch (err) {
      setStatus({ type: 'error', message: s.connError });
      setSaving(false);
    }
  }, [apiKey, onClose]);

  // ── Apply pasted text (shared logic) ──
  const applyPaste = useCallback((text) => {
    setApiKey(text);
    setTestValid(false);
    setStatus(null);
    setShowPassword(true);
    setTimeout(() => setShowPassword(false), 1500);
  }, []);

  // ── Native paste on input (Ctrl+V — no permission needed) ──
  const handleNativePaste = useCallback((e) => {
    const text = e.clipboardData?.getData('text')?.trim();
    if (text) {
      e.preventDefault();
      applyPaste(text);
    }
  }, [applyPaste]);

  // ── Paste button: try Clipboard API, fallback to focus + hint ──
  const handlePasteClick = useCallback(async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text?.trim()) {
        applyPaste(text.trim());
        return;
      }
    } catch {
      // Permission denied or not available — fallback
    }
    // Fallback: focus input and show hint
    inputRef.current?.focus();
    setStatus({ type: 'error', message: s.pasteHint });
    setTimeout(() => setStatus((st) => st?.message === s.pasteHint ? null : st), 3000);
  }, [applyPaste]);

  // ── Reset state when closing ──
  const handleClose = () => {
    setApiKey('');
    setShowPassword(false);
    setStatus(null);
    setTestValid(false);
    setTesting(false);
    setSaving(false);
    onClose();
    // Refocus message input (legacy: closeApiKeySettings sets focus back)
    setTimeout(() => {
      const msgInput = document.getElementById('message-input') || document.querySelector('[data-chat-input]');
      msgInput?.focus();
    }, 100);
  };

  // ── Reset test result when key changes ──
  const handleKeyChange = (e) => {
    setApiKey(e.target.value);
    setTestValid(false);
    setStatus(null);
  };

  return (
    <Overlay open={open} onClose={handleClose} width="480px">
      <OverlayHeader title={s.title} icon={<KeyIcon size={20} />} onClose={handleClose} />
      <OverlayBody>
        <FormGroup label={s.label} hint={s.hint}>
          <div className={styles.passwordWrapper}>
            <input
              ref={inputRef}
              type={showPassword ? 'text' : 'password'}
              className={styles.textInput}
              value={apiKey}
              onChange={handleKeyChange}
              onPaste={handleNativePaste}
              placeholder={s.placeholder}
              style={{ paddingRight: '72px' }}
            />
            <button
              className={styles.inlineBtn}
              onClick={() => setShowPassword((v) => !v)}
              title={s.showHide}
              type="button"
            >
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2">
                {showPassword ? (
                  <>
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
                    <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
                    <line x1="1" y1="1" x2="23" y2="23" />
                  </>
                ) : (
                  <>
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                    <circle cx="12" cy="12" r="3" />
                  </>
                )}
              </svg>
            </button>
            <button
              className={`${styles.inlineBtn} ${styles.inlineBtnPaste}`}
              onClick={handlePasteClick}
              title={s.paste}
              type="button"
            >
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
              </svg>
            </button>
          </div>
        </FormGroup>

        {status && (
          <div className={`${styles.statusArea} ${status.type === 'success' ? styles.success : ''} ${status.type === 'error' ? styles.error : ''}`}>
            {status.type === 'loading' && <span className={styles.statusSpinner} />}
            {status.message}
          </div>
        )}
      </OverlayBody>
      <OverlayFooter>
        <Button variant="secondary" onClick={handleTest} disabled={!apiKey.trim() || testing || saving}>
          {sc.test}
        </Button>
        {testValid && (
          <Button variant="primary" onClick={handleSave} disabled={saving}>
            {sc.save}
          </Button>
        )}
      </OverlayFooter>
    </Overlay>
  );
}
