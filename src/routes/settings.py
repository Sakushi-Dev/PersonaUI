"""
Settings Routes - User Settings Verwaltung (serverseitig gespeichert)

Die JSON-Struktur nutzt klare Sektionen (api, interface, features, afterthought, cortex).
Die Frontend-API liefert eine geflattete Ansicht, damit get('key') weiter funktioniert.
"""
from flask import Blueprint, request
import os
import json
from utils.settings_defaults import load_model_options
from utils.settings_manager import load_section, save_section, get_section_defaults, load_defaults
from utils.logger import log
from routes.helpers import success_response, error_response, handle_route_error

settings_bp = Blueprint('settings', __name__)

# Modell-Optionen aus eigener Datei
MODEL_OPTIONS = load_model_options()

# Keys die nur aus defaults kommen und nicht gespeichert werden
_DEFAULTS_ONLY_KEYS = {'autofillModel'}

# Keys die in der cortex-Sektion leben, aber dem Frontend via user-settings bereitgestellt werden
_CORTEX_PROXY_KEYS = {'cortexEnabled', 'cortexFrequency', 'journalReminderRange'}


def _flatten_defaults():
    """Flattened die neue defaults-Struktur zu einem flachen Dict für das Frontend."""
    d = load_defaults()
    api = d.get('api', {})
    iface = d.get('interface', {})
    bubble = iface.get('bubble', {})
    theme = iface.get('theme', {})
    features = d.get('features', {})
    at = d.get('afterthought', {})

    flat = {}
    # API
    flat['apiKey'] = api.get('key', '')
    flat['apiModel'] = api.get('model', '')
    flat['autofillModel'] = api.get('autofillModel', '')
    flat['apiTemperature'] = api.get('temperature', '0.7')
    flat['contextLimit'] = api.get('contextLimit', '100')
    # Interface
    flat['uiLanguage'] = iface.get('uiLanguage', 'en')
    flat['darkMode'] = iface.get('darkMode', False)
    flat['dynamicBackground'] = iface.get('dynamicBackground', True)
    flat['notificationSound'] = iface.get('notificationSound', True)
    # Bubble
    flat['bubbleFontFamily'] = bubble.get('fontFamily', 'ubuntu')
    flat['bubbleFontSize'] = bubble.get('fontSize', '18')
    # Theme
    flat['backgroundColorDark'] = theme.get('backgroundColorDark', '#151a24')
    flat['backgroundColorLight'] = theme.get('backgroundColorLight', '#a3baff')
    flat['secondaryColorDark'] = theme.get('secondaryColorDark', '#1a2e2b')
    flat['secondaryColorLight'] = theme.get('secondaryColorLight', '#fd91ee')
    flat['gradientColor1Dark'] = theme.get('gradientColor1Dark', '#1f2d47')
    flat['gradientColor1Light'] = theme.get('gradientColor1Light', '#66cfff')
    flat['nonverbalColor'] = theme.get('nonverbalColor', '#e4ba00')
    flat['colorHue'] = theme.get('colorHue', '220')
    # Features
    flat['experimentalMode'] = features.get('experimentalMode', False)
    # Afterthought mode
    flat['afterthoughtMode'] = at.get('mode', 'off')

    return flat


# Flat defaults (cached on import)
DEFAULT_SETTINGS = _flatten_defaults()


