# Schritt 5C: ChatPage Integration

## Übersicht

Dieser Schritt verdrahtet das neue `CortexOverlay` (Schritt 5A) in die bestehende ChatPage-Architektur und ersetzt alle Memory-Referenzen. Zusätzlich wird der Cortex-Update-Indikator (aus Schritt 3B) implementiert, der subtiles visuelles Feedback gibt, wenn ein Background-Update läuft.

### Betroffene Dateien

| Aktion | Datei | Änderung |
|--------|-------|----------|
| Anpassen | `frontend/src/features/chat/ChatPage.jsx` | MemoryOverlay → CortexOverlay, State umbenennen |
| Anpassen | `frontend/src/features/chat/components/Header/Header.jsx` | „Erinnern"-Button → „Cortex"-Button, Memory-Polling entfernen |
| Anpassen | `frontend/src/features/chat/components/Header/Header.module.css` | CSS-Klassen umbenennen |
| Anpassen | `frontend/src/features/overlays/index.js` | Export austauschen |
| Anpassen | `frontend/src/features/overlays/DebugOverlay.jsx` | Memory-Debug-Felder → Cortex-Status |
| Anpassen | `frontend/src/features/chat/hooks/useMessages.js` | `cortex-update` CustomEvent dispatchen |
| Anpassen | `frontend/src/context/SessionContext.jsx` | `lastMemoryMessageId` entfernen |
| Prüfen | `frontend/src/features/chat/components/ChatInput/ContextBar.jsx` | Keine Änderung nötig |
| ENTFERNEN | `frontend/src/features/overlays/MemoryOverlay.jsx` | Wird durch CortexOverlay ersetzt |
| ENTFERNEN | `frontend/src/services/memoryApi.js` | Wird durch cortexApi.js ersetzt |

---

## 1. Ist-Zustand: Overlay-Architektur in ChatPage.jsx

### 1.1 Overlay-Pattern

Jedes Overlay in `ChatPage.jsx` folgt einem einheitlichen Pattern:

```
1. Import aus features/overlays (barrel export)
2. useOverlay() Hook → { isOpen, open, close }
3. Prop-Passing an Header (onOpen*-Callback)
4. <XyzOverlay open={x.isOpen} onClose={x.close} /> im JSX
```

**Aktueller Memory-Flow:**

```jsx
// 1. Import
import { ..., MemoryOverlay, ... } from '../overlays';

// 2. Hook
const memory = useOverlay();

// 3. Header-Prop
<Header onOpenMemory={memory.open} ... />

// 4. Render
<MemoryOverlay open={memory.isOpen} onClose={memory.close} />
```

### 1.2 useOverlay Hook

Der Hook (`frontend/src/hooks/useOverlay.js`) ist minimal:

```javascript
export function useOverlay(initialState = false) {
  const [isOpen, setIsOpen] = useState(initialState);
  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => setIsOpen(false), []);
  const toggle = useCallback(() => setIsOpen((prev) => !prev), []);
  return { isOpen, open, close, toggle };
}
```

Es wird **kein neuer Hook benötigt** — das bestehende `useOverlay` reicht für CortexOverlay.

### 1.3 Header-Anbindung (Ist-Zustand)

`Header.jsx` empfängt `onOpenMemory` als Prop und nutzt es an zwei Stellen:

1. **„Erinnern"-Button** (direkt sichtbar in der Header-Leiste):
   - Prüft `checkMemoryAvailability()` per Polling (15s Intervall)
   - Zeigt Warning/Critical-States visuell an
   - Button-Text: `Erinnern`

2. **Dropdown-Menüeintrag „Erinnerungen"**:
   - Unter dem ☰-Hamburger-Menü
   - Ruft `onOpenMemory()` auf

### 1.4 ContextBar.jsx (Keine Änderung)

Die `ContextBar` zeigt ausschließlich **Kontextlimit vs. Nachrichtenanzahl** an. Sie hat **keinen Memory-Bezug** — sie nutzt nur `totalMessageCount` und `contextLimit` aus der Settings. **Keine Änderung erforderlich.**

### 1.5 SessionContext Memory-State

`SessionContext.jsx` enthält `lastMemoryMessageId`:

```javascript
const [lastMemoryMessageId, setLastMemoryMessageId] = useState(null);
```

Wird gesetzt bei:
- `initSession()` (Zeile 66): `setLastMemoryMessageId(sessionData.last_memory_message_id || null)`
- `switchSession()` (Zeile 174): `setLastMemoryMessageId(data.last_memory_message_id || null)`

Und exponiert im Context-Value (Zeile 272): `lastMemoryMessageId`

**Wird im Cortex-System nicht mehr benötigt**, da das Tier-basierte System Nachrichten zählt statt einen Message-Marker zu verwenden.

---

## 2. ChatPage.jsx — Änderungen

### 2.1 Import-Block

