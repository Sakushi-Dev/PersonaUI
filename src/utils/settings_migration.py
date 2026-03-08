"""
Einmalige Settings-Migrationen beim Server-Start.

Aufgaben:
1. memoriesEnabled → cortexEnabled (user-Sektion)
2. Alte Einzel-Dateien → einheitliche settings.json migrieren
"""

import json
import os

from utils.logger import log


_SETTINGS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'settings'
)
_SETTINGS_FILE = os.path.join(_SETTINGS_DIR, 'settings.json')

# Alte Einzel-Dateien und ihre Ziel-Sektionen
_OLD_FILES_MAP = {
    'user_settings.json': 'user',
    'user_profile.json': 'profile',
    'afterthought_settings.json': 'afterthought',
    'cortex_settings.json': 'cortex',
    'onboarding.json': 'onboarding',
    'window_settings.json': 'window',
    'update_state.json': 'update_state',
}


def migrate_settings():
    """Führt alle einmaligen Settings-Migrationen durch.

    Aufgerufen in der Startup-Sequenz (startup.py), NACH init_all_dbs()
    und VOR dem Start des Flask-Servers.

    Migrationen:
        1. Alte Einzel-Dateien → einheitliche settings.json
        2. memoriesEnabled → cortexEnabled (user-Sektion)
        3. .env ANTHROPIC_API_KEY → settings.json apiKey
    """
    _migrate_old_files_to_unified()
    _migrate_memories_to_cortex()
    _migrate_env_to_settings()


def _migrate_old_files_to_unified():
    """Migriert alte Einzel-Dateien in die einheitliche settings.json.

    Wenn bereits eine settings.json existiert UND keine alten Dateien mehr da sind,
    wird nichts getan. Wenn alte Dateien gefunden werden, werden deren Werte
    in die entsprechende Sektion übernommen und die alte Datei gelöscht.
    """
    # Prüfen ob alte Dateien existieren
    old_files_present = {}
    for old_name, section in _OLD_FILES_MAP.items():
        old_path = os.path.join(_SETTINGS_DIR, old_name)
        if os.path.exists(old_path):
            old_files_present[old_name] = (old_path, section)

    if not old_files_present:
        return  # Keine Migration nötig

    # Bestehende settings.json laden (falls vorhanden)
    unified = {}
    if os.path.exists(_SETTINGS_FILE):
        try:
            with open(_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                unified = json.load(f)
        except (json.JSONDecodeError, OSError):
            unified = {}

    # Alte Dateien einlesen und in Sektionen übernehmen
    migrated_count = 0
    for old_name, (old_path, section) in old_files_present.items():
        try:
            with open(old_path, 'r', encoding='utf-8') as f:
                old_data = json.load(f)
            # Nur übernehmen wenn Sektion noch nicht existiert oder leer ist
            if section not in unified or not unified[section]:
                unified[section] = old_data
            else:
                # Merge: existierende Werte behalten, neue ergänzen
                unified[section] = {**old_data, **unified[section]}
            migrated_count += 1
        except (json.JSONDecodeError, OSError) as e:
            log.error("Migration: Kann %s nicht lesen: %s", old_name, e)
            continue

    if migrated_count == 0:
        return

    # Unified settings.json schreiben
    try:
        os.makedirs(_SETTINGS_DIR, exist_ok=True)
        with open(_SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(unified, f, indent=4, ensure_ascii=False)
        log.info("Settings-Migration: %d Datei(en) in settings.json überführt", migrated_count)
    except OSError as e:
        log.error("Settings-Migration: Kann settings.json nicht schreiben: %s", e)
        return  # Alte Dateien NICHT löschen wenn Schreiben fehlschlägt

    # Alte Dateien löschen (nur wenn Schreiben erfolgreich)
    for old_name, (old_path, _section) in old_files_present.items():
        try:
            os.remove(old_path)
            log.info("Settings-Migration: %s gelöscht (migriert)", old_name)
        except OSError:
            pass  # Nicht kritisch


def _migrate_memories_to_cortex():
    """Migriert memoriesEnabled → cortexEnabled in der user-Sektion.

    - Liest settings.json user-Sektion
    - Wenn 'memoriesEnabled' vorhanden: Wert übernehmen, alten Key entfernen
    """
    if not os.path.exists(_SETTINGS_FILE):
        return

    try:
        with open(_SETTINGS_FILE, 'r', encoding='utf-8') as f:
            settings = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        log.error("Settings-Migration: Kann settings.json nicht lesen: %s", e)
        return

    user = settings.get('user', {})
    if 'memoriesEnabled' not in user:
        return  # Bereits migriert oder Neuinstallation

    # Wert übernehmen
    old_value = user.pop('memoriesEnabled')
    user['cortexEnabled'] = old_value
    settings['user'] = user

    try:
        with open(_SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
        log.info("Settings migriert: memoriesEnabled → cortexEnabled = %s", old_value)
    except OSError as e:
        log.error("Settings-Migration: Kann settings.json nicht schreiben: %s", e)


def _migrate_env_to_settings():
    """Migriert ANTHROPIC_API_KEY aus .env in settings.json und löscht .env.

    Wenn .env existiert und einen API-Key enthält, wird dieser in die
    user-Sektion von settings.json übernommen. Danach wird .env gelöscht.
    """
    _SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(_SRC_DIR, '.env')

    if not os.path.exists(env_path):
        return

    # API-Key aus .env lesen
    api_key = ''
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('ANTHROPIC_API_KEY='):
                    api_key = line.split('=', 1)[1].strip()
                    break
    except OSError as e:
        log.error("Settings-Migration: Kann .env nicht lesen: %s", e)
        return

    if api_key:
        # In settings.json schreiben
        settings = {}
        if os.path.exists(_SETTINGS_FILE):
            try:
                with open(_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
            except (json.JSONDecodeError, OSError):
                settings = {}

        user = settings.get('user', {})
        # Nur übernehmen wenn noch kein Key in settings.json
        if not user.get('apiKey'):
            user['apiKey'] = api_key
            settings['user'] = user
            try:
                with open(_SETTINGS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(settings, f, indent=4, ensure_ascii=False)
                log.info("Settings-Migration: API-Key aus .env in settings.json übernommen")
            except OSError as e:
                log.error("Settings-Migration: Kann settings.json nicht schreiben: %s", e)
                return  # .env NICHT löschen wenn Schreiben fehlschlägt

    # .env löschen
    try:
        os.remove(env_path)
        log.info("Settings-Migration: .env gelöscht (nicht mehr benötigt)")
    except OSError:
        pass
