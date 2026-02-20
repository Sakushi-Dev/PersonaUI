# Schritt 6C: Settings Migration

## Übersicht

Dieses Dokument beschreibt die **vollständige Migration** der Settings-Infrastruktur vom alten Memory-System zum neuen Cortex-System. Drei zentrale Operationen werden durchgeführt:

1. **`defaults.json` Aktualisierung** — `memoriesEnabled` wird durch `cortexEnabled: true` ersetzt
2. **`user_settings.json` Runtime-Migration** — Bestehende `memoriesEnabled`-Werte werden automatisch beim Start in `cortexEnabled` überführt, der alte Key wird entfernt
3. **`cortex_settings.json` Erstanlage** — Neue Datei für domänenspezifische Cortex-Konfiguration (Tier-Schwellwerte), getrennt von den allgemeinen User-Settings

### Warum eine separate `cortex_settings.json`?

| Aspekt | `user_settings.json` | `cortex_settings.json` |
|--------|----------------------|------------------------|
| **Zweck** | Allgemeine UI/App-Einstellungen | Domänenspezifische Cortex-Parameter |
| **Verwaltet durch** | `SettingsContext` (Frontend) / `settings.py` (Backend) | Cortex-API (`/api/cortex/settings`) |
| **Reset-Verhalten** | Reset setzt **alle** Settings zurück | Cortex-Settings bleiben erhalten |
| **Schlüssel** | `cortexEnabled` (on/off Toggle) | `tierThresholds`, `autoUpdate`, `maxFileSizeKb` |
| **Frontend-Zugriff** | `useSettings().get('cortexEnabled')` | Dedizierter Cortex-API-Call |

> **Prinzip:** `cortexEnabled` lebt in `user_settings.json`, weil es ein einfacher Toggle ist und vom SettingsContext gelesen wird. Tier-Schwellwerte und andere Cortex-Parameter leben in `cortex_settings.json`, weil sie domänenspezifisch sind und nicht beim Settings-Reset verschwinden sollen.

---

## 1. `defaults.json` — Vorher vs. Nachher

### 1.1 Vorher (IST-Zustand)

```json
{
    "apiModel": "claude-sonnet-4-5-20250929",
    "apiAutofillModel": "claude-sonnet-4-5-20250929",
    "apiTemperature": "0.7",
    "contextLimit": "65",
    "backgroundColor_dark": "#1a2332",
    "backgroundColor_light": "#a3baff",
    "bubbleFontFamily": "ubuntu",
    "bubbleFontSize": "18",
    "color2_dark": "#3d4f66",
    "color2_light": "#fd91ee",
    "colorGradient1_dark": "#2a3f5f",
    "colorGradient1_light": "#66cfff",
    "colorHue": "220",
    "darkMode": false,
    "dynamicBackground": true,
    "experimentalMode": false,
    "memoriesEnabled": true,
    "nachgedankeMode": "off",
    "nonverbalColor": "#e4ba00",
    "notificationSound": true
}
```

### 1.2 Nachher (SOLL-Zustand)

```diff
 {
     "apiModel": "claude-sonnet-4-5-20250929",
     "apiAutofillModel": "claude-sonnet-4-5-20250929",
     "apiTemperature": "0.7",
     "contextLimit": "65",
     "backgroundColor_dark": "#1a2332",
     "backgroundColor_light": "#a3baff",
     "bubbleFontFamily": "ubuntu",
     "bubbleFontSize": "18",
     "color2_dark": "#3d4f66",
     "color2_light": "#fd91ee",
     "colorGradient1_dark": "#2a3f5f",
     "colorGradient1_light": "#66cfff",
     "colorHue": "220",
     "darkMode": false,
     "dynamicBackground": true,
     "experimentalMode": false,
-    "memoriesEnabled": true,
+    "cortexEnabled": true,
     "nachgedankeMode": "off",
     "nonverbalColor": "#e4ba00",
     "notificationSound": true
 }
```

### 1.3 Auswirkung