**Vorher:**
```jsx
import {
  PersonaSettingsOverlay,
  InterfaceSettingsOverlay,
  ApiKeyOverlay,
  ApiSettingsOverlay,
  ServerSettingsOverlay,
  AvatarEditorOverlay,
  MemoryOverlay,
  CustomSpecsOverlay,
  UserProfileOverlay,
  QRCodeOverlay,
  AccessControlOverlay,
  DebugOverlay,
  CreditExhaustedOverlay,
  ApiWarningOverlay,
} from '../overlays';
```

**Nachher:**
```jsx
import {
  PersonaSettingsOverlay,
  InterfaceSettingsOverlay,
  ApiKeyOverlay,
  ApiSettingsOverlay,
  ServerSettingsOverlay,
  AvatarEditorOverlay,
  CortexOverlay,           // ← ersetzt MemoryOverlay
  CustomSpecsOverlay,
  UserProfileOverlay,
  QRCodeOverlay,
  AccessControlOverlay,
  DebugOverlay,
  CreditExhaustedOverlay,
  ApiWarningOverlay,
} from '../overlays';
```

### 2.2 useOverlay-Instanz umbenennen

**Vorher:**
```jsx
const memory = useOverlay();
```

**Nachher:**
```jsx
const cortex = useOverlay();
```

### 2.3 Header-Prop umbenennen

**Vorher:**
```jsx
<Header
  ...
  onOpenMemory={memory.open}
  ...
/>
```

**Nachher:**
```jsx
<Header
  ...
  onOpenCortex={cortex.open}
  ...
/>
```

### 2.4 Overlay-Render austauschen

**Vorher:**
```jsx
<MemoryOverlay
  open={memory.isOpen}
  onClose={memory.close}
/>
```

**Nachher:**
```jsx
<CortexOverlay
  open={cortex.isOpen}
  onClose={cortex.close}
/>
```

### 2.5 Cortex-Update-Indikator (neuer State + Event-Listener)

Ein neuer lokaler State innerhalb `ChatPageContent` zeigt an, ob gerade ein Cortex-Update im Hintergrund läuft:

```jsx
// ── Cortex update indicator ──
const [cortexUpdating, setCortexUpdating] = useState(false);
const cortexTimerRef = useRef(null);

useEffect(() => {
  const handleCortexUpdate = (e) => {
    setCortexUpdating(true);
    // Auto-hide nach 4 Sekunden
    clearTimeout(cortexTimerRef.current);
    cortexTimerRef.current = setTimeout(() => {
      setCortexUpdating(false);
    }, 4000);
  };

  window.addEventListener('cortex-update', handleCortexUpdate);
  return () => {
    window.removeEventListener('cortex-update', handleCortexUpdate);
    clearTimeout(cortexTimerRef.current);
  };
}, []);
```

**Render-Position:** Direkt über der `ContextBar`, als subtile Inline-Notification:

```jsx
<div style={{ position: 'relative', height: 0, zIndex: 50 }}>
  <ContextBar />
  {cortexUpdating && <CortexUpdateIndicator />}
</div>
```

### 2.6 Vollständige ChatPage.jsx (geänderte Bereiche)

