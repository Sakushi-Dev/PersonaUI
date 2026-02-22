// ── CortexOverlay ──
// Cortex settings + file management in a tabbed overlay

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useSession } from '../../hooks/useSession';
import { useSettings } from '../../hooks/useSettings';
import { useLanguage } from '../../hooks/useLanguage';
import Overlay from '../../components/Overlay/Overlay';
import OverlayHeader from '../../components/Overlay/OverlayHeader';
import { CortexIcon } from '../../components/Icons/Icons';
import OverlayBody from '../../components/Overlay/OverlayBody';
import OverlayFooter from '../../components/Overlay/OverlayFooter';
import Toggle from '../../components/Toggle/Toggle';
import Button from '../../components/Button/Button';
import Spinner from '../../components/Spinner/Spinner';
import { getCortexFiles, saveCortexFile, resetCortexFile, resetAllCortexFiles } from '../../services/cortexApi';
import styles from './Overlays.module.css';

// ── Tab keys (labels resolved via i18n) ──
const TAB_KEYS = [
  { key: 'memory',       labelKey: 'tabMemory',       fileType: 'memory' },
  { key: 'soul',         labelKey: 'tabSoul',         fileType: 'soul' },
  { key: 'relationship', labelKey: 'tabRelationship', fileType: 'relationship' },
];

// ── Frequency option keys (labels resolved via i18n) ──
const FREQ_KEYS = [
  { value: 'frequent', labelKey: 'frequent',  percent: 50, hintKey: 'freqHintFrequent' },
  { value: 'medium',   labelKey: 'medium',    percent: 75, hintKey: 'freqHintMedium' },
  { value: 'rare',     labelKey: 'rare',      percent: 95, hintKey: 'freqHintRare' },
];
const DEFAULT_FREQUENCY = 'medium';

