# Schritt 1B: Frontend Memory-System entfernen

> **Ziel:** Alle Memory-bezogenen UI-Komponenten, Services, States und CSS aus beiden Frontends (React + Legacy) vollständig entfernen. Die Memory-UI wird in **Schritt 5** durch das neue `CortexOverlay` ersetzt.

---

## Übersicht aller betroffenen Dateien

### React Frontend (`frontend/src/`)

| # | Datei | Aktion | Beschreibung |
|---|-------|--------|-------------|
| 1 | `features/overlays/MemoryOverlay.jsx` | **LÖSCHEN** | Komplette Datei (326 Zeilen) – Memory-Verwaltungs-Overlay |
| 2 | `services/memoryApi.js` | **LÖSCHEN** | Komplette Datei (36 Zeilen) – Alle `/api/memory/*` Aufrufe |
| 3 | `features/overlays/index.js` | BEARBEITEN | Export `MemoryOverlay` entfernen |
| 4 | `features/chat/ChatPage.jsx` | BEARBEITEN | Import, Overlay-Hook, Header-Prop und JSX entfernen |
| 5 | `features/chat/components/Header/Header.jsx` | BEARBEITEN | Memory-Button, Import, State, Effect und Logik entfernen |
| 6 | `features/chat/components/Header/Header.module.css` | BEARBEITEN | Kompletten Memory-Button CSS-Block entfernen (Zeilen 92–175) |
| 7 | `features/overlays/Overlays.module.css` | BEARBEITEN | `/* Memory List */` CSS-Block entfernen (Zeilen 1138–1245) |
| 8 | `context/SessionContext.jsx` | BEARBEITEN | `lastMemoryMessageId` State + alle Setter entfernen |
| 9 | `features/overlays/DebugOverlay.jsx` | BEARBEITEN | Memory-Import und Memory-spezifische Debug-Rows entfernen |
| 10 | `features/chat/components/MessageList/MessageBubble.jsx` | BEARBEITEN | `memorized` Prop und CSS-Klasse entfernen |
| 11 | `features/chat/components/MessageList/MessageList.jsx` | BEARBEITEN | `memorized={!!msg.memorized}` Prop entfernen |
| 12 | `features/chat/components/MessageList/MessageList.module.css` | BEARBEITEN | `.memorized` CSS-Block entfernen |
| 13 | `features/chat/components/MessageList/PromptInfoOverlay.jsx` | BEARBEITEN | `memoryEst`/`memoryScaled` Berechnung und UI-Block entfernen |

### Legacy Frontend (`src/static/`, `src/templates/`)

| # | Datei | Aktion | Beschreibung |
|---|-------|--------|-------------|
| 14 | `static/js/modules/MemoryManager.js` | **LÖSCHEN** | Komplette Datei (733 Zeilen) – Memory-Klasse |
| 15 | `templates/chat/_overlay_memory.html` | **LÖSCHEN** | Komplette Datei – Memory Creation + Settings Overlays |
| 16 | `static/js/chat.js` | BEARBEITEN | MemoryManager Import, Instanziierung und alle Referenzen entfernen |
| 17 | `templates/chat.html` | BEARBEITEN | `{% include '_overlay_memory.html' %}` und `window.lastMemoryMessageId` entfernen |
| 18 | `templates/chat/_header.html` | BEARBEITEN | Memory-Button und Memory-Settings-Dropdown-Item entfernen |
| 19 | `static/css/chat.css` | BEARBEITEN | Alle Memory-CSS-Blöcke entfernen (5 Bereiche) |
| 20 | `static/js/modules/SessionManager.js` | BEARBEITEN | `memoryManager`-Referenzen entfernen |
| 21 | `static/js/modules/DebugPanel.js` | BEARBEITEN | `memoryManager`-Referenzen und Memory-Debug-Zeilen entfernen |

---

## Teil 1: React Frontend

### 1.1 LÖSCHEN: `frontend/src/features/overlays/MemoryOverlay.jsx`

