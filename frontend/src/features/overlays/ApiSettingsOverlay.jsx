// ── ApiSettingsOverlay ──
// Structured into: Modell → Antwortverhalten → Erweitert

import { useState, useEffect, useCallback } from 'react';
import { useSettings } from '../../hooks/useSettings';
import { useLanguage } from '../../hooks/useLanguage';
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

export default function ApiSettingsOverlay({ open, onClose, panelOnly }) {
  const { get, setMany, reset, defaults, loaded } = useSettings();
  const { t } = useLanguage();
  const s = t('apiSettings');
  const sc = t('common');
  const modelOptions = defaults.apiModelOptions ?? [];

  const [model, setModel] = useState('');
  const [temperature, setTemperature] = useState(0.7);
  const [contextLimit, setContextLimit] = useState(100);
  const [experimentalMode, setExperimentalMode] = useState(false);
  const [afterthoughtMode, setAfterthoughtMode] = useState('off');

  // ── Load settings when overlay opens ──
  useEffect(() => {
    if (!open) return;
    setModel(get('apiModel', 'claude-sonnet-4-5-20250929'));
    setTemperature(parseFloat(get('apiTemperature', '0.7')));
    setContextLimit(parseInt(get('contextLimit', '100'), 10));
    setExperimentalMode(get('experimentalMode', false));
    setAfterthoughtMode(get('afterthoughtMode', 'off'));
  }, [open, get]);

  // ── Save ──
  const handleSave = useCallback(() => {
    setMany({
      apiModel: model,
      apiTemperature: String(temperature),
      contextLimit: String(contextLimit),
      experimentalMode,
      afterthoughtMode,
    });
    onClose();
  }, [model, temperature, contextLimit, experimentalMode, afterthoughtMode, setMany, onClose]);

  // ── Reset ──
  const handleReset = useCallback(() => {
    setModel('claude-sonnet-4-5-20250929');
    setTemperature(0.7);
    setContextLimit(100);
    setExperimentalMode(false);
    setAfterthoughtMode('off');
  }, []);

  return (
    <Overlay open={open} onClose={onClose} width="540px" panelOnly={panelOnly}>
      <OverlayHeader title={s.title} icon={<ChatIcon size={20} />} onClose={onClose} />
      <OverlayBody>

        {/* ═══ Section: Model ═══ */}
        <div className={styles.ifaceSection}>
          <h3 className={styles.ifaceSectionTitle}>{s.model}</h3>
          <div className={styles.ifaceCard}>
            <div className={styles.ifaceFieldGroup}>
              <span className={styles.ifaceFieldLabel}>{s.claudeModel}</span>
              <span className={styles.ifaceFieldHint}>{s.claudeModelHint}</span>
              <select
                className={styles.select}
                value={model}
                onChange={(e) => setModel(e.target.value)}
                disabled={!loaded || modelOptions.length === 0}
              >
                {modelOptions.length === 0
                  ? <option value="">{s.loadingModel}</option>
                  : modelOptions.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))
                }
              </select>
            </div>
          </div>
        </div>

        {/* ═══ Section: Response Behavior ═══ */}
        <div className={styles.ifaceSection}>
          <h3 className={styles.ifaceSectionTitle}>{s.responseBehavior}</h3>
          <div className={styles.ifaceCard}>
            <div className={styles.ifaceFieldGroup}>
              <span className={styles.ifaceFieldHint}>{s.temperatureHint}</span>
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
                <span>{s.factual}</span>
                <span>{s.creative}</span>
              </div>
            </div>

            <div className={styles.ifaceDivider} />

            <div className={styles.ifaceFieldGroup}>
              <span className={styles.ifaceFieldHint}>{s.contextHint}</span>
              <Slider
                label={s.contextLimit}
                value={contextLimit}
                onChange={(v) => setContextLimit(Math.round(v))}
                min={50}
                max={400}
                step={5}
                displayValue={`${contextLimit} ${s.messages}`}
              />
            </div>
          </div>
        </div>

        {/* ═══ Section: Advanced ═══ */}
        <div className={styles.ifaceSection}>
          <h3 className={styles.ifaceSectionTitle}>{s.advanced}</h3>
          <div className={styles.ifaceCard}>
            <div className={styles.ifaceToggleRow}>
              <div className={styles.ifaceToggleInfo}>
                <span className={styles.ifaceToggleLabel}>{s.promptMode}</span>
                <span className={styles.ifaceToggleHint}>
                  {experimentalMode
                    ? s.experimentalOn
                    : s.experimentalOff}
                </span>
              </div>
              <Toggle
                checked={experimentalMode}
                onChange={setExperimentalMode}
                id="experimental-mode"
              />
            </div>

            <div className={styles.ifaceDivider} />

            <FormGroup label={s.afterthought} hint={s.afterthoughtHint}>
              <div className={styles.typePills}>
                {[
                  { value: 'off',     label: s.afterthoughtOff },
                  { value: 'rare',    label: s.afterthoughtRare },
                  { value: 'medium',  label: s.afterthoughtMedium },
                  { value: 'high',    label: s.afterthoughtHigh },
                ].map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    className={`${styles.typePill} ${afterthoughtMode === opt.value ? styles.typePillActive : ''}`}
                    onClick={() => setAfterthoughtMode(opt.value)}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
              {afterthoughtMode !== 'off' && (
                <div className={styles.typeDescBox}>
                  <span className={styles.typeDescText}>
                    {afterthoughtMode === 'rare' && s.afterthoughtDescRare}
                    {afterthoughtMode === 'medium' && s.afterthoughtDescMedium}
                    {afterthoughtMode === 'high' && s.afterthoughtDescHigh}
                  </span>
                </div>
              )}
            </FormGroup>
          </div>

          {/* Token Info */}
          <div className={styles.ifaceInfoNote}>
            {s.tokenInfo}
          </div>
        </div>

      </OverlayBody>
      <OverlayFooter>
        <Button variant="secondary" onClick={handleReset}>{sc.reset}</Button>
        <Button variant="primary" onClick={handleSave}>{sc.save}</Button>
      </OverlayFooter>
    </Overlay>
  );
}
