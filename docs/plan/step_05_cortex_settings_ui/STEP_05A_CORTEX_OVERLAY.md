# Schritt 5A: CortexOverlay Component

> **⚠️ v3:** Tier-Modell vereinfacht. Statt 3 Slider-Regler gibt es jetzt einen **Frequenz-Selector** (Radio-Buttons/Segmented Control) mit 3 festen Optionen: Häufig (50%), Mittel (75%), Selten (95%).

## Übersicht

Das `CortexOverlay` ersetzt das bisherige `MemoryOverlay` als zentrale Verwaltungsoberfläche für das Cortex-System. Es kombiniert **Settings-Steuerung** (Enable/Disable, Frequenz-Auswahl) mit **Datei-Verwaltung** (Lesen/Bearbeiten der drei Cortex-Markdown-Dateien).

### Betroffene Dateien

| Aktion | Datei |
|---|---|
| NEU erstellen | `frontend/src/features/overlays/CortexOverlay.jsx` |
| NEU erstellen | `frontend/src/services/cortexApi.js` |
| Anpassen | `frontend/src/features/overlays/index.js` (Export hinzufügen) |
| Anpassen | `frontend/src/features/overlays/Overlays.module.css` (neue Klassen) |
| Anpassen | `frontend/src/features/chat/ChatPage.jsx` (Overlay einbinden) |
| Anpassen | `frontend/src/features/chat/components/Header/Header.jsx` (Button umbenennen) |
| ENTFERNEN | `frontend/src/features/overlays/MemoryOverlay.jsx` (nach Migration) |

---

## 2. Architektur-Entscheidungen

### State-Aufteilung

| State | Typ | Quelle | Beschreibung |
|---|---|---|---|
| `cortexEnabled` | Settings | `useSettings().get('cortexEnabled')` | Cortex an/aus |
| `frequency` | Settings | `useSettings().get('cortexFrequency')` | Gewählte Frequenz (`"frequent"` / `"medium"` / `"rare"`) |
| `activeTab` | Lokal | `useState('memory')` | Aktuell sichtbarer Tab |
| `files` | Lokal (API) | `useState({})` | Datei-Inhalte von Server |
| `editContent` | Lokal | `useState('')` | Textarea-Inhalt beim Bearbeiten |
| `editing` | Lokal | `useState(false)` | Ob gerade editiert wird |
| `loading` | Lokal | `useState(true)` | Lade-Indikator |
| `saving` | Lokal | `useState(false)` | Speicher-Indikator |
| `error` | Lokal | `useState(null)` | Fehlermeldung |

### Warum Settings vs. Lokal?

- **`cortexEnabled`** und **`frequency`** → `useSettings()`, weil sie serverseitig persistiert werden und von der Trigger-Logik gelesen werden müssen
- **File-Inhalte** → Lokal + API-Calls, weil die Dateien per REST geladen/gespeichert werden (nicht Teil des Settings-Systems)
- **UI-State** (activeTab, editing, etc.) → Rein lokal, ephemer

---

## 3. API-Integration

### Benötigte Endpoints (aus Step 2C/6)

```
GET  /api/cortex/files?persona_id={id}
     → { success: true, files: { memory: "...", soul: "...", relationship: "..." }, persona_name: "..." }

PUT  /api/cortex/files
     Body: { persona_id, file_type: "memory"|"soul"|"relationship", content: "..." }
     → { success: true }

POST /api/cortex/files/reset
     Body: { persona_id, file_type: "memory"|"soul"|"relationship" }
     → { success: true, content: "..." }
```

### Service-Datei: `frontend/src/services/cortexApi.js`

```js
const BASE = '/api/cortex';

export async function getCortexFiles(personaId) {
  const res = await fetch(`${BASE}/files?persona_id=${personaId}`);
  if (!res.ok) throw new Error(`GET cortex files failed: ${res.status}`);
  return res.json();
}

export async function saveCortexFile(personaId, fileType, content) {
  const res = await fetch(`${BASE}/files`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ persona_id: personaId, file_type: fileType, content }),
  });
  if (!res.ok) throw new Error(`PUT cortex file failed: ${res.status}`);
  return res.json();
}

export async function resetCortexFile(personaId, fileType) {
  const res = await fetch(`${BASE}/files/reset`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ persona_id: personaId, file_type: fileType }),
  });
  if (!res.ok) throw new Error(`POST cortex reset failed: ${res.status}`);
  return res.json();
}
```