**Komplette Datei löschen.** 326 Zeilen, enthält:
- Memory-Liste gruppiert nach Kategorie
- CRUD-Operationen (Create/Preview/Edit/Delete/Toggle)
- Stats-Anzeige (Gesamt/Aktiv/Inaktiv)
- `memoriesEnabled` Toggle
- Alle 8 Imports aus `memoryApi.js`

```
rm frontend/src/features/overlays/MemoryOverlay.jsx
```

### 1.2 LÖSCHEN: `frontend/src/services/memoryApi.js`

**Komplette Datei löschen.** 36 Zeilen, enthält 8 API-Funktionen:
- `getMemories()` → `GET /api/memory/list`
- `createMemory()` → `POST /api/memory/create`
- `previewMemory()` → `POST /api/memory/preview`
- `updateMemory()` → `PUT /api/memory/:id`
- `deleteMemory()` → `DELETE /api/memory/:id`
- `toggleMemory()` → `PATCH /api/memory/:id/toggle`
- `checkMemoryAvailability()` → `GET /api/memory/check-availability/:sessionId`
- `getMemoryStats()` → `GET /api/memory/stats`

```
rm frontend/src/services/memoryApi.js
```

### 1.3 BEARBEITEN: `frontend/src/features/overlays/index.js`

**Entfernen (Zeile 11):**
```js
export { default as MemoryOverlay } from './MemoryOverlay';
```

### 1.4 BEARBEITEN: `frontend/src/features/chat/ChatPage.jsx`

**4 Änderungen:**

**a) Import entfernen (Zeile 34):**
```js
// Entfernen aus dem Overlay-Import-Block:
  MemoryOverlay,
```

**b) Overlay-Hook entfernen (Zeile 143):**
```js
// Entfernen:
  const memory = useOverlay();
```

**c) Header-Prop entfernen (Zeile 221):**
```js
// Entfernen:
        onOpenMemory={memory.open}
```

**d) JSX-Block entfernen (Zeilen 293–296):**
```jsx
// Entfernen:
      <MemoryOverlay
        open={memory.isOpen}
        onClose={memory.close}
      />
```

### 1.5 BEARBEITEN: `frontend/src/features/chat/components/Header/Header.jsx`

**5 Änderungen:**

**a) Import entfernen (Zeile 11):**
```js
import { checkMemoryAvailability } from '../../../../services/memoryApi';
```

**b) Prop entfernen (Zeile 58):**
```js
  onOpenMemory,
```

**c) State + Effect entfernen (Zeilen 94–115):**
```js
// Kompletten Block entfernen:
  // ── Memory availability ──
  const [memoryState, setMemoryState] = useState({ available: false, warning: false, critical: false });

  useEffect(() => {
    if (!sessionId) return;
    // ... (21 Zeilen)
  }, [sessionId]);
```

**d) Berechnete Klasse + Handler entfernen (Zeilen 117–124):**
```js
// Entfernen:
  const memoryBtnClass = [ ... ].filter(Boolean).join(' ');

  const handleMemoryClick = useCallback(() => {
    if (memoryState.available) {
      onOpenMemory?.();
    }
  }, [memoryState.available, onOpenMemory]);
```

**e) JSX: Memory-Button-Block im Header entfernen (ca. Zeilen 152–164):**
```jsx
// Entfernen:
          {/* Memory Button */}
          <button
            className={memoryBtnClass}
            onClick={handleMemoryClick}
            title={...}
          >
            Erinnern
          </button>
```

### 1.6 BEARBEITEN: `frontend/src/features/chat/components/Header/Header.module.css`

**Kompletten Memory-Button CSS-Block entfernen (Zeilen 92–175):**
```css
/* Entfernen: */
/* ── Memory Button ── */
.memoryBtn { ... }
.memoryBtn:hover:not(.memoryDisabled) { ... }
.memoryDisabled { ... }
.memoryWarning { ... }
.memoryCritical { ... }
@keyframes memoryContextPulse { ... }
@keyframes memoryContextCriticalPulse { ... }
:global(body.dark-mode) .memoryBtn { ... }
:global(body.dark-mode) .memoryBtn:hover:not(.memoryDisabled) { ... }
:global(body.dark-mode) .memoryDisabled { ... }
:global(body.dark-mode) .memoryWarning { ... }
:global(body.dark-mode) .memoryCritical { ... }
```

