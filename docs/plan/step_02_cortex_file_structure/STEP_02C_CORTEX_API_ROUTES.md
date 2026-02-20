# Schritt 2C: Cortex API Routes

## Übersicht

Das Cortex-System benötigt REST-Endpunkte, damit das Frontend (`CortexOverlay.jsx`) die drei Cortex-Dateien (`memory.md`, `soul.md`, `relationship.md`) lesen, bearbeiten und zurücksetzen kann. Zusätzlich braucht die UI Zugriff auf die Cortex-Einstellungen (Aktivierungsstufen, Ein/Aus-Schalter).

Dieses Dokument definiert den neuen Blueprint `cortex_bp` mit allen Endpunkten, Request/Response-Schemas, Fehlerbehandlung und der Registrierung im bestehenden Route-System.

**Architektur-Prinzip:** Die Routes folgen exakt den bestehenden Flask-Patterns — `success_response` / `error_response` Helpers, `@handle_route_error` Decorator, `resolve_persona_id()` für Persona-Auflösung, und JSON-basierte Request/Response-Formate.

---

## 1. Endpunkt-Übersicht

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/cortex/files` | Alle 3 Cortex-Dateien der aktiven Persona laden |
| `GET` | `/api/cortex/file/<filename>` | Einzelne Cortex-Datei lesen |
| `PUT` | `/api/cortex/file/<filename>` | Einzelne Cortex-Datei aktualisieren (User-Editing) |
| `POST` | `/api/cortex/reset/<filename>` | Einzelne Datei auf Template zurücksetzen |
| `POST` | `/api/cortex/reset` | Alle 3 Dateien auf Templates zurücksetzen |
| `GET` | `/api/cortex/settings` | Cortex-Einstellungen laden (Tiers, enabled) |
| `PUT` | `/api/cortex/settings` | Cortex-Einstellungen aktualisieren |

---

## 2. Vollständiger Route-Code

### `src/routes/cortex.py`

```python
"""
Cortex Routes — REST-Endpunkte für Cortex-Dateizugriff und Cortex-Settings.

Ermöglicht dem Frontend (CortexOverlay) das Lesen, Bearbeiten und Zurücksetzen
der drei Cortex-Dateien (memory.md, soul.md, relationship.md) sowie die
Konfiguration der Cortex-Einstellungen (Aktivierungsstufen, Ein/Aus).
"""

import os
import json
from flask import Blueprint, request

from utils.provider import get_cortex_service
from utils.cortex_service import CORTEX_FILES, TEMPLATES
from utils.logger import log
from routes.helpers import (
    success_response,
    error_response,
    handle_route_error,
    resolve_persona_id,
)

cortex_bp = Blueprint('cortex', __name__)


# ─── Konstanten ──────────────────────────────────────────────────────────────

# Pfad zur Cortex-Settings-Datei (neben user_settings.json)
CORTEX_SETTINGS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    'settings', 'cortex_settings.json'
)

# Default-Werte für Cortex-Settings
CORTEX_SETTINGS_DEFAULTS = {
    'enabled': True,
    'tiers': {
        'tier1': {'threshold': 50, 'enabled': True},
        'tier2': {'threshold': 75, 'enabled': True},
        'tier3': {'threshold': 95, 'enabled': True},
    },
}

# Erlaubte Dateinamen (Whitelist) — redundant zur CortexService-Validierung,
# aber als zusätzliche Sicherheit in der Route-Schicht
ALLOWED_FILENAMES = set(CORTEX_FILES)  # {'memory.md', 'soul.md', 'relationship.md'}


# ─── Filename Validation Helper ─────────────────────────────────────────────

def _validate_filename(filename: str):
    """
    Validiert den Dateinamen gegen die Whitelist.

    Args:
        filename: Der zu prüfende Dateiname

    Returns:
        (True, None) bei gültigem Namen,
        (False, error_response) bei ungültigem Namen
    """
    if filename not in ALLOWED_FILENAMES:
        return False, error_response(
            f'Ungültiger Dateiname: {filename}. '
            f'Erlaubt: {", ".join(sorted(ALLOWED_FILENAMES))}',
            400
        )
    return True, None


# ─── Cortex Settings I/O ────────────────────────────────────────────────────

