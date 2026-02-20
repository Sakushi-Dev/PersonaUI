# Schritt 5B: Cortex Frontend API Service

## Übersicht

Der neue **`cortexApi.js`** Service stellt die Frontend-Anbindung an die Cortex-REST-Endpunkte (definiert in [Schritt 2C](../step_02_cortex_file_structure/STEP_02C_CORTEX_API_ROUTES.md)) bereit. Er ermöglicht dem `CortexOverlay.jsx` (Schritt 5A) das Lesen, Bearbeiten und Zurücksetzen der drei Cortex-Dateien (`memory.md`, `soul.md`, `relationship.md`) sowie den Zugriff auf die Cortex-Einstellungen.

**Dieser Service ersetzt `memoryApi.js`** — das alte Memory-System wird durch das Cortex-System abgelöst. `memoryApi.js` bleibt vorerst im Repo (bis die Migration abgeschlossen ist), wird aber von keiner neuen Komponente mehr importiert.

---

## 1. Architektur-Kontext

### 1.1 Bestehende Service-Patterns

Alle API-Services im Frontend folgen demselben Muster:

| Datei | Pattern |
|---|---|
| `settingsApi.js` | Einfachstes CRUD: `apiGet` / `apiPut` / `apiPost` |
| `sessionApi.js` | `personaId` als Query-Parameter bei GET/DELETE, als Body bei POST |
| `memoryApi.js` | Direkte Wrapper um `apiGet` / `apiPost` / `apiPut` / `apiDelete` / `apiPatch` |
| `personaApi.js` | ID in URL-Pfad (`/api/personas/${id}`) |

**Gemeinsam:** Alle Services importieren die HTTP-Methoden aus `apiClient.js` und exportieren benannte Funktionen (kein Default-Export). Kein Service enthält eigene `try/catch`-Blöcke — die Fehlerbehandlung erfolgt in `apiClient.js` (`handleResponse`) und in den aufrufenden Komponenten.

### 1.2 API-Client (`apiClient.js`)

Der zentrale HTTP-Client stellt bereit:

```javascript
apiGet(path)           // GET  → JSON
apiPost(path, body)    // POST → JSON
apiPut(path, body)     // PUT  → JSON
apiDelete(path)        // DELETE → JSON
apiPatch(path, body)   // PATCH → JSON
```

Alle Methoden:
- Prependen automatisch `API_BASE_URL`
- Parsen die JSON-Response via `handleResponse()`
- Werfen Error-Objekte mit `.status` und `.data` bei nicht-2xx Responses
- Leiten bei 403/`access_denied` automatisch zur Waiting-Page um

### 1.3 PersonaId-Übergabe

Das Backend (`resolve_persona_id()` in `routes/helpers.py`) löst die Persona-ID in dieser Reihenfolge auf:

1. **Query-Parameter** `?persona_id=xxx` (bevorzugt bei GET-Requests)
2. **JSON-Body** `{ "persona_id": "xxx" }` (bevorzugt bei POST/PUT-Requests)
3. Session-Lookup (Fallback)
4. Aktive Persona (letzter Fallback)

**Für den Cortex-Service gilt:**
- **GET-Requests**: `personaId` als Query-Parameter (konsistent mit `sessionApi.js`)
- **POST/PUT-Requests**: `personaId` im JSON-Body (konsistent mit `sessionApi.js`)

### 1.4 Woher kommt `personaId`?

Der `personaId` wird aus dem `SessionContext` bezogen:

```jsx
import { useContext } from 'react';
import { SessionContext } from '../context/SessionContext';

function CortexOverlay() {
  const { personaId } = useContext(SessionContext);

  // personaId ist immer verfügbar (Default: 'default')
  // Wird bei Persona-Switch automatisch aktualisiert
}
```

Die aufrufende Komponente (`CortexOverlay`) ist dafür verantwortlich, `personaId` an die API-Funktionen zu übergeben.

---

## 2. Endpunkt-Mapping

| Frontend-Funktion | HTTP | Backend-Route | PersonaId via |
|---|---|---|---|
| `getCortexFiles(personaId)` | GET | `/api/cortex/files` | Query-Param |
| `getCortexFile(personaId, filename)` | GET | `/api/cortex/file/<filename>` | Query-Param |
| `saveCortexFile(personaId, filename, content)` | PUT | `/api/cortex/file/<filename>` | JSON-Body |
| `resetCortexFile(personaId, filename)` | POST | `/api/cortex/reset/<filename>` | JSON-Body |
| `resetAllCortexFiles(personaId)` | POST | `/api/cortex/reset` | JSON-Body |
| `getCortexSettings()` | GET | `/api/cortex/settings` | — (global) |
| `saveCortexSettings(settings)` | PUT | `/api/cortex/settings` | — (global) |

