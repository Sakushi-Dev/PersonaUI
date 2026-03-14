"""
Template loader — reads .md files from cortex_service/templates/ directory.

Templates are loaded from disk so they can be edited without touching Python code.
"""

import os
from ..logger import log

_TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')

_cache = None


def _load_templates() -> dict:
    """Loads all .md template files from the templates/ directory."""
    global _cache
    if _cache is not None:
        return _cache

    templates = {}
    if not os.path.isdir(_TEMPLATES_DIR):
        log.warning("Cortex templates directory missing: %s", _TEMPLATES_DIR)
        return templates

    for filename in os.listdir(_TEMPLATES_DIR):
        if not filename.endswith('.md'):
            continue
        filepath = os.path.join(_TEMPLATES_DIR, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                templates[filename] = f.read()
        except Exception as e:
            log.error("Failed to load cortex template %s: %s", filename, e)

    _cache = templates
    log.info("Cortex templates loaded: %s", list(templates.keys()))
    return templates


def get_templates() -> dict:
    """Returns {filename: content} for all cortex templates."""
    return dict(_load_templates())


def get_template(filename: str) -> str:
    """Returns template content for a specific file, or empty string."""
    return _load_templates().get(filename, '')


def reload_templates():
    """Clears template cache so they are re-read from disk."""
    global _cache
    _cache = None