export default function CortexOverlay({ open, onClose, panelOnly }) {
  const { personaId, character } = useSession();
  const { get, setMany } = useSettings();
  const { t } = useLanguage();
  const s = t('cortex');
  const sc = t('common');

  // Resolve i18n for tabs + frequency options
  const TABS = useMemo(() =>
    TAB_KEYS.map(tab => ({ ...tab, label: s[tab.labelKey] || tab.key })),
    [s]
  );
  const FREQUENCY_OPTIONS = useMemo(() =>
    FREQ_KEYS.map(opt => ({ ...opt, label: s[opt.labelKey] || opt.value, hint: s[opt.hintKey] || '' })),
    [s]
  );

  // ── Settings State ──
  const [cortexEnabled, setCortexEnabled] = useState(true);
  const [frequency, setFrequency] = useState(DEFAULT_FREQUENCY);

  // ── File State ──
  const [files, setFiles] = useState({ memory: '', soul: '', relationship: '' });
  const [personaName, setPersonaName] = useState('');
  const [activeTab, setActiveTab] = useState('memory');
  const [editing, setEditing] = useState(false);
  const [editContent, setEditContent] = useState('');

  // ── Loading / Error ──
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  // ══════════════════════════════════════════
  // Load settings + files when overlay opens
  // ══════════════════════════════════════════
  useEffect(() => {
    if (!open) return;

    // Sync settings into local state
    setCortexEnabled(get('cortexEnabled', true));
    setFrequency(get('cortexFrequency', DEFAULT_FREQUENCY));

    // Reset UI state
    setActiveTab('memory');
    setEditing(false);
    setError(null);

    // Fetch files
    if (personaId) {
      setLoading(true);
      getCortexFiles(personaId)
        .then((data) => {
          setFiles(data.files || { memory: '', soul: '', relationship: '' });
          setPersonaName(data.persona_name || character?.char_name || '');
        })
        .catch((err) => {
          console.error('Failed to load cortex files:', err);
          setError(s.loadError);
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [open, personaId, get, character]);

  // ══════════════════════════════════════════
  // File Actions
  // ══════════════════════════════════════════
  const currentFileType = TABS.find((t) => t.key === activeTab)?.fileType || 'memory';
  const currentContent = files[currentFileType] || '';

  const handleStartEdit = useCallback(() => {
    setEditContent(currentContent);
    setEditing(true);
  }, [currentContent]);

  const handleCancelEdit = useCallback(() => {
    setEditing(false);
    setEditContent('');
  }, []);

  const handleSaveFile = useCallback(async () => {
    setSaving(true);
    setError(null);
    try {
      await saveCortexFile(personaId, `${currentFileType}.md`, editContent);
      setFiles((prev) => ({ ...prev, [currentFileType]: editContent }));
      setEditing(false);
    } catch (err) {
      console.error('Failed to save cortex file:', err);
      setError(s.saveError);
    } finally {
      setSaving(false);
    }
  }, [personaId, currentFileType, editContent]);

  const handleResetFile = useCallback(async () => {
    const tabLabel = TABS.find((t) => t.fileType === currentFileType)?.label || currentFileType;
    if (!window.confirm(s.resetConfirm.replace('{label}', tabLabel))) return;
    setSaving(true);
    setError(null);
    try {
      const data = await resetCortexFile(personaId, `${currentFileType}.md`);
      setFiles((prev) => ({ ...prev, [currentFileType]: data.content || '' }));
      setEditing(false);
    } catch (err) {
      console.error('Failed to reset cortex file:', err);
      setError(s.resetError);
    } finally {
      setSaving(false);
    }
  }, [personaId, currentFileType]);

  const handleResetAll = useCallback(async () => {
    if (!window.confirm(s.resetAllConfirm)) return;
    setSaving(true);
    setError(null);
    try {
      const data = await resetAllCortexFiles(personaId);
      setFiles(data.files || { memory: '', soul: '', relationship: '' });
      setEditing(false);
    } catch (err) {
      console.error('Failed to reset all cortex files:', err);
      setError(s.resetAllError);
    } finally {
      setSaving(false);
    }
  }, [personaId]);

  // ══════════════════════════════════════════
  // Save Settings (Footer "Speichern")
  // ══════════════════════════════════════════
  const handleSaveSettings = useCallback(() => {
    setMany({
      cortexEnabled,
      cortexFrequency: frequency,
    });
    onClose();
  }, [cortexEnabled, frequency, setMany, onClose]);

  // ══════════════════════════════════════════
  // Reset Settings (Footer "Zurücksetzen")
  // ══════════════════════════════════════════
  const handleResetSettings = useCallback(() => {
    setCortexEnabled(true);
    setFrequency(DEFAULT_FREQUENCY);
  }, []);

  // ══════════════════════════════════════════
  // Tab change: cancel ongoing edit
  // ══════════════════════════════════════════
  const handleTabChange = useCallback((tabKey) => {
    setActiveTab(tabKey);
    setEditing(false);
    setEditContent('');
    setError(null);
  }, []);

  // ══════════════════════════════════════════
  // Render
  // ══════════════════════════════════════════
  return (
    <Overlay open={open} onClose={onClose} width="580px" panelOnly={panelOnly}>
      <OverlayHeader title={s.title} icon={<CortexIcon size={20} />} onClose={onClose} />
      <OverlayBody>

        {/* ═══ Section: Cortex Aktivierung ═══ */}
        <div className={styles.ifaceSection}>
          <h3 className={styles.ifaceSectionTitle}>{s.status}</h3>
          <div className={styles.ifaceCard}>
            <div className={styles.ifaceToggleRow}>
              <div className={styles.ifaceToggleInfo}>
                <span className={styles.ifaceToggleLabel}>{s.cortexSystem}</span>
                <span className={styles.ifaceToggleHint}>
                  {cortexEnabled
                    ? s.enabledHint
                    : s.disabledHint}
                </span>
              </div>
              <Toggle
                checked={cortexEnabled}
                onChange={setCortexEnabled}
                id="cortex-enabled"
              />
            </div>
          </div>
        </div>

        {/* ═══ Section: Update-Frequenz ═══ */}
        <div className={styles.ifaceSection}>
          <h3 className={styles.ifaceSectionTitle}>{s.updateFrequency}</h3>
          <div className={styles.ifaceCard}>
            <div className={styles.ifaceFieldGroup}>
              <span className={styles.ifaceFieldLabel}>{s.updateInterval}</span>
              <span className={styles.ifaceFieldHint}>
                {s.updateIntervalHint}
              </span>

              {/* Segmented Control / Radio Group */}
              <div className={styles.cortexFrequencySelector}>
                {FREQUENCY_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    className={`${styles.cortexFrequencyOption} ${
                      frequency === opt.value ? styles.cortexFrequencyActive : ''
                    }`}
                    onClick={() => setFrequency(opt.value)}
                    type="button"
                    role="radio"
                    aria-checked={frequency === opt.value}
                    aria-label={`${opt.label} – Update alle ${opt.percent}% des Kontexts`}
                  >
                    <span className={styles.cortexFrequencyLabel}>{opt.label}</span>
                    <span className={styles.cortexFrequencyPercent}>{opt.percent}%</span>
                  </button>
                ))}
              </div>

              {/* Hint for active selection */}
              <span className={styles.ifaceInfoNote}>
                {FREQUENCY_OPTIONS.find((o) => o.value === frequency)?.hint}
              </span>
            </div>
          </div>
        </div>

        {/* ═══ Section: Cortex-Dateien ═══ */}
        <div className={styles.ifaceSection}>
          <h3 className={styles.ifaceSectionTitle}>
            {s.files}
            {personaName && (
              <span className={styles.cortexPersonaBadge}>
                {personaName}
              </span>
            )}
          </h3>

          <div className={styles.ifaceCard}>
            {/* Tab Bar */}
            <div className={styles.cortexTabBar}>
              {TABS.map((tab) => (
                <button
                  key={tab.key}
                  type="button"
                  className={`${styles.cortexTab} ${activeTab === tab.key ? styles.cortexTabActive : ''}`}
                  onClick={() => handleTabChange(tab.key)}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            <div className={styles.ifaceDivider} />

            {/* File Content Area */}
            {loading ? (
              <div className={styles.centeredContent}>
                <Spinner />
              </div>
            ) : !personaId ? (
              <p className={styles.emptyText}>
                {s.noPersona}
              </p>
            ) : currentContent === '' && !editing ? (
              /* Empty State */
              <div className={styles.cortexEmptyState}>
                <p className={styles.emptyText}>
                  {s.emptyFile}
                </p>
                <Button variant="secondary" size="sm" onClick={handleStartEdit}>
                  {s.manualEdit}
                </Button>
              </div>
            ) : editing ? (
              /* Edit Mode */
              <div className={styles.cortexEditArea}>
                <textarea
                  className={styles.textarea}
                  value={editContent}
                  onChange={(e) => setEditContent(e.target.value)}
                  rows={12}
                  placeholder={s.editPlaceholder}
                  disabled={saving}
                />
                <div className={styles.cortexEditActions}>
                  <Button variant="secondary" size="sm" onClick={handleCancelEdit} disabled={saving}>
                    {sc.cancel}
                  </Button>
                  <Button variant="ghost" size="sm" onClick={handleResetFile} disabled={saving}>
                    {s.resetFile}
                  </Button>
                  <Button variant="primary" size="sm" onClick={handleSaveFile} disabled={saving}>
                    {saving ? sc.saving : s.saveFile}
                  </Button>
                </div>
              </div>
            ) : (
              /* Read-Only View */
              <div className={styles.cortexFileView}>
                <pre className={styles.cortexFileContent}>
                  {currentContent}
                </pre>
                <div className={styles.cortexFileActions}>
                  <Button variant="secondary" size="sm" onClick={handleStartEdit}>
                    {sc.edit}
                  </Button>
                  <Button variant="ghost" size="sm" onClick={handleResetFile} disabled={saving}>
                    {s.resetFile}
                  </Button>
                </div>
              </div>
            )}

            {/* Error Display */}
            {error && (
              <div className={`${styles.statusArea} ${styles.error}`}>
                {error}
              </div>
            )}

            {/* Reset All Button */}
            {personaId && !loading && (
              <div className={styles.cortexResetAllRow}>
                <Button variant="ghost" size="sm" onClick={handleResetAll} disabled={saving}>
                  {s.resetAll}
                </Button>
              </div>
            )}
          </div>
        </div>

      </OverlayBody>
      <OverlayFooter>
        <Button variant="secondary" onClick={handleResetSettings}>{sc.reset}</Button>
        <Button variant="primary" onClick={handleSaveSettings}>{sc.save}</Button>
      </OverlayFooter>
    </Overlay>
  );
}