### Lade-Zeitpunkt

- **Beim Öffnen** (`useEffect` auf `open`): `getCortexFiles(personaId)` aufrufen
- **Beim Tab-Wechsel**: Kein erneuter API-Call — alle 3 Dateien werden initial geladen
- **Beim Speichern**: `saveCortexFile()` für die aktive Datei
- **Beim Zurücksetzen**: `resetCortexFile()` für die aktive Datei

---

## 4. Vollständige Component-Struktur

```jsx
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
      await saveCortexFile(personaId, currentFileType, editContent);
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
      const data = await resetCortexFile(personaId, currentFileType);
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
```

---

## 5. CSS-Klassen

### Bestehende Klassen (aus `Overlays.module.css`)

| Klasse | Verwendung |
|---|---|
| `.ifaceSection` | Jede der 3 Sektionen (Status, Frequenz, Dateien) |
| `.ifaceSectionTitle` | Sektions-Überschrift |
| `.ifaceCard` | Karten-Container für Settings |
| `.ifaceToggleRow` / `.ifaceToggleInfo` / `.ifaceToggleLabel` / `.ifaceToggleHint` | Cortex-Enable-Toggle |
| `.ifaceFieldHint` | Beschreibungstext unter Überschriften |
| `.ifaceInfoNote` | Hinweis unter Frequenz-Selector |
| `.tabBar` / `.tab` / `.activeTab` | Tab-Leiste für Datei-Auswahl |
| `.textarea` | Textarea im Edit-Modus |
| `.emptyText` | Leerer-Zustand-Text |
| `.centeredContent` | Spinner-Container beim Laden |
| `.statusArea` / `.error` | Fehlermeldungs-Box |

### Neue Klassen (hinzuzufügen)

```css
/* ═══ Cortex Overlay – Frequenz-Selector (Segmented Control) ═══ */

.cortexFrequencySelector {
  display: flex;
  gap: 0;
  border: 1px solid var(--overlay-border-color, rgba(0, 0, 0, 0.12));
  border-radius: var(--radius-md, 8px);
  overflow: hidden;
  margin: 12px 0 8px;
}

.cortexFrequencyOption {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 12px 8px;
  border: none;
  background: transparent;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
  color: var(--overlay-text-secondary, #666);
  position: relative;
}

/* Vertikale Trennlinie zwischen Optionen */
.cortexFrequencyOption + .cortexFrequencyOption {
  border-left: 1px solid var(--overlay-border-color, rgba(0, 0, 0, 0.12));
}

.cortexFrequencyOption:hover {
  background: rgba(99, 102, 241, 0.05);
}

/* Aktive Auswahl */
.cortexFrequencyActive {
  background: rgba(99, 102, 241, 0.1) !important;
  color: var(--overlay-accent, #6366f1);
}

.cortexFrequencyActive::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--overlay-accent, #6366f1);
  border-radius: 3px 3px 0 0;
}

.cortexFrequencyEmoji {
  font-size: 20px;
  line-height: 1;
}

.cortexFrequencyLabel {
  font-size: 13px;
  font-weight: 600;
}

.cortexFrequencyPercent {
  font-size: 11px;
  opacity: 0.7;
}

/* ═══ Cortex Overlay – Persona Badge ═══ */

.cortexPersonaBadge {
  font-size: 11px;
  font-weight: 500;
  text-transform: none;
  letter-spacing: 0;
  background: rgba(99, 102, 241, 0.1);
  color: var(--overlay-accent, #6366f1);
  padding: 2px 8px;
  border-radius: 12px;
  margin-left: auto;
}

/* ═══ Cortex Overlay – File View ═══ */

.cortexFileView {
  background: var(--overlay-input-bg, rgba(0, 0, 0, 0.03));
  border: 1px solid var(--overlay-border-color, rgba(0, 0, 0, 0.08));
  border-radius: var(--radius-md, 8px);
  padding: 16px;
}

.cortexFileContent {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
  max-height: 300px;
  overflow-y: auto;
  color: var(--overlay-text, #1a1a1a);
}

.cortexFileActions {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
  gap: 8px;
}

/* ═══ Cortex Overlay – Edit Area ═══ */

.cortexEditArea {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.cortexEditArea .textarea {
  min-height: 200px;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 13px;
  line-height: 1.6;
}

.cortexEditActions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

/* ═══ Cortex Overlay – Empty State ═══ */

.cortexEmptyState {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 24px 16px;
  text-align: center;
}

/* ═══ Dark Mode ═══ */

:root[data-theme="dark"] .cortexFrequencyOption {
  color: rgba(255, 255, 255, 0.6);
}

:root[data-theme="dark"] .cortexFrequencyActive {
  background: rgba(99, 102, 241, 0.2) !important;
  color: #818cf8;
}

:root[data-theme="dark"] .cortexPersonaBadge {
  background: rgba(99, 102, 241, 0.2);
}
```