```jsx
// ── ChatPage ──
// Main chat page composing all chat components

import { useEffect, useCallback, useContext, useState, useRef } from 'react';
import { useSession } from '../../hooks/useSession';
import { useSettings } from '../../hooks/useSettings';
import { useTheme } from '../../hooks/useTheme';
import { useOverlay } from '../../hooks/useOverlay';
import { UserContext } from '../../context/UserContext';
import { useMessages } from './hooks/useMessages';
import { useAfterthought } from './hooks/useAfterthought';
import { useSidebar } from './hooks/useSidebar';
import { useSwipe } from './hooks/useSwipe';

import DynamicBackground from '../../components/DynamicBackground/DynamicBackground';
import StaticBackground from '../../components/StaticBackground/StaticBackground';
import Header from './components/Header/Header';
import Sidebar from './components/Sidebar/Sidebar';
import MessageList from './components/MessageList/MessageList';
import ChatInput from './components/ChatInput/ChatInput';
import ContextBar from './components/ChatInput/ContextBar';
import CortexUpdateIndicator from './components/CortexUpdateIndicator/CortexUpdateIndicator'; // ← NEU
import Spinner from '../../components/Spinner/Spinner';
import ErrorBoundary from '../../components/ErrorBoundary/ErrorBoundary';
import AccessNotification from './components/AccessNotification/AccessNotification';
import { resolveFontFamily } from '../../utils/constants';

import {
  PersonaSettingsOverlay,
  InterfaceSettingsOverlay,
  ApiKeyOverlay,
  ApiSettingsOverlay,
  ServerSettingsOverlay,
  AvatarEditorOverlay,
  CortexOverlay,              // ← ersetzt MemoryOverlay
  CustomSpecsOverlay,
  UserProfileOverlay,
  QRCodeOverlay,
  AccessControlOverlay,
  DebugOverlay,
  CreditExhaustedOverlay,
  ApiWarningOverlay,
} from '../overlays';

import styles from './ChatPage.module.css';

// ... (ChatPage Wrapper bleibt gleich) ...

function ChatPageContent() {
  const { sessionId, personaId, character, switchPersona, switchSession, createSession } = useSession();
  const { get } = useSettings();
  // ... (Theme-Sync bleibt gleich) ...

  // ... (Core hooks: useMessages, useAfterthought, useSidebar, useSwipe – bleiben gleich) ...

  // ── Overlay hooks ──
  const personaSettings = useOverlay();
  const interfaceSettings = useOverlay();
  const apiKey = useOverlay();
  const apiSettings = useOverlay();
  const serverSettings = useOverlay();
  const avatarEditor = useOverlay();
  const cortex = useOverlay();         // ← war: memory
  const customSpecs = useOverlay();
  const userProfile = useOverlay();
  const qrCode = useOverlay();
  const accessControl = useOverlay();
  const debug = useOverlay();
  const creditExhausted = useOverlay();
  const apiWarning = useOverlay();

  // ── Cortex update indicator ──
  const [cortexUpdating, setCortexUpdating] = useState(false);
  const cortexTimerRef = useRef(null);

  useEffect(() => {
    const handleCortexUpdate = (e) => {
      setCortexUpdating(true);
      clearTimeout(cortexTimerRef.current);
      cortexTimerRef.current = setTimeout(() => {
        setCortexUpdating(false);
      }, 4000);
    };

    window.addEventListener('cortex-update', handleCortexUpdate);
    return () => {
      window.removeEventListener('cortex-update', handleCortexUpdate);
      clearTimeout(cortexTimerRef.current);
    };
  }, []);

  // ... (Callbacks bleiben gleich, außer Memory-Referenzen) ...

  return (
    <div className={styles.page} {...swipeHandlers}>
      {dynamicBg ? <DynamicBackground /> : <StaticBackground />}

      <Header
        onToggleSidebar={sidebar.toggle}
        onOpenPersonaSettings={personaSettings.open}
        onOpenInterfaceSettings={interfaceSettings.open}
        onOpenApiKey={apiKey.open}
        onOpenApiSettings={apiSettings.open}
        onOpenServerSettings={serverSettings.open}
        onOpenCortex={cortex.open}            {/* ← war: onOpenMemory={memory.open} */}
        onOpenUserProfile={userProfile.open}
        onOpenQRCode={qrCode.open}
        onOpenAccessControl={accessControl.open}
      />

      <div style={{ position: 'relative', height: 0, zIndex: 50 }}>
        <ContextBar />
        {cortexUpdating && <CortexUpdateIndicator />}
      </div>

      {/* ... Sidebar, MessageList, ChatInput bleiben gleich ... */}

      {/* ── Overlays ── */}
      {/* ... andere Overlays bleiben gleich ... */}

      <CortexOverlay                         {/* ← war: MemoryOverlay */}
        open={cortex.isOpen}
        onClose={cortex.close}
      />

      {/* ... restliche Overlays bleiben gleich ... */}
    </div>
  );
}
```

---

## 3. Header.jsx — Änderungen

### 3.1 Prop-Signatur

**Vorher:**
```jsx
export default function Header({
  onToggleSidebar,
  onOpenPersonaSettings,
  onOpenInterfaceSettings,
  onOpenApiKey,
  onOpenApiSettings,
  onOpenServerSettings,
  onOpenMemory,
  onOpenUserProfile,
  onOpenQRCode,
  onOpenAccessControl,
}) {
```

**Nachher:**
```jsx
export default function Header({
  onToggleSidebar,
  onOpenPersonaSettings,
  onOpenInterfaceSettings,
  onOpenApiKey,
  onOpenApiSettings,
  onOpenServerSettings,
  onOpenCortex,               // ← ersetzt onOpenMemory
  onOpenUserProfile,
  onOpenQRCode,
  onOpenAccessControl,
}) {
```

### 3.2 Import entfernen

**Entfernen:**
```jsx
import { checkMemoryAvailability } from '../../../../services/memoryApi';
```

Kein Ersatz-Import nötig — der Cortex-Button braucht kein Availability-Polling.

### 3.3 Memory-State + Polling entfernen

**Komplett entfernen** (Zeilen 98–116 im Ist-Zustand):

```jsx
// ── ENTFERNEN: Memory availability ──
const [memoryState, setMemoryState] = useState({ available: false, warning: false, critical: false });

useEffect(() => {
  if (!sessionId) return;
  let mounted = true;
  const check = async () => {
    try {
      const data = await checkMemoryAvailability(sessionId);
      if (mounted && data?.success) {
        setMemoryState({
          available: !!data.available,
          warning: !!data.context_limit_warning,
          critical: !!data.context_limit_critical,
        });
      }
    } catch {
      // ignore
    }
  };
  check();
  const interval = setInterval(check, 15000);
  return () => { mounted = false; clearInterval(interval); };
}, [sessionId]);

// ── ENTFERNEN: Memory button class computation ──
const memoryBtnClass = [ ... ];
const handleMemoryClick = useCallback(() => { ... }, [...]);
```

