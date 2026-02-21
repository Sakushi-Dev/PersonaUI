// ── Step: API-Key (6/6) ──

import { useState, useCallback, useRef } from 'react';
import { testApiKey } from '../../../services/serverApi';
import { t } from '../useTranslation';
import styles from './Steps.module.css';

export default function StepApi({ data, onChange, onNext, onBack, language }) {
  const s = t(language, 'api');
  const c = t(language, 'common');

  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [showWarning, setShowWarning] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const apiInputRef = useRef(null);

  const update = (field, value) => {
    onChange((prev) => ({ ...prev, [field]: value }));
  };

  const handleTest = useCallback(async () => {
    if (!data.apiKey?.trim()) {
      setTestResult({ success: false, message: s.errorEmpty });
      return;
    }
    setTesting(true);
    setTestResult({ success: false, message: s.testing });

    try {
      const result = await testApiKey(data.apiKey.trim());
      const valid = result.success;
      setTestResult({
        success: valid,
        message: valid ? s.valid : `✗ ${result.error || s.fallbackInvalid}`,
      });
      update('apiKeyValid', valid);
    } catch (err) {
      setTestResult({ success: false, message: s.connError });
      update('apiKeyValid', false);
    } finally {
      setTesting(false);
    }
  }, [data.apiKey, s]);

  const handleNext = () => {
    if (data.apiKeyValid) {
      onNext();
    } else {
      setShowWarning(true);
    }
  };

  // Apply pasted text (shared logic)
  const applyPaste = useCallback((text) => {
    update('apiKey', text);
    update('apiKeyValid', false);
    setTestResult(null);
    setShowPassword(true);
    setTimeout(() => setShowPassword(false), 1500);
  }, []);

  // Native paste on input (Ctrl+V — no permission needed)
  const handleNativePaste = useCallback((e) => {
    const text = e.clipboardData?.getData('text')?.trim();
    if (text) {
      e.preventDefault();
      applyPaste(text);
    }
  }, [applyPaste]);

  // Paste button: try Clipboard API, fallback to focus + hint
  const handlePasteClick = async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text?.trim()) {
        applyPaste(text.trim());
        return;
      }
    } catch {
      // Permission denied or not available
    }
    apiInputRef.current?.focus();
    setTestResult({ success: false, message: s.pasteHint });
    setTimeout(() => setTestResult((r) => r?.message === s.pasteHint ? null : r), 3000);
  };

  return (
    <div className={styles.card}>
      <div className={styles.cardHeader}>
        <span className={styles.cardStep}>6 / 6</span>
        <h2>{s.title}</h2>
        <p className={styles.cardDesc}>{s.desc}</p>
      </div>
      <div className={styles.cardBody}>

        {/* API Key */}
        <div className={styles.fieldGroup}>
          <label className={styles.label}>{s.keyLabel}</label>
          <div className={styles.apiInputRow}>
            <div className={styles.passwordWrapper}>
              <input
                ref={apiInputRef}
                type={showPassword ? 'text' : 'password'}
                className={styles.input}
                value={data.apiKey}
                onChange={(e) => { update('apiKey', e.target.value); update('apiKeyValid', false); setTestResult(null); }}
                onPaste={handleNativePaste}
                placeholder={s.keyPlaceholder}
                style={{ paddingRight: '72px' }}
              />
              <button
                className={styles.eyeBtn}
                onClick={() => setShowPassword(!showPassword)}
                title={s.showHideTitle}
                type="button"
              >
                <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
              </button>
              <button
                className={`${styles.eyeBtn} ${styles.pasteBtn}`}
                onClick={handlePasteClick}
                title={s.pasteTitle}
                type="button"
              >
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                </svg>
              </button>
            </div>
            <button className={styles.btnSecondary} onClick={handleTest} disabled={testing}>
              {s.testBtn}
            </button>
          </div>
          {testResult && (
            <div className={`${styles.apiStatus} ${testResult.success ? styles.apiSuccess : styles.apiError}`}>
              {testResult.message}
            </div>
          )}
          <div className={`${styles.infoBox} ${styles.infoBoxCompact}`}>
            <span className={styles.infoIcon}></span>
            <span dangerouslySetInnerHTML={{ __html: s.infoText }} />
          </div>
        </div>
      </div>
      <div className={styles.cardFooter}>
        <button className={styles.btnGhost} onClick={onBack}>{c.back}</button>
        <button className={styles.btnPrimary} onClick={handleNext}>{c.next}</button>
      </div>

      {/* API Key Warning Modal */}
      {showWarning && (
        <div className={styles.warningOverlay} onClick={(e) => { if (e.target === e.currentTarget) setShowWarning(false); }}>
          <div className={styles.warningCard}>
            <div className={styles.warningIcon}>!</div>
            <h3>{s.warningTitle}</h3>
            <p>{s.warningText}</p>
            <p className={styles.warningHint} dangerouslySetInnerHTML={{ __html: s.warningHint }} />
            <div className={styles.warningActions}>
              <button className={styles.btnGhost} onClick={() => setShowWarning(false)}>{s.warningBack}</button>
              <button className={styles.btnSecondary} onClick={() => { setShowWarning(false); onNext(); }}>{s.warningContinue}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
