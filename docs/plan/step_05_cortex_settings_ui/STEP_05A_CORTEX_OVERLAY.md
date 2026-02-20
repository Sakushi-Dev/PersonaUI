# Schritt 5A: CortexOverlay Component

## Übersicht

Das `CortexOverlay` ersetzt das bisherige `MemoryOverlay` als zentrale Verwaltungsoberfläche für das Cortex-System. Es kombiniert **Settings-Steuerung** (Enable/Disable, Tier-Schwellwerte) mit **Datei-Verwaltung** (Lesen/Bearbeiten der drei Cortex-Markdown-Dateien).

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
| `tierThresholds` | Settings | `useSettings().get(...)` | 3 Schwellwerte (50/75/95) |
| `activeTab` | Lokal | `useState('memory')` | Aktuell sichtbarer Tab |
| `files` | Lokal (API) | `useState({})` | Datei-Inhalte von Server |
| `editContent` | Lokal | `useState('')` | Textarea-Inhalt beim Bearbeiten |
| `editing` | Lokal | `useState(false)` | Ob gerade editiert wird |
| `loading` | Lokal | `useState(true)` | Lade-Indikator |
| `saving` | Lokal | `useState(false)` | Speicher-Indikator |
| `error` | Lokal | `useState(null)` | Fehlermeldung |

### Warum Settings vs. Lokal?

- **`cortexEnabled`** und **Tier-Schwellwerte** → `useSettings()`, weil sie serverseitig persistiert werden und von der PromptEngine gelesen werden müssen
- **File-Inhalte** → Lokal + API-Calls, weil die Dateien per REST geladen/gespeichert werden (nicht Teil des Settings-Systems)
- **UI-State** (activeTab, editing, etc.) → Rein lokal, ephemer

---

## 3. API-Integration

### Benötigte Endpoints (aus Step 6)

```
GET  /api/cortex/files?persona_id={id}
     → { success: true, files: { memory: "...", soul: "...", relationship: "..." }, persona_name: "..." }

PUT  /api/cortex/files
     Body: { persona_id, file_type: "memory"|"soul"|"relationship", content: "..." }
     → { success: true }

POST /api/cortex/files/reset
     Body: { persona_id, file_type: "memory"|"soul"|"relationship" }
     → { success: true, content: "..." }  // gibt Default-Inhalt zurück
```

### Service-Datei: `frontend/src/services/cortexApi.js`