---

## 3. Vollständiger Code

### `frontend/src/services/cortexApi.js`

```javascript
// ── Cortex API Service ──
//
// Frontend-Anbindung an die Cortex-REST-Endpunkte (src/routes/cortex.py).
// Ersetzt memoryApi.js — das alte Memory-System wird durch Cortex abgelöst.

import { apiGet, apiPost, apiPut } from './apiClient';


// ═════════════════════════════════════════════════════════════════════════════
//  CORTEX FILE OPERATIONS
// ═════════════════════════════════════════════════════════════════════════════


/**
 * Lädt alle 3 Cortex-Dateien (memory.md, soul.md, relationship.md) der Persona.
 *
 * @param {string} personaId - Die Persona-ID (aus SessionContext)
 * @returns {Promise<{success: boolean, files: {memory: string, soul: string, relationship: string}, persona_id: string}>}
 */
export function getCortexFiles(personaId) {
  return apiGet(`/api/cortex/files?persona_id=${personaId}`);
}


/**
 * Lädt den Inhalt einer einzelnen Cortex-Datei.
 *
 * @param {string} personaId - Die Persona-ID (aus SessionContext)
 * @param {string} filename  - Dateiname: 'memory.md', 'soul.md' oder 'relationship.md'
 * @returns {Promise<{success: boolean, filename: string, content: string, persona_id: string}>}
 */
export function getCortexFile(personaId, filename) {
  return apiGet(`/api/cortex/file/${filename}?persona_id=${personaId}`);
}


/**
 * Speichert den Inhalt einer einzelnen Cortex-Datei (User-Editing via CortexOverlay).
 *
 * @param {string} personaId - Die Persona-ID (aus SessionContext)
 * @param {string} filename  - Dateiname: 'memory.md', 'soul.md' oder 'relationship.md'
 * @param {string} content   - Der neue Datei-Inhalt (Markdown)
 * @returns {Promise<{success: boolean, filename: string, persona_id: string}>}
 */
export function saveCortexFile(personaId, filename, content) {
  return apiPut(`/api/cortex/file/${filename}`, {
    content,
    persona_id: personaId,
  });
}


/**
 * Setzt eine einzelne Cortex-Datei auf das Template zurück.
 *
 * @param {string} personaId - Die Persona-ID (aus SessionContext)
 * @param {string} filename  - Dateiname: 'memory.md', 'soul.md' oder 'relationship.md'
 * @returns {Promise<{success: boolean, filename: string, content: string, persona_id: string}>}
 */
export function resetCortexFile(personaId, filename) {
  return apiPost(`/api/cortex/reset/${filename}`, {
    persona_id: personaId,
  });
}


/**
 * Setzt alle 3 Cortex-Dateien der Persona auf die Templates zurück.
 *
 * @param {string} personaId - Die Persona-ID (aus SessionContext)
 * @returns {Promise<{success: boolean, files: {memory: string, soul: string, relationship: string}, persona_id: string}>}
 */
export function resetAllCortexFiles(personaId) {
  return apiPost('/api/cortex/reset', {
    persona_id: personaId,
  });
}


// ═════════════════════════════════════════════════════════════════════════════
//  CORTEX SETTINGS
// ═════════════════════════════════════════════════════════════════════════════


/**
 * Lädt die aktuellen Cortex-Einstellungen (Tiers, enabled).
 *
 * @returns {Promise<{success: boolean, settings: object, defaults: object}>}
 */
export function getCortexSettings() {
  return apiGet('/api/cortex/settings');
}


/**
 * Aktualisiert die Cortex-Einstellungen (Partial Update).
 *
 * @param {object} settings - Teilweise oder vollständige Settings
 * @param {boolean} [settings.enabled] - Cortex global ein/aus
 * @param {object}  [settings.tiers]   - Tier-Konfiguration (partial merge)
 * @returns {Promise<{success: boolean, settings: object, defaults: object}>}
 */
export function saveCortexSettings(settings) {
  return apiPut('/api/cortex/settings', settings);
}
```