### 3.4 Cortex-Button (ersetzt Memory-Button)

Der „Erinnern"-Button wird durch einen einfacheren „Cortex"-Button ersetzt. Kein Availability-Check nötig — das CortexOverlay ist immer zugänglich:

**Vorher:**
```jsx
{/* Memory Button */}
<button
  className={memoryBtnClass}
  onClick={handleMemoryClick}
  title={memoryState.available
    ? (memoryState.critical
      ? 'Erinnerung dringend empfohlen – Kontextlimit fast erreicht!'
      : memoryState.warning
        ? 'Erinnerung empfohlen – Kontextlimit wird bald erreicht'
        : 'Erinnerung erstellen')
    : 'Erinnerung erstellen (ab 3 Nachrichten)'}
>
  Erinnern
</button>
```

**Nachher:**
```jsx
{/* Cortex Button */}
<button
  className={styles.cortexBtn}
  onClick={onOpenCortex}
  title="Cortex – Gedächtnis & Persönlichkeit"
>
  Cortex
</button>
```

**Begründung für das Entfernen des Availability-Checks:**
- Das alte Memory-System benötigte mindestens 3 Nachrichten, bevor eine Erinnerung erstellt werden konnte → daher der periodische Availability-Check
- Das Cortex-System zeigt **immer** die drei Markdown-Dateien (memory.md, soul.md, relationship.md) an — sie sind immer editierbar, auch leer
- Die Tier-basierte Aktualisierung läuft automatisch im Hintergrund — kein manuelles Triggern nötig
- **Ergebnis:** 15-Sekunden-Polling wird eliminiert → Performance-Gewinn

### 3.5 Dropdown-Menüeintrag umbenennen

**Vorher:**
```jsx
<DropdownItem label="Erinnerungen" onClick={() => { close(); onOpenMemory?.(); }} />
```

**Nachher:**
```jsx
<DropdownItem label="Cortex" onClick={() => { close(); onOpenCortex?.(); }} />
```

### 3.6 Header.jsx — Vollständiger geänderter Code

```jsx
// ── Header Component ──

import { useState, useEffect, useCallback } from 'react';
import { useSession } from '../../../../hooks/useSession';
import { useSettings } from '../../../../hooks/useSettings';
import Avatar from '../../../../components/Avatar/Avatar';
import Dropdown from '../../../../components/Dropdown/Dropdown';
import DropdownItem from '../../../../components/Dropdown/DropdownItem';
import DropdownSubmenu from '../../../../components/Dropdown/DropdownSubmenu';
import { checkApiStatus } from '../../../../services/serverApi';
// ENTFERNT: import { checkMemoryAvailability } from '../../../../services/memoryApi';
import styles from './Header.module.css';

// ── SVG Icons ──
// ... (SoundOnIcon, SoundOffIcon, QRCodeIcon bleiben identisch) ...

export default function Header({
  onToggleSidebar,
  onOpenPersonaSettings,
  onOpenInterfaceSettings,
  onOpenApiKey,
  onOpenApiSettings,
  onOpenServerSettings,
  onOpenCortex,               // ← NEU (war: onOpenMemory)
  onOpenUserProfile,
  onOpenQRCode,
  onOpenAccessControl,
}) {
  const { character, sessionId } = useSession();
  const { get, set } = useSettings();

  const charName = character?.char_name || 'PersonaUI';
  const charAvatar = character?.avatar;
  const charAvatarType = character?.avatar_type;

  // ── Sound toggle state ──
  const soundEnabled = get('notificationSound', false);
  const toggleSound = useCallback(() => {
    set('notificationSound', !soundEnabled);
  }, [soundEnabled, set]);

  // ── API Status ──
  const [apiConnected, setApiConnected] = useState(null);

  useEffect(() => {
    let mounted = true;
    const check = async () => {
      try {
        const data = await checkApiStatus();
        if (mounted) setApiConnected(!!data?.has_api_key);
      } catch {
        if (mounted) setApiConnected(false);
      }
    };
    check();
    const interval = setInterval(check, 30000);
    return () => { mounted = false; clearInterval(interval); };
  }, []);

  // ENTFERNT: Gesamter memoryState-Block + useEffect + memoryBtnClass + handleMemoryClick

  return (
    <header className={styles.header}>
      <div className={styles.headerContent}>
        {/* ── Left: Avatar + Name ── */}
        <div className={styles.left}>
          <div className={styles.characterInfo} onClick={onToggleSidebar}>
            <Avatar src={charAvatar} type={charAvatarType} name={charName} size={48} />
            <h2 className={styles.characterName}>{charName}</h2>
          </div>
        </div>

        {/* ── Center: Logo ── */}
        <div className={styles.center}>
          <div className={styles.logo}>PERSONA UI</div>
        </div>

        {/* ── Right: Actions ── */}
        <div className={styles.right}>
          {/* Cortex Button (war: Memory Button) */}
          <button
            className={styles.cortexBtn}
            onClick={onOpenCortex}
            title="Cortex – Gedächtnis & Persönlichkeit"
          >
            Cortex
          </button>

          {/* Sound Toggle */}
          <button
            className={`${styles.soundToggle} ${!soundEnabled ? styles.soundMuted : ''}`}
            onClick={toggleSound}
            title="Benachrichtigungston an/aus"
          >
            {soundEnabled ? <SoundOnIcon /> : <SoundOffIcon />}
          </button>

          {/* QR Code Button */}
          <button className={styles.qrCodeBtn} onClick={onOpenQRCode} title="QR-Code & Netzwerk-Adressen">
            <QRCodeIcon />
          </button>

          {/* API Status Indicator */}
          <div
            className={`${styles.apiStatus} ${apiConnected === true ? styles.apiConnected : apiConnected === false ? styles.apiDisconnected : ''}`}
            title={apiConnected === true ? 'Bestätigter API Zugang' : apiConnected === false ? 'API Zugang benötigt' : 'Lädt...'}
          >
            <span className={styles.statusDot} />
          </div>

          {/* Settings Dropdown */}
          <Dropdown
            trigger={<button className={styles.dropdownToggle} title="Einstellungen">☰</button>}
          >
            {(close) => (
              <>
                <DropdownItem label="Mein Profil" onClick={() => { close(); onOpenUserProfile?.(); }} />
                <DropdownItem label="Set API-Key" onClick={() => { close(); onOpenApiKey?.(); }} />
                <DropdownItem label="Cortex" onClick={() => { close(); onOpenCortex?.(); }} />
                <DropdownItem label="Persona" onClick={() => { close(); onOpenPersonaSettings?.(); }} />
                <DropdownSubmenu label="Einstellungen">
                  <DropdownItem label="Interface" onClick={() => { close(); onOpenInterfaceSettings?.(); }} />
                  <DropdownItem label="API / Chat" onClick={() => { close(); onOpenApiSettings?.(); }} />
                  <DropdownItem label="Server" onClick={() => { close(); onOpenServerSettings?.(); }} />
                  <DropdownItem label="Zugangskontrolle" onClick={() => { close(); onOpenAccessControl?.(); }} />
                </DropdownSubmenu>
              </>
            )}
          </Dropdown>
        </div>
      </div>
    </header>
  );
}
```