```js
// ── Cortex API Service ──

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
import Slider from '../../components/Slider/Slider';
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

// ── Tier-Defaults & Constraints ──
const TIER_DEFAULTS = { tier1: 50, tier2: 75, tier3: 95 };
const TIER_MIN = 5;
const TIER_MAX = 99;
const TIER_STEP = 5;
const TIER_GAP = 10;

export default function CortexOverlay({ open, onClose }) {
  const { personaId, character } = useSession();
  const { get, setMany } = useSettings();

  // ── Settings State (synced from useSettings on open) ──
  const [cortexEnabled, setCortexEnabled] = useState(true);
  const [tiers, setTiers] = useState({ ...TIER_DEFAULTS });

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
    setTiers({
      tier1: parseInt(get('cortexTier1', '50'), 10),
      tier2: parseInt(get('cortexTier2', '75'), 10),
      tier3: parseInt(get('cortexTier3', '95'), 10),
    });

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
  // Tier Validation
  // ══════════════════════════════════════════
  const updateTier = useCallback((key, rawValue) => {
    setTiers((prev) => {
      const next = { ...prev, [key]: rawValue };

      // Enforce: tier1 < tier2 < tier3 with minimum TIER_GAP
      if (key === 'tier1') {
        if (next.tier1 >= next.tier2 - TIER_GAP) {
          next.tier2 = Math.min(next.tier1 + TIER_GAP, TIER_MAX);
        }
        if (next.tier2 >= next.tier3 - TIER_GAP) {
          next.tier3 = Math.min(next.tier2 + TIER_GAP, TIER_MAX);
        }
      } else if (key === 'tier2') {
        if (next.tier2 <= next.tier1 + TIER_GAP) {
          next.tier1 = Math.max(next.tier2 - TIER_GAP, TIER_MIN);
        }
        if (next.tier2 >= next.tier3 - TIER_GAP) {
          next.tier3 = Math.min(next.tier2 + TIER_GAP, TIER_MAX);
        }
      } else if (key === 'tier3') {
        if (next.tier3 <= next.tier2 + TIER_GAP) {
          next.tier2 = Math.max(next.tier3 - TIER_GAP, TIER_MIN);
        }
        if (next.tier2 <= next.tier1 + TIER_GAP) {
          next.tier1 = Math.max(next.tier2 - TIER_GAP, TIER_MIN);
        }
      }

      return next;
    });
  }, []);

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
      cortexTier1: String(tiers.tier1),
      cortexTier2: String(tiers.tier2),
      cortexTier3: String(tiers.tier3),
    });
    onClose();
  }, [cortexEnabled, tiers, setMany, onClose]);

  // ══════════════════════════════════════════
  // Reset Settings (Footer "Zurücksetzen")
  // ══════════════════════════════════════════
  const handleResetSettings = useCallback(() => {
    setCortexEnabled(true);
    setTiers({ ...TIER_DEFAULTS });
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

        {/* ═══ Section: Tier-Konfiguration ═══ */}
        <div className={styles.ifaceSection}>
          <h3 className={styles.ifaceSectionTitle}>Aktivierungsstufen</h3>
          <div className={styles.ifaceCard}>
            <div className={styles.ifaceFieldGroup}>
              <span className={styles.ifaceFieldLabel}>Tier 1 – Memory</span>
              <span className={styles.ifaceFieldHint}>
                Ab diesem Schwellwert wird memory.md in den Prompt geladen
              </span>
              <Slider
                label="Tier 1"
                value={tiers.tier1}
                onChange={(v) => updateTier('tier1', Math.round(v))}
                min={TIER_MIN}
                max={TIER_MAX}
                step={TIER_STEP}
                displayValue={`${tiers.tier1}%`}
              />
            </div>

            <div className={styles.ifaceDivider} />

            <div className={styles.ifaceFieldGroup}>
              <span className={styles.ifaceFieldLabel}>Tier 2 – Seele</span>
              <span className={styles.ifaceFieldHint}>
                Ab diesem Schwellwert wird zusätzlich soul.md geladen
              </span>
              <Slider
                label="Tier 2"
                value={tiers.tier2}
                onChange={(v) => updateTier('tier2', Math.round(v))}
                min={TIER_MIN}
                max={TIER_MAX}
                step={TIER_STEP}
                displayValue={`${tiers.tier2}%`}
              />
            </div>

            <div className={styles.ifaceDivider} />

            <div className={styles.ifaceFieldGroup}>
              <span className={styles.ifaceFieldLabel}>Tier 3 – Beziehung</span>
              <span className={styles.ifaceFieldHint}>
                Ab diesem Schwellwert wird zusätzlich relationship.md geladen
              </span>
              <Slider
                label="Tier 3"
                value={tiers.tier3}
                onChange={(v) => updateTier('tier3', Math.round(v))}
                min={TIER_MIN}
                max={TIER_MAX}
                step={TIER_STEP}
                displayValue={`${tiers.tier3}%`}
              />
            </div>

            {/* Tier-Visualisierung */}
            <div className={styles.cortexTierBar}>
              <div className={styles.cortexTierSegment} style={{ width: `${tiers.tier1}%` }} />
              <div className={styles.cortexTierSegment} style={{ width: `${tiers.tier2 - tiers.tier1}%` }} />
              <div className={styles.cortexTierSegment} style={{ width: `${tiers.tier3 - tiers.tier2}%` }} />
              <div className={styles.cortexTierSegment} style={{ width: `${100 - tiers.tier3}%` }} />
            </div>

            <div className={styles.ifaceInfoNote}>
              Tier 1 &lt; Tier 2 &lt; Tier 3 – Mindestabstand: {TIER_GAP}%
            </div>
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

Folgende existierende Klassen werden direkt wiederverwendet:

| Klasse | Verwendung |
|---|---|
| `.ifaceSection` | Jede der 3 Sektionen (Status, Tiers, Dateien) |
| `.ifaceSectionTitle` | Sektions-Überschrift |
| `.ifaceCard` | Karten-Container für Settings |
| `.ifaceToggleRow` / `.ifaceToggleInfo` / `.ifaceToggleLabel` / `.ifaceToggleHint` | Cortex-Enable-Toggle |
| `.ifaceFieldGroup` / `.ifaceFieldLabel` / `.ifaceFieldHint` | Slider-Felder pro Tier |
| `.ifaceDivider` | Trennlinie zwischen Slider-Feldern |
| `.ifaceInfoNote` | Hinweis unter Tier-Karte |
| `.tabBar` / `.tab` / `.activeTab` | Tab-Leiste für Datei-Auswahl |
| `.textarea` | Textarea im Edit-Modus |
| `.emptyText` | Leerer-Zustand-Text |
| `.centeredContent` | Spinner-Container beim Laden |
| `.statusArea` / `.error` | Fehlermeldungs-Box |

### Neue Klassen (hinzuzufügen)

```css
/* ── Cortex Overlay – Tier Bar ── */

