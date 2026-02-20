"""
Einmalige Settings-Migrationen beim Server-Start.

Aufgaben:
1. memoriesEnabled → cortexEnabled (user_settings.json)
2. cortex_settings.json Erstanlage (falls nicht vorhanden)
"""

import json
import os

from utils.logger import log


_SETTINGS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'settings'
)
_USER_SETTINGS_FILE = os.path.join(_SETTINGS_DIR, 'user_settings.json')
_CORTEX_SETTINGS_FILE = os.path.join(_SETTINGS_DIR, 'cortex_settings.json')

# Standard-Werte für cortex_settings.json (vereinfachtes Modell)
_CORTEX_DEFAULTS = {
    "enabled": True,
    "frequency": "medium",
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
            json.dump(settings, f, indent=4, ensure_ascii=False)
        log.info("Settings migriert: memoriesEnabled → cortexEnabled = %s", old_value)
    except OSError as e:
        log.error("Settings-Migration: Kann user_settings.json nicht schreiben: %s", e)


def _ensure_cortex_settings():
    """Erstellt cortex_settings.json mit Standardwerten, falls nicht vorhanden.

    Wenn die Datei bereits existiert, werden fehlende Keys ergänzt (forward-compatible).
    Bestehende Werte werden NICHT überschrieben.
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
                    log.info(
                        "cortex_settings.json: Key '%s' ergänzt (Default: %s)",
                        key, default_value
                    )

            if updated:
                with open(_CORTEX_SETTINGS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(existing, f, indent=4, ensure_ascii=False)
        except (json.JSONDecodeError, OSError) as e:
            log.error(
                "Settings-Migration: Fehler bei cortex_settings.json Aktualisierung: %s",
                e
            )
        return

    # Datei existiert nicht — Neuanlage
    try:
        os.makedirs(os.path.dirname(_CORTEX_SETTINGS_FILE), exist_ok=True)
        with open(_CORTEX_SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(_CORTEX_DEFAULTS, f, indent=4, ensure_ascii=False)
        log.info("cortex_settings.json erstellt mit Standardwerten")
    except OSError as e:
        log.error("Settings-Migration: Kann cortex_settings.json nicht erstellen: %s", e)
