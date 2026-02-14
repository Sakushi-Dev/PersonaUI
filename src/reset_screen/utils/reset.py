"""Reset-Sequenz – Führt den kompletten Reset mit GUI-Ausgabe durch."""

import os
import glob
import json
import random
import shutil
import time


# Base directory = src/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _type(window, text, cls='default'):
    """Tippt eine Zeile im Reset-Fenster mit Typewriter-Effekt."""
    safe = text.replace(chr(92), chr(92) + chr(92))
    safe = safe.replace(chr(39), chr(92) + chr(39))
    safe = safe.replace(chr(34), chr(92) + chr(34))
    try:
        window.evaluate_js("typeLine('" + safe + "', '" + cls + "')")
    except Exception:
        pass
    time.sleep(len(text) * 0.014 + 0.10)


def _type_bar(window, text, cls='warn', duration=800):
    """Tippt eine Zeile mit Ladebalken-Animation."""
    safe = text.replace(chr(92), chr(92) + chr(92))
    safe = safe.replace(chr(39), chr(92) + chr(39))
    safe = safe.replace(chr(34), chr(92) + chr(34))
    try:
        window.evaluate_js(
            "typeLineWithBar('" + safe + "', '" + cls + "', " + str(duration) + ")"
        )
    except Exception:
        pass
    time.sleep(len(text) * 0.014 + duration / 1000.0 + 0.15)


def _delete_files(pattern):
    """Löscht Dateien nach Glob-Pattern. Gibt Anzahl gelöschter Dateien zurück."""
    files = glob.glob(pattern)
    count = 0
    for f in files:
        try:
            os.remove(f)
            count += 1
        except Exception:
            pass
    return count