### 1.7 BEARBEITEN: `frontend/src/features/overlays/Overlays.module.css`

**Memory List CSS-Block entfernen (Zeilen 1138–1245):**
```css
/* Entfernen: */
/* ── Memory List ── */
.statsBar { ... }
.categoryGroups { ... }
.categoryGroup { ... }
.categoryHeader { ... }
.categoryHeader:hover { ... }
.listHeader { ... }
.memoryList { ... }
.memoryItem { ... }
.memoryItem:last-child { ... }
.memoryContent { ... }
.memoryContent p { ... }
.inactive { ... }
.memoryActions { ... }
.editArea { ... }
.editActions { ... }
```

> **Achtung:** `.statsBar`, `.listHeader`, `.categoryGroups` etc. prüfen ob sie ausschließlich von MemoryOverlay genutzt werden. Falls ja → entfernen. Falls von anderen Overlays mitgenutzt → behalten.

### 1.8 BEARBEITEN: `frontend/src/context/SessionContext.jsx`

**Alle `lastMemoryMessageId`-Referenzen entfernen:**

**a) State-Deklaration (Zeile 16):**
```js
const [lastMemoryMessageId, setLastMemoryMessageId] = useState(null);
```

**b) Setter-Aufrufe in `initSession` (Zeilen 66, 83):**
```js
setLastMemoryMessageId(sessionData.last_memory_message_id || null);
```

**c) Setter-Aufruf in `switchSession` (Zeile 174):**
```js
setLastMemoryMessageId(data.last_memory_message_id || null);
```

**d) Context-Value (Zeile 272):**
```js
    lastMemoryMessageId,
```

### 1.9 BEARBEITEN: `frontend/src/features/overlays/DebugOverlay.jsx`

**3 Änderungen:**

**a) Import entfernen (Zeile 13):**
```js
import { checkMemoryAvailability } from '../../services/memoryApi';
```

**b) `refreshInfo` Callback umschreiben (Zeilen 25–31):**
Die Funktion `refreshInfo` nutzt `checkMemoryAvailability` – entweder komplett entfernen oder durch eine generische Debug-API ersetzen.

**c) Memory-spezifische Debug-Rows im JSX entfernen (Zeilen 100–116):**
```jsx
// Entfernen:
              {sessionInfo && !sessionInfo.error && (
                <>
                  <div className={styles.debugRow}>
                    <span>Last Memory Marker:</span>
                    <code>{sessionInfo.last_marker || '-'}</code>
                  </div>
                  <div className={styles.debugRow}>
                    <span>User msgs since marker:</span>
                    <code>{sessionInfo.user_messages_since_marker ?? '-'}</code>
                  </div>
                  <div className={styles.debugRow}>
                    <span>Memory Available:</span>
                    <code>{sessionInfo.available ? '✅' : '❌'}</code>
                  </div>
                  <div className={styles.debugRow}>
                    <span>Context Ratio:</span>
                    <code>{sessionInfo.context_ratio ?? '-'}</code>
                  </div>
                </>
              )}
```

### 1.10 BEARBEITEN: `frontend/src/features/chat/components/MessageList/MessageBubble.jsx`

**2 Änderungen:**

**a) Prop entfernen (Zeile 21):**
```js
  memorized = false,
```

**b) CSS-Klasse aus bubbleClasses entfernen (Zeile 46):**
```js
// Entfernen:
    memorized ? styles.memorized : '',
```

### 1.11 BEARBEITEN: `frontend/src/features/chat/components/MessageList/MessageList.jsx`

**Prop entfernen (Zeile 90):**
```jsx
// Entfernen:
                memorized={!!msg.memorized}
```

### 1.12 BEARBEITEN: `frontend/src/features/chat/components/MessageList/MessageList.module.css`

