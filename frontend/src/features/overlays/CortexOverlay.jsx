// ── CortexOverlay ──
// Cortex settings + file management in a tabbed overlay

import { useState, useEffect, useCallback } from 'react';
import { useSession } from '../../hooks/useSession';
import { useSettings } from '../../hooks/useSettings';
import Overlay from '../../components/Overlay/Overlay';
import OverlayHeader from '../../components/Overlay/OverlayHeader';
import OverlayBody from '../../components/Overlay/OverlayBody';
import OverlayFooter from '../../components/Overlay/OverlayFooter';
import Toggle from '../../components/Toggle/Toggle';
import Button from '../../components/Button/Button';
import Spinner from '../../components/Spinner/Spinner';
import { getCortexFiles, saveCortexFile, resetCortexFile } from '../../services/cortexApi';
import styles from './Overlays.module.css';

// ── Tab-Konfiguration ──
const TABS = [
  { key: 'memory',       label: '🧠 Memory',     fileType: 'memory' },
  { key: 'soul',         label: '💜 Seele',       fileType: 'soul' },
  { key: 'relationship', label: '💞 Beziehung',   fileType: 'relationship' },
];

// ── Frequenz-Optionen ──
const FREQUENCY_OPTIONS = [
  { value: 'frequent', label: 'Häufig',  emoji: '🔥', percent: 50, hint: 'Update alle 50% des Kontexts' },
  { value: 'medium',   label: 'Mittel',  emoji: '⚡', percent: 75, hint: 'Update alle 75% des Kontexts' },
  { value: 'rare',     label: 'Selten',  emoji: '🌙', percent: 95, hint: 'Update alle 95% des Kontexts' },
];
const DEFAULT_FREQUENCY = 'medium';

export default function CortexOverlay({ open, onClose }) {
  const { personaId, character } = useSession();
  const { get, setMany } = useSettings();

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
          setError('Cortex-Dateien konnten nicht geladen werden.');
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
      setError('Datei konnte nicht gespeichert werden.');
    } finally {
      setSaving(false);
    }
  }, [personaId, currentFileType, editContent]);

  const handleResetFile = useCallback(async () => {
    setSaving(true);
    setError(null);
    try {
      const data = await resetCortexFile(personaId, `${currentFileType}.md`);
      setFiles((prev) => ({ ...prev, [currentFileType]: data.content || '' }));
      setEditing(false);
    } catch (err) {
      console.error('Failed to reset cortex file:', err);
      setError('Datei konnte nicht zurückgesetzt werden.');
    } finally {
      setSaving(false);
    }
  }, [personaId, currentFileType]);

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
    <Overlay open={open} onClose={onClose} width="580px">
      <OverlayHeader title="🧬 Cortex" onClose={onClose} />
      <OverlayBody>

        {/* ═══ Section: Cortex Aktivierung ═══ */}
        <div className={styles.ifaceSection}>
          <h3 className={styles.ifaceSectionTitle}>Status</h3>
          <div className={styles.ifaceCard}>
            <div className={styles.ifaceToggleRow}>
              <div className={styles.ifaceToggleInfo}>
                <span className={styles.ifaceToggleLabel}>Cortex-System</span>
                <span className={styles.ifaceToggleHint}>
                  {cortexEnabled
                    ? 'Cortex ist aktiv – Dateien werden in den Prompt eingebunden.'
                    : 'Cortex ist deaktiviert – keine Cortex-Daten im Prompt.'}
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

        {/* ═══ Section: Frequenz-Auswahl ═══ */}
        <div className={styles.ifaceSection}>
          <h3 className={styles.ifaceSectionTitle}>Update-Frequenz</h3>
          <div className={styles.ifaceCard}>
            <span className={styles.ifaceFieldHint}>
              Wie oft soll Cortex seine Dateien aktualisieren?
              Der Prozentsatz bezieht sich auf dein Kontext-Limit.
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
                  <span className={styles.cortexFrequencyEmoji}>{opt.emoji}</span>
                  <span className={styles.cortexFrequencyLabel}>{opt.label}</span>
                  <span className={styles.cortexFrequencyPercent}>{opt.percent}%</span>
                </button>
              ))}
            </div>

            {/* Hint für aktive Auswahl */}
            <span className={styles.ifaceInfoNote}>
              {FREQUENCY_OPTIONS.find((o) => o.value === frequency)?.hint}
            </span>
          </div>
        </div>

        {/* ═══ Section: Cortex-Dateien ═══ */}
        <div className={styles.ifaceSection}>
          <h3 className={styles.ifaceSectionTitle}>
            Cortex-Dateien
            {personaName && (
              <span className={styles.cortexPersonaBadge}>
                {personaName}
              </span>
            )}
          </h3>

          {/* Tab Bar */}
          <div className={styles.tabBar}>
            {TABS.map((tab) => (
              <button
                key={tab.key}
                className={`${styles.tab} ${activeTab === tab.key ? styles.activeTab : ''}`}
                onClick={() => handleTabChange(tab.key)}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* File Content Area */}
          {loading ? (
            <div className={styles.centeredContent}>
              <Spinner />
            </div>
          ) : !personaId ? (
            <p className={styles.emptyText}>
              Keine Persona ausgewählt. Bitte erstelle zuerst eine Persona.
            </p>
          ) : currentContent === '' && !editing ? (
            /* Empty State */
            <div className={styles.cortexEmptyState}>
              <p className={styles.emptyText}>
                Diese Datei ist noch leer. Cortex wird sie automatisch befüllen,
                oder du kannst sie manuell bearbeiten.
              </p>
              <Button variant="secondary" size="sm" onClick={handleStartEdit}>
                ✏️ Manuell bearbeiten
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
                placeholder="Markdown-Inhalt eingeben..."
                disabled={saving}
              />
              <div className={styles.cortexEditActions}>
                <Button variant="secondary" size="sm" onClick={handleCancelEdit} disabled={saving}>
                  Abbrechen
                </Button>
                <Button variant="ghost" size="sm" onClick={handleResetFile} disabled={saving}>
                  Zurücksetzen
                </Button>
                <Button variant="primary" size="sm" onClick={handleSaveFile} disabled={saving}>
                  {saving ? 'Speichert...' : 'Datei speichern'}
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
                  ✏️ Bearbeiten
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
        </div>

      </OverlayBody>
      <OverlayFooter>
        <Button variant="secondary" onClick={handleResetSettings}>Zurücksetzen</Button>
        <Button variant="primary" onClick={handleSaveSettings}>Speichern</Button>
      </OverlayFooter>
    </Overlay>
  );
}
