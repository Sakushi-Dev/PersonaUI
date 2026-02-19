// ── ApiSettingsOverlay ──
// Structured into: Modell → Antwortverhalten → Erweitert

import { useState, useEffect, useCallback } from 'react';
import { useSettings } from '../../hooks/useSettings';
import Overlay from '../../components/Overlay/Overlay';
import OverlayHeader from '../../components/Overlay/OverlayHeader';
import OverlayBody from '../../components/Overlay/OverlayBody';
import OverlayFooter from '../../components/Overlay/OverlayFooter';
import Toggle from '../../components/Toggle/Toggle';
import Slider from '../../components/Slider/Slider';
import Button from '../../components/Button/Button';
import styles from './Overlays.module.css';

export default function ApiSettingsOverlay({ open, onClose }) {
  const { get, setMany, reset, defaults, loaded } = useSettings();
  const modelOptions = defaults.apiModelOptions ?? [];

  const [model, setModel] = useState('');
  const [temperature, setTemperature] = useState(0.7);
  const [contextLimit, setContextLimit] = useState(65);
  const [experimentalMode, setExperimentalMode] = useState(false);
  const [nachgedanke, setNachgedanke] = useState(false);

  // ── Load settings when overlay opens ──
  useEffect(() => {
    if (!open) return;
    setModel(get('apiModel', 'claude-sonnet-4-5-20250929'));
    setTemperature(parseFloat(get('apiTemperature', '0.7')));
    setContextLimit(parseInt(get('contextLimit', '65'), 10));
    setExperimentalMode(get('experimentalMode', false));
    setNachgedanke(get('nachgedankeEnabled', false));
  }, [open, get]);

  // ── Save ──
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

  // ── Reset ──
  const handleReset = useCallback(() => {
    setModel('claude-sonnet-4-5-20250929');
    setTemperature(0.7);
    setContextLimit(65);
    setExperimentalMode(false);
    setNachgedanke(false);
  }, []);

  return (
    <Overlay open={open} onClose={onClose} width="540px">
      <OverlayHeader title="API / Chat Einstellungen" onClose={onClose} />
      <OverlayBody>

        {/* ═══ Section: Modell ═══ */}
        <div className={styles.ifaceSection}>
          <h3 className={styles.ifaceSectionTitle}>Modell</h3>
          <div className={styles.ifaceCard}>
            <div className={styles.ifaceFieldGroup}>
              <span className={styles.ifaceFieldLabel}>Claude Modell</span>
              <span className={styles.ifaceFieldHint}>Wähle das KI-Modell für deine Unterhaltungen</span>
              <select
                className={styles.select}
                value={model}
                onChange={(e) => setModel(e.target.value)}
                disabled={!loaded || modelOptions.length === 0}
              >
                {modelOptions.length === 0
                  ? <option value="">Wird geladen…</option>
                  : modelOptions.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))
                }
              </select>
            </div>
          </div>
        </div>

        {/* ═══ Section: Antwortverhalten ═══ */}
        <div className={styles.ifaceSection}>
          <h3 className={styles.ifaceSectionTitle}>Antwortverhalten</h3>
          <div className={styles.ifaceCard}>
            <div className={styles.ifaceFieldGroup}>
              <span className={styles.ifaceFieldHint}>Steuert die Kreativität der Antworten</span>
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
            </div>

            <div className={styles.ifaceDivider} />

            <div className={styles.ifaceFieldGroup}>
              <span className={styles.ifaceFieldHint}>Höherer Kontext = mehr Kosten pro Nachricht</span>
              <Slider
                label="Kontext-Limit"
                value={contextLimit}
                onChange={(v) => setContextLimit(Math.round(v))}
                min={50}
                max={400}
                step={5}
                displayValue={`${contextLimit} Nachrichten`}
              />
            </div>
          </div>
        </div>

        {/* ═══ Section: Erweitert ═══ */}
        <div className={styles.ifaceSection}>
          <h3 className={styles.ifaceSectionTitle}>Erweitert</h3>
          <div className={styles.ifaceCard}>
            <div className={styles.ifaceToggleRow}>
              <div className={styles.ifaceToggleInfo}>
                <span className={styles.ifaceToggleLabel}>Prompt-Modus</span>
                <span className={styles.ifaceToggleHint}>
                  {experimentalMode
                    ? 'Experimenteller Modus mit erweiterten Prompt-Techniken.'
                    : 'Standard-Modus mit bewährtem Prompt-Aufbau.'}
                </span>
              </div>
              <Toggle
                checked={experimentalMode}
                onChange={setExperimentalMode}
                id="experimental-mode"
              />
            </div>

            <div className={styles.ifaceDivider} />

            <div className={styles.ifaceToggleRow}>
              <div className={styles.ifaceToggleInfo}>
                <span className={styles.ifaceToggleLabel}>Nachgedanke</span>
                <span className={styles.ifaceToggleHint}>
                  Innerer Dialog-System mit eskalierenden Zeitintervallen.
                  Die KI kann von sich aus Nachrichten senden.
                </span>
              </div>
              <Toggle
                checked={nachgedanke}
                onChange={setNachgedanke}
                id="nachgedanke-toggle"
              />
            </div>
          </div>

          {/* Token Info */}
          <div className={styles.ifaceInfoNote}>
            Klicke auf das (i) Symbol bei KI-Nachrichten, um Token-Verbrauch und Kosten einzusehen.
          </div>
        </div>

      </OverlayBody>
      <OverlayFooter>
        <Button variant="secondary" onClick={handleReset}>Zurücksetzen</Button>
        <Button variant="primary" onClick={handleSave}>Speichern</Button>
      </OverlayFooter>
    </Overlay>
  );
}
