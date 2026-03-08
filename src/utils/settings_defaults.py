"""
Hilfsfunktionen zum Laden von Settings-Defaults.

Delegiert an den zentralen settings_manager für die Defaults-Struktur.
model_options.json bleibt separat (read-only Developer-Config).
"""

import json
import os
from typing import Any, Dict, List, Optional


_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MODEL_OPTIONS_FILE = os.path.join(_BASE_DIR, 'settings', 'default', 'model_options.json')
_MODEL_OPTIONS_CACHE: Optional[List[Dict[str, Any]]] = None


def load_defaults() -> Dict[str, Any]:
    """Ladet Default-Settings (user-Sektion) aus defaults.json."""
    from utils.settings_manager import get_section_defaults
    return get_section_defaults('user')


def get_default(key: str, fallback: Any = None) -> Any:
    """Gibt einen Default-Wert zurück (user-Sektion)."""
    defaults = load_defaults()
    return defaults.get(key, fallback)


def get_api_model_default() -> Optional[str]:
    """Gibt das Default-Modell für die API zurück."""
    return get_default('apiModel')


def load_model_options() -> List[Dict[str, Any]]:
    """Lädt Modell-Optionen aus model_options.json."""
    global _MODEL_OPTIONS_CACHE
    if _MODEL_OPTIONS_CACHE is not None:
        return _MODEL_OPTIONS_CACHE
    try:
        with open(_MODEL_OPTIONS_FILE, 'r', encoding='utf-8') as f:
            _MODEL_OPTIONS_CACHE = json.load(f)
    except Exception:
        _MODEL_OPTIONS_CACHE = []
    return _MODEL_OPTIONS_CACHE


def get_api_model_options() -> List[Dict[str, Any]]:
    """Gibt die Modell-Optionen inkl. Meta zurück."""
    return load_model_options()


def get_autofill_model() -> Optional[str]:
    """Gibt das Default-Modell für Auto-Fill zurück."""
    return get_default('apiAutofillModel') or get_default('apiModel')