- `load_defaults()` in `src/utils/settings_defaults.py` cached `defaults.json` beim ersten Zugriff
- `_load_settings()` in `src/routes/settings.py` merged `defaults` mit `user_settings` → neue Installationen bekommen automatisch `cortexEnabled: true`
- Der Cache (`_DEFAULTS_CACHE`) wird beim Modulimport einmalig befüllt — kein Restart nötig bei reiner Code-Änderung

---

## 2. `user_settings.json` — Runtime-Migration

### 2.1 Problem

Bestehende Installationen haben in `src/settings/user_settings.json`:

```json
{
    "memoriesEnabled": true,
    ...
}
```

Oder für User, die Memories deaktiviert haben:

```json
{
    "memoriesEnabled": false,
    ...
}
```

Nach dem Code-Update kennt die App nur noch `cortexEnabled`. Ohne Migration:
- `_load_settings()` merged Defaults (`cortexEnabled: true`) mit User-Settings → `memoriesEnabled` bleibt als toter Key
- Ein User der Memories **deaktiviert** hatte, bekommt plötzlich Cortex **aktiviert** (weil der Default `true` ist)

### 2.2 Migrationsfunktion

```python
# src/utils/settings_migration.py

"""
Einmalige Settings-Migrationen beim Server-Start.
"""

import json
import os
from utils.logger import log

_SETTINGS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'settings')
_USER_SETTINGS_FILE = os.path.join(_SETTINGS_DIR, 'user_settings.json')
_CORTEX_SETTINGS_FILE = os.path.join(_SETTINGS_DIR, 'cortex_settings.json')

# Standard-Werte für cortex_settings.json
_CORTEX_DEFAULTS = {
    "cortexEnabled": True,
    "tierThresholds": {
        "tier1": 50,
        "tier2": 75,
        "tier3": 95
    }
}


def migrate_settings():
    """Führt alle einmaligen Settings-Migrationen durch.
    
    Aufgerufen in der Startup-Sequenz (startup.py), NACH init_all_dbs()
    und VOR dem Start des Flask-Servers.
    
    Migrationen:
        1. memoriesEnabled → cortexEnabled (user_settings.json)
        2. cortex_settings.json Erstanlage (falls nicht vorhanden)
    """
    _migrate_memories_to_cortex()
    _ensure_cortex_settings()


def _migrate_memories_to_cortex():
    """Migriert memoriesEnabled → cortexEnabled in user_settings.json.
    
    - Liest user_settings.json
    - Wenn 'memoriesEnabled' vorhanden: Wert übernehmen, alten Key entfernen
    - Wenn 'memoriesEnabled' NICHT vorhanden: nichts tun (Neuinstallation oder bereits migriert)
    """
    if not os.path.exists(_USER_SETTINGS_FILE):
        return  # Neuinstallation — defaults.json hat bereits cortexEnabled
    
    try:
        with open(_USER_SETTINGS_FILE, 'r', encoding='utf-8') as f:
            settings = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        log.error("Settings-Migration: Kann user_settings.json nicht lesen: %s", e)
        return
    
    if 'memoriesEnabled' not in settings:
        return  # Bereits migriert oder Neuinstallation
    
    # Wert übernehmen
    old_value = settings.pop('memoriesEnabled')
    settings['cortexEnabled'] = old_value
    
    try:
        with open(_USER_SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, indent=4, ensure_ascii=False, fp=f)
        log.info("Settings migriert: memoriesEnabled → cortexEnabled = %s", old_value)
    except OSError as e:
        log.error("Settings-Migration: Kann user_settings.json nicht schreiben: %s", e)


def _ensure_cortex_settings():
    """Erstellt cortex_settings.json mit Standardwerten, falls nicht vorhanden.
    
    Wenn die Datei bereits existiert, wird sie NICHT überschrieben.
    Fehlende Keys werden ergänzt (forward-compatible).
    """
    if os.path.exists(_CORTEX_SETTINGS_FILE):
        # Datei existiert — prüfe ob neue Keys fehlen
        try:
            with open(_CORTEX_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                existing = json.load(f)
            
            updated = False
            for key, default_value in _CORTEX_DEFAULTS.items():
                if key not in existing:
                    existing[key] = default_value
                    updated = True
                    log.info("cortex_settings.json: Key '%s' ergänzt (Default: %s)", key, default_value)
            
            if updated:
                with open(_CORTEX_SETTINGS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(existing, indent=4, ensure_ascii=False, fp=f)
        except (json.JSONDecodeError, OSError) as e:
            log.error("Settings-Migration: Fehler bei cortex_settings.json Aktualisierung: %s", e)
        return
    
    # Datei existiert nicht — Neuanlage
    try:
        os.makedirs(os.path.dirname(_CORTEX_SETTINGS_FILE), exist_ok=True)
        with open(_CORTEX_SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(_CORTEX_DEFAULTS, f, indent=4, ensure_ascii=False)
        log.info("cortex_settings.json erstellt mit Standardwerten")
    except OSError as e:
        log.error("Settings-Migration: Kann cortex_settings.json nicht erstellen: %s", e)
```