**Memorized CSS-Block entfernen (Zeilen 154–166):**
```css
/* Entfernen: */
.memorized {
  border-color: rgba(0, 160, 253, 0.6) !important;
  border-width: 1.5px !important;
  position: relative;
}

.memorized::after {
  content: 'in-memory';
  position: absolute;
  bottom: 8px;
  font-size: 12px;
  font-weight: 600;
  color: rgba(0, 160, 253, 0.6);
}
```

### 1.13 BEARBEITEN: `frontend/src/features/chat/components/MessageList/PromptInfoOverlay.jsx`

**Memory-Token-Anzeige entfernen:**

**a) Variable entfernen (Zeile 20):**
```js
  const memoryEst = stats.memory_est || 0;
```

**b) Berechnung entfernen (Zeile 28):**
```js
  const memoryScaled = Math.round(memoryEst * scale);
```

**c) JSX-Block entfernen (Zeilen 103–107):**
```jsx
// Entfernen:
              {memoryScaled > 0 && (
                <div className={styles.statItem}>
                  <span className={styles.statName}>Memory</span>
                  <span className={styles.statValue}>{memoryScaled.toLocaleString()} Token</span>
                </div>
              )}
```

---

## Teil 2: Legacy Frontend

### 2.1 LÖSCHEN: `src/static/js/modules/MemoryManager.js`

**Komplette Datei löschen.** 733 Zeilen, enthält:
- `class MemoryManager` mit allen DOM-Bindings (`memory-btn`, `memory-overlay`, etc.)
- `checkMemoryAvailability()` → Polling des `/api/memory/check-availability` Endpoints
- `createMemory()` / `saveMemory()` → Preview + Create Flow
- `openMemorySettings()` / `loadMemories()` / `renderMemories()` → Settings-Overlay
- `toggleMemory()` / `editMemory()` / `deleteMemory()` → CRUD
- `markMemorizedBubbles()` → DOM-Manipulation für "in-memory" Badge
- `updateContextLimitHighlight()` → Warning/Critical Pulse-Animation

```
rm src/static/js/modules/MemoryManager.js
```

### 2.2 LÖSCHEN: `src/templates/chat/_overlay_memory.html`

**Komplette Datei löschen.** Enthält zwei Overlays:
- `#memory-creation-overlay` – Loading-State + Preview-Textarea + Save/Retry/Cancel Buttons
- `#memory-overlay` – Settings mit Toggle, Memory-Liste, Counter

```
rm src/templates/chat/_overlay_memory.html
```

### 2.3 BEARBEITEN: `src/static/js/chat.js`

**5 Änderungen:**

**a) Import entfernen (Zeile 11):**
```js
import { MemoryManager } from './modules/MemoryManager.js';
```

**b) Instanziierung entfernen (Zeile 28):**
```js
this.memory = new MemoryManager();
```

**c) DebugPanel-Übergabe anpassen (Zeile 33):**
```js
// Vorher:
this.debugPanel = new DebugPanel(this.memory);
// Nachher:
this.debugPanel = new DebugPanel();
```

**d) SessionManager-Sharing entfernen (Zeilen 46–48):**
```js
// Entfernen:
        // Share MessageManager und MemoryManager mit SessionManager für Soft-Reload
        this.sessions.memoryManager = this.memory;
```

**e) Message-Sent-Callback entfernen (Zeilen 50–51):**
```js
// Entfernen:
        // Set message sent callback für Memory
        this.messages.setMessageSentCallback(() => this.memory.onMessageSent());
```

**f) Session-List Click-Handler: Memory-Zeile entfernen (Zeile 163):**
```js
// Entfernen:
                this.memory.onSessionChange();
```

### 2.4 BEARBEITEN: `src/templates/chat.html`

**2 Änderungen:**

**a) Include entfernen (Zeile 62):**
```html
    {% include 'chat/_overlay_memory.html' %}
```

**b) JavaScript-Variable entfernen (Zeile 88):**
```html
        window.lastMemoryMessageId = {% if last_memory_message_id %}{{ last_memory_message_id }}{% else %}null{% endif %};
```

