// ── ApiSettingsOverlay ──
// Model, temperature, context limit, experimental mode, afterthought toggle

import { useState, useEffect, useCallback } from 'react';
import { useSettings } from '../../hooks/useSettings';
import Overlay from '../../components/Overlay/Overlay';
import OverlayHeader from '../../components/Overlay/OverlayHeader';
import OverlayBody from '../../components/Overlay/OverlayBody';
import OverlayFooter from '../../components/Overlay/OverlayFooter';
import FormGroup from '../../components/FormGroup/FormGroup';
import Toggle from '../../components/Toggle/Toggle';
import Slider from '../../components/Slider/Slider';
import Button from '../../components/Button/Button';
import styles from './Overlays.module.css';

const MODEL_OPTIONS = [
  { value: 'claude-sonnet-4-5-20250929', label: 'Claude Sonnet 4.5 (Neueste)' },
  { value: 'claude-sonnet-4-20250514', label: 'Claude Sonnet 4 (Mai 2025)' },
  { value: 'claude-3-5-sonnet-latest', label: 'Claude Sonnet 3.7 (latest)' },
  { value: 'claude-3-5-sonnet-20250220', label: 'Claude Sonnet 3.7 (Februar 2025)' },
];

export default function ApiSettingsOverlay({ open, onClose }) {
  const { get, setMany, reset } = useSettings();

  const [model, setModel] = useState('');
  const [temperature, setTemperature] = useState(0.7);
  const [contextLimit, setContextLimit] = useState(25);
  const [experimentalMode, setExperimentalMode] = useState(false);
  const [nachgedanke, setNachgedanke] = useState(false);

  // Load current settings when opened
  useEffect(() => {
    if (open) {
      setModel(get('apiModel', 'claude-sonnet-4-5-20250929'));
      setTemperature(parseFloat(get('apiTemperature', '0.7')));
      setContextLimit(parseInt(get('contextLimit', '25'), 10));
      setExperimentalMode(get('experimentalMode', false));
      setNachgedanke(get('nachgedankeEnabled', false));
    }
  }, [open, get]);

  const handleSave = useCallback(() => {
    setMany({
      apiModel: model,
      apiTemperature: String(temperature),
      contextLimit: String(contextLimit),
      experimentalMode,
      nachgedankeEnabled: nachgedanke,
    });
    onClose();
  }, [model, temperature, contextLimit, experimentalMode, nachgedanke, setMany, onClose]);

  const handleReset = useCallback(() => {
    setModel('claude-sonnet-4-5-20250929');
    setTemperature(0.7);
    setContextLimit(25);
    setExperimentalMode(false);
    setNachgedanke(false);
  }, []);

  return (
    <Overlay open={open} onClose={onClose} width="520px">
      <OverlayHeader title="API / Chat Einstellungen" onClose={onClose} />
      <OverlayBody>
        <FormGroup label="Claude Modell">
          <select
            className={styles.select}
            value={model}
            onChange={(e) => setModel(e.target.value)}
          >
            {MODEL_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </FormGroup>

        <Slider
          label="Temperature"
          value={temperature}
          onChange={setTemperature}
          min={0.1}
          max={1.2}
          step={0.1}
          displayValue={temperature.toFixed(1)}
        />
        <div className={styles.sliderLabels}>
          <span>Sachlich</span>
          <span>Kreativ</span>
        </div>

        <Slider
          label="Kontext-Limit"
          value={contextLimit}
          onChange={(v) => setContextLimit(Math.round(v))}
          min={10}
          max={100}
          step={5}
          displayValue={`${contextLimit} Nachrichten`}
        />
        <p className={styles.hint}>Höherer Kontext = mehr Kosten pro Nachricht</p>

        <div className={styles.settingRow}>
          <Toggle
            label={experimentalMode ? 'Experimental' : 'Default'}
            checked={experimentalMode}
            onChange={setExperimentalMode}
            id="experimental-mode"
          />
          <div className={styles.settingInfo}>
            <p className={styles.settingLabel}>Prompt-Modus</p>
            <p className={styles.hint}>
              {experimentalMode
                ? 'Experimenteller Modus mit erweiterten Prompt-Techniken.'
                : 'Standard-Modus mit bewährtem Prompt-Aufbau.'
              }
            </p>
          </div>
        </div>

        <div className={styles.settingRow}>
          <Toggle
            label={nachgedanke ? 'An' : 'Aus'}
            checked={nachgedanke}
            onChange={setNachgedanke}
            id="nachgedanke-toggle"
          />
          <div className={styles.settingInfo}>
            <p className={styles.settingLabel}>Nachgedanke</p>
            <p className={styles.hint}>
              Innerer Dialog-System mit eskalierenden Zeitintervallen.
              Die KI kann von sich aus Nachrichten senden.
            </p>
          </div>
        </div>

        <div className={styles.infoBox}>
          <p className={styles.infoTitle}>ℹ️ Token-Info</p>
          <p className={styles.hint}>
            Klicke auf das (i) Symbol bei KI-Nachrichten, um Token-Verbrauch und Kosten einzusehen.
          </p>
        </div>
      </OverlayBody>
      <OverlayFooter>
        <Button variant="secondary" onClick={handleReset}>Zurücksetzen</Button>
        <Button variant="primary" onClick={handleSave}>Speichern</Button>
      </OverlayFooter>
    </Overlay>
  );
}