### 2.3 Ablaufdiagramm der Migration

```
Server-Start
    │
    ▼
migrate_settings()
    │
    ├── _migrate_memories_to_cortex()
    │       │
    │       ├── user_settings.json existiert nicht?
    │       │       └── return (Neuinstallation)
    │       │
    │       ├── 'memoriesEnabled' nicht in settings?
    │       │       └── return (bereits migriert)
    │       │
    │       └── 'memoriesEnabled' vorhanden?
    │               ├── cortexEnabled = settings.pop('memoriesEnabled')
    │               └── save user_settings.json
    │
    └── _ensure_cortex_settings()
            │
            ├── cortex_settings.json existiert?
            │       ├── Fehlende Keys ergänzen (forward-compatible)
            │       └── return
            │
            └── cortex_settings.json existiert nicht?
                    └── Erstelle mit _CORTEX_DEFAULTS
```

### 2.4 Migrationsszenarien

| Szenario | Ausgangslage | Ergebnis nach Migration |
|----------|-------------|------------------------|
| **Neuinstallation** | Kein `user_settings.json` vorhanden | `defaults.json` liefert `cortexEnabled: true`, `cortex_settings.json` wird erstellt |
| **Bestandsuser — Memories aktiv** | `memoriesEnabled: true` in `user_settings.json` | `cortexEnabled: true`, `memoriesEnabled` entfernt, `cortex_settings.json` erstellt |
| **Bestandsuser — Memories deaktiviert** | `memoriesEnabled: false` in `user_settings.json` | `cortexEnabled: false`, `memoriesEnabled` entfernt, `cortex_settings.json` erstellt |
| **Bereits migriert** | `cortexEnabled: true/false`, kein `memoriesEnabled` | Keine Änderung, `cortex_settings.json` Keys ggf. ergänzt |
| **Korrupte Datei** | `user_settings.json` nicht parsebar | Fehler geloggt, keine Änderung (App nutzt Defaults) |

---

## 3. `cortex_settings.json` — Neue Konfigurationsdatei

### 3.1 Datei-Ort

```
src/
  settings/
    defaults.json           ← Allgemeine Defaults (enthält cortexEnabled)
    user_settings.json      ← Persistierte User-Einstellungen (enthält cortexEnabled)
    cortex_settings.json    ← NEU: Cortex-spezifische Konfiguration
    model_options.json
    server_settings.json
    ...
```

### 3.2 Struktur

```json
{
    "cortexEnabled": true,
    "tierThresholds": {
        "tier1": 50,
        "tier2": 75,
        "tier3": 95
    }
}
```

### 3.3 Key-Beschreibung

| Key | Typ | Default | Beschreibung |
|-----|-----|---------|-------------|
| `cortexEnabled` | `bool` | `true` | Master-Switch: Cortex-System aktiv/inaktiv |
| `tierThresholds.tier1` | `int` | `50` | Nachrichten-Schwelle für Tier-1-Update (Faktenextraktion) |
| `tierThresholds.tier2` | `int` | `75` | Nachrichten-Schwelle für Tier-2-Update (Persönlichkeit/Beziehung) |
| `tierThresholds.tier3` | `int` | `95` | Nachrichten-Schwelle für Tier-3-Update (Vollanalyse) |

