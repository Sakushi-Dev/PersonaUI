"""Reset sequence – Performs the reset with selectable options and GUI output."""

import os
import glob
import json
import random
import shutil
import time


# Base directory = src/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ─────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────

def _type(window, text, cls='default'):
    """Types a line in the reset window with typewriter effect."""
    safe = text.replace(chr(92), chr(92) + chr(92))
    safe = safe.replace(chr(39), chr(92) + chr(39))
    safe = safe.replace(chr(34), chr(92) + chr(34))
    try:
        window.evaluate_js("typeLine('" + safe + "', '" + cls + "')")
    except Exception:
        pass
    time.sleep(len(text) * 0.014 + 0.10)


def _type_bar(window, text, cls='warn', duration=800):
    """Types a line with progress bar animation."""
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
    """Deletes files by glob pattern. Returns the number of deleted files."""
    files = glob.glob(pattern)
    count = 0
    for f in files:
        try:
            os.remove(f)
            count += 1
        except Exception:
            pass
    return count


def _delete_dirs_recursive(base, dirname):
    """Recursively deletes all directories with the given name."""
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


# ─────────────────────────────────────────────
# Persona Detection
# ─────────────────────────────────────────────

def collect_personas(src_dir=None):
    """Collects all available personas with ID, name and status.

    Returns:
        list[dict]: [{"id": "...", "name": "...", "is_default": bool, "is_active": bool}, ...]
    """
    if src_dir is None:
        src_dir = BASE_DIR

    personas = []

    # Default Persona
    default_path = os.path.join(src_dir, 'instructions', 'personas', 'default', 'default_persona.json')
    default_name = 'Mia'
    try:
        with open(default_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            default_name = data.get('persona_settings', {}).get('name', 'Mia')
    except Exception:
        pass

    # Active persona ID
    active_id = 'default'
    active_path = os.path.join(src_dir, 'instructions', 'personas', 'active', 'persona_config.json')
    try:
        with open(active_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            active_id = data.get('active_persona_id', 'default')
    except Exception:
        pass

    personas.append({
        'id': 'default',
        'name': default_name,
        'is_default': True,
        'is_active': active_id == 'default',
    })

    # Created Personas
    personas_dir = os.path.join(src_dir, 'instructions', 'created_personas')
    if os.path.isdir(personas_dir):
        for fn in sorted(os.listdir(personas_dir)):
            if not fn.endswith('.json'):
                continue
            pid = fn.replace('.json', '')
            try:
                with open(os.path.join(personas_dir, fn), 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    name = data.get('persona_settings', {}).get('name', pid)
                    personas.append({
                        'id': pid,
                        'name': name,
                        'is_default': False,
                        'is_active': active_id == pid,
                    })
            except Exception:
                personas.append({
                    'id': pid,
                    'name': pid,
                    'is_default': False,
                    'is_active': active_id == pid,
                })

    return personas


def _collect_persona_names(src_dir):
    """Collects all persona names (for farewell messages)."""
    names = []
    for p in collect_personas(src_dir):
        if p['name']:
            names.append(p['name'])
    return names


def _get_farewell_messages(names, max_count=3):
    """Generates fun farewell messages for deleted personas."""
    if not names:
        return []

    templates = [
        "{name} will miss you...",
        "{name} waves goodbye",
        "{name} is packing their bags...",
        "{name} quietly whispers 'Goodbye'",
        "{name} deletes themselves with dignity",
        "{name} had so much more to say...",
        "{name} vanishes into the digital void",
        "{name} whispers: 'Don't forget me...'",
        "{name} turns around one last time",
        "{name}: 'So this is it...'",
        "{name} is in a better place now (recycle bin)",
        "{name} dissolves into ones and zeros",
        "{name} just had a great joke ready...",
        "{name} takes their memories with them",
        "{name}: 'No backup? Really?'",
    ]

    messages = []
    used_names = random.sample(names, min(max_count, len(names)))
    used_templates = random.sample(templates, min(max_count, len(templates)))

    for name, tmpl in zip(used_names, used_templates):
        messages.append(tmpl.format(name=name))

    return messages


# ─────────────────────────────────────────────
# Individual Reset Steps
# ─────────────────────────────────────────────

def _reset_databases(window, src, errors, persona_ids=None):
    """Deletes databases. If persona_ids given, only those."""
    data_dir = os.path.join(src, 'data')

    if persona_ids is None:
        # All databases
        db_count = _delete_files(os.path.join(data_dir, '*.db'))
        _delete_files(os.path.join(data_dir, '*.db.backup'))
        if db_count > 0:
            _type(window, f'        {db_count} database(s) deleted', 'info')
        else:
            _type(window, '        No databases found', 'default')

        remaining = glob.glob(os.path.join(data_dir, '*.db'))
        if remaining:
            _type(window, '        WARNING: Some DBs could not be deleted!', 'error')
            errors.append('Databases could not be deleted (app still running?)')
    else:
        # Only specific persona DBs
        count = 0
        for pid in persona_ids:
            if pid == 'default':
                db_path = os.path.join(data_dir, 'main.db')
            else:
                db_path = os.path.join(data_dir, f'persona_{pid}.db')

            if os.path.exists(db_path):
                try:
                    os.remove(db_path)
                    count += 1
                except Exception:
                    _type(window, f'        WARNING: DB for {pid} could not be deleted', 'error')
                    errors.append(f'DB for persona {pid} not deleted (locked?)')

            backup = db_path + '.backup'
            if os.path.exists(backup):
                try:
                    os.remove(backup)
                except Exception:
                    pass

        if count > 0:
            _type(window, f'        {count} database(s) deleted', 'info')
        else:
            _type(window, '        No matching databases found', 'default')


def _reset_env(window, src, errors):
    """Deletes the .env file (API key + secret)."""
    env_path = os.path.join(src, '.env')
    if os.path.exists(env_path):
        try:
            os.remove(env_path)
            _type(window, '        .env deleted (API key removed)', 'info')
        except Exception:
            _type(window, '        ERROR: .env could not be deleted', 'error')
            errors.append('.env could not be deleted')
    else:
        _type(window, '        No .env found', 'default')


def _reset_settings(window, src, errors):
    """Deletes settings files."""
    settings_dir = os.path.join(src, 'settings')
    targets = [
        'server_settings.json',
        'user_settings.json',
        'user_profile.json',
        'window_settings.json',
        'onboarding.json',
        'cycle_state.json',
        'emoji_usage.json',
        'cortex_settings.json',
    ]
    count = 0
    for name in targets:
        fp = os.path.join(settings_dir, name)
        if os.path.exists(fp):
            try:
                os.remove(fp)
                count += 1
            except Exception:
                _type(window, f'        ERROR: {name} could not be deleted', 'error')
                errors.append(f'{name} could not be deleted')
    if count > 0:
        _type(window, f'        {count} settings file(s) deleted', 'info')
    else:
        _type(window, '        No settings to delete', 'default')


def _reset_personas_all(window, src, errors):
    """Deletes ALL created personas + custom specs + active config."""
    personas_dir = os.path.join(src, 'instructions', 'created_personas')
    persona_names = _collect_persona_names(src)

    p_count = _delete_files(os.path.join(personas_dir, '*.json'))
    if p_count > 0:
        _type(window, f'        {p_count} persona(s) deleted', 'info')
        farewells = _get_farewell_messages(persona_names)
        for msg in farewells:
            _type(window, f'        {msg}', 'fun')
    else:
        _type(window, '        No created personas found', 'default')

    # Custom Specs
    custom_spec = os.path.join(src, 'instructions', 'personas', 'spec', 'custom_spec', 'custom_spec.json')
    if os.path.exists(custom_spec):
        try:
            os.remove(custom_spec)
            _type(window, '        Custom specs deleted', 'info')
        except Exception:
            _type(window, '        ERROR: Custom specs could not be deleted', 'error')

    # Active persona config
    active_config = os.path.join(src, 'instructions', 'personas', 'active', 'persona_config.json')
    if os.path.exists(active_config):
        try:
            os.remove(active_config)
            _type(window, '        Active persona config removed', 'info')
        except Exception:
            _type(window, '        ERROR: persona_config.json could not be removed', 'error')


def _reset_personas_selected(window, src, errors, persona_ids):
    """Deletes only selected personas (JSON + DB + Cortex + Notes)."""
    personas_dir = os.path.join(src, 'instructions', 'created_personas')
    data_dir = os.path.join(src, 'data')
    cortex_custom = os.path.join(src, 'instructions', 'personas', 'cortex', 'custom')
    persona_notes_dir = os.path.join(src, 'data', 'persona_notes')

    deleted_names = []

    for pid in persona_ids:
        name = pid

        if pid == 'default':
            # Default Persona: Only delete chat data + cortex + notes,
            # but NOT the default_persona.json (that's the template)
            _type(window, '        Deleting default persona data...', 'warn')

            # DB
            db_path = os.path.join(data_dir, 'main.db')
            if os.path.exists(db_path):
                try:
                    os.remove(db_path)
                    _type(window, '          main.db deleted', 'info')
                except Exception:
                    _type(window, '          WARNING: main.db locked', 'error')
                    errors.append('main.db could not be deleted')

            # Cortex – Default-Dateien auf Templates zurücksetzen
            cortex_default_dir = os.path.join(src, 'instructions', 'personas', 'cortex', 'default')
            if os.path.isdir(cortex_default_dir):
                try:
                    from utils.cortex_service import TEMPLATES
                    for fname, template_content in TEMPLATES.items():
                        fpath = os.path.join(cortex_default_dir, fname)
                        with open(fpath, 'w', encoding='utf-8') as f:
                            f.write(template_content)
                    _type(window, '          Cortex memory reset to templates', 'info')
                except ImportError:
                    # Fallback: Dateien löschen (werden beim nächsten Start neu erstellt)
                    for fname in ['memory.md', 'soul.md', 'relationship.md']:
                        fpath = os.path.join(cortex_default_dir, fname)
                        if os.path.isfile(fpath):
                            try:
                                os.remove(fpath)
                            except Exception:
                                pass
                    _type(window, '          Cortex files deleted (will be recreated)', 'info')
                except Exception as e:
                    _type(window, f'          WARNING: Cortex reset failed: {e}', 'error')
                    errors.append(f'Default cortex reset: {e}')

            # Notes
            notes_dir = os.path.join(persona_notes_dir, 'default')
            if os.path.isdir(notes_dir):
                for entry in os.listdir(notes_dir):
                    entry_path = os.path.join(notes_dir, entry)
                    if entry == '.gitkeep':
                        continue
                    try:
                        if os.path.isfile(entry_path):
                            os.remove(entry_path)
                        elif os.path.isdir(entry_path):
                            shutil.rmtree(entry_path)
                    except Exception:
                        pass
                _type(window, '          Persona notes deleted', 'info')

            # Reset active config if default was active
            active_config = os.path.join(src, 'instructions', 'personas', 'active', 'persona_config.json')
            try:
                with open(active_config, 'r', encoding='utf-8') as f:
                    ac = json.load(f)
                if ac.get('active_persona_id') == 'default':
                    os.remove(active_config)
                    _type(window, '          Active config removed (will be recreated on next start)', 'info')
            except Exception:
                pass

            deleted_names.append('Default')
            continue

        # Custom Persona
        persona_file = os.path.join(personas_dir, f'{pid}.json')
        if os.path.exists(persona_file):
            try:
                with open(persona_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    name = data.get('persona_settings', {}).get('name', pid)
            except Exception:
                pass
            try:
                os.remove(persona_file)
                _type(window, f'        {name} – Persona file deleted', 'info')
            except Exception:
                _type(window, f'        ERROR: {name} could not be deleted', 'error')
                errors.append(f'Persona {name} could not be deleted')

        # DB
        db_path = os.path.join(data_dir, f'persona_{pid}.db')
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
                _type(window, '          Database deleted', 'info')
            except Exception:
                _type(window, '          WARNING: Database locked', 'error')
                errors.append(f'DB for {name} not deleted')
        backup = db_path + '.backup'
        if os.path.exists(backup):
            try:
                os.remove(backup)
            except Exception:
                pass

        # Cortex custom dir
        cortex_dir = os.path.join(cortex_custom, pid)
        if os.path.isdir(cortex_dir):
            try:
                shutil.rmtree(cortex_dir)
                _type(window, '          Cortex memory deleted', 'info')
            except Exception:
                pass

        # Notes
        notes_dir = os.path.join(persona_notes_dir, pid)
        if os.path.isdir(notes_dir):
            try:
                shutil.rmtree(notes_dir)
                _type(window, '          Notes deleted', 'info')
            except Exception:
                pass

        deleted_names.append(name)

        # Falls diese Persona aktiv war, active config entfernen
        active_config = os.path.join(src, 'instructions', 'personas', 'active', 'persona_config.json')
        try:
            with open(active_config, 'r', encoding='utf-8') as f:
                ac = json.load(f)
            if ac.get('active_persona_id') == pid:
                os.remove(active_config)
                _type(window, '          Was active persona – config removed', 'warn')
        except Exception:
            pass

    # Farewell messages
    farewells = _get_farewell_messages(deleted_names)
    for msg in farewells:
        _type(window, f'        {msg}', 'fun')


def _reset_cortex(window, src, errors):
    """Deletes all Cortex custom memory files and resets default cortex to templates."""
    # 1. Custom-Cortex-Verzeichnisse löschen
    cortex_custom = os.path.join(src, 'instructions', 'personas', 'cortex', 'custom')
    cortex_count = 0
    if os.path.isdir(cortex_custom):
        for entry in os.listdir(cortex_custom):
            entry_path = os.path.join(cortex_custom, entry)
            if entry == '.gitkeep':
                continue
            if os.path.isdir(entry_path):
                try:
                    shutil.rmtree(entry_path)
                    cortex_count += 1
                except Exception:
                    pass
            elif os.path.isfile(entry_path):
                try:
                    os.remove(entry_path)
                    cortex_count += 1
                except Exception:
                    pass
    if cortex_count > 0:
        _type(window, f'        {cortex_count} cortex memory store(s) deleted', 'info')

    # 2. Default-Cortex-Dateien auf Templates zurücksetzen
    cortex_default = os.path.join(src, 'instructions', 'personas', 'cortex', 'default')
    if os.path.isdir(cortex_default):
        try:
            from utils.cortex_service import TEMPLATES
            for fname, template_content in TEMPLATES.items():
                fpath = os.path.join(cortex_default, fname)
                with open(fpath, 'w', encoding='utf-8') as f:
                    f.write(template_content)
            _type(window, '        Default cortex memory reset to templates', 'info')
        except ImportError:
            for fname in ['memory.md', 'soul.md', 'relationship.md']:
                fpath = os.path.join(cortex_default, fname)
                if os.path.isfile(fpath):
                    try:
                        os.remove(fpath)
                    except Exception:
                        pass
            _type(window, '        Default cortex files deleted (will be recreated)', 'info')
        except Exception as e:
            _type(window, f'        WARNING: Default cortex reset failed: {e}', 'error')
            errors.append(f'Default cortex reset: {e}')
    elif cortex_count == 0:
        _type(window, '        No cortex data found', 'default')


def _reset_persona_notes(window, src, errors):
    """Deletes all persona notes."""
    persona_notes_dir = os.path.join(src, 'data', 'persona_notes')
    notes_count = 0
    if os.path.isdir(persona_notes_dir):
        for entry in os.listdir(persona_notes_dir):
            entry_path = os.path.join(persona_notes_dir, entry)
            if entry in ('.gitkeep', 'default'):
                continue
            if os.path.isdir(entry_path):
                try:
                    shutil.rmtree(entry_path)
                    notes_count += 1
                except Exception:
                    pass
            elif os.path.isfile(entry_path):
                try:
                    os.remove(entry_path)
                    notes_count += 1
                except Exception:
                    pass
    if notes_count > 0:
        _type(window, f'        {notes_count} persona note(s) deleted', 'info')
    else:
        _type(window, '        No persona notes found', 'default')


def _reset_logs(window, src, errors):
    """Deletes all log files."""
    logs_dir = os.path.join(src, 'logs')
    log_count = _delete_files(os.path.join(logs_dir, '*.log*'))
    if log_count > 0:
        _type(window, f'        {log_count} log file(s) deleted', 'info')
    else:
        _type(window, '        No logs found', 'default')


def _reset_avatars(window, src, errors):
    """Deletes uploaded avatars + index."""
    project_root = os.path.dirname(src)
    custom_dir = os.path.join(project_root, 'frontend', 'public', 'avatar', 'costum')
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
        _type(window, f'        {avatar_count} avatar(s) deleted', 'info')
    else:
        _type(window, '        No custom avatars found', 'default')

    avatar_index = os.path.join(project_root, 'frontend', 'public', 'avatar', 'index.json')
    if os.path.exists(avatar_index):
        try:
            os.remove(avatar_index)
            _type(window, '        Avatar index removed (will be rebuilt on next start)', 'info')
        except Exception:
            pass


def _reset_cache(window, src, errors):
    """Deletes __pycache__ + temporary files."""
    cache_count = _delete_dirs_recursive(src, '__pycache__')
    _type(window, f'        {cache_count} __pycache__ folder(s) deleted', 'info')

    restart_bat = os.path.join(src, 'restart_server.bat')
    if os.path.exists(restart_bat):
        try:
            os.remove(restart_bat)
            _type(window, '        restart_server.bat deleted', 'info')
        except Exception:
            pass


def _reset_prompts(window, src, errors):
    """Resets prompts to factory defaults."""
    try:
        instructions_dir = os.path.join(src, 'instructions')
        from utils.prompt_engine import PromptEngine
        engine = PromptEngine(instructions_dir=instructions_dir)
        result = engine.factory_reset(scope='full')
        if result.get('errors'):
            for err in result['errors']:
                _type(window, f'        ERROR: {err}', 'error')
                errors.append(f'Prompt reset: {err}')
        else:
            restored = result.get('restored', 0)
            _type(window, f'        {restored} prompt file(s) restored', 'info')
    except ImportError:
        _type(window, '        PromptEngine not available – manual reset...', 'warn')
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
                    errors.append(f'Prompt reset: {filename} failed')
            defaults_meta = os.path.join(defaults_dir, '_meta')
            if os.path.isdir(defaults_meta):
                meta_dir = os.path.join(prompts_dir, '_meta')
                os.makedirs(meta_dir, exist_ok=True)
                user_manifest = os.path.join(meta_dir, 'user_manifest.json')
                if os.path.isfile(user_manifest):
                    try:
                        os.remove(user_manifest)
                    except Exception:
                        errors.append('Prompt reset: user_manifest.json deletion failed')
                for filename in os.listdir(defaults_meta):
                    if not filename.endswith('.json'):
                        continue
                    s = os.path.join(defaults_meta, filename)
                    d = os.path.join(meta_dir, filename)
                    try:
                        shutil.copy2(s, d)
                        restored += 1
                    except Exception:
                        errors.append(f'Prompt reset: _meta/{filename} failed')
            _type(window, f'        {restored} prompt file(s) restored', 'info')
        else:
            _type(window, '        WARNING: _defaults/ directory not found', 'error')
            errors.append('Prompt reset: _defaults/ directory missing')
    except Exception as e:
        _type(window, f'        WARNING: Prompt reset not possible: {e}', 'warn')
        errors.append(f'Prompt reset: {e}')


# ─────────────────────────────────────────────
# Preset Definitions
# ─────────────────────────────────────────────

PRESETS = {
    'full': {
        'name': 'Full Reset',
        'desc': 'Deletes all data and restores everything to factory defaults.',
        'steps': ['databases', 'env', 'settings', 'personas_all', 'cortex',
                  'persona_notes', 'logs', 'avatars', 'cache', 'prompts'],
    },
    'keep_api': {
        'name': 'Reset (Keep API Key)',
        'desc': 'Like full reset, but your API key is preserved.',
        'steps': ['databases', 'settings', 'personas_all', 'cortex',
                  'persona_notes', 'logs', 'avatars', 'cache', 'prompts'],
    },
    'chat_only': {
        'name': 'Chat Data Only',
        'desc': 'Deletes all chat messages, sessions and cortex memory for all personas.',
        'steps': ['databases', 'cortex'],
    },
    'personas_select': {
        'name': 'Select Personas',
        'desc': 'Choose individual personas to delete (incl. their chats, cortex & notes).',
        'steps': ['personas_selected'],
    },
    'settings_only': {
        'name': 'Settings & Profile',
        'desc': 'Resets settings, profile and onboarding.',
        'steps': ['settings'],
    },
    'prompts_only': {
        'name': 'Reset Prompts',
        'desc': 'Restores all prompt files to factory defaults.',
        'steps': ['prompts'],
    },
    'troubleshoot': {
        'name': 'Troubleshoot',
        'desc': 'Clears cache, logs and temporary files. Fixes common startup issues.',
        'steps': ['cache', 'logs'],
    },
}

PRESET_ORDER = ['full', 'keep_api', 'chat_only', 'personas_select',
                'settings_only', 'prompts_only', 'troubleshoot']


STEP_LABELS = {
    'databases':         'Delete databases',
    'env':               'Delete .env (API key)',
    'settings':          'Delete settings',
    'personas_all':      'Delete all personas',
    'personas_selected': 'Delete selected personas',
    'cortex':            'Delete cortex memory',
    'persona_notes':     'Delete persona notes',
    'logs':              'Delete logs',
    'avatars':           'Delete avatars',
    'cache':             'Clear cache & temp',
    'prompts':           'Reset prompts',
}


# ─────────────────────────────────────────────
# Main Reset Sequence
# ─────────────────────────────────────────────

def reset_sequence(window, preset_id='full', selected_persona_ids=None):
    """Executes the reset based on the selected preset.

    Args:
        window:               pywebview window instance
        preset_id:            ID of the selected preset (e.g. 'full', 'keep_api', ...)
        selected_persona_ids: List of persona IDs (only for 'personas_select')
    """
    src = BASE_DIR
    errors = []

    preset = PRESETS.get(preset_id, PRESETS['full'])
    steps = preset['steps']
    total = len(steps)

    _type(window, '', 'default')
    _type(window, f'> Running {preset["name"]}...', 'warn')
    _type(window, '', 'default')

    for idx, step in enumerate(steps, 1):
        label = STEP_LABELS.get(step, step)
        _type_bar(window, f'  [{idx}/{total}] {label} ', 'warn', 600)

        if step == 'databases':
            _reset_databases(window, src, errors)
        elif step == 'env':
            _reset_env(window, src, errors)
        elif step == 'settings':
            _reset_settings(window, src, errors)
        elif step == 'personas_all':
            _reset_personas_all(window, src, errors)
        elif step == 'personas_selected':
            if selected_persona_ids:
                _reset_personas_selected(window, src, errors, selected_persona_ids)
            else:
                _type(window, '        No personas selected', 'default')
        elif step == 'cortex':
            _reset_cortex(window, src, errors)
        elif step == 'persona_notes':
            _reset_persona_notes(window, src, errors)
        elif step == 'logs':
            _reset_logs(window, src, errors)
        elif step == 'avatars':
            _reset_avatars(window, src, errors)
        elif step == 'cache':
            _reset_cache(window, src, errors)
        elif step == 'prompts':
            _reset_prompts(window, src, errors)

    # ── Result ──
    _type(window, '', 'default')
    if errors:
        _type(window, '> Reset completed with warnings:', 'warn')
        for err in errors:
            _type(window, f'  ! {err}', 'error')
    else:
        _type(window, '> Reset completed successfully!', 'info')

    _type(window, '', 'default')

    # Hints per preset
    if preset_id == 'full':
        _type(window, '> Everything will be freshly initialized on next start.', 'default')
        _type(window, '> API key and settings will need to be entered again.', 'default')
    elif preset_id == 'keep_api':
        _type(window, '> Everything will be freshly initialized on next start.', 'default')
        _type(window, '> Your API key has been preserved.', 'info')
    elif preset_id == 'chat_only':
        _type(window, '> All chat data has been deleted. Personas & settings remain intact.', 'default')
    elif preset_id == 'personas_select':
        _type(window, '> Selected personas have been removed.', 'default')
    elif preset_id == 'settings_only':
        _type(window, '> Settings reset. Onboarding will be shown again on next start.', 'default')
    elif preset_id == 'prompts_only':
        _type(window, '> Prompts have been restored to factory defaults.', 'default')
    elif preset_id == 'troubleshoot':
        _type(window, '> Cache and logs have been cleared. App should start normally again.', 'default')

    _type(window, '', 'default')

    # Show "Close" or "Start" button
    try:
        window.evaluate_js("showFinishButtons()")
    except Exception:
        pass