def _load_cortex_settings() -> dict:
    """Lädt Cortex-Settings aus JSON-Datei, merged mit Defaults."""
    try:
        if os.path.exists(CORTEX_SETTINGS_FILE):
            with open(CORTEX_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                saved = json.load(f)
            # Merge: Defaults als Basis, gespeicherte Werte überschreiben
            merged = {**CORTEX_SETTINGS_DEFAULTS, **saved}
            # Tiers separat mergen (nested dict)
            merged['tiers'] = {**CORTEX_SETTINGS_DEFAULTS['tiers'], **saved.get('tiers', {})}
            return merged
        return dict(CORTEX_SETTINGS_DEFAULTS)
    except Exception as e:
        log.error("Fehler beim Laden der Cortex-Settings: %s", e)
        return dict(CORTEX_SETTINGS_DEFAULTS)


def _save_cortex_settings(settings: dict) -> bool:
    """Speichert Cortex-Settings in JSON-Datei."""
    try:
        os.makedirs(os.path.dirname(CORTEX_SETTINGS_FILE), exist_ok=True)
        with open(CORTEX_SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        log.error("Fehler beim Speichern der Cortex-Settings: %s", e)
        return False


# ═════════════════════════════════════════════════════════════════════════════
#  CORTEX FILE ENDPOINTS
# ═════════════════════════════════════════════════════════════════════════════


@cortex_bp.route('/api/cortex/files', methods=['GET'])
@handle_route_error('get_cortex_files')
def get_cortex_files():
    """
    Gibt alle 3 Cortex-Dateien der aktiven Persona zurück.

    Query-Parameter:
        persona_id: Optional — Persona-ID (Standard: aktive Persona via resolve_persona_id)

    Returns:
        {
            "success": true,
            "files": {
                "memory": "# Erinnerungen\n...",
                "soul": "# Seelen-Entwicklung\n...",
                "relationship": "# Beziehungsdynamik\n..."
            },
            "persona_id": "default"
        }
    """
    persona_id = resolve_persona_id()
    cortex = get_cortex_service()
    files = cortex.read_all(persona_id)

    return success_response(files=files, persona_id=persona_id)


@cortex_bp.route('/api/cortex/file/<filename>', methods=['GET'])
@handle_route_error('get_cortex_file')
def get_cortex_file(filename):
    """
    Gibt den Inhalt einer einzelnen Cortex-Datei zurück.

    URL-Parameter:
        filename: 'memory.md', 'soul.md' oder 'relationship.md'

    Query-Parameter:
        persona_id: Optional — Persona-ID

    Returns:
        {
            "success": true,
            "filename": "memory.md",
            "content": "# Erinnerungen\n...",
            "persona_id": "default"
        }

    Fehler:
        400 — Ungültiger Dateiname
    """
    valid, err = _validate_filename(filename)
    if not valid:
        return err

    persona_id = resolve_persona_id()
    cortex = get_cortex_service()
    content = cortex.read_file(persona_id, filename)

    return success_response(filename=filename, content=content, persona_id=persona_id)


@cortex_bp.route('/api/cortex/file/<filename>', methods=['PUT'])
@handle_route_error('update_cortex_file')
def update_cortex_file(filename):
    """
    Aktualisiert den Inhalt einer einzelnen Cortex-Datei (User-Editing via UI).

    URL-Parameter:
        filename: 'memory.md', 'soul.md' oder 'relationship.md'

    Erwartet JSON:
        {
            "content": "# Neuer Inhalt...",
            "persona_id": "optional"
        }

    Returns:
        {
            "success": true,
            "filename": "memory.md",
            "persona_id": "default"
        }

    Fehler:
        400 — Ungültiger Dateiname oder fehlendes 'content' Feld
    """
    valid, err = _validate_filename(filename)
    if not valid:
        return err

    data = request.get_json()
    if not data or 'content' not in data:
        return error_response('Feld "content" fehlt im Request-Body')

    content = data['content']
    persona_id = resolve_persona_id()
    cortex = get_cortex_service()

    try:
        cortex.write_file(persona_id, filename, content)
    except Exception as e:
        log.error("Fehler beim Schreiben von %s/%s: %s", persona_id, filename, e)
        return error_response('Datei konnte nicht gespeichert werden', 500)

    return success_response(filename=filename, persona_id=persona_id)


# ═════════════════════════════════════════════════════════════════════════════
#  CORTEX RESET ENDPOINTS
# ═════════════════════════════════════════════════════════════════════════════


@cortex_bp.route('/api/cortex/reset/<filename>', methods=['POST'])
@handle_route_error('reset_cortex_file')
def reset_cortex_file(filename):
    """
    Setzt eine einzelne Cortex-Datei auf das Template zurück.

    URL-Parameter:
        filename: 'memory.md', 'soul.md' oder 'relationship.md'

    Erwartet JSON (optional):
        {
            "persona_id": "optional"
        }

    Returns:
        {
            "success": true,
            "filename": "memory.md",
            "content": "# Erinnerungen\n...",
            "persona_id": "default"
        }

    Fehler:
        400 — Ungültiger Dateiname
    """
    valid, err = _validate_filename(filename)
    if not valid:
        return err

    persona_id = resolve_persona_id()
    cortex = get_cortex_service()
    template_content = TEMPLATES[filename]

    try:
        cortex.write_file(persona_id, filename, template_content)
    except Exception as e:
        log.error("Fehler beim Reset von %s/%s: %s", persona_id, filename, e)
        return error_response('Datei konnte nicht zurückgesetzt werden', 500)

    return success_response(filename=filename, content=template_content, persona_id=persona_id)


@cortex_bp.route('/api/cortex/reset', methods=['POST'])
@handle_route_error('reset_all_cortex_files')
def reset_all_cortex_files():
    """
    Setzt alle 3 Cortex-Dateien der aktiven Persona auf Templates zurück.

    Erwartet JSON (optional):
        {
            "persona_id": "optional"
        }

    Returns:
        {
            "success": true,
            "files": {
                "memory": "# Erinnerungen\n...",
                "soul": "# Seelen-Entwicklung\n...",
                "relationship": "# Beziehungsdynamik\n..."
            },
            "persona_id": "default"
        }
    """
    persona_id = resolve_persona_id()
    cortex = get_cortex_service()
    reset_files = {}

    for fname, template_content in TEMPLATES.items():
        try:
            cortex.write_file(persona_id, fname, template_content)
            # Key ohne .md-Extension (konsistent mit read_all)
            key = fname.replace('.md', '')
            reset_files[key] = template_content
        except Exception as e:
            log.error("Fehler beim Reset von %s/%s: %s", persona_id, fname, e)
            return error_response(
                f'Reset fehlgeschlagen bei {fname}', 500
            )

    return success_response(files=reset_files, persona_id=persona_id)


# ═════════════════════════════════════════════════════════════════════════════
#  CORTEX SETTINGS ENDPOINTS
# ═════════════════════════════════════════════════════════════════════════════


@cortex_bp.route('/api/cortex/settings', methods=['GET'])
@handle_route_error('get_cortex_settings')
def get_cortex_settings():
    """
    Gibt die aktuellen Cortex-Einstellungen zurück.

    Returns:
        {
            "success": true,
            "settings": {
                "enabled": true,
                "tiers": {
                    "tier1": {"threshold": 50, "enabled": true},
                    "tier2": {"threshold": 75, "enabled": true},
                    "tier3": {"threshold": 95, "enabled": true}
                }
            },
            "defaults": { ... }
        }
    """
    settings = _load_cortex_settings()
    return success_response(settings=settings, defaults=CORTEX_SETTINGS_DEFAULTS)


@cortex_bp.route('/api/cortex/settings', methods=['PUT'])
@handle_route_error('update_cortex_settings')
def update_cortex_settings():
    """
    Aktualisiert die Cortex-Einstellungen (Partial Update).

    Erwartet JSON:
        {
            "enabled": false,
            "tiers": {
                "tier1": {"threshold": 40, "enabled": true}
            }
        }

    Returns:
        {
            "success": true,
            "settings": { ... aktualisiert ... },
            "defaults": { ... }
        }

    Fehler:
        400 — Keine Daten oder Speichern fehlgeschlagen
    """
    data = request.get_json()
    if not data:
        return error_response('Keine Daten')

    current = _load_cortex_settings()

    # Top-Level Keys mergen
    for key, value in data.items():
        if key == 'tiers' and isinstance(value, dict):
            # Tiers granular mergen (einzelne Tier-Objekte aktualisieren)
            for tier_key, tier_value in value.items():
                if tier_key in current['tiers'] and isinstance(tier_value, dict):
                    current['tiers'][tier_key].update(tier_value)
        else:
            current[key] = value

    if _save_cortex_settings(current):
        return success_response(settings=current, defaults=CORTEX_SETTINGS_DEFAULTS)
    else:
        return error_response('Speichern fehlgeschlagen', 500)
```

---

## 3. Request/Response JSON-Schemas

### 3.1 GET `/api/cortex/files`

**Request:**
```
GET /api/cortex/files
GET /api/cortex/files?persona_id=a1b2c3d4
```

**Response (200):**
```json
{
    "success": true,
    "files": {
        "memory": "# Erinnerungen\n\nHier halte ich fest...",
        "soul": "# Seelen-Entwicklung\n\nHier reflektiere ich...",
        "relationship": "# Beziehungsdynamik\n\nHier halte ich fest..."
    },
    "persona_id": "default"
}
```

### 3.2 GET `/api/cortex/file/<filename>`

**Request:**
```
GET /api/cortex/file/memory.md
GET /api/cortex/file/soul.md?persona_id=a1b2c3d4
```

**Response (200):**
```json
{
    "success": true,
    "filename": "memory.md",
    "content": "# Erinnerungen\n\nHier halte ich fest, was ich mir merken möchte...",
    "persona_id": "default"
}
```

**Response (400) — Ungültiger Dateiname:**
```json
{
    "success": false,
    "error": "Ungültiger Dateiname: notes.md. Erlaubt: memory.md, relationship.md, soul.md"
}
```

### 3.3 PUT `/api/cortex/file/<filename>`

**Request:**
```
PUT /api/cortex/file/memory.md
Content-Type: application/json

{
    "content": "# Erinnerungen\n\n## Wichtige Details über User\n\n- Mag Kaffee\n- Programmierer",
    "persona_id": "a1b2c3d4"
}
```

**Response (200):**
```json
{
    "success": true,
    "filename": "memory.md",
    "persona_id": "a1b2c3d4"
}
```

**Response (400) — Fehlender Content:**
```json
{
    "success": false,
    "error": "Feld \"content\" fehlt im Request-Body"
}
```

**Response (400) — Ungültiger Dateiname:**
```json
{
    "success": false,
    "error": "Ungültiger Dateiname: hack.md. Erlaubt: memory.md, relationship.md, soul.md"
}
```

**Response (500) — Schreibfehler:**
```json
{
    "success": false,
    "error": "Datei konnte nicht gespeichert werden"
}
```

### 3.4 POST `/api/cortex/reset/<filename>`

**Request:**
```
POST /api/cortex/reset/memory.md
Content-Type: application/json

{
    "persona_id": "a1b2c3d4"
}
```

**Response (200):**
```json
{
    "success": true,
    "filename": "memory.md",
    "content": "# Erinnerungen\n\nHier halte ich fest, was ich mir merken möchte...",
    "persona_id": "a1b2c3d4"
}
```

### 3.5 POST `/api/cortex/reset`

**Request:**
```
POST /api/cortex/reset
Content-Type: application/json

{
    "persona_id": "default"
}
```

**Response (200):**
```json
{
    "success": true,
    "files": {
        "memory": "# Erinnerungen\n\nHier halte ich fest...",
        "soul": "# Seelen-Entwicklung\n\nHier reflektiere ich...",
        "relationship": "# Beziehungsdynamik\n\nHier halte ich fest..."
    },
    "persona_id": "default"
}
```

**Response (500) — Teilweiser Fehler:**
```json
{
    "success": false,
    "error": "Reset fehlgeschlagen bei soul.md"
}
```

### 3.6 GET `/api/cortex/settings`

**Request:**
```
GET /api/cortex/settings
```

**Response (200):**
```json
{
    "success": true,
    "settings": {
        "enabled": true,
        "tiers": {
            "tier1": {"threshold": 50, "enabled": true},
            "tier2": {"threshold": 75, "enabled": true},
            "tier3": {"threshold": 95, "enabled": true}
        }
    },
    "defaults": {
        "enabled": true,
        "tiers": {
            "tier1": {"threshold": 50, "enabled": true},
            "tier2": {"threshold": 75, "enabled": true},
            "tier3": {"threshold": 95, "enabled": true}
        }
    }
}
```

### 3.7 PUT `/api/cortex/settings`

**Request:**
```
PUT /api/cortex/settings
Content-Type: application/json

{
    "enabled": false,
    "tiers": {
        "tier1": {"threshold": 40}
    }
}
```

**Response (200):**
```json
{
    "success": true,
    "settings": {
        "enabled": false,
        "tiers": {
            "tier1": {"threshold": 40, "enabled": true},
            "tier2": {"threshold": 75, "enabled": true},
            "tier3": {"threshold": 95, "enabled": true}
        }
    },
    "defaults": {
        "enabled": true,
        "tiers": {
            "tier1": {"threshold": 50, "enabled": true},
            "tier2": {"threshold": 75, "enabled": true},
            "tier3": {"threshold": 95, "enabled": true}
        }
    }
}
```

**Response (400) — Keine Daten:**
```json
{
    "success": false,
    "error": "Keine Daten"
}
```

---

## 4. Fehlerbehandlung

### 4.1 Schichtenmodell

```
┌─────────────────────────────────────────────────────────────────┐
│ Schicht 1: @handle_route_error Decorator                        │
│   → Fängt ALLE unerwarteten Exceptions                          │
│   → Gibt {'success': false, 'error': 'Server-Fehler'} + 500    │
│   → Loggt Traceback via log.error()                             │
├─────────────────────────────────────────────────────────────────┤
│ Schicht 2: Dateiname-Validierung (_validate_filename)           │
│   → Whitelist-Check gegen ALLOWED_FILENAMES                     │
│   → 400 + spezifische Fehlermeldung bei ungültigem Namen        │
│   → Verhindert Path-Traversal-Angriffe (z.B. "../../../etc/..") │
├─────────────────────────────────────────────────────────────────┤
│ Schicht 3: Request-Validierung                                  │
│   → Prüft ob 'content' im JSON-Body vorhanden ist (PUT)        │
│   → Prüft ob JSON-Body überhaupt vorhanden ist (Settings PUT)  │
│   → 400 + spezifische Fehlermeldung                             │
├─────────────────────────────────────────────────────────────────┤
│ Schicht 4: CortexService-Fehler                                 │
│   → write_file() kann Exceptions werfen                         │
│   → Werden in der Route gefangen → 500 + generische Meldung    │
│   → read_file() gibt leeren String bei Fehler (kein Absturz)   │
├─────────────────────────────────────────────────────────────────┤
│ Schicht 5: Settings-I/O-Fehler                                  │
│   → Laden: Fallback auf Defaults (kein Absturz)                 │
│   → Speichern: 500 + Fehlermeldung                              │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Fehler-Tabelle

| Situation | HTTP Status | Response |
|-----------|:-----------:|---------|
| Ungültiger Dateiname (`hack.md`, `../secret`) | 400 | `"Ungültiger Dateiname: {name}. Erlaubt: memory.md, relationship.md, soul.md"` |
| Fehlendes `content` Feld im PUT-Body | 400 | `"Feld \"content\" fehlt im Request-Body"` |
| Leerer JSON-Body bei Settings PUT | 400 | `"Keine Daten"` |
| Datei kann nicht geschrieben werden | 500 | `"Datei konnte nicht gespeichert werden"` |
| Reset einer Datei schlägt fehl | 500 | `"Reset fehlgeschlagen bei {filename}"` |
| Settings können nicht gespeichert werden | 500 | `"Speichern fehlgeschlagen"` |
| Unerwartete Exception (Catch-all) | 500 | `"Server-Fehler"` |

### 4.3 Path-Traversal-Schutz

Die Dateinamen-Validierung verhindert Path-Traversal-Angriffe zweifach:

1. **Route-Schicht:** `_validate_filename()` prüft gegen eine Whitelist (`ALLOWED_FILENAMES`)
2. **Service-Schicht:** `CortexService.read_file()` / `write_file()` prüfen ebenfalls gegen `CORTEX_FILES`

```python
# Angriff: GET /api/cortex/file/../../../etc/passwd
# → _validate_filename('../../../etc/passwd') → False → 400
# → Selbst wenn Schicht 1 umgangen wird: CortexService wirft ValueError

ALLOWED_FILENAMES = {'memory.md', 'soul.md', 'relationship.md'}

# Auch URL-encoded Angriffe werden abgefangen:
# GET /api/cortex/file/..%2F..%2Fetc%2Fpasswd
# Flask decodiert automatisch → '../../../etc/passwd' → Whitelist-Check → 400
```

---

## 5. Persona-Auflösung via `resolve_persona_id`

### 5.1 Wie es funktioniert

Alle Cortex-Endpunkte nutzen `resolve_persona_id()` aus `routes/helpers.py`, um die Persona-ID zu bestimmen. Die Auflösung folgt einer Prioritäts-Kette:

```
1. Query-Parameter ?persona_id=a1b2c3d4      ← höchste Priorität
2. JSON-Body {"persona_id": "a1b2c3d4"}      ← für POST/PUT
3. Fallback: get_active_persona_id()          ← aktive Persona
```

> **Hinweis:** Der Session-Lookup (`find_session_persona`) wird im Cortex-Kontext nicht genutzt, da kein `session_id` an `resolve_persona_id` übergeben wird. Die Cortex-Dateien sind immer an die aktive Persona gebunden, nicht an eine Chat-Session.

### 5.2 Verwendung in den Endpunkten

```python
# Jeder Cortex-Endpunkt beginnt mit:
persona_id = resolve_persona_id()

# Beispiele für Frontend-Aufrufe:

# Standard: Aktive Persona (häufigster Fall)
fetch('/api/cortex/files')
→ resolve_persona_id() → get_active_persona_id() → 'default'

# Spezifische Persona via Query-Parameter
fetch('/api/cortex/files?persona_id=a1b2c3d4')
→ resolve_persona_id() → 'a1b2c3d4'

# Spezifische Persona via JSON-Body (PUT/POST)
fetch('/api/cortex/file/memory.md', {
    method: 'PUT',
    body: JSON.stringify({ content: '...', persona_id: 'a1b2c3d4' })
})
→ resolve_persona_id() → 'a1b2c3d4'
```

### 5.3 Warum kein 404 für fehlende Persona?

Der `CortexService.ensure_cortex_files()` wird intern bei jedem `read_file()` / `write_file()` aufgerufen. Wenn ein Cortex-Verzeichnis für die angefragt Persona noch nicht existiert, wird es automatisch mit Templates erstellt (Lazy Initialization). Ein expliziter 404-Check ist daher nicht nötig — das System ist selbstheilend.

```python
# CortexService.read_file() intern:
self.ensure_cortex_files(persona_id)  # ← Erstellt fehlende Dateien/Verzeichnis
filepath = os.path.join(self.get_cortex_path(persona_id), filename)
with open(filepath, 'r', encoding='utf-8') as f:
    return f.read()
```

---

## 6. Blueprint-Registrierung

### 6.1 In `src/routes/__init__.py`

```python
"""
Routes Package — Modulare Route-Verwaltung für die Chat-Anwendung
"""
# Import aller Route-Blueprints
from routes.main import main_bp
from routes.chat import chat_bp
from routes.character import character_bp
from routes.sessions import sessions_bp
from routes.api import api_bp
from routes.avatar import avatar_bp
from routes.memory import memory_bp
from routes.access import access_bp
from routes.settings import settings_bp
from routes.custom_specs import custom_specs_bp
from routes.user_profile import user_profile_bp
from routes.onboarding import onboarding_bp
from routes.commands import commands_bp
from routes.react_frontend import react_bp, has_react_build
from routes.cortex import cortex_bp                          # ← NEU


def register_routes(app):
    """Registriert alle Route-Blueprints bei der Flask-App"""
    # React-Frontend Blueprint (Assets aus frontend/dist/)
    if has_react_build():
        app.register_blueprint(react_bp)

    app.register_blueprint(access_bp)
    app.register_blueprint(onboarding_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(character_bp)
    app.register_blueprint(sessions_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(avatar_bp)
    app.register_blueprint(memory_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(custom_specs_bp)
    app.register_blueprint(user_profile_bp)
    app.register_blueprint(commands_bp)
    app.register_blueprint(cortex_bp)                        # ← NEU
```

### 6.2 In `src/app.py`

**Keine Änderung in `app.py` nötig.** Die Blueprint-Registrierung läuft vollständig über `register_routes(app)` in `routes/__init__.py`. Die Zeile `register_routes(app)` ist bereits in `app.py` (Zeile 63) vorhanden.

```python
# src/app.py (bestehend, Zeile 63):
register_routes(app)
# → Ruft register_routes() auf → registriert alle Blueprints inkl. cortex_bp
```

### 6.3 Registrierungs-Reihenfolge

Der `cortex_bp` wird **nach** allen bestehenden Blueprints registriert. Da Cortex-Routes alle unter `/api/cortex/` laufen, gibt es keine Konflikte mit bestehenden Routes. Die Reihenfolge spielt für API-Endpunkte keine Rolle (nur für Template-Routes mit Catch-all-Patterns relevant).

---

## 7. Dateinamen-Validierung

### 7.1 Doppelte Absicherung

| Schicht | Wo | Wie |
|---------|-----|-----|
| Route | `_validate_filename()` in `cortex.py` | Whitelist-Check `ALLOWED_FILENAMES` |
| Service | `CortexService.read_file()` / `write_file()` | `if filename not in CORTEX_FILES: raise ValueError` |

Die doppelte Validierung ist beabsichtigt (Defense in Depth):
- Die Route-Schicht gibt eine benutzerfreundliche 400-Antwort
- Die Service-Schicht fängt Programmierfehler (direkte Aufrufe ohne Route)

### 7.2 Erlaubte Dateinamen

```python
CORTEX_FILES = ['memory.md', 'soul.md', 'relationship.md']
ALLOWED_FILENAMES = {'memory.md', 'soul.md', 'relationship.md'}
```

| Eingabe | Ergebnis |
|---------|----------|
| `memory.md` | ✅ Gültig |
| `soul.md` | ✅ Gültig |
| `relationship.md` | ✅ Gültig |
| `notes.md` | ❌ 400 — nicht in Whitelist |
| `../secret.txt` | ❌ 400 — nicht in Whitelist |
| `memory` | ❌ 400 — Extension fehlt |
| `MEMORY.MD` | ❌ 400 — Case-sensitive |
| `` (leer) | ❌ 404 — Flask URL-Matching schlägt fehl |

### 7.3 URL-Routing und Dateinamen

Flask URL-Parameter `<filename>` erlaubt standardmäßig keinen `/` (Slash). Deshalb ist ein Path-Traversal über die URL wie `/api/cortex/file/../../etc/passwd` nicht möglich — Flask matched den Parameter nur bis zum nächsten `/`.

Für doppelt-codierte Angriffe (`%2F`) greift die Whitelist-Validierung.

---

## 8. Cortex-Settings Speicherung

### 8.1 Speicherort

```
src/settings/cortex_settings.json
```

Neben den bestehenden Settings-Dateien:

```
src/settings/
├── defaults.json            ← User-Settings Defaults
├── user_settings.json       ← Aktive User-Settings
├── model_options.json       ← API-Modell-Optionen
├── server_settings.json     ← Server-Konfiguration
├── onboarding.json          ← Onboarding-Status
├── window_settings.json     ← Fenster-Position/Größe
├── update_state.json        ← Update-Status
├── user_profile.json        ← User-Profil
└── cortex_settings.json     ← NEU: Cortex-Einstellungen
```

### 8.2 Dateiformat

```json
{
    "enabled": true,
    "tiers": {
        "tier1": {
            "threshold": 50,
            "enabled": true
        },
        "tier2": {
            "threshold": 75,
            "enabled": true
        },
        "tier3": {
            "threshold": 95,
            "enabled": true
        }
    }
}
```

### 8.3 Settings-Felder Erklärung

| Feld | Typ | Default | Beschreibung |
|------|-----|---------|-------------|
| `enabled` | `bool` | `true` | Cortex-System global ein/aus |
| `tiers.tier1.threshold` | `int` | `50` | Schwellenwert in % des `contextLimit` — Stufe 1 |
| `tiers.tier1.enabled` | `bool` | `true` | Ob Stufe 1 aktiv ist |
| `tiers.tier2.threshold` | `int` | `75` | Schwellenwert in % des `contextLimit` — Stufe 2 |
| `tiers.tier2.enabled` | `bool` | `true` | Ob Stufe 2 aktiv ist |
| `tiers.tier3.threshold` | `int` | `95` | Schwellenwert in % des `contextLimit` — Stufe 3 |
| `tiers.tier3.enabled` | `bool` | `true` | Ob Stufe 3 aktiv ist |

### 8.4 Relationship zu `user_settings.json`

Die Cortex-Settings werden bewusst **separat** von `user_settings.json` gespeichert:

| Aspekt | `user_settings.json` | `cortex_settings.json` |
|--------|---------------------|----------------------|
| Zweck | Allgemeine UI/Modell-Settings | Cortex-spezifische Konfiguration |
| Geladen von | `settings_bp` (`/api/user-settings`) | `cortex_bp` (`/api/cortex/settings`) |
| Rücksetzen | Global Reset setzt auf Defaults | Cortex Reset ist unabhängig |
| Frontend-Zugriff | `useSettings` Hook | `useCortex` Hook (neu in Schritt 5) |

> **Hinweis:** Das Feld `memoriesEnabled` in `user_settings.json` wird in Schritt 1 entfernt. Das neue `enabled` in `cortex_settings.json` übernimmt diese Rolle.

### 8.5 Merge-Strategie

Beim Laden der Cortex-Settings wird ein Merge mit Defaults durchgeführt, sodass neu hinzugefügte Settings automatisch mit Defaults ergänzt werden:

```python
def _load_cortex_settings() -> dict:
    # Datei laden
    saved = json.load(f)
    # Top-Level mergen
    merged = {**CORTEX_SETTINGS_DEFAULTS, **saved}
    # Tiers separat mergen (nested dict)
    merged['tiers'] = {**CORTEX_SETTINGS_DEFAULTS['tiers'], **saved.get('tiers', {})}
    return merged
```

Beim Aktualisieren wird granular gemerged — einzelne Tier-Änderungen überschreiben nur die betroffenen Felder:

```python
# PUT {"tiers": {"tier1": {"threshold": 40}}}
# → Nur tier1.threshold wird auf 40 gesetzt
# → tier1.enabled, tier2.*, tier3.* bleiben unverändert
```

---

## 9. .gitignore

Die Settings-Datei enthält Benutzer-Konfiguration und sollte ignoriert werden:

```gitignore
# Cortex-Settings (Benutzer-Konfiguration)
src/settings/cortex_settings.json
```

Dies folgt dem bestehenden Muster — `user_settings.json` und `user_profile.json` sind ebenfalls gitignored.

---

## 10. Zusammenfassung der Änderungen

### Neue Dateien

| Datei | Zweck |
|-------|-------|
| `src/routes/cortex.py` | Blueprint `cortex_bp` mit allen 7 Endpunkten |

### Geänderte Dateien

| Datei | Änderung |
|-------|----------|
| `src/routes/__init__.py` | Import `cortex_bp` + `register_blueprint(cortex_bp)` |

### Neue Settings-Datei (zur Laufzeit erstellt)

| Datei | Zweck |
|-------|-------|
| `src/settings/cortex_settings.json` | Cortex-Einstellungen (wird automatisch bei erstem Zugriff erstellt) |

### Keine Änderung

| Datei | Begründung |
|-------|-----------|
| `src/app.py` | Registrierung läuft über `register_routes()` — dort wird `cortex_bp` ergänzt |
| `src/routes/helpers.py` | `resolve_persona_id()` und andere Helpers werden unverändert genutzt |

---

## 11. Abhängigkeiten zu anderen Schritten

| Abhängigkeit | Richtung | Details |
|-------------|----------|---------|
| **Schritt 2B** (CortexService) | ← Voraussetzung | `get_cortex_service()`, `read_file()`, `write_file()`, `read_all()`, `CORTEX_FILES`, `TEMPLATES` werden benötigt |
| **Schritt 1** (Remove Old Memory) | ← Voraussetzung | `memory_bp` wird entfernt — `cortex_bp` tritt an dessen Stelle (keine direkte Abhängigkeit, aber semantisch die Nachfolge) |
| **Schritt 3** (Activation Tiers) | → Nachfolger | Tier-Settings werden über `/api/cortex/settings` konfiguriert |
| **Schritt 5** (Cortex Settings UI) | → Nachfolger | `CortexOverlay.jsx` nutzt alle 7 Endpunkte |
| **Schritt 6** (API Integration) | → Nachfolger | Chat-Flow liest Cortex-Settings um Tier-Trigger zu bestimmen |

---

## 12. Frontend-Nutzung (Vorschau für Schritt 5)

So wird das Frontend die Cortex-Endpunkte aufrufen:

```javascript
// services/cortexService.js (wird in Schritt 5 erstellt)

const API_BASE = '/api/cortex';

export const cortexService = {
    // Alle Dateien laden
    getFiles: () =>
        fetch(`${API_BASE}/files`).then(r => r.json()),

    // Einzelne Datei laden
    getFile: (filename) =>
        fetch(`${API_BASE}/file/${filename}`).then(r => r.json()),

    // Datei aktualisieren (User-Editing)
    updateFile: (filename, content) =>
        fetch(`${API_BASE}/file/${filename}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content }),
        }).then(r => r.json()),

    // Einzelne Datei zurücksetzen
    resetFile: (filename) =>
        fetch(`${API_BASE}/reset/${filename}`, { method: 'POST' }).then(r => r.json()),

    // Alle Dateien zurücksetzen
    resetAll: () =>
        fetch(`${API_BASE}/reset`, { method: 'POST' }).then(r => r.json()),

    // Cortex-Settings laden
    getSettings: () =>
        fetch(`${API_BASE}/settings`).then(r => r.json()),

    // Cortex-Settings aktualisieren
    updateSettings: (settings) =>
        fetch(`${API_BASE}/settings`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings),
        }).then(r => r.json()),
};
```