### 3.4 Warum `cortexEnabled` an zwei Orten?

`cortexEnabled` existiert sowohl in `user_settings.json` als auch in `cortex_settings.json`:

| Datei | Rolle | Gelesen von |
|-------|-------|-------------|
| `user_settings.json` | **Primäre Quelle** für den Toggle-State | `SettingsContext`, `settings.py`, `ChatService` |
| `cortex_settings.json` | **Initial-Default** und Backup | `_ensure_cortex_settings()` bei Erstanlage |

> **Maßgeblich ist `user_settings.json`**. Der Wert in `cortex_settings.json` dient nur als Referenz-Default und wird beim Erstellen der Datei gesetzt. Änderungen am Toggle laufen über die bestehende Settings-API (`PUT /api/user-settings`).

### 3.5 Tier-Schwellwerte — Lesen im Backend

```python
# src/utils/cortex/settings.py (NEU)

"""Cortex-spezifische Settings laden."""

import json
import os
from utils.logger import log

_CORTEX_SETTINGS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'settings', 'cortex_settings.json'
)

_TIER_DEFAULTS = {"tier1": 50, "tier2": 75, "tier3": 95}


def load_cortex_settings() -> dict:
    """Lädt cortex_settings.json. Gibt Defaults zurück bei Fehler."""
    try:
        with open(_CORTEX_SETTINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError) as e:
        log.warning("cortex_settings.json nicht lesbar: %s — nutze Defaults", e)
        return {"cortexEnabled": True, "tierThresholds": dict(_TIER_DEFAULTS)}


def get_tier_thresholds() -> dict:
    """Gibt die Tier-Schwellwerte zurück."""
    settings = load_cortex_settings()
    return settings.get('tierThresholds', dict(_TIER_DEFAULTS))


def save_cortex_settings(settings: dict) -> bool:
    """Speichert cortex_settings.json."""
    try:
        with open(_CORTEX_SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
        return True
    except OSError as e:
        log.error("cortex_settings.json speichern fehlgeschlagen: %s", e)
        return False
```

---

## 4. Integration in die Startup-Sequenz

### 4.1 Einbindung in `startup.py`

Die Migration wird in `src/splash_screen/utils/startup.py` aufgerufen, **nach** `init_all_dbs()` und **vor** den Fun-Messages:

```python
# src/splash_screen/utils/startup.py — startup_sequence()

def startup_sequence(window, server_mode, server_port, start_flask_fn, host):
    # ... Startmeldungen, Update-Check ...

    # Datenbanken initialisieren
    splash_type(window, '> Initialisiere Datenbanken...', 'default')
    init_all_dbs()
    splash_type(window, '  Datenbanken bereit.', 'info')
    splash_type(window, '', 'default')

    # ── NEU: Settings-Migration ──────────────────────────────────
    splash_type(window, '> Prüfe Settings-Migration...', 'default')
    from utils.settings_migration import migrate_settings
    migrate_settings()
    splash_type(window, '  Settings bereit.', 'info')
    splash_type(window, '', 'default')
    # ─────────────────────────────────────────────────────────────

    # Lustige Persona-Lademeldungen
    fun_msgs = get_fun_messages()
    # ... Rest der Startup-Sequenz ...
```

### 4.2 Reihenfolge der Startup-Operationen

```
startup_sequence()
    │
    ├── 1. Splash-Meldungen
    ├── 2. check_for_update()
    ├── 3. init_all_dbs()
    ├── 4. migrate_settings()          ← NEU
    │       ├── memoriesEnabled → cortexEnabled
    │       └── cortex_settings.json erstellen
    ├── 5. ensure_cortex_dirs()        ← NEU (Schritt 6B)
    ├── 6. Fun-Messages
    └── 7. start_flask_server()
```

### 4.3 Fallback für `--no-gui` Modus

Im `--no-gui` Modus (ohne pywebview) wird die Startup-Sequenz nicht durchlaufen. Die Migration muss also auch dort aufgerufen werden:

