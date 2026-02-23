"""
Cortex Routes — REST-Endpunkte für Cortex-Dateizugriff und Cortex-Settings.

Ermöglicht dem Frontend (CortexOverlay) das Lesen, Bearbeiten und Zurücksetzen
der drei Cortex-Dateien (memory.md, soul.md, relationship.md) sowie die
Konfiguration der Cortex-Einstellungen (enabled, frequency).
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

# Default-Werte für Cortex-Settings (vereinfacht: enabled + frequency)
CORTEX_SETTINGS_DEFAULTS = {
    'enabled': True,
    'frequency': 'medium',
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
        persona_id: Optional — Persona-ID (Standard: aktive Persona)

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

    Returns:
        { "success": true, "filename": "memory.md", "content": "...", "persona_id": "default" }

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
        { "content": "# Neuer Inhalt...", "persona_id": "optional" }

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

    Returns:
        { "success": true, "filename": "memory.md", "content": "...", "persona_id": "default" }
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

    Returns:
        {
            "success": true,
            "files": { "memory": "...", "soul": "...", "relationship": "..." },
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
            "settings": { "enabled": true, "frequency": "medium" },
            "defaults": { "enabled": true, "frequency": "medium" }
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
        { "enabled": false }
        oder
        { "frequency": "low" }

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
        current[key] = value

    if _save_cortex_settings(current):
        return success_response(settings=current, defaults=CORTEX_SETTINGS_DEFAULTS)
    else:
        return error_response('Speichern fehlgeschlagen', 500)