---

## 4. Header.module.css — Änderungen

### 4.1 CSS-Klassen umbenennen

Alle `.memory*`-Klassen werden durch `.cortex*`-Klassen ersetzt. Die CSS-Styles werden vereinfacht, da der Cortex-Button keine Warning/Critical-States hat:

**Entfernen:**
```css
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

**Ersetzen durch:**
```css
/* ── Cortex Button ── */
.cortexBtn {
  background: rgba(120, 90, 220, 0.15);
  border: 1px solid rgba(120, 90, 220, 0.35);
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 500;
  color: rgba(90, 60, 180, 1);
}

.cortexBtn:hover {
  background: rgba(120, 90, 220, 0.25);
  border-color: rgba(120, 90, 220, 0.5);
}

:global(body.dark-mode) .cortexBtn {
  background: rgba(140, 110, 240, 0.2);
  border-color: rgba(140, 110, 240, 0.4);
  color: rgba(170, 150, 255, 1);
}

:global(body.dark-mode) .cortexBtn:hover {
  background: rgba(140, 110, 240, 0.3);
  border-color: rgba(140, 110, 240, 0.6);
}
```

**Design-Begründung:**
- Violett-Töne statt Blau → visuell vom API-Status abgegrenzt, signalisiert „Gedächtnis/KI"
- Kein Disabled-State → Cortex-Overlay ist immer zugänglich
- Kein Warning/Critical-Pulse → Tier-basiertes System benötigt keinen User-Eingriff

---

## 5. Overlays-Barrel-Export (index.js)

### 5.1 Änderung

**Vorher:**
```javascript
export { default as MemoryOverlay } from './MemoryOverlay';
```

**Nachher:**
```javascript
export { default as CortexOverlay } from './CortexOverlay';
```

---

## 6. SessionContext.jsx — Memory-State entfernen

### 6.1 Zu entfernende Zeilen

| Zeile (ca.) | Code | Grund |
|---|---|---|
| 16 | `const [lastMemoryMessageId, setLastMemoryMessageId] = useState(null);` | Nicht mehr benötigt |
| 66 | `setLastMemoryMessageId(sessionData.last_memory_message_id \|\| null);` | Cortex nutzt Tier-Tracker statt Message-Marker |
| 83 | `setLastMemoryMessageId(sessionData.last_memory_message_id \|\| null);` | Gleicher Grund |
| 174 | `setLastMemoryMessageId(data.last_memory_message_id \|\| null);` | Gleicher Grund |
| 272 | `lastMemoryMessageId,` (im value-Objekt) | Nicht mehr exponiert |

### 6.2 Vorher/Nachher

**State-Deklaration entfernen:**
```jsx
// ENTFERNEN:
const [lastMemoryMessageId, setLastMemoryMessageId] = useState(null);
```

**setLastMemoryMessageId-Aufrufe entfernen** (3 Stellen in initSession + switchSession):
```jsx
// ENTFERNEN (jeweils):
setLastMemoryMessageId(sessionData.last_memory_message_id || null);
```

**Context-Value bereinigen:**
```jsx
// ENTFERNEN aus value-Objekt:
lastMemoryMessageId,
```

### 6.3 Auswirkung

`lastMemoryMessageId` wird aktuell nur vom `DebugOverlay` gelesen (über `useSession()`). Da das DebugOverlay ebenfalls geändert wird (Abschnitt 8), gibt es keine verwaisten Referenzen.

Prüfung auf andere Consumer:
```
Suche nach "lastMemoryMessageId" im gesamten Frontend → Treffer nur in SessionContext.jsx
```

---

## 7. useMessages.js — Cortex-Update Event dispatchen

### 7.1 Änderung im onDone-Callback

Der `onDone`-Callback in `sendMessage` muss das `cortex-update` CustomEvent dispatchen, wenn das Backend ein Cortex-Update getriggert hat (Schritt 3B, Abschnitt 8.3):

**Vorher (Zeilen 67–83):**
```javascript
onDone: (data) => {
  setIsStreaming(false);
  setIsLoading(false);
  setStreamingStats(data.stats || null);

  updateLastMessage({
    message: data.response,
    _streaming: false,
    character_name: data.character_name,
    timestamp: new Date().toISOString(),
    stats: data.stats,
  });

  if (get('notificationSound', false)) {
    playNotificationSound();
  }
},
```

**Nachher:**
```javascript
onDone: (data) => {
  setIsStreaming(false);
  setIsLoading(false);
  setStreamingStats(data.stats || null);

  updateLastMessage({
    message: data.response,
    _streaming: false,
    character_name: data.character_name,
    timestamp: new Date().toISOString(),
    stats: data.stats,
  });

  // Cortex-Update Benachrichtigung (aus SSE done-Event)
  if (data.cortex_update?.triggered) {
    window.dispatchEvent(new CustomEvent('cortex-update', {
      detail: { tier: data.cortex_update.tier }
    }));
  }

  if (get('notificationSound', false)) {
    playNotificationSound();
  }
},
```

### 7.2 Nur im sendMessage-Callback

Der `regenerateLastMsg`-Callback hat ebenfalls einen `onDone`-Handler (Zeile 179), dort wird **kein** Cortex-Event benötigt — Regenerate ändert die Nachrichtenanzahl nicht, daher kann kein neuer Tier erreicht werden (Schritt 3B, Abschnitt 9).

---

## 8. DebugOverlay.jsx — Memory-Felder durch Cortex-Status ersetzen

### 8.1 Import ändern

**Vorher:**
```jsx
import { checkMemoryAvailability } from '../../services/memoryApi';
```

**Nachher:**
```jsx
import { getCortexFiles } from '../../services/cortexApi';
```

### 8.2 Refresh-Funktion ändern

**Vorher:**
```jsx
const refreshInfo = useCallback(async () => {
  if (!sessionId) return;
  setLoadingInfo(true);
  try {
    const data = await checkMemoryAvailability(sessionId);
    setSessionInfo(data);
  } catch {
    setSessionInfo({ error: 'Failed to load' });
  } finally {
    setLoadingInfo(false);
  }
}, [sessionId]);
```

**Nachher:**
```jsx
const refreshInfo = useCallback(async () => {
  if (!personaId) return;
  setLoadingInfo(true);
  try {
    const data = await getCortexFiles(personaId);
    setSessionInfo(data);
  } catch {
    setSessionInfo({ error: 'Failed to load' });
  } finally {
    setLoadingInfo(false);
  }
}, [personaId]);
```

### 8.3 Debug-Felder ersetzen

**Vorher:**
```jsx
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

