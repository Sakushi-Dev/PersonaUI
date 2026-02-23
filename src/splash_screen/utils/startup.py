"""Startup sequence and helpers for the splash screen."""

import os
import time
import random
import socket as sock
import threading

from utils.database import init_all_dbs
from utils.cortex_service import ensure_cortex_dirs
from splash_screen.utils.update_check import check_for_update


# ---------------------------------------------------------------------------
# Splash typing helpers
# ---------------------------------------------------------------------------

def splash_type(window, text, cls='default'):
    """Type a line in the splash window with typewriter effect."""
    safe = text.replace(chr(92), chr(92) + chr(92))
    safe = safe.replace(chr(39), chr(92) + chr(39))
    safe = safe.replace(chr(34), chr(92) + chr(34))
    try:
        window.evaluate_js("typeLine('" + safe + "', '" + cls + "')")
    except Exception:
        pass
    # Wait for typing animation to finish (18ms per char + 80ms pause)
    time.sleep(len(text) * 0.018 + 0.12)


def splash_type_bar(window, text, cls='fun', duration=1500):
    """Type a line with loading bar animation."""
    safe = text.replace(chr(92), chr(92) + chr(92))
    safe = safe.replace(chr(39), chr(92) + chr(39))
    safe = safe.replace(chr(34), chr(92) + chr(34))
    try:
        window.evaluate_js(
            "typeLineWithBar('" + safe + "', '" + cls + "', " + str(duration) + ")"
        )
    except Exception:
        pass
    # Wait: typing time + bar duration
    time.sleep(len(text) * 0.018 + duration / 1000.0 + 0.15)


# ---------------------------------------------------------------------------
# Fun loading messages
# ---------------------------------------------------------------------------

def get_fun_messages():
    """Read persona names and generate fun loading messages."""
    import json as j

    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # src/
    personas_dir = os.path.join(base, 'instructions', 'created_personas')
    active_path = os.path.join(
        base, 'instructions', 'personas', 'active', 'persona_config.json'
    )

    names = []

    # Read active persona
    try:
        with open(active_path, 'r', encoding='utf-8') as f:
            data = j.load(f)
            n = data.get('persona_settings', {}).get('name', '')
            if n:
                names.append(n)
    except Exception:
        pass

    # Read created personas
    try:
        for fn in os.listdir(personas_dir):
            if fn.endswith('.json'):
                with open(os.path.join(personas_dir, fn), 'r', encoding='utf-8') as f:
                    data = j.load(f)
                    n = data.get('persona_settings', {}).get('name', '')
                    if n and n not in names:
                        names.append(n)
    except Exception:
        pass

    if not names:
        names = ['Persona']

    templates = [
        ("Loading {name}'s emotions", 1800),
        ("Calibrating {name}'s personality", 1500),
        ("Waking {name} from sleep", 1200),
        ("Sorting {name}'s memories", 1600),
        ("{name} is practicing their first sentence", 1400),
        ("Brewing coffee for {name}", 1000),
        ("Setting {name}'s mood to 'good'", 1300),
        ("{name} is getting ready", 1100),
        ("Shuffling {name}'s conversation topics", 1500),
        ("{name} is warming up their neurons", 1200),
        ("Activating {name}'s humor module", 1400),
        ("{name} is secretly reading your old chats", 1700),
        ("Optimizing {name}'s response time", 1300),
        ("{name} is choosing an outfit", 1100),
        ("Boosting {name}'s empathy level", 1500),
    ]

    # 1 random message with ONE random persona
    name = random.choice(names)
    tmpl, dur = random.choice(templates)
    return [(tmpl.format(name=name), dur)]


# ---------------------------------------------------------------------------
# Startup sequence
# ---------------------------------------------------------------------------

