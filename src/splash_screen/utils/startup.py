"""Startup-Sequenz und Helfer für den Splash-Screen."""

import os
import time
import random
import socket as sock
import threading

from utils.database import init_all_dbs
from splash_screen.utils.update_check import check_for_update


# ---------------------------------------------------------------------------
# Splash-Typing Helfer
# ---------------------------------------------------------------------------

def splash_type(window, text, cls='default'):
    """Tippt eine Zeile im Splash-Fenster mit Typewriter-Effekt."""
    safe = text.replace(chr(92), chr(92) + chr(92))
    safe = safe.replace(chr(39), chr(92) + chr(39))
    safe = safe.replace(chr(34), chr(92) + chr(34))
    try:
        window.evaluate_js("typeLine('" + safe + "', '" + cls + "')")
    except Exception:
        pass
    # Warte bis Tipp-Animation fertig (18ms pro Zeichen + 80ms Pause)
    time.sleep(len(text) * 0.018 + 0.12)


def splash_type_bar(window, text, cls='fun', duration=1500):
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
    # Warte: Tipp-Zeit + Balken-Dauer
    time.sleep(len(text) * 0.018 + duration / 1000.0 + 0.15)


# ---------------------------------------------------------------------------
# Lustige Lademeldungen
# ---------------------------------------------------------------------------

def get_fun_messages():
    """Liest Persona-Namen und generiert lustige Lademeldungen."""
    import json as j

    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # src/
    personas_dir = os.path.join(base, 'instructions', 'created_personas')
    active_path = os.path.join(
        base, 'instructions', 'personas', 'active', 'persona_config.json'
    )

    names = []

    # Aktive Persona lesen
    try:
        with open(active_path, 'r', encoding='utf-8') as f:
            data = j.load(f)
            n = data.get('persona_settings', {}).get('name', '')
            if n:
                names.append(n)
    except Exception:
        pass

    # Erstellte Personas lesen
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
        ("{name}'s Emotionen werden geladen", 1800),
        ("{name}'s Persönlichkeit wird kalibriert", 1500),
        ("{name} wird aus dem Schlaf geweckt", 1200),
        ("{name}'s Erinnerungen werden sortiert", 1600),
        ("{name} übt gerade ihren ersten Satz", 1400),
        ("Kaffee für {name} wird gekocht", 1000),
        ("{name}'s Laune wird auf 'gut' gestellt", 1300),
        ("{name} macht sich hübsch", 1100),
        ("{name}'s Gesprächsthemen werden gemischt", 1500),
        ("{name} wärmt ihre Neuronen auf", 1200),
        ("{name}'s Humor-Modul wird aktiviert", 1400),
        ("{name} liest heimlich deine alten Chats", 1700),
        ("{name}'s Reaktionszeit wird optimiert", 1300),
        ("{name} entscheidet sich für ein Outfit", 1100),
        ("{name}'s Empathie-Level wird hochgefahren", 1500),
    ]

    # 1 random message with ONE random persona
    name = random.choice(names)
    tmpl, dur = random.choice(templates)
    return [(tmpl.format(name=name), dur)]


# ---------------------------------------------------------------------------
# Startup-Sequenz
# ---------------------------------------------------------------------------

def startup_sequence(window, server_mode, server_port, start_flask_fn, host):
    """Initialisiert alles und tippt Output ins Splash-Fenster.

    Args:
        window:          pywebview-Fenster-Instanz
        server_mode:     'local' oder 'listen'
        server_port:     Port-Nummer
        start_flask_fn:  Callable zum Starten des Flask-Servers
        host:            Host-Adresse
    """
    # Tippe Startmeldungen
    splash_type(window, '> Starte PersonaUI...', 'info')
    splash_type(window, f'> Arbeitsverzeichnis: {os.getcwd()}', 'default')
    splash_type(window, '', 'default')

    # Update check: Check origin/main for new stable version
    splash_type(window, '> Prüfe auf Updates...', 'default')
    try:
        update_info = check_for_update()
        if update_info.get('error'):
            splash_type(window, '  Update-Check übersprungen (kein Netzwerk).', 'default')
        elif update_info.get('available'):
            n = update_info.get('new_commits', 0)
            splash_type(window, '', 'default')
            splash_type(window, f'  *** Neue stabile Version verfügbar! ({n} neue Commits) ***', 'warn')
            splash_type(window, '  → Führe bin/update.bat aus, um zu aktualisieren.', 'warn')
            splash_type(window, '', 'default')
        else:
            splash_type(window, '  PersonaUI ist aktuell.', 'info')
    except Exception:
        splash_type(window, '  Update-Check übersprungen.', 'default')
    splash_type(window, '', 'default')

    # Datenbanken initialisieren
    splash_type(window, '> Initialisiere Datenbanken...', 'default')
    init_all_dbs()
    splash_type(window, '  Datenbanken bereit.', 'info')
    splash_type(window, '', 'default')

    # Lustige Persona-Lademeldungen
    fun_msgs = get_fun_messages()
    for msg, dur in fun_msgs:
        splash_type_bar(window, '  ' + msg + ' ', 'fun', dur)
    splash_type(window, '', 'default')

    # Host/IP bestimmen und anzeigen
    if server_mode == 'listen':
        try:
            s = sock.socket(sock.AF_INET, sock.SOCK_DGRAM)
            s.settimeout(0)
            s.connect(('8.8.8.8', 80))
            primary_ip = s.getsockname()[0]
            s.close()
            splash_type(window, f'> Server-Modus: listen ({primary_ip})', 'default')
        except Exception:
            splash_type(window, '> Server-Modus: listen', 'default')
    else:
        splash_type(window, '> Server-Modus: lokal', 'default')

    splash_type(window, f'> Port: {server_port}', 'default')
    splash_type(window, '', 'default')
    splash_type(window, '> Flask-Server wird hochgefahren...', 'default')

    # Flask-Server im Hintergrund starten
    server_thread = threading.Thread(
        target=start_flask_fn,
        args=(host, server_port),
        daemon=True,
    )
    server_thread.start()

    # Warten bis Server antwortet (schneller Socket-Check)
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
                splash_type(window, f'  Server startet... ({int(waited)}s)', 'default')

    if ready:
        splash_type(window, '', 'default')
        splash_type(window, '> Server bereit!', 'info')
        splash_type(window, '> Lade Oberflaeche...', 'info')
        time.sleep(0.5)
        # App im selben Fenster laden
        window.load_url(f"http://127.0.0.1:{server_port}")
    else:
        splash_type(window, '> Server konnte nicht gestartet werden!', 'error')
        splash_type(window, f'  Timeout nach {max_wait} Sekunden.', 'error')