```python
# src/app.py — if __name__ == '__main__':

    else:
        # Fallback: Normaler Flask-Server ohne GUI-Fenster
        init_all_dbs()
        from utils.settings_migration import migrate_settings    # ← NEU
        migrate_settings()                                        # ← NEU
        app.run(host=host, port=server_port, debug=False)
```

Gleiches gilt für den `ImportError`-Fallback (wenn pywebview nicht installiert ist):

```python
        except ImportError:
            show_console_window()
            log.warning("PyWebView nicht installiert. Starte im Browser-Modus...")
            init_all_dbs()
            from utils.settings_migration import migrate_settings    # ← NEU
            migrate_settings()                                        # ← NEU
            log.info("Server running at: http://%s:%s", host, server_port)
            app.run(host=host, port=server_port, debug=False)
```

---

## 5. Settings-Route: Handhabung neuer Keys

### 5.1 Bestehende Logik (unverändert)

Die Route `src/routes/settings.py` braucht **keine Änderung** für `cortexEnabled`:

```python
# Bestehendes Verhalten in _load_settings():
def _load_settings():
    saved = json.load(f)           # user_settings.json
    merged = {**DEFAULT_SETTINGS, **saved}  # Defaults + gespeicherte Werte
    return merged
```

- **Neuinstallation:** `DEFAULT_SETTINGS` enthält `cortexEnabled: true` (aus `defaults.json`), kein `memoriesEnabled` mehr
- **Nach Migration:** `user_settings.json` enthält `cortexEnabled: true/false`, wird beim Merge geladen
- **Frontend Toggle:** `PUT /api/user-settings` mit `{"cortexEnabled": false}` → `_save_settings()` schreibt den Wert

### 5.2 `_DEFAULTS_ONLY_KEYS` — Kein Handlungsbedarf

```python
# Keys die nur aus defaults kommen und nicht in user_settings gespeichert werden
_DEFAULTS_ONLY_KEYS = {'apiAutofillModel'}
```

`cortexEnabled` ist **nicht** in `_DEFAULTS_ONLY_KEYS` → wird regulär in `user_settings.json` persistiert. Das ist das gewünschte Verhalten.

### 5.3 Reset-Verhalten

```python
@settings_bp.route('/api/user-settings/reset', methods=['POST'])
def reset_user_settings():
    if _save_settings(dict(DEFAULT_SETTINGS)):
        return success_response(settings=DEFAULT_SETTINGS, ...)
```

Bei Reset werden `DEFAULT_SETTINGS` geschrieben. Da `defaults.json` jetzt `cortexEnabled: true` enthält:
- Reset → `cortexEnabled` wird auf `true` zurückgesetzt
- `cortex_settings.json` wird **nicht** resetzt (separate Datei, separater Mechanismus)

### 5.4 Cortex-Settings-Route (neu, in Schritt 6B definiert)

Tier-Schwellwerte werden **nicht** über `/api/user-settings` verwaltet, sondern über eine dedizierte Route:

```python
# src/routes/cortex.py (Auszug)

@cortex_bp.route('/api/cortex/settings', methods=['GET'])
def get_cortex_settings():
    """Gibt Cortex-spezifische Settings zurück (Tiers, etc.)."""
    settings = load_cortex_settings()
    return success_response(settings=settings)


@cortex_bp.route('/api/cortex/settings', methods=['PUT'])
def update_cortex_settings():
    """Aktualisiert Cortex-Settings (partial update)."""
    data = request.get_json()
    current = load_cortex_settings()
    current.update(data)
    if save_cortex_settings(current):
        return success_response(settings=current)
    return error_response('Speichern fehlgeschlagen', 500)
```

---

## 6. Frontend: SettingsContext-Änderungen

### 6.1 Keine Code-Änderung am SettingsContext

Der `SettingsContext` (`frontend/src/context/SettingsContext.jsx`) ist **vollständig generisch** und braucht keine Änderung:

```jsx
// Bestehende API — funktioniert sofort mit cortexEnabled:
const get = useCallback((key, defaultValue) => {
    if (key in settings) return settings[key];
    if (key in defaults) return defaults[key];
    return defaultValue;
}, [settings, defaults]);

const set = useCallback((key, value) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
    pendingUpdates.current[key] = value;
    scheduleFlush();
}, [scheduleFlush]);
```

