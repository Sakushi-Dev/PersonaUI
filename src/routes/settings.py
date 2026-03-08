"""
Settings Routes - User Settings Verwaltung (serverseitig gespeichert)
"""
from flask import Blueprint, request
import os
import json
from utils.settings_defaults import load_defaults, load_model_options
from utils.settings_manager import load_section, save_section, get_section_defaults
from utils.logger import log
from routes.helpers import success_response, error_response, handle_route_error

settings_bp = Blueprint('settings', __name__)

# Default-Werte (user-Sektion aus defaults.json)
DEFAULT_SETTINGS = load_defaults()

# Modell-Optionen aus eigener Datei
MODEL_OPTIONS = load_model_options()

# Keys die nur aus defaults kommen und nicht in user-Sektion gespeichert werden
_DEFAULTS_ONLY_KEYS = {'apiAutofillModel'}

# Nachgedanke/Afterthought Defaults
_AFTERTHOUGHT_DEFAULTS = get_section_defaults('afterthought')


def _load_settings():
    """Lädt User-Settings aus settings.json (user-Sektion)"""
    return load_section('user')


def _save_settings(settings):
    """Speichert User-Settings in settings.json (ohne defaults-only Keys)"""
    filtered = {k: v for k, v in settings.items() if k not in _DEFAULTS_ONLY_KEYS}
    return save_section('user', filtered)


@settings_bp.route('/api/user-settings', methods=['GET'])
@handle_route_error('get_user_settings')
def get_user_settings():
    """Gibt alle User-Settings zurück"""
    settings = _load_settings()
    return success_response(settings=settings, defaults={**DEFAULT_SETTINGS, 'apiModelOptions': MODEL_OPTIONS})


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
        return success_response(settings=current, defaults={**DEFAULT_SETTINGS, 'apiModelOptions': MODEL_OPTIONS})
    else:
        return error_response('Speichern fehlgeschlagen', 500)


@settings_bp.route('/api/user-settings/reset', methods=['POST'])
@handle_route_error('reset_user_settings')
def reset_user_settings():
    """Setzt alle User-Settings auf Standardwerte zurück"""
    if _save_settings(dict(DEFAULT_SETTINGS)):
        return success_response(settings=DEFAULT_SETTINGS, defaults={**DEFAULT_SETTINGS, 'apiModelOptions': MODEL_OPTIONS})
    return error_response('Reset fehlgeschlagen', 500)


# ── Nachgedanke / Afterthought Settings ──

def load_afterthought_settings():
    """Lädt Nachgedanke-Settings aus settings.json (afterthought-Sektion)"""
    return load_section('afterthought')


def _save_afterthought_settings(settings):
    """Speichert Nachgedanke-Settings in settings.json (afterthought-Sektion)"""
    return save_section('afterthought', settings)


@settings_bp.route('/api/afterthought-settings', methods=['GET'])
@handle_route_error('get_afterthought_settings')
def get_afterthought_settings():
    """Gibt Nachgedanke-Settings zurück (Phasen-Zeiten, Frequenzen)"""
    settings = load_afterthought_settings()
    return success_response(settings=settings, defaults=_AFTERTHOUGHT_DEFAULTS)


@settings_bp.route('/api/afterthought-settings', methods=['PUT'])
@handle_route_error('update_afterthought_settings')
def update_afterthought_settings():
    """Aktualisiert Nachgedanke-Settings (partial update)"""
    data = request.get_json()
    if not data:
        return error_response('Keine Daten')

    current = load_afterthought_settings()
    current.update(data)

    if _save_afterthought_settings(current):
        return success_response(settings=current, defaults=_AFTERTHOUGHT_DEFAULTS)
    else:
        return error_response('Speichern fehlgeschlagen', 500)