**Nachher:**
```jsx
{sessionInfo && !sessionInfo.error && (
  <>
    <div className={styles.debugRow}>
      <span>Cortex Files:</span>
      <code>
        {sessionInfo.files
          ? Object.keys(sessionInfo.files).join(', ')
          : '-'}
      </code>
    </div>
    <div className={styles.debugRow}>
      <span>memory.md:</span>
      <code>{sessionInfo.files?.memory ? `${sessionInfo.files.memory.length} chars` : '-'}</code>
    </div>
    <div className={styles.debugRow}>
      <span>soul.md:</span>
      <code>{sessionInfo.files?.soul ? `${sessionInfo.files.soul.length} chars` : '-'}</code>
    </div>
    <div className={styles.debugRow}>
      <span>relationship.md:</span>
      <code>{sessionInfo.files?.relationship ? `${sessionInfo.files.relationship.length} chars` : '-'}</code>
    </div>
  </>
)}
```

### 8.4 Kommentar aktualisieren

**Vorher:**
```jsx
// ── DebugOverlay ──
// Debug panel with toast tests, memory buttons, session info
```

**Nachher:**
```jsx
// ── DebugOverlay ──
// Debug panel with toast tests, cortex status, session info
```

---

## 9. CortexUpdateIndicator — Neue Komponente