---

## 6. Tab-Design (unverändert)

### Verhalten

Tab-Leiste nutzt existierende `.tabBar` / `.tab` / `.activeTab` Klassen. 3 Tabs, horizontal.

```
┌──────────────────────────────────────────────────┐
│  [🧠 Memory]  [💜 Seele]  [💞 Beziehung]        │
└──────────────────────────────────────────────────┘
```

### Tab-Wechsel-Logik

1. Benutzer klickt auf Tab → `handleTabChange(tabKey)`
2. Falls `editing === true`: Bearbeitung wird **verworfen** (kein Auto-Save)
3. `activeTab` wird gesetzt, `editing` auf `false`
4. Content wird aus dem bereits geladenen `files`-Objekt gelesen (kein API-Call)

### Datei-Mapping

| Tab-Key | `fileType` (API) | Datei auf Server |
|---|---|---|
| `memory` | `memory` | `cortex/{persona_id}/memory.md` |
| `soul` | `soul` | `cortex/{persona_id}/soul.md` |
| `relationship` | `relationship` | `cortex/{persona_id}/relationship.md` |

---

## 7. Textarea-Editing-Flow (unverändert)

### Zustände pro Tab

```
┌─────────────────────┐       ┌─────────────────────┐
│   READ-ONLY VIEW    │──────▶│    EDIT MODE         │
│                     │ Click  │                     │
│  <pre> mit Content  │ Edit   │  <textarea>         │
│  [✏️ Bearbeiten]    │       │  [Abbrechen]        │
│                     │       │  [Zurücksetzen]     │
│                     │◀──────│  [Datei speichern]  │
│                     │ Save/  │                     │
│                     │ Cancel │                     │
└─────────────────────┘       └─────────────────────┘
        │                              │
        │ (content === '')              │
        ▼                              │
┌─────────────────────┐               │
│   EMPTY STATE       │───────────────┘
│                     │  Click Edit
│  "Datei ist leer..."│
│  [✏️ Manuell bearb.]│
└─────────────────────┘
```

---

## 8. Error Handling (unverändert)

| Fehler | Auslöser | UI-Reaktion |
|---|---|---|
| Dateien laden fehlgeschlagen | `getCortexFiles()` rejected | `error`-State |
| Datei speichern fehlgeschlagen | `saveCortexFile()` rejected | `error`-State, Textarea bleibt offen |
| Datei zurücksetzen fehlgeschlagen | `resetCortexFile()` rejected | `error`-State |
| Keine Persona ausgewählt | `personaId` ist null | Spezial-Empty-State |

Error wird bei Tab-Wechsel, neuem Speicher-Versuch und beim Overlay-Öffnen zurückgesetzt.

---

## 9. Wire-Up: Overlay-Registrierung (unverändert)

### Schritt 1: Export in `index.js`

```js
export { default as CortexOverlay } from './CortexOverlay';
```

### Schritt 2: Overlay-Hook in `ChatPage.jsx`

```jsx
const cortex = useOverlay();
// ...
<CortexOverlay open={cortex.isOpen} onClose={cortex.close} />
```

### Schritt 3: Header-Button umbenennen