### 6.2 Nutzung in Komponenten

**Cortex an/aus Toggle (z.B. CortexOverlay):**

```jsx
import { useContext } from 'react';
import { SettingsContext } from '../context/SettingsContext';

function CortexOverlay() {
    const { get, set } = useContext(SettingsContext);
    
    const cortexEnabled = get('cortexEnabled', true);
    
    const handleToggle = () => {
        set('cortexEnabled', !cortexEnabled);
    };
    
    // ...
}
```

**Tier-Schwellwerte (NICHT über SettingsContext):**

```jsx
// Tier-Schwellwerte kommen über die Cortex-API, nicht über useSettings
import { apiGet, apiPut } from '../services/apiClient';

async function loadCortexSettings() {
    return apiGet('/api/cortex/settings');
}

async function saveCortexSettings(settings) {
    return apiPut('/api/cortex/settings', settings);
}
```

### 6.3 `constants.js` — DEFAULTS-Objekt

Das `DEFAULTS`-Objekt in `frontend/src/utils/constants.js` enthält **kein** `memoriesEnabled` und braucht **kein** `cortexEnabled`:

```javascript
// constants.js — DEFAULTS (aktuell)
export const DEFAULTS = {
    bubbleFontSize: 18,
    bubbleFontFamily: "...",
    // ... UI-Defaults ...
    experimentalMode: false,
    nachgedankeMode: 'off',
    notificationSound: true,
};
```

Der Default für `cortexEnabled` kommt vom Server (`defaults.json` → `GET /api/user-settings` → `data.defaults`). Das Frontend-`DEFAULTS`-Objekt ist nur ein Fallback, bevor die Server-Daten geladen sind. Da `cortexEnabled` erst relevant ist, **nachdem** Settings geladen wurden (`loaded === true`), ist kein Frontend-Default nötig.

---

## 7. Rückwärtskompatibilität

### 7.1 Idempotenz der Migration

| Aufruf | Verhalten |
|--------|-----------|
| **1. Start nach Update** | `memoriesEnabled` → `cortexEnabled`, `cortex_settings.json` erstellt |
| **2. Start** | `memoriesEnabled` nicht mehr vorhanden → `_migrate_memories_to_cortex()` macht nichts |
| **N. Start** | Identisch zu 2. Start — kein Performance-Impact |

### 7.2 Was passiert bei Downgrade?

Falls ein User auf eine ältere Version zurückwechselt:
- `cortexEnabled` in `user_settings.json` wird ignoriert (alter Code kennt den Key nicht)
- `memoriesEnabled` fehlt → `defaults.json` der alten Version liefert den Default
- `cortex_settings.json` wird ignoriert (alter Code kennt die Datei nicht)
- **Kein Datenverlust, keine Fehler**

### 7.3 Was passiert bei korrupten Dateien?

| Datei | Problem | Verhalten |
|-------|---------|-----------|
| `user_settings.json` nicht parsebar | `json.JSONDecodeError` | Fehler geloggt, Migration übersprungen, App nutzt `defaults.json` |
| `user_settings.json` nicht schreibbar | `OSError` | Fehler geloggt, alter State bleibt, App nutzt Merge mit Defaults |
| `cortex_settings.json` nicht lesbar | `FileNotFoundError` / `JSONDecodeError` | `load_cortex_settings()` gibt Defaults zurück |
| `settings/` Verzeichnis fehlt | `OSError` | `os.makedirs(exist_ok=True)` erstellt es |

### 7.4 Altes Legacy-Frontend (`src/static/js/`)

Das alte Jinja-Frontend in `src/static/js/modules/MemoryManager.js` referenziert noch `memoriesEnabled`:

```javascript
// MemoryManager.js (Legacy)
UserSettings.set('memoriesEnabled', isEnabled);
const isEnabled = UserSettings.get('memoriesEnabled', ...);
```

