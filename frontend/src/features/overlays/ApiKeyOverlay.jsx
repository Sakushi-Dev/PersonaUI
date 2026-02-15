// ── ApiKeyOverlay ──
// API key input, test, and save flow

import { useState, useCallback } from 'react';
import Overlay from '../../components/Overlay/Overlay';
import OverlayHeader from '../../components/Overlay/OverlayHeader';
import OverlayBody from '../../components/Overlay/OverlayBody';
import OverlayFooter from '../../components/Overlay/OverlayFooter';
import FormGroup from '../../components/FormGroup/FormGroup';
import Button from '../../components/Button/Button';
import Spinner from '../../components/Spinner/Spinner';
import { testApiKey, saveApiKey } from '../../services/serverApi';
import styles from './Overlays.module.css';

export default function ApiKeyOverlay({ open, onClose }) {
  const [apiKey, setApiKey] = useState('');
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null); // { success, message }
  const [saving, setSaving] = useState(false);

  const handleTest = useCallback(async () => {
    if (!apiKey.trim()) return;
    setTesting(true);
    setTestResult(null);

    try {
      const result = await testApiKey(apiKey.trim());
      setTestResult({
        success: result.success,
        message: result.success
          ? '✅ API-Key ist gültig!'
          : `❌ ${result.error || 'API-Key ungültig'}`,
      });
    } catch (err) {
      setTestResult({ success: false, message: `❌ Fehler: ${err.message}` });
    } finally {
      setTesting(false);
    }
  }, [apiKey]);

  const handleSave = useCallback(async () => {
    if (!apiKey.trim()) return;
    setSaving(true);
    try {
      await saveApiKey(apiKey.trim());
      onClose();
    } catch (err) {
      setTestResult({ success: false, message: `❌ Speichern fehlgeschlagen: ${err.message}` });
    } finally {
      setSaving(false);
    }
  }, [apiKey, onClose]);

  const handlePaste = useCallback(async () => {
    try {
      const text = await navigator.clipboard.readText();
      setApiKey(text);
    } catch {
      // Clipboard permission denied
    }
  }, []);

  const handleClose = () => {
    setApiKey('');
    setTestResult(null);
    onClose();
  };

  return (
    <Overlay open={open} onClose={handleClose} width="480px">
      <OverlayHeader title="Anthropic API-Key Verwaltung" onClose={handleClose} />
      <OverlayBody>
        <FormGroup label="API Key">
          <div className={styles.inputRow}>
            <input
              type="password"
              className={styles.textInput}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="sk-ant-api03-..."
            />
            <button className={styles.iconBtn} onClick={handlePaste} title="Einfügen">
              📋
            </button>
          </div>
        </FormGroup>

        {testing && (
          <div className={styles.statusArea}>
            <Spinner /> <span>Teste API-Key...</span>
          </div>
        )}

        {testResult && (
          <div className={`${styles.statusArea} ${testResult.success ? styles.success : styles.error}`}>
            {testResult.message}
          </div>
        )}
      </OverlayBody>
      <OverlayFooter>
        <Button variant="secondary" onClick={handleTest} disabled={!apiKey.trim() || testing}>
          Testen
        </Button>
        {testResult?.success && (
          <Button variant="primary" onClick={handleSave} disabled={saving}>
            {saving ? 'Speichert...' : 'Speichern'}
          </Button>
        )}
      </OverlayFooter>
    </Overlay>
  );
}