.cortexTierBar {
  display: flex;
  height: 8px;
  border-radius: 4px;
  overflow: hidden;
  margin: 12px 0 4px;
  background: rgba(0, 0, 0, 0.06);
}

.cortexTierSegment:nth-child(1) {
  background: var(--color-success, #22c55e);
  opacity: 0.5;
}

.cortexTierSegment:nth-child(2) {
  background: var(--color-warning, #f59e0b);
  opacity: 0.6;
}

.cortexTierSegment:nth-child(3) {
  background: var(--color-danger, #ef4444);
  opacity: 0.6;
}

.cortexTierSegment:nth-child(4) {
  background: transparent;
}

/* ── Cortex Overlay – Persona Badge ── */

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

/* ── Cortex Overlay – File View ── */

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

/* ── Cortex Overlay – Edit Area ── */

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

/* ── Cortex Overlay – Empty State ── */

.cortexEmptyState {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 24px 16px;
  text-align: center;
}

/* ── Dark Mode ── */

:root[data-theme="dark"] .cortexTierBar {
  background: rgba(255, 255, 255, 0.08);
}

:root[data-theme="dark"] .cortexPersonaBadge {
  background: rgba(99, 102, 241, 0.2);
}
```

---

## 6. Tab-Design im Detail

### Verhalten

Die Tab-Leiste verwendet die existierenden `.tabBar` / `.tab` / `.activeTab` Klassen aus `CustomSpecsOverlay`. 3 Tabs, horizontal, scrollbar bei Bedarf.

```
┌──────────────────────────────────────────────────┐
│  [🧠 Memory]  [💜 Seele]  [💞 Beziehung]        │
└──────────────────────────────────────────────────┘
```

### Tab-Wechsel-Logik

1. Benutzer klickt auf Tab → `handleTabChange(tabKey)` wird aufgerufen
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

## 7. Textarea-Editing-Flow

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

### Ablauf: Datei bearbeiten

1. User klickt **"✏️ Bearbeiten"** → `handleStartEdit()`
2. `editContent` wird mit aktuellem `files[fileType]` befüllt
3. `editing = true` → Textarea wird angezeigt
4. User bearbeitet Text in Textarea
5. **Speichern**: `handleSaveFile()` → `PUT /api/cortex/files` → bei Erfolg: `files` State updaten, `editing = false`
6. **Abbrechen**: `handleCancelEdit()` → `editing = false`, Änderungen verworfen
7. **Zurücksetzen**: `handleResetFile()` → `POST /api/cortex/files/reset` → Server liefert Default-Inhalt → `files` State updaten

### Validierung

- Kein Client-Side Markdown-Validierung (der User kann beliebigen Markdown-Text eingeben)
- Maximal-Länge wird **nicht** erzwungen (Server kann optional ein Limit prüfen)
- `saving`-Flag disabled alle Buttons während des Speichervorgangs

---

## 8. Error Handling

### Fehlerfälle und Behandlung

| Fehler | Auslöser | UI-Reaktion |
|---|---|---|
| Dateien laden fehlgeschlagen | `getCortexFiles()` rejected | `error`-State gesetzt, `.statusArea.error` angezeigt |
| Datei speichern fehlgeschlagen | `saveCortexFile()` rejected | `error`-State gesetzt, Textarea bleibt offen |
| Datei zurücksetzen fehlgeschlagen | `resetCortexFile()` rejected | `error`-State gesetzt |
| Keine Persona ausgewählt | `personaId` ist null/undefined | Spezial-Empty-State: "Keine Persona ausgewählt" |
| Netzwerkfehler | fetch failed | Generische Error-Box |

### Error-Display

```jsx
{error && (
  <div className={`${styles.statusArea} ${styles.error}`}>
    {error}
  </div>
)}
```

Verwendet die bestehenden `.statusArea.error` Klassen (rötlicher Hintergrund, roter Text).

### Error-Reset

- Error wird bei Tab-Wechsel zurückgesetzt (`handleTabChange`)
- Error wird bei neuem Speicher-/Reset-Versuch zurückgesetzt
- Error wird beim Öffnen des Overlays zurückgesetzt

---

## 9. Empty State

### Kein Persona ausgewählt

```
┌──────────────────────────────────────┐
│  🧬 Cortex                      [✕] │
│──────────────────────────────────────│
│                                      │
│  Keine Persona ausgewählt.           │
│  Bitte erstelle zuerst eine Persona. │
│                                      │
└──────────────────────────────────────┘
```

### Datei noch leer

```
┌──────────────────────────────────────┐
│  [🧠 Memory] [💜 Seele] [💞 Bezihg] │
│──────────────────────────────────────│
│                                      │
│  Diese Datei ist noch leer.          │
│  Cortex wird sie automatisch         │
│  befüllen, oder du kannst sie        │
│  manuell bearbeiten.                 │
│                                      │
│       [✏️ Manuell bearbeiten]        │
│                                      │
└──────────────────────────────────────┘
```

---

## 10. Wire-Up: Overlay-Registrierung

### Schritt 1: Export in `index.js`

```js
// frontend/src/features/overlays/index.js
export { default as CortexOverlay } from './CortexOverlay';
// MemoryOverlay Export entfernen (nach vollständiger Migration)
```

### Schritt 2: Overlay-Hook in `ChatPage.jsx`

```jsx
// In ChatPageContent():

// ERSETZE:
// const memory = useOverlay();
// DURCH:
const cortex = useOverlay();

// ... und weiter unten im JSX:

// ERSETZE:
// <MemoryOverlay open={memory.isOpen} onClose={memory.close} />
// DURCH:
<CortexOverlay open={cortex.isOpen} onClose={cortex.close} />
```

### Schritt 3: Header-Button umbenennen

In `Header.jsx`:

```jsx
// Props:
// ERSETZE: onOpenMemory
// DURCH:   onOpenCortex

// Button-Text:
// ERSETZE: "Erinnern"
// DURCH:   "Cortex"
```

In `ChatPage.jsx`:

```jsx
// Header props:
// ERSETZE: onOpenMemory={memory.open}
// DURCH:   onOpenCortex={cortex.open}
```

### Schritt 4: Import anpassen

```jsx
// ChatPage.jsx imports:
// ERSETZE: MemoryOverlay,
// DURCH:   CortexOverlay,

// Import aus overlays/index.js
import {
  // ...
  CortexOverlay,    // NEU (ersetzt MemoryOverlay)
  // ...
} from '../overlays';
```

---

## 11. Overlay-Wireframe (ASCII)

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
│  AKTIVIERUNGSSTUFEN                                  │
│  ┌──────────────────────────────────────────────┐    │
│  │  Tier 1 – Memory                             │    │
│  │  Ab diesem Schwellwert wird memory.md geladen │    │
│  │  Tier 1         ──────●──────────────  50%    │    │  ← Slider
│  │  ─────────────────────────────────────────── │    │
│  │  Tier 2 – Seele                               │    │
│  │  Ab diesem Schwellwert wird soul.md geladen   │    │
│  │  Tier 2         ────────────●────────  75%    │    │  ← Slider
│  │  ─────────────────────────────────────────── │    │
│  │  Tier 3 – Beziehung                          │    │
│  │  Ab diesem Schwellwert wird relationship.md   │    │
│  │  Tier 3         ──────────────────●──  95%    │    │  ← Slider
│  │                                               │    │
│  │  [████░░░░████░░░░████████░░]                │    │  ← Tier-Bar
│  │  Tier 1 < Tier 2 < Tier 3 – Mindestabstand 10% │  │
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

## 12. Hinweise zur Implementierung

### Design-Pattern-Konsistenz

- **Exakt** die gleiche Overlay-Shell wie `ApiSettingsOverlay`:
  - `Overlay` → `OverlayHeader` → `OverlayBody` → `OverlayFooter`
  - `width="580px"` (leicht breiter als `540px` wegen Tabs + Textarea)
- **Settings-Sync-Pattern** wie `ApiSettingsOverlay`:
  - `useEffect` auf `open` → lokalen State aus `get()` befüllen
  - Footer "Speichern" → `setMany()` aufrufen + `onClose()`
  - Footer "Zurücksetzen" → lokalen State auf Defaults setzen
- **Tab-Pattern** wie `CustomSpecsOverlay`:
  - `.tabBar` mit `.tab` / `.activeTab`
  - `activeTab` State-Variable
- **Textarea-Pattern** wie `MemoryOverlay`:
  - `.textarea` Klasse
  - Edit/Cancel/Save Flow mit separatem `editContent` State

### Settings-Keys

Neue Keys im Settings-System (müssen auch in `defaults.json` registriert werden):

```json
{
  "cortexEnabled": true,
  "cortexTier1": "50",
  "cortexTier2": "75",
  "cortexTier3": "95"
}
```

### Reihenfolge der Implementierung

1. `cortexApi.js` Service-Datei erstellen
2. `CortexOverlay.jsx` Component erstellen
3. Neue CSS-Klassen zu `Overlays.module.css` hinzufügen
4. `index.js` Export aktualisieren
5. `ChatPage.jsx` umverdrahten (Memory → Cortex)
6. `Header.jsx` Button-Label und Props umbenennen
7. Settings-Defaults in `defaults.json` ergänzen
8. `MemoryOverlay.jsx` als deprecated markieren (Entfernung in separatem Cleanup-Step)
