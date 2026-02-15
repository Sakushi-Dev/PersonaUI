// ── Step: API & Chat (3/4) ──

import { useState, useCallback } from 'react';
import FormGroup from '../../../components/FormGroup/FormGroup';
import Slider from '../../../components/Slider/Slider';
import Toggle from '../../../components/Toggle/Toggle';
import Button from '../../../components/Button/Button';
import Spinner from '../../../components/Spinner/Spinner';
import { testApiKey } from '../../../services/serverApi';
import styles from './Steps.module.css';

export default function StepApi({ data, onChange, onNext, onBack }) {
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [showWarning, setShowWarning] = useState(false);

  const update = (field, value) => {
    onChange({ ...data, [field]: value });
  };

  const handleTest = useCallback(async () => {
    if (!data.apiKey?.trim()) return;
    setTesting(true);
    setTestResult(null);

    try {
      const result = await testApiKey(data.apiKey.trim());
      const valid = result.success;
      setTestResult({
        success: valid,
        message: valid ? '✅ API-Key ist gültig!' : `❌ ${result.error || 'Ungültig'}`,
      });
      update('apiKeyValid', valid);
    } catch (err) {
      setTestResult({ success: false, message: `❌ ${err.message}` });
      update('apiKeyValid', false);
    } finally {
      setTesting(false);
    }
  }, [data.apiKey]);

  const handleNext = () => {
    if (!data.apiKeyValid && data.apiKey?.trim()) {
      setShowWarning(true);
    } else if (!data.apiKey?.trim()) {
      setShowWarning(true);
    } else {
      onNext();
    }
  };

  // Warning modal
  if (showWarning) {
    return (
      <div className={styles.step}>
        <h2 className={styles.title}>⚠️ Kein gültiger API-Key</h2>
        <p className={styles.subtitle}>
          Ohne API-Key kannst du PersonaUI nur eingeschränkt erkunden.
          Die Chat-Funktion wird nicht verfügbar sein.
        </p>
        <div className={styles.footer}>
          <Button variant="secondary" onClick={() => setShowWarning(false)}>Zurück</Button>
          <Button variant="primary" onClick={() => { setShowWarning(false); onNext(); }}>
            Trotzdem fortfahren
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.step}>
      <h2 className={styles.title}>API & Chat <span className={styles.stepNum}>(3/4)</span></h2>
      <p className={styles.subtitle}>Konfiguriere deine KI-Verbindung</p>

      <Slider
        label="Kontext-Limit"
        value={parseInt(data.contextLimit, 10)}
        onChange={(v) => update('contextLimit', String(Math.round(v)))}
        min={10}
        max={100}
        step={5}
        displayValue={`${data.contextLimit} Nachrichten`}
      />
      <p className={styles.hint}>Empfohlen: 65 (Balance zwischen Qualität und Kosten)</p>

      <div className={styles.settingRow}>
        <Toggle
          label={data.nachgedankeEnabled ? 'An' : 'Aus'}
          checked={data.nachgedankeEnabled}
          onChange={(v) => update('nachgedankeEnabled', v)}
          id="ob-nachgedanke"
        />
        <div>
          <span className={styles.label}>Nachgedanke (Beta)</span>
          <p className={styles.hint}>KI kann eigenständig Nachrichten senden. Verursacht zusätzliche Kosten.</p>
        </div>
      </div>

      <FormGroup label="Anthropic API-Key">
        <div className={styles.apiKeyRow}>
          <input
            className={styles.input}
            type="password"
            value={data.apiKey}
            onChange={(e) => { update('apiKey', e.target.value); update('apiKeyValid', false); setTestResult(null); }}
            placeholder="sk-ant-api03-..."
          />
          <Button variant="secondary" size="sm" onClick={handleTest} disabled={!data.apiKey?.trim() || testing}>
            {testing ? <Spinner /> : 'Testen'}
          </Button>
        </div>
      </FormGroup>

      {testResult && (
        <div className={`${styles.statusBox} ${testResult.success ? styles.success : styles.error}`}>
          {testResult.message}
        </div>
      )}

      <div className={styles.footer}>
        <Button variant="secondary" onClick={onBack}>Zurück</Button>
        <Button variant="primary" onClick={handleNext}>Weiter</Button>
      </div>
    </div>
  );
}