### 9.1 Zweck

Ein kleines, nicht-blockierendes visuelles Element, das anzeigt, wenn ein Cortex-Update im Hintergrund gestartet wurde. Erscheint unterhalb der ContextBar und verschwindet nach 4 Sekunden.

### 9.2 Dateistruktur

```
frontend/src/features/chat/components/CortexUpdateIndicator/
├── CortexUpdateIndicator.jsx
└── CortexUpdateIndicator.module.css
```

### 9.3 Component

```jsx
// ── CortexUpdateIndicator ──
// Subtle notification when a background cortex update is running

import styles from './CortexUpdateIndicator.module.css';

export default function CortexUpdateIndicator() {
  return (
    <div className={styles.indicator}>
      <span className={styles.icon}>🧠</span>
      <span className={styles.text}>Cortex aktualisiert sich…</span>
    </div>
  );
}
```

### 9.4 CSS

```css
/* ── Cortex Update Indicator ── */
.indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  margin: 4px auto;
  width: fit-content;
  background: rgba(120, 90, 220, 0.12);
  border: 1px solid rgba(120, 90, 220, 0.25);
  border-radius: 16px;
  font-size: 12px;
  font-weight: 500;
  color: rgba(90, 60, 180, 0.9);
  animation: cortexSlideIn 0.3s ease-out, cortexPulse 2s ease-in-out infinite;
  pointer-events: none;
}

:global(body.dark-mode) .indicator {
  background: rgba(140, 110, 240, 0.15);
  border-color: rgba(140, 110, 240, 0.3);
  color: rgba(180, 160, 255, 0.9);
}

.icon {
  font-size: 14px;
  line-height: 1;
}

.text {
  white-space: nowrap;
}

@keyframes cortexSlideIn {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes cortexPulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}
```

### 9.5 Design-Begründung

- **Position:** Unterhalb der ContextBar, zentriert — nicht überlappend mit Chat-Bubbles
- **Stil:** Gleiche Violett-Farbpalette wie der Cortex-Button → visuell zusammengehörig
- **Animation:** Sanftes Einblenden + pulsierender Opacity-Effekt → kommuniziert laufenden Prozess
- **Verhalten:** `pointer-events: none` → clickthrough, blockiert keine Interaktion
- **Timing:** 4 Sekunden sichtbar (gesteuert durch ChatPage.jsx Timer)

---

## 10. Event-Flow: Cortex-Update → UI-Indikator

```
┌─────────────────────────────────────────────────────────────────┐
│ Backend: chat_stream() in routes/chat.py                        │
│                                                                  │
│ 1. Nachricht N wird generiert (SSE Stream)                       │
│ 2. check_and_trigger_cortex_update() → Tier 1 erreicht!         │
│ 3. Background-Thread gestartet für CortexUpdateService           │
│ 4. done-Event enthält: { cortex_update: { triggered: true, tier: 1 } } │
└──────────────────────────┬──────────────────────────────────────┘
                           │ SSE data: {...}
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ Frontend: useMessages.js → onDone Callback                       │
│                                                                  │
│ 5. data.cortex_update?.triggered === true                        │
│ 6. window.dispatchEvent(new CustomEvent('cortex-update', {       │
│       detail: { tier: 1 }                                        │
│    }))                                                           │
└──────────────────────────┬──────────────────────────────────────┘
                           │ CustomEvent
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ Frontend: ChatPage.jsx → useEffect Event Listener                │
│                                                                  │
│ 7. setCortexUpdating(true)                                       │
│ 8. setTimeout(() => setCortexUpdating(false), 4000)              │
│ 9. <CortexUpdateIndicator /> wird gerendert                     │
│ 10. Nach 4s: Indikator verschwindet                              │
└─────────────────────────────────────────────────────────────────┘
```

**Warum CustomEvent statt React State-Prop-Drilling?**
- `useMessages` ist ein Hook innerhalb von `ChatPageContent` — könnte theoretisch direkt State setzen
- Aber: Das Event-Pattern ist flexibler (andere Komponenten können auch darauf reagieren)
- Konsistent mit dem Konzept aus Schritt 3B, Abschnitt 8.3
- Der CortexUpdateIndicator könnte in Zukunft auch auf andere Events reagieren (z.B. manuelles Update aus dem Overlay)

---

## 11. ContextBar.jsx — Keine Änderung

Die `ContextBar` zeigt ausschließlich das Verhältnis Nachrichten / Kontextlimit an:

```jsx
const { totalMessageCount } = useSession();
const contextLimit = parseInt(get('contextLimit', 30), 10);
```

Sie hat:
- Keinen `memoryApi`-Import
- Keinen Memory-State
- Keinen Memory-Bezug im JSX