def startup_sequence(window, server_mode, server_port, start_flask_fn, host, dev_mode=False):
    """Initialize everything and type output into the splash window.

    Args:
        window:          pywebview window instance
        server_mode:     'local' or 'listen'
        server_port:     port number
        start_flask_fn:  callable to start the Flask server
        host:            host address
        dev_mode:        True if --dev flag is set (Vite dev server)
    """
    from splash_screen.utils.update_check import get_local_version

    local_ver = get_local_version() or 'unknown'

    # Type startup messages
    splash_type(window, f'> Starting PersonaUI v{local_ver}...', 'info')
    cwd = os.getcwd()
    short_path = os.path.join(os.path.basename(os.path.dirname(cwd)), os.path.basename(cwd))
    splash_type(window, f'> Working directory: .../{short_path}', 'default')
    splash_type(window, '', 'default')

    # Update check: compare local version against origin/main
    splash_type(window, '> Checking for updates...', 'default')
    try:
        update_info = check_for_update()
        error = update_info.get('error')
        if error and 'no network' in error:
            splash_type(window, '  Update check skipped (no network).', 'default')
        elif update_info.get('available'):
            remote_ver = update_info.get('remote_version', '?')
            splash_type(window, '', 'default')
            splash_type(window, f'  *** New version available: v{remote_ver} (current: v{local_ver}) ***', 'warn')
            splash_type(window, '  Run bin/update.bat to update.', 'warn')
            splash_type(window, '', 'default')
        else:
            splash_type(window, f'  PersonaUI is up to date (v{local_ver}).', 'info')
    except Exception:
        splash_type(window, '  Update check skipped.', 'default')
    splash_type(window, '', 'default')

    # Initialize databases
    splash_type(window, '> Initializing databases...', 'default')
    init_all_dbs()
    splash_type(window, '  Databases ready.', 'info')
    splash_type(window, '', 'default')

    # Ensure Cortex directories
    splash_type(window, '> Checking Cortex directories...', 'default')
    ensure_cortex_dirs()
    splash_type(window, '  Cortex ready.', 'info')
    splash_type(window, '', 'default')

    # Settings migration (memoriesEnabled → cortexEnabled)
    splash_type(window, '> Checking settings migration...', 'default')
    from utils.settings_migration import migrate_settings
    migrate_settings()
    splash_type(window, '  Settings ready.', 'info')
    splash_type(window, '', 'default')

    # Fun persona loading messages
    fun_msgs = get_fun_messages()
    for msg, dur in fun_msgs:
        splash_type_bar(window, '  ' + msg + ' ', 'fun', dur)
    splash_type(window, '', 'default')

    # Determine and display host/IP
    if server_mode == 'listen':
        try:
            s = sock.socket(sock.AF_INET, sock.SOCK_DGRAM)
            s.settimeout(0)
            s.connect(('8.8.8.8', 80))
            primary_ip = s.getsockname()[0]
            s.close()
            splash_type(window, f'> Server mode: listen ({primary_ip})', 'default')
        except Exception:
            splash_type(window, '> Server mode: listen', 'default')
    else:
        splash_type(window, '> Server mode: local', 'default')

    splash_type(window, f'> Port: {server_port}', 'default')
    splash_type(window, '', 'default')
    splash_type(window, '> Starting Flask server...', 'default')

    # Start Flask server in background
    server_thread = threading.Thread(
        target=start_flask_fn,
        args=(host, server_port),
        daemon=True,
    )
    server_thread.start()

    # Wait until server responds (fast socket check)
    max_wait = 30
    waited = 0
    ready = False

    while waited < max_wait:
        try:
            s = sock.socket(sock.AF_INET, sock.SOCK_STREAM)
            s.settimeout(0.5)
            s.connect(('127.0.0.1', server_port))
            s.close()
            ready = True
            break
        except Exception:
            time.sleep(0.3)
            waited += 0.3
            if waited % 3 < 0.5:
                splash_type(window, f'  Server starting... ({int(waited)}s)', 'default')

    if ready:
        splash_type(window, '', 'default')
        splash_type(window, '> Server ready!', 'info')

        if dev_mode:
            # Dev-Modus: Auf Vite Dev-Server warten und laden
            vite_port = 5173
            splash_type(window, '> Waiting for Vite dev server (port 5173)...', 'info')
            vite_waited = 0
            vite_ready = False
            vite_max_wait = 30  # npm + Vite can take >15s on Windows
            while vite_waited < vite_max_wait:
                try:
                    # Actual HTTP request instead of just socket check
                    from urllib.request import urlopen
                    resp = urlopen(f'http://localhost:{vite_port}/', timeout=2)
                    resp.close()
                    vite_ready = True
                    break
                except Exception:
                    time.sleep(0.5)
                    vite_waited += 0.5
                    if vite_waited % 5 < 0.6:
                        splash_type(window, f'  Vite starting... ({int(vite_waited)}s)', 'default')
            if vite_ready:
                splash_type(window, '> Vite dev server ready! (HMR active)', 'info')
                time.sleep(0.5)
                window.load_url(f"http://localhost:{vite_port}")
            else:
                splash_type(window, '> Vite dev server unreachable after 30s, loading Flask UI...', 'warn')
                time.sleep(0.5)
                window.load_url(f"http://127.0.0.1:{server_port}")
        else:
            splash_type(window, '> Loading interface...', 'info')
            time.sleep(0.5)
            # Load app in the same window
            window.load_url(f"http://127.0.0.1:{server_port}")
    else:
        splash_type(window, '> Server could not be started!', 'error')
        splash_type(window, f'  Timeout after {max_wait} seconds.', 'error')
