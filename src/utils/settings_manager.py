"""
Zentraler Settings Manager — Alle Settings in einer einzigen settings.json.

Sektionen:
    api          – API-Konfiguration (Key, Modell, Temperatur, …)
    interface    – UI-Einstellungen (Sprache, Theme, Fonts, …)
    features     – Feature-Flags (experimentalMode)
    afterthought – Afterthought-System (Mode, Phasen, Frequenzen)
    cortex       – Cortex-System (enabled, frequency)
    profile      – Benutzerprofil (Name, Avatar, …)
    initialization – First-Run Status (completed, disclaimer)
    window       – Fensterposition/-größe (PyWebView)
    update_state – Letzter erfolgreicher Update-Versionsstand
"""

import json
import os
import threading
from typing import Any, Dict, Optional

from utils.logger import log


# ─── Pfade ────────────────────────────────────────────────────────────────────

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SETTINGS_DIR = os.path.join(_BASE_DIR, 'settings')
SETTINGS_FILE = os.path.join(_SETTINGS_DIR, 'settings.json')
DEFAULTS_FILE = os.path.join(_SETTINGS_DIR, 'default', 'defaults.json')

# Alle gültigen Sektionen
SECTIONS = ('api', 'interface', 'features', 'afterthought', 'cortex', 'profile', 'initialization', 'window', 'update_state')

# ─── Interner State ───────────────────────────────────────────────────────────

_lock = threading.Lock()
_cache: Optional[Dict[str, Any]] = None
_defaults_cache: Optional[Dict[str, Any]] = None


# ─── Defaults ─────────────────────────────────────────────────────────────────

def load_defaults() -> Dict[str, Any]:
    """Lädt die gesamte defaults.json (gecached)."""
    global _defaults_cache
    if _defaults_cache is not None:
        return _defaults_cache
    try:
        with open(DEFAULTS_FILE, 'r', encoding='utf-8') as f:
            _defaults_cache = json.load(f)
    except Exception:
        _defaults_cache = {}
    return _defaults_cache


def get_section_defaults(section: str) -> Dict[str, Any]:
    """Gibt die Defaults für eine bestimmte Sektion zurück."""
    return dict(load_defaults().get(section, {}))


# ─── Laden ────────────────────────────────────────────────────────────────────

def load_all() -> Dict[str, Any]:
    """Lädt die gesamte settings.json, gemerged mit Defaults."""
    global _cache
    if _cache is not None:
        return _cache

    defaults = load_defaults()
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                saved = json.load(f)
            # Deep-Merge pro Sektion
            merged = {}
            for section in SECTIONS:
                merged[section] = {**defaults.get(section, {}), **saved.get(section, {})}
            _cache = merged
            return merged
    except Exception as e:
        log.error("Fehler beim Laden der Settings: %s", e)

    # Fallback: nur Defaults
    _cache = {s: dict(defaults.get(s, {})) for s in SECTIONS}
    return _cache


def load_section(section: str) -> Dict[str, Any]:
    """Lädt eine Sektion aus settings.json (gemerged mit Defaults)."""
    return dict(load_all().get(section, {}))


def get_value(section: str, key: str, fallback: Any = None) -> Any:
    """Liest einen einzelnen Wert aus einer Sektion."""
    return load_section(section).get(key, fallback)


# ─── Speichern ────────────────────────────────────────────────────────────────

def save_section(section: str, data: Dict[str, Any]) -> bool:
    """Speichert eine Sektion in settings.json (überschreibt nur diese Sektion)."""
    global _cache
    with _lock:
        try:
            all_settings = {}
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    all_settings = json.load(f)
            all_settings[section] = data
            os.makedirs(_SETTINGS_DIR, exist_ok=True)
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(all_settings, f, indent=4, ensure_ascii=False)
            _cache = None  # Cache invalidieren
            return True
        except Exception as e:
            log.error("Fehler beim Speichern der Settings (%s): %s", section, e)
            return False


def save_all(data: Dict[str, Any]) -> bool:
    """Speichert die gesamte settings.json."""
    global _cache
    with _lock:
        try:
            os.makedirs(_SETTINGS_DIR, exist_ok=True)
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            _cache = None
            return True
        except Exception as e:
            log.error("Fehler beim Speichern aller Settings: %s", e)
            return False


# ─── Reset ────────────────────────────────────────────────────────────────────

def reset_all() -> bool:
    """Setzt alle Settings auf Defaults zurück."""
    defaults = load_defaults()
    return save_all(dict(defaults))


def reset_section(section: str) -> bool:
    """Setzt eine Sektion auf Defaults zurück."""
    return save_section(section, get_section_defaults(section))


# ─── Cache ────────────────────────────────────────────────────────────────────

def invalidate_cache():
    """Invalidiert den Settings-Cache (z.B. nach externem Schreiben)."""
    global _cache, _defaults_cache
    _cache = None
    _defaults_cache = None