def _load_settings():
    """Lädt Settings aus allen Sektionen, flattened für Frontend-API.
    Injiziert cortexEnabled/cortexFrequency aus der cortex-Sektion."""
    api = load_section('api')
    iface = load_section('interface')
    bubble = iface.get('bubble', {})
    theme = iface.get('theme', {})
    features = load_section('features')
    at = load_section('afterthought')
    cortex = load_section('cortex')

    flat = {}
    # API
    flat['apiKey'] = api.get('key', '')
    flat['apiModel'] = api.get('model', '')
    flat['autofillModel'] = api.get('autofillModel', '')
    flat['apiTemperature'] = api.get('temperature', '0.7')
    flat['contextLimit'] = api.get('contextLimit', '100')
    # Interface
    flat['uiLanguage'] = iface.get('uiLanguage', 'en')
    flat['darkMode'] = iface.get('darkMode', False)
    flat['dynamicBackground'] = iface.get('dynamicBackground', True)
    flat['notificationSound'] = iface.get('notificationSound', True)
    # Bubble
    flat['bubbleFontFamily'] = bubble.get('fontFamily', 'ubuntu')
    flat['bubbleFontSize'] = bubble.get('fontSize', '18')
    # Theme
    flat['backgroundColorDark'] = theme.get('backgroundColorDark', '#151a24')
    flat['backgroundColorLight'] = theme.get('backgroundColorLight', '#a3baff')
    flat['secondaryColorDark'] = theme.get('secondaryColorDark', '#1a2e2b')
    flat['secondaryColorLight'] = theme.get('secondaryColorLight', '#fd91ee')
    flat['gradientColor1Dark'] = theme.get('gradientColor1Dark', '#1f2d47')
    flat['gradientColor1Light'] = theme.get('gradientColor1Light', '#66cfff')
    flat['nonverbalColor'] = theme.get('nonverbalColor', '#e4ba00')
    flat['colorHue'] = theme.get('colorHue', '220')
    # Features
    flat['experimentalMode'] = features.get('experimentalMode', False)
    # Afterthought mode
    flat['afterthoughtMode'] = at.get('mode', 'off')
    # Cortex proxy
    flat['cortexEnabled'] = cortex.get('enabled', True)
    flat['cortexFrequency'] = cortex.get('frequency', 'medium')
    flat['journalReminderRange'] = cortex.get('journalReminderRange', [6, 12])

    return flat


# Mapping: flat frontend key → (section, nested_path)
_KEY_TO_SECTION = {
    'apiKey':              ('api', 'key'),
    'apiModel':            ('api', 'model'),
    'apiTemperature':      ('api', 'temperature'),
    'contextLimit':        ('api', 'contextLimit'),
    'uiLanguage':          ('interface', 'uiLanguage'),
    'darkMode':            ('interface', 'darkMode'),
    'dynamicBackground':   ('interface', 'dynamicBackground'),
    'notificationSound':   ('interface', 'notificationSound'),
    'bubbleFontFamily':    ('interface', 'bubble.fontFamily'),
    'bubbleFontSize':      ('interface', 'bubble.fontSize'),
    'backgroundColorDark': ('interface', 'theme.backgroundColorDark'),
    'backgroundColorLight':('interface', 'theme.backgroundColorLight'),
    'secondaryColorDark':  ('interface', 'theme.secondaryColorDark'),
    'secondaryColorLight': ('interface', 'theme.secondaryColorLight'),
    'gradientColor1Dark':  ('interface', 'theme.gradientColor1Dark'),
    'gradientColor1Light': ('interface', 'theme.gradientColor1Light'),
    'nonverbalColor':      ('interface', 'theme.nonverbalColor'),
    'colorHue':            ('interface', 'theme.colorHue'),
    'experimentalMode':    ('features', 'experimentalMode'),
    'afterthoughtMode':    ('afterthought', 'mode'),
}


def _save_settings(flat_settings):
    """Verteilt geflattete Frontend-Settings auf die richtigen Sektionen."""
    # Lade aktuelle Sektionen
    sections = {
        'api': load_section('api'),
        'interface': load_section('interface'),
        'features': load_section('features'),
        'afterthought': load_section('afterthought'),
    }

    # Stelle sicher, dass verschachtelte Objekte existieren
    sections['interface'].setdefault('bubble', {})
    sections['interface'].setdefault('theme', {})

    for key, value in flat_settings.items():
        if key in _DEFAULTS_ONLY_KEYS or key in _CORTEX_PROXY_KEYS:
            continue
        if key not in _KEY_TO_SECTION:
            continue

        section_name, path = _KEY_TO_SECTION[key]
        section = sections[section_name]

        if '.' in path:
            parts = path.split('.')
            target = section
            for part in parts[:-1]:
                target = target.setdefault(part, {})
            target[parts[-1]] = value
        else:
            section[path] = value

    # Speichere alle geänderten Sektionen
    ok = True
    for section_name, data in sections.items():
        if not save_section(section_name, data):
            ok = False
    return ok


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


# ── Afterthought Settings ──

# Afterthought Defaults
_AFTERTHOUGHT_DEFAULTS = get_section_defaults('afterthought')


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