def _collect_persona_names(src_dir):
    """Sammelt alle Persona-Namen aus created_personas + active config."""
    names = []

    # Aktive Persona
    active_path = os.path.join(src_dir, 'instructions', 'personas', 'active', 'persona_config.json')
    try:
        with open(active_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            n = data.get('persona_settings', {}).get('name', '')
            if n:
                names.append(n)
    except Exception:
        pass

    # Erstellte Personas
    personas_dir = os.path.join(src_dir, 'instructions', 'created_personas')
    try:
        for fn in os.listdir(personas_dir):
            if fn.endswith('.json'):
                with open(os.path.join(personas_dir, fn), 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    n = data.get('persona_settings', {}).get('name', '')
                    if n and n not in names:
                        names.append(n)
    except Exception:
        pass

    return names


def _get_farewell_messages(names, max_count=3):
    """Generiert lustige Abschiedsmeldungen für gelöschte Personas."""
    if not names:
        return []

    templates = [
        "{name} wird dich vermissen...",
        "{name} winkt zum Abschied",
        "{name} packt ihre Sachen...",
        "{name} sagt leise 'Tschüss'",
        "{name} löscht sich selbst mit Würde",
        "{name} hatte noch so viel zu erzählen...",
        "{name} verschwindet im digitalen Nichts",
        "{name} flüstert: 'Vergiss mich nicht...'",
        "{name} dreht sich ein letztes Mal um",
        "{name}: 'Das war's wohl...'",
        "{name} ist jetzt an einem besseren Ort (Papierkorb)",
        "{name} löst sich in Einsen und Nullen auf",
        "{name} hatte gerade einen guten Witz parat...",
        "{name} nimmt ihre Erinnerungen mit",
        "{name}: 'Kein Backup? Wirklich?'",
    ]

    messages = []
    used_names = random.sample(names, min(max_count, len(names)))
    used_templates = random.sample(templates, min(max_count, len(templates)))

    for name, tmpl in zip(used_names, used_templates):
        messages.append(tmpl.format(name=name))

    return messages


def _delete_dirs_recursive(base, dirname):
    """Löscht alle Verzeichnisse mit gegebenem Namen rekursiv."""
    count = 0
    for root, dirs, _ in os.walk(base, topdown=False):
        for d in dirs:
            if d == dirname:
                try:
                    shutil.rmtree(os.path.join(root, d))
                    count += 1
                except Exception:
                    pass
    return count


def reset_sequence(window):
    """Führt den kompletten Reset durch und zeigt Fortschritt im GUI-Fenster.

    Args:
        window: pywebview-Fenster-Instanz
    """
    src = BASE_DIR
    errors = []

    _type(window, '', 'default')
    _type(window, '> Reset wird ausgeführt...', 'warn')
    _type(window, '', 'default')

    # ========================================
    # [1/9] Datenbanken
    # ========================================
    _type_bar(window, '  [1/9] Lösche Datenbanken ', 'warn', 600)
    data_dir = os.path.join(src, 'data')
    db_count = _delete_files(os.path.join(data_dir, '*.db'))
    _delete_files(os.path.join(data_dir, '*.db.backup'))
    if db_count > 0:
        _type(window, f'        {db_count} Datenbank(en) gelöscht', 'info')
    else:
        _type(window, '        Keine Datenbanken gefunden', 'default')

    # Prüfen ob .db noch da (locked?)
    remaining = glob.glob(os.path.join(data_dir, '*.db'))
    if remaining:
        _type(window, '        WARNUNG: Einige DBs konnten nicht gelöscht werden!', 'error')
        errors.append('Datenbanken konnten nicht gelöscht werden (App noch offen?)')

    # ========================================
    # [2/9] .env
    # ========================================
    _type_bar(window, '  [2/9] Lösche .env ', 'warn', 400)
    env_path = os.path.join(src, '.env')
    if os.path.exists(env_path):
        try:
            os.remove(env_path)
            _type(window, '        .env gelöscht', 'info')
        except Exception:
            _type(window, '        FEHLER: .env konnte nicht gelöscht werden', 'error')
            errors.append('.env konnte nicht gelöscht werden')
    else:
        _type(window, '        Keine .env gefunden', 'default')

    # ========================================
    # [3/9] Settings
    # ========================================
    _type_bar(window, '  [3/9] Lösche Einstellungen ', 'warn', 600)
    settings_dir = os.path.join(src, 'settings')
    for name in ['server_settings.json', 'user_settings.json', 'user_profile.json', 'window_settings.json', 'onboarding.json']:
        fp = os.path.join(settings_dir, name)
        if os.path.exists(fp):
            try:
                os.remove(fp)
                _type(window, f'        {name} gelöscht', 'info')
            except Exception:
                _type(window, f'        FEHLER: {name} konnte nicht gelöscht werden', 'error')
                errors.append(f'{name} konnte nicht gelöscht werden')
        else:
            _type(window, f'        {name} nicht vorhanden', 'default')

    # ========================================
    # [4/9] Erstellte Personas + Custom Specs
    # ========================================
    _type_bar(window, '  [4/9] Lösche Personas & Custom Specs ', 'warn', 700)
    personas_dir = os.path.join(src, 'instructions', 'created_personas')

    # Persona-Namen sammeln bevor sie gelöscht werden
    persona_names = _collect_persona_names(src)

    p_count = _delete_files(os.path.join(personas_dir, '*.json'))
    if p_count > 0:
        _type(window, f'        {p_count} Persona(s) gelöscht', 'info')
        # Lustige Abschiedsmeldungen
        farewells = _get_farewell_messages(persona_names)
        for msg in farewells:
            _type(window, f'        {msg}', 'fun')
    else:
        _type(window, '        Keine erstellten Personas gefunden', 'default')

    custom_spec = os.path.join(src, 'instructions', 'personas', 'spec', 'custom_spec', 'custom_spec.json')
    if os.path.exists(custom_spec):
        try:
            os.remove(custom_spec)
            _type(window, '        Custom Specs gelöscht', 'info')
        except Exception:
            _type(window, '        FEHLER: Custom Specs konnte nicht gelöscht werden', 'error')
    else:
        _type(window, '        Keine Custom Specs vorhanden', 'default')

    # ========================================
    # [5/9] Aktive Persona entfernen (wird beim Start auto-erstellt)
    # ========================================
    _type_bar(window, '  [5/9] Entferne aktive Persona-Config ', 'warn', 400)
    active_config = os.path.join(src, 'instructions', 'personas', 'active', 'persona_config.json')
    if os.path.exists(active_config):
        try:
            os.remove(active_config)
            _type(window, '        persona_config.json entfernt (wird beim Start auto-erstellt)', 'info')
        except Exception:
            _type(window, '        FEHLER: persona_config.json konnte nicht entfernt werden', 'error')
    else:
        _type(window, '        persona_config.json nicht vorhanden', 'default')

    # ========================================
    # [6/9] Logs
    # ========================================
    _type_bar(window, '  [6/9] Lösche Logs ', 'warn', 400)
    logs_dir = os.path.join(src, 'logs')
    log_count = _delete_files(os.path.join(logs_dir, '*.log*'))
    if log_count > 0:
        _type(window, f'        {log_count} Log-Datei(en) gelöscht', 'info')
    else:
        _type(window, '        Keine Logs gefunden', 'default')

    # ========================================
    # [7/9] Hochgeladene Avatare
    # ========================================
    _type_bar(window, '  [7/9] Lösche hochgeladene Avatare ', 'warn', 500)
    custom_dir = os.path.join(src, 'static', 'images', 'custom')
    avatar_count = 0
    if os.path.isdir(custom_dir):
        for f in os.listdir(custom_dir):
            if f != '.gitkeep':
                try:
                    os.remove(os.path.join(custom_dir, f))
                    avatar_count += 1
                except Exception:
                    pass
    if avatar_count > 0:
        _type(window, f'        {avatar_count} Avatar(e) gelöscht', 'info')
    else:
        _type(window, '        Keine Custom Avatare gefunden', 'default')

    # ========================================
    # [8/8] __pycache__ + temporäre Dateien
    # ========================================
    _type_bar(window, '  [8/9] Lösche Cache & temporäre Dateien ', 'warn', 600)
    cache_count = _delete_dirs_recursive(src, '__pycache__')
    _type(window, f'        {cache_count} __pycache__ Ordner gelöscht', 'info')

    restart_bat = os.path.join(src, 'restart_server.bat')
    if os.path.exists(restart_bat):
        try:
            os.remove(restart_bat)
            _type(window, '        restart_server.bat gelöscht', 'info')
        except Exception:
            pass

    # ========================================
    # [9/9] Prompts auf Factory-Defaults zurücksetzen
    # ========================================
    _type_bar(window, '  [9/9] Setze Prompts auf Factory-Defaults zurück ', 'warn', 500)
    try:
        instructions_dir = os.path.join(src, 'instructions')
        from utils.prompt_engine import PromptEngine
        engine = PromptEngine(instructions_dir=instructions_dir)
        result = engine.factory_reset(scope='full')
        if result.get('errors'):
            for err in result['errors']:
                _type(window, f'        FEHLER: {err}', 'error')
                errors.append(f'Prompt-Reset: {err}')
        else:
            restored = result.get('restored', 0)
            _type(window, f'        {restored} Prompt-Dateien wiederhergestellt', 'info')
    except ImportError:
        # Fallback: Manuell aus _defaults/ kopieren
        _type(window, '        PromptEngine nicht verfügbar – manueller Reset...', 'warn')
        instructions_dir = os.path.join(src, 'instructions')
        prompts_dir = os.path.join(instructions_dir, 'prompts')
        defaults_dir = os.path.join(prompts_dir, '_defaults')
        restored = 0
        if os.path.isdir(defaults_dir):
            for filename in os.listdir(defaults_dir):
                if not filename.endswith('.json'):
                    continue
                s = os.path.join(defaults_dir, filename)
                d = os.path.join(prompts_dir, filename)
                try:
                    shutil.copy2(s, d)
                    restored += 1
                except Exception:
                    errors.append(f'Prompt-Reset: {filename} fehlgeschlagen')
            # _meta/ Unterordner
            defaults_meta = os.path.join(defaults_dir, '_meta')
            if os.path.isdir(defaults_meta):
                meta_dir = os.path.join(prompts_dir, '_meta')
                os.makedirs(meta_dir, exist_ok=True)
                # User-Manifest löschen (Full-Reset)
                user_manifest = os.path.join(meta_dir, 'user_manifest.json')
                if os.path.isfile(user_manifest):
                    try:
                        os.remove(user_manifest)
                    except Exception:
                        errors.append('Prompt-Reset: user_manifest.json löschen fehlgeschlagen')
                for filename in os.listdir(defaults_meta):
                    if not filename.endswith('.json'):
                        continue
                    s = os.path.join(defaults_meta, filename)
                    d = os.path.join(meta_dir, filename)
                    try:
                        shutil.copy2(s, d)
                        restored += 1
                    except Exception:
                        errors.append(f'Prompt-Reset: _meta/{filename} fehlgeschlagen')
            _type(window, f'        {restored} Prompt-Dateien wiederhergestellt', 'info')
        else:
            _type(window, '        WARNUNG: _defaults/ Verzeichnis nicht gefunden', 'error')
            errors.append('Prompt-Reset: _defaults/ Verzeichnis fehlt')
    except Exception as e:
        _type(window, f'        WARNUNG: Prompt-Reset nicht möglich: {e}', 'warn')
        errors.append(f'Prompt-Reset: {e}')

    # ========================================
    # Ergebnis
    # ========================================
    _type(window, '', 'default')
    if errors:
        _type(window, '> Reset mit Warnungen abgeschlossen:', 'warn')
        for err in errors:
            _type(window, f'  ! {err}', 'error')
    else:
        _type(window, '> Reset erfolgreich abgeschlossen!', 'info')

    _type(window, '', 'default')
    _type(window, '> Beim nächsten Start wird alles frisch initialisiert.', 'default')
    _type(window, '> API-Schlüssel und Einstellungen müssen neu eingegeben werden.', 'default')
    _type(window, '', 'default')

    # Zeige "Schließen" oder "Starten" Button
    try:
        window.evaluate_js("showFinishButtons()")
    except Exception:
        pass