Nach der Migration existiert `memoriesEnabled` nicht mehr in den Settings. Das Legacy-Frontend bekommt `undefined` zurück, was zum Default `true` aufgelöst wird. **Kein Breaking Change**, da das Legacy-Frontend ohnehin durch das React-Frontend ersetzt wird (Schritt 1B).

---

## 8. Alle betroffenen Dateien

### 8.1 Modifizierte Dateien

| Datei | Änderung | Details |
|-------|----------|---------|
| `src/settings/defaults.json` | Key-Tausch | `memoriesEnabled` → `cortexEnabled: true` |
| `src/splash_screen/utils/startup.py` | Import + Aufruf | `migrate_settings()` nach `init_all_dbs()` |
| `src/app.py` | Import + Aufruf (2×) | `migrate_settings()` in `--no-gui` und `ImportError`-Fallback |

### 8.2 Neue Dateien

| Datei | Zweck |
|-------|-------|
| `src/utils/settings_migration.py` | Migrationsfunktionen (`migrate_settings()`, `_migrate_memories_to_cortex()`, `_ensure_cortex_settings()`) |
| `src/settings/cortex_settings.json` | Cortex-spezifische Konfiguration (wird automatisch erstellt) |
| `src/utils/cortex/settings.py` | Lese-/Schreibfunktionen für `cortex_settings.json` |

### 8.3 Unveränderte Dateien

| Datei | Warum unverändert |
|-------|-------------------|
| `src/routes/settings.py` | Generische Logik — erkennt `cortexEnabled` automatisch über defaults-Merge |
| `src/utils/settings_defaults.py` | Lädt `defaults.json` generisch — kein Key-spezifischer Code |
| `frontend/src/context/SettingsContext.jsx` | Vollständig generisch — `get('cortexEnabled')` funktioniert sofort |
| `frontend/src/services/settingsApi.js` | Keine API-Änderung für User-Settings |
| `frontend/src/utils/constants.js` | Kein `cortexEnabled`-Default nötig (kommt vom Server) |
| `src/settings/user_settings.json` | Wird **zur Laufzeit** migriert, nicht im Code-Update |

---

## 9. Checkliste

### 9.1 Backend

- [ ] `src/settings/defaults.json` — `memoriesEnabled` durch `cortexEnabled: true` ersetzen
- [ ] `src/utils/settings_migration.py` — Neue Datei mit `migrate_settings()`
- [ ] `src/utils/cortex/settings.py` — Neue Datei mit `load_cortex_settings()`, `save_cortex_settings()`
- [ ] `src/splash_screen/utils/startup.py` — `migrate_settings()` Aufruf nach `init_all_dbs()`
- [ ] `src/app.py` — `migrate_settings()` in `--no-gui` und `ImportError`-Fallback

### 9.2 Neue Datei (automatisch erstellt)

- [ ] `src/settings/cortex_settings.json` — Wird von `_ensure_cortex_settings()` beim ersten Start angelegt

### 9.3 Tests

- [ ] Migration: `memoriesEnabled: true` → `cortexEnabled: true`
- [ ] Migration: `memoriesEnabled: false` → `cortexEnabled: false`
- [ ] Migration: Kein `memoriesEnabled` vorhanden → keine Änderung
- [ ] Migration: Mehrfacher Aufruf → idempotent
- [ ] Migration: Korrupte `user_settings.json` → Fehler geloggt, kein Crash
- [ ] `cortex_settings.json` wird erstellt wenn nicht vorhanden
- [ ] `cortex_settings.json` bestehende Datei wird nicht überschrieben
- [ ] `cortex_settings.json` fehlende Keys werden ergänzt
- [ ] Settings-Reset setzt `cortexEnabled: true`, lässt `cortex_settings.json` unberührt
- [ ] `GET /api/user-settings` liefert `cortexEnabled` (kein `memoriesEnabled`)
- [ ] `PUT /api/user-settings` mit `{"cortexEnabled": false}` persistiert korrekt

### 9.4 Frontend

- [ ] `useSettings().get('cortexEnabled')` gibt korrekten Wert zurück
- [ ] Toggle Cortex an/aus → `set('cortexEnabled', value)` → Server-Persist
- [ ] Settings-Reset → `cortexEnabled` zurück auf `true`