---

## 4. Vergleich: `memoryApi.js` → `cortexApi.js`

### 4.1 Funktions-Mapping

| Alter Service (`memoryApi.js`) | Neuer Service (`cortexApi.js`) | Anmerkung |
|---|---|---|
| `getMemories()` | `getCortexFiles(personaId)` | Lädt jetzt alle 3 Dateien statt DB-Einträge |
| `createMemory(data)` | — | Entfällt: Cortex-Dateien existieren immer |
| `updateMemory(id, data)` | `saveCortexFile(personaId, filename, content)` | Datei statt DB-Eintrag |
| `deleteMemory(id)` | `resetCortexFile(personaId, filename)` | Reset statt Delete |
| `toggleMemory(id)` | — | Entfällt: kein Toggle für Markdown-Dateien |
| `previewMemory(data)` | — | Entfällt: Inline-Editing in CortexOverlay |
| `checkMemoryAvailability(sessionId)` | `getCortexSettings()` | Prüfung über `settings.enabled` |
| `getMemoryStats()` | — | Entfällt: Stats sind jetzt Datei-Metadaten |
| — | `getCortexFile(personaId, filename)` | NEU: Einzeldatei-Zugriff |
| — | `resetAllCortexFiles(personaId)` | NEU: Komplett-Reset |
| — | `saveCortexSettings(settings)` | NEU: Settings-Speicherung |

### 4.2 Wesentliche Unterschiede

| Aspekt | `memoryApi.js` (alt) | `cortexApi.js` (neu) |
|---|---|---|
| **Datenmodell** | DB-Einträge (CRUD) | Markdown-Dateien (Read/Write/Reset) |
| **PersonaId** | Nicht verwendet | Pflichtparameter für alle File-Operationen |
| **Imports** | `apiGet, apiPost, apiPut, apiDelete, apiPatch` | `apiGet, apiPost, apiPut` (weniger Methoden nötig) |
| **Settings** | Keine eigenen Settings | Eigene Cortex-Settings (enabled, tiers) |
| **Error-Handling** | Via `apiClient.js` (kein eigenes try/catch) | Via `apiClient.js` (kein eigenes try/catch) |

---

## 5. Usage-Beispiel: CortexOverlay Integration

### 5.1 Dateien laden und anzeigen

```jsx
import { useContext, useEffect, useState } from 'react';
import { SessionContext } from '../../context/SessionContext';
import * as cortexApi from '../../services/cortexApi';

function CortexOverlay() {
  const { personaId } = useContext(SessionContext);
  const [files, setFiles] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Alle Cortex-Dateien beim Öffnen laden
  useEffect(() => {
    async function loadFiles() {
      try {
        setLoading(true);
        setError(null);
        const data = await cortexApi.getCortexFiles(personaId);
        if (data.success) {
          setFiles(data.files);
        }
      } catch (err) {
        setError(err.message || 'Fehler beim Laden der Cortex-Dateien');
      } finally {
        setLoading(false);
      }
    }
    loadFiles();
  }, [personaId]);

  // ...
}
```

### 5.2 Datei speichern (nach Editing)

```jsx
const handleSave = async (filename, content) => {
  try {
    const data = await cortexApi.saveCortexFile(personaId, filename, content);
    if (data.success) {
      // Lokalen State aktualisieren
      setFiles(prev => ({
        ...prev,
        [filename.replace('.md', '')]: content,
      }));
    }
  } catch (err) {
    setError(err.message || 'Fehler beim Speichern');
  }
};
```

### 5.3 Einzelne Datei zurücksetzen

```jsx
const handleReset = async (filename) => {
  try {
    const data = await cortexApi.resetCortexFile(personaId, filename);
    if (data.success) {
      // Backend gibt den Template-Inhalt zurück
      setFiles(prev => ({
        ...prev,
        [filename.replace('.md', '')]: data.content,
      }));
    }
  } catch (err) {
    setError(err.message || 'Fehler beim Zurücksetzen');
  }
};
```

### 5.4 Settings laden und aktualisieren