### 2.5 BEARBEITEN: `src/templates/chat/_header.html`

**2 Änderungen:**

**a) Memory-Button entfernen (Zeilen 25–28):**
```html
            <!-- Memory Button -->
            <button class="memory-btn disabled" id="memory-btn" title="Erinnerung erstellen (ab 3 Nachrichten)">
                Erinnern
            </button>
```

**b) Memory-Settings Dropdown-Item entfernen (Zeilen 73–75):**
```html
                    <button class="dropdown-item" id="memory-settings-btn">
                        Erinnerungen
                    </button>
```

### 2.6 BEARBEITEN: `src/static/css/chat.css`

**5 CSS-Bereiche entfernen:**

| Bereich | Zeilen (ca.) | Inhalt |
|---------|-------------|--------|
| Memory Button (dark-mode) | 192–220 | `body.dark-mode .memory-btn` + Varianten |
| Memory Button (light-mode) | 1054–1185 | `.memory-btn`, `.disabled`, `.creating`, Animationen, `.memory-icon` |
| Memory Creation Overlay | 1248–1370 | `.memory-creation-overlay`, `.memory-state`, `.memory-loading-spinner`, `.memory-preview-textarea` |
| Memorized Bubbles | 2510–2542 | `.message-bubble.memorized`, `::after` mit "in-memory" Label |
| Memory Overlay | 3797–4060+ | `.memory-controls`, `.memory-counter`, `.memories-list`, `.memory-item`, `.memory-toggle`, `.memory-edit-*`, `.memory-delete-*` |

### 2.7 BEARBEITEN: `src/static/js/modules/SessionManager.js`

**3 Zeilen entfernen:**

```js
// Zeile 16 – Entfernen:
        this.memoryManager = null;  // Wird von ChatApp gesetzt

// Zeilen 493–495 – Entfernen:
        // 6. Memory-Manager über Session-Wechsel informieren
        if (this.memoryManager) {
            this.memoryManager.onSessionChange();
        }
```

### 2.8 BEARBEITEN: `src/static/js/modules/DebugPanel.js`

**Alle Memory-Referenzen entfernen:**

- Zeile 7: Constructor-Parameter `memoryManager` entfernen
- Zeile 8: `this.memoryManager = memoryManager;` entfernen  
- Zeilen 42–88: Komplett "Memory Button State Buttons" Sektion entfernen
- Zeile 148: `window.lastMemoryMessageId` Debug-Zeile entfernen
- Zeilen 155–163: Memory-Availability-Check im Debug-Refresh entfernen

---

## UI-Elemente die verschwinden

### React Frontend
| Element | Position | Beschreibung |
|---------|----------|-------------|
| **"Erinnern"-Button** | Header (rechts) | Blauer Button mit Warning/Critical Pulse-Animation |
| **MemoryOverlay** | Overlay | Erinnerungen verwalten (Liste, Toggle, CRUD, Stats-Bar) |
| **"in-memory" Badge** | Chat-Bubbles | Blaue Umrandung + "in-memory" Label auf memorized Messages |
| **Memory-Token-Zeile** | PromptInfoOverlay | "Memory: X Token" in der Token-Aufschlüsselung |
| **Memory Debug-Rows** | DebugOverlay | Last Memory Marker, User msgs, Available, Context Ratio |

### Legacy Frontend
| Element | Position | Beschreibung |
|---------|----------|-------------|
| **"Erinnern"-Button** | Header (rechts) | Memory-Button mit disabled/creating/warning/critical States |
| **Memory Creation Overlay** | Overlay | Loading-Spinner → Textarea-Preview → Save/Retry/Cancel |
| **Memory Settings Overlay** | Overlay | Toggle + Memory-Liste mit Edit/Delete/Toggle pro Item |
| **"Erinnerungen" Menüeintrag** | Settings-Dropdown | Dropdown-Item im Settings-Menü |
| **"in-memory" Badge** | Chat-Bubbles | Blaue Umrandung + "in-memory" Label |
| **Memory Debug-Buttons** | Debug Panel | Memory-State-Test-Buttons + Availability-Check |

