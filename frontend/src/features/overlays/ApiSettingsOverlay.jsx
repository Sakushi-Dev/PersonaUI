// ── ApiSettingsOverlay ──
// Structured into: Modell → Antwortverhalten → Erweitert

import { useState, useEffect, useCallback } from 'react';
import { useSettings } from '../../hooks/useSettings';
import Overlay from '../../components/Overlay/Overlay';
import OverlayHeader from '../../components/Overlay/OverlayHeader';
import { ChatIcon } from '../../components/Icons/Icons';
import OverlayBody from '../../components/Overlay/OverlayBody';
import OverlayFooter from '../../components/Overlay/OverlayFooter';
import FormGroup from '../../components/FormGroup/FormGroup';
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
  const [nachgedankeMode, setNachgedankeMode] = useState('off');

  // ── Load settings when overlay opens ──
  useEffect(() => {
    if (!open) return;
    setModel(get('apiModel', 'claude-sonnet-4-5-20250929'));
    setTemperature(parseFloat(get('apiTemperature', '0.7')));
    setContextLimit(parseInt(get('contextLimit', '65'), 10));
    setExperimentalMode(get('experimentalMode', false));
    setNachgedankeMode(get('nachgedankeMode', 'off'));
  }, [open, get]);

  // ── Save ──
  const handleSave = useCallback(() => {
    setMany({
      apiModel: model,
      apiTemperature: String(temperature),
      contextLimit: String(contextLimit),
      experimentalMode,
      nachgedankeMode,
    });
    onClose();
  }, [model, temperature, contextLimit, experimentalMode, nachgedankeMode, setMany, onClose]);

  // ── Reset ──
  const handleReset = useCallback(() => {
    setModel('claude-sonnet-4-5-20250929');
    setTemperature(0.7);
    setContextLimit(65);
    setExperimentalMode(false);
    setNachgedankeMode('off');
  }, []);

  return (
    <Overlay open={open} onClose={onClose} width="540px">
      <OverlayHeader title="API / Chat Einstellungen" icon={<ChatIcon size={20} />} onClose={onClose} />
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

            <FormGroup label="Nachgedanke" hint="Innerer Dialog-System — die KI kann von sich aus Nachrichten senden. Höhere Frequenz = mehr API-Kosten im Hintergrund.">
              <div className={styles.typePills}>
                {[
                  { value: 'off',     label: 'Aus' },
                  { value: 'selten',  label: 'Selten' },
                  { value: 'mittel',  label: 'Mittel' },
                  { value: 'hoch',    label: 'Hoch' },
                ].map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    className={`${styles.typePill} ${nachgedankeMode === opt.value ? styles.typePillActive : ''}`}
                    onClick={() => setNachgedankeMode(opt.value)}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
              {nachgedankeMode !== 'off' && (
                <div className={styles.typeDescBox}>
                  <span className={styles.typeDescText}>
                    {nachgedankeMode === 'selten' && 'Jede 3. Nachricht löst einen inneren Dialog aus.'}
                    {nachgedankeMode === 'mittel' && 'Jede 2. Nachricht löst einen inneren Dialog aus.'}
                    {nachgedankeMode === 'hoch' && 'Jede Nachricht löst einen inneren Dialog aus.'}
                  </span>
                </div>
              )}
            </FormGroup>
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