```jsx
const [settings, setSettings] = useState(null);

// Laden
useEffect(() => {
  async function loadSettings() {
    try {
      const data = await cortexApi.getCortexSettings();
      if (data.success) {
        setSettings(data.settings);
      }
    } catch (err) {
      console.warn('Cortex-Settings nicht verfügbar:', err);
    }
  }
  loadSettings();
}, []);

// Aktualisieren (z.B. Toggle enabled)
const handleToggleCortex = async () => {
  try {
    const data = await cortexApi.saveCortexSettings({
      enabled: !settings.enabled,
    });
    if (data.success) {
      setSettings(data.settings);
    }
  } catch (err) {
    console.warn('Settings-Update fehlgeschlagen:', err);
  }
};
```

---

## 6. Error-Handling-Strategie

### 6.1 Schicht-Architektur

```
┌─────────────────────────────────────────┐
│  CortexOverlay.jsx                      │  try/catch um API-Calls
│  → setzt error-State, zeigt Toast/Alert │  → User-facing Fehlermeldungen
├─────────────────────────────────────────┤
│  cortexApi.js                           │  Kein eigenes try/catch
│  → reiner Durchreicher                  │  → Propagiert Errors nach oben
├─────────────────────────────────────────┤
│  apiClient.js                           │  handleResponse()
│  → wirft Error mit .status & .data      │  → 403 → Redirect zu Waiting-Page
│  → parsed JSON-Response                 │  → Andere → Error-Objekt
└─────────────────────────────────────────┘
```

### 6.2 Mögliche Fehler

| HTTP Status | Ursache | Behandlung im Frontend |
|---|---|---|
| 400 | Ungültiger Dateiname, fehlendes `content` | Error-Message anzeigen |
| 403 | Access denied (externer User) | Auto-Redirect via `apiClient.js` |
| 500 | Server-Fehler (Dateisystem, CortexService) | Retry-Option oder Error-Toast |
| Network Error | Server nicht erreichbar | "Verbindung fehlgeschlagen" anzeigen |

### 6.3 Pattern-Konsistenz

Der `cortexApi.js` Service enthält **bewusst kein eigenes try/catch** — genau wie alle anderen Services (`memoryApi.js`, `settingsApi.js`, `sessionApi.js`, `personaApi.js`). Die Fehlerbehandlung ist konsistent auf zwei Ebenen verteilt:

1. **`apiClient.js`**: Technische Fehlerbehandlung (HTTP-Status-Codes, JSON-Parsing, Access-Redirect)
2. **Aufrufende Komponente**: Fachliche Fehlerbehandlung (Error-State, User-Feedback)

---

## 7. Datei-Registrierung

Die neue Datei wird im gleichen Verzeichnis wie alle anderen Services angelegt:

```
frontend/src/services/
├── accessApi.js
├── apiClient.js
├── avatarApi.js
├── chatApi.js
├── cortexApi.js          ← NEU
├── customSpecsApi.js
├── memoryApi.js          ← DEPRECATED (wird in Step 7 entfernt)
├── onboardingApi.js
├── personaApi.js
├── serverApi.js
├── sessionApi.js
├── settingsApi.js
└── userProfileApi.js
```

**Naming-Pattern:** `{feature}Api.js` — konsistent mit allen bestehenden Services.

---

## 8. Migrations-Hinweis

### 8.1 Ablösungsplan für `memoryApi.js`

1. **Schritt 5B (dieses Dokument):** `cortexApi.js` erstellen
2. **Schritt 5A:** `CortexOverlay.jsx` importiert `cortexApi.js` statt `memoryApi.js`
3. **Schritt 7 (Final Review):** Alle verbleibenden Imports von `memoryApi.js` auf `cortexApi.js` migrieren, `memoryApi.js` entfernen

### 8.2 Koexistenz-Phase

Während der Migration können beide Services parallel existieren. Keine Funktion in `cortexApi.js` kollidiert mit `memoryApi.js` — sie verwenden unterschiedliche API-Pfade (`/api/cortex/*` vs. `/api/memory/*`).

---

## Zusammenfassung

| Aspekt | Detail |
|---|---|
| **Datei** | `frontend/src/services/cortexApi.js` |
| **Imports** | `apiGet`, `apiPost`, `apiPut` aus `apiClient.js` |
| **Exports** | 7 benannte Funktionen (kein Default-Export) |
| **PersonaId** | Query-Param bei GET, JSON-Body bei POST/PUT |
| **Error-Handling** | Kein eigenes try/catch — delegiert an `apiClient.js` + Komponente |
| **Ersetzt** | `memoryApi.js` (altes Memory-System) |
| **Konsistenz** | Folgt exakt dem Pattern von `sessionApi.js` und `settingsApi.js` |