```jsx
// Props: onOpenMemory → onOpenCortex
// Button-Text: "Erinnern" → "Cortex"
```

---

## 10. Overlay-Wireframe (ASCII) — NEU

```
┌──────────────────────────────────────────────────────┐
│  🧬 Cortex                                      [✕] │  ← OverlayHeader
├──────────────────────────────────────────────────────┤
│                                                      │  ← OverlayBody
│  STATUS                                              │
│  ┌──────────────────────────────────────────────┐    │
│  │  Cortex-System                         [●──] │    │  ← Toggle
│  │  Cortex ist aktiv – Dateien werden in den    │    │
│  │  Prompt eingebunden.                         │    │
│  └──────────────────────────────────────────────┘    │
│                                                      │
│  UPDATE-FREQUENZ                                     │
│  ┌──────────────────────────────────────────────┐    │
│  │  Wie oft soll Cortex seine Dateien            │    │
│  │  aktualisieren?                               │    │
│  │                                               │    │
│  │  ┌──────────┬──────────┬──────────┐          │    │
│  │  │  🔥      │  ⚡      │  🌙      │          │    │  ← Segmented Control
│  │  │ Häufig   │ [Mittel] │ Selten   │          │    │
│  │  │  50%     │  75%     │  95%     │          │    │
│  │  └──────────┴──────────┴──────────┘          │    │
│  │                                               │    │
│  │  Update alle 75% des Kontexts                 │    │  ← Dynamischer Hint
│  └──────────────────────────────────────────────┘    │
│                                                      │
│  CORTEX-DATEIEN                        [Persona-Name]│
│  [🧠 Memory] [💜 Seele] [💞 Beziehung]              │  ← Tabs
│  ┌──────────────────────────────────────────────┐    │
│  │  # Gedächtnis                                │    │
│  │                                              │    │
│  │  - User mag Musik                            │    │  ← File Content
│  │  - Letzte Unterhaltung: Reisen               │    │
│  │  - ...                                       │    │
│  │                                              │    │
│  │                        [✏️ Bearbeiten]       │    │
│  └──────────────────────────────────────────────┘    │
│                                                      │
├──────────────────────────────────────────────────────┤
│                   [Zurücksetzen]  [Speichern]        │  ← OverlayFooter
└──────────────────────────────────────────────────────┘
```

---

## 11. Implementierungshinweise

### Design-Pattern-Konsistenz

- Exakt gleiche Overlay-Shell wie `ApiSettingsOverlay`: Overlay → OverlayHeader → OverlayBody → OverlayFooter
- `width="580px"`
- Settings-Sync-Pattern: `useEffect` auf `open` → lokalen State befüllen → Footer "Speichern" → `setMany()` + `onClose()`
- Tab-Pattern wie `CustomSpecsOverlay`
- Textarea-Pattern wie `MemoryOverlay`

### Settings-Keys (vereinfacht)

Neue Keys im Settings-System — in `defaults.json` registrieren:

```json
{
  "cortexEnabled": true,
  "cortexFrequency": "medium"
}
```

**Nur 2 Keys** statt der alten 4 (cortexEnabled + cortexTier1/2/3).

### Reihenfolge der Implementierung

1. `cortexApi.js` Service-Datei erstellen
2. `CortexOverlay.jsx` Component erstellen
3. Neue CSS-Klassen zu `Overlays.module.css` hinzufügen
4. `index.js` Export aktualisieren
5. `ChatPage.jsx` umverdrahten (Memory → Cortex)
6. `Header.jsx` Button-Label und Props umbenennen
7. Settings-Defaults in `defaults.json` ergänzen
8. `MemoryOverlay.jsx` als deprecated markieren

---

## 12. Abhängigkeiten

| Abhängigkeit | Richtung | Details |
|-------------|----------|---------|
| **Schritt 2C** | ← | API-Endpoints für Cortex-Dateien |
| **Schritt 3B** | ← | `cortex_settings.json` Struktur (`enabled`, `frequency`) |
| **Schritt 5B** | → | `cortexApi.js` Service (hier definiert, dort detailliert) |
| **Schritt 5C** | → | ChatPage/Header Wiring |