---

## Reihenfolge der Entfernung

### Phase 1: Dateien löschen (kein Refactoring nötig)
1. `frontend/src/features/overlays/MemoryOverlay.jsx` löschen
2. `frontend/src/services/memoryApi.js` löschen
3. `src/static/js/modules/MemoryManager.js` löschen
4. `src/templates/chat/_overlay_memory.html` löschen

### Phase 2: React-Imports + Referenzen bereinigen
5. `frontend/src/features/overlays/index.js` → Export entfernen
6. `frontend/src/features/chat/ChatPage.jsx` → Import, Hook, Prop, JSX entfernen
7. `frontend/src/features/chat/components/Header/Header.jsx` → Memory-Button komplett entfernen
8. `frontend/src/context/SessionContext.jsx` → `lastMemoryMessageId` entfernen
9. `frontend/src/features/overlays/DebugOverlay.jsx` → Memory-Referenzen entfernen
10. `frontend/src/features/chat/components/MessageList/MessageBubble.jsx` → `memorized` Prop entfernen
11. `frontend/src/features/chat/components/MessageList/MessageList.jsx` → `memorized` Prop entfernen
12. `frontend/src/features/chat/components/MessageList/PromptInfoOverlay.jsx` → Memory-Token entfernen

### Phase 3: Legacy-Imports + Referenzen bereinigen
13. `src/static/js/chat.js` → MemoryManager Import + alle Referenzen entfernen
14. `src/templates/chat.html` → Include + `window.lastMemoryMessageId` entfernen
15. `src/templates/chat/_header.html` → Memory-Button + Dropdown-Item entfernen
16. `src/static/js/modules/SessionManager.js` → `memoryManager`-Referenzen entfernen
17. `src/static/js/modules/DebugPanel.js` → Memory-Referenzen entfernen

### Phase 4: CSS aufräumen
18. `frontend/src/features/chat/components/Header/Header.module.css` → Memory-Button CSS entfernen
19. `frontend/src/features/overlays/Overlays.module.css` → Memory-List CSS entfernen
20. `frontend/src/features/chat/components/MessageList/MessageList.module.css` → `.memorized` entfernen
21. `src/static/css/chat.css` → Alle 5 Memory-CSS-Bereiche entfernen

### Phase 5: Validierung
22. `npm run build` im `frontend/`-Verzeichnis → Build muss fehlerfrei durchlaufen
23. Manueller Check: Keine `memory`/`Memory`-Referenzen mehr in `frontend/src/`
24. Manueller Check: Keine `MemoryManager`-Referenzen mehr in `src/static/js/`

---

## Was ersetzt die Memory-UI?

> **Schritt 5 (CortexOverlay)** führt ein neues `CortexOverlay` ein, das die Rolle des MemoryOverlay übernimmt. Der "Erinnern"-Button im Header wird durch einen neuen Cortex-Button ersetzt, der Zugang zu Cortex-Dateiverwaltung bietet.

**Bis Schritt 5:** Die Stelle des Memory-Buttons im Header bleibt leer. Es gibt **keine Zwischenlösung** – die Memory-Funktion ist nach Schritt 1B komplett deaktiviert, bis das Cortex-System sie in Schritt 5 ablöst.

---

## Hinweise

- Die `memoriesEnabled` User-Setting wird in Schritt 1A (Backend) aus `user_settings.json` / `defaults.json` entfernt
- Die `/api/memory/*` Routen werden ebenfalls in Schritt 1A entfernt
- Die `msg.memorized`-Property in Chat-History-Daten kommt vom Backend und fällt mit den Backend-Änderungen automatisch weg
- `PromptInfoOverlay`: Die `memory_est` Stats kommen aus der Prompt-Engine und fallen mit dem Backend-Removal weg – die Frontend-Anzeige sollte trotzdem entfernt werden um tote Code-Pfade zu vermeiden
