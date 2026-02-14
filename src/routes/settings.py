"""
Settings Routes - User Settings Verwaltung (serverseitig gespeichert)
"""
from flask import Blueprint, request
import os
import json
from utils.settings_defaults import load_defaults
from utils.logger import log
from routes.helpers import success_response, error_response, handle_route_error

settings_bp = Blueprint('settings', __name__)

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'settings', 'user_settings.json')

# Default-Werte (aus settings/defaults.json)
DEFAULT_SETTINGS = load_defaults()

# Keys die nur aus defaults kommen und nicht in user_settings gespeichert werden
_DEFAULTS_ONLY_KEYS = {'apiModelOptions', 'apiAutofillModel'}


def _load_settings():
    """Lädt User-Settings aus JSON-Datei"""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                saved = json.load(f)
            # Merge mit Defaults (neue Keys werden automatisch ergänzt)
            merged = {**DEFAULT_SETTINGS, **saved}
            return merged
        return dict(DEFAULT_SETTINGS)
    except Exception as e:
        log.error("Fehler beim Laden der User-Settings: %s", e)
        return dict(DEFAULT_SETTINGS)


def _save_settings(settings):
    """Speichert User-Settings in JSON-Datei (ohne defaults-only Keys)"""
    try:
        # Entferne Keys die nur in defaults existieren sollen
        filtered = {k: v for k, v in settings.items() if k not in _DEFAULTS_ONLY_KEYS}
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(filtered, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        log.error("Fehler beim Speichern der User-Settings: %s", e)
        return False


@settings_bp.route('/api/user-settings', methods=['GET'])
@handle_route_error('get_user_settings')
def get_user_settings():
    """Gibt alle User-Settings zurück"""
    settings = _load_settings()
    return success_response(settings=settings, defaults=DEFAULT_SETTINGS)


@settings_bp.route('/api/user-settings', methods=['PUT'])
@handle_route_error('update_user_settings')
def update_user_settings():
    """Aktualisiert User-Settings (partial update)"""
    data = request.get_json()
    if not data:
        return error_response('Keine Daten')

    current = _load_settings()
    current.update(data)

    if _save_settings(current):
        return success_response(settings=current, defaults=DEFAULT_SETTINGS)
    else:
        return error_response('Speichern fehlgeschlagen', 500)


@settings_bp.route('/api/user-settings/reset', methods=['POST'])
@handle_route_error('reset_user_settings')
def reset_user_settings():
    """Setzt alle User-Settings auf Standardwerte zurück"""
    if _save_settings(dict(DEFAULT_SETTINGS)):
        return success_response(settings=DEFAULT_SETTINGS, defaults=DEFAULT_SETTINGS)
    return error_response('Reset fehlgeschlagen', 500)