**Fazit:** Keine Änderung nötig. Die ContextBar bleibt wie sie ist.

---

## 12. Zusammenfassung aller Änderungen

### 12.1 Geänderte Dateien

| # | Datei | Art der Änderung |
|---|-------|-----------------|
| 1 | `frontend/src/features/chat/ChatPage.jsx` | Import: `MemoryOverlay` → `CortexOverlay`. Hook: `memory` → `cortex`. Prop: `onOpenMemory` → `onOpenCortex`. Render: `<MemoryOverlay>` → `<CortexOverlay>`. NEU: `cortexUpdating` State + Event-Listener + `<CortexUpdateIndicator>`. NEU: Import `CortexUpdateIndicator`. |
| 2 | `frontend/src/features/chat/components/Header/Header.jsx` | Prop: `onOpenMemory` → `onOpenCortex`. Import entfernen: `checkMemoryAvailability`. State entfernen: `memoryState`, Polling-useEffect, `memoryBtnClass`, `handleMemoryClick`. Button: `Erinnern` → `Cortex` (einfacher, immer aktiv). Dropdown: `Erinnerungen` → `Cortex`. |
| 3 | `frontend/src/features/chat/components/Header/Header.module.css` | Klassen entfernen: `.memoryBtn`, `.memoryDisabled`, `.memoryWarning`, `.memoryCritical`, Keyframes. Klassen hinzufügen: `.cortexBtn` (+ dark-mode Varianten). |
| 4 | `frontend/src/features/overlays/index.js` | Export: `MemoryOverlay` → `CortexOverlay`. |
| 5 | `frontend/src/features/overlays/DebugOverlay.jsx` | Import: `checkMemoryAvailability` → `getCortexFiles`. Refresh nutzt `personaId` statt `sessionId`. Debug-Felder: Memory-Marker/Availability → Cortex-Dateien-Status. |
| 6 | `frontend/src/features/chat/hooks/useMessages.js` | `onDone`-Callback: `cortex-update` CustomEvent dispatchen wenn `data.cortex_update?.triggered`. |
| 7 | `frontend/src/context/SessionContext.jsx` | State entfernen: `lastMemoryMessageId` + alle `setLastMemoryMessageId()`-Aufrufe + Context-Value-Eintrag. |

### 12.2 Neue Dateien

| # | Datei | Zweck |
|---|-------|-------|
| 1 | `frontend/src/features/chat/components/CortexUpdateIndicator/CortexUpdateIndicator.jsx` | Subtiler Indikator für laufende Cortex-Updates |
| 2 | `frontend/src/features/chat/components/CortexUpdateIndicator/CortexUpdateIndicator.module.css` | Styling mit Violett-Palette, Animations |

### 12.3 Zu entfernende Dateien

| # | Datei | Grund |
|---|-------|-------|
| 1 | `frontend/src/features/overlays/MemoryOverlay.jsx` | Ersetzt durch CortexOverlay.jsx (Schritt 5A) |
| 2 | `frontend/src/services/memoryApi.js` | Ersetzt durch cortexApi.js (Schritt 5B) |

> **Hinweis:** Die Dateien aus #12.3 werden erst entfernt, wenn CortexOverlay.jsx (Schritt 5A) und cortexApi.js (Schritt 5B) vollständig implementiert sind. Bis dahin bleiben sie als Referenz im Repo.

---

## 13. Abhängigkeiten zu anderen Schritten

| Abhängigkeit | Richtung | Details |
|---|---|---|
| **Schritt 5A** (CortexOverlay.jsx) | ← Voraussetzung | Die Overlay-Komponente muss existieren, bevor sie hier eingebunden wird |
| **Schritt 5B** (cortexApi.js) | ← Voraussetzung | Der DebugOverlay-Refresh nutzt `getCortexFiles()` aus dem neuen Service |
| **Schritt 3B** (Aktivierungsstufen) | ← Voraussetzung | Das Backend muss `cortex_update` im done-Event senden |
| **Schritt 1B** (Frontend Memory Removal) | ← Parallel/Voraussetzung | `memoryApi.js` und `MemoryOverlay.jsx` werden dort als deprecated markiert, hier werden die Referenzen ersetzt |

---

## 14. Reihenfolge der Implementierung

```
1. CortexUpdateIndicator erstellen (neue Komponente, keine Abhängigkeiten)
2. index.js Export ändern (nach Erstellung von CortexOverlay in 5A)
3. SessionContext.jsx bereinigen (lastMemoryMessageId entfernen)
4. Header.jsx umbauen (Prop, Button, Polling entfernen)
5. Header.module.css umbauen (Memory-Klassen → Cortex-Klassen)
6. ChatPage.jsx umbauen (Import, Hook, Render, Event-Listener)
7. useMessages.js erweitern (cortex-update Event)
8. DebugOverlay.jsx umbauen (Memory-Debug → Cortex-Debug)
9. MemoryOverlay.jsx + memoryApi.js entfernen (letzter Schritt)
```
