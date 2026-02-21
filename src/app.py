import os
import sys
import subprocess
import threading

# WICHTIG: Wechsle ins src Verzeichnis für korrekte Pfade
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

from flask import Flask, jsonify, redirect, url_for, request
from flask_cors import CORS
from dotenv import load_dotenv
from datetime import timedelta

# Importiere Utility-Funktionen
from utils.logger import log
from utils.database import init_all_dbs
from utils.provider import init_services
from utils.helpers import format_message, ensure_env_file
from utils.access_control import check_access

# Importiere Route-Registrierung
from routes import register_routes

# Splash-Screen Modul
from splash_screen import (
    load_splash_html,
    hide_console_window,
    show_console_window,
    startup_sequence,
)


# Stelle sicher, dass .env Datei existiert
ensure_env_file()

# Lade Umgebungsvariablen
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'fallback-secret-key-for-development')
app.json.sort_keys = False  # Reihenfolge der Keys beibehalten (Default -> Custom)

# CORS für React-Frontend (Vite Dev-Server auf Port 5173)
CORS(app, resources={r"/*": {"origins": ["http://localhost:5173", "http://127.0.0.1:5173"]}}, supports_credentials=True)

# Session-Konfiguration
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)  # Session bleibt 7 Tage gültig
app.config['SESSION_COOKIE_SECURE'] = False  # Für HTTPS auf True setzen
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Schutz vor XSS
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF-Schutz

# Initialisiere Services (API-Client, Chat-Service)
init_services()

# Registriere Template-Filter
app.jinja_env.filters['format_message'] = format_message

# Registriere alle Route-Blueprints
register_routes(app)


# Zugangskontrolle: IP-basierte Whitelist/Blacklist
@app.before_request
def check_ip_access():
    """Prüft ob die anfragende IP Zugang hat (Whitelist/Blacklist)"""
    
    # Statische Dateien und Access-Endpunkte immer erlauben
    if request.endpoint in ('static', None):
        return None
    
    # React-Frontend Assets immer erlauben (/assets/*, /vite.svg)
    if request.endpoint and request.endpoint.startswith('react.'):
        return None
    
    # Access-Routes immer erlauben (Waiting-Screen, Polling, Request)
    if request.endpoint and request.endpoint.startswith('access.'):
        return None
    
    # Onboarding immer erlauben (First-Run Setup)
    if request.endpoint and request.endpoint.startswith('onboarding.'):
        return None
    
    # API-Endpunkte für Access-Kontrolle immer erlauben
    if request.path.startswith('/api/access/'):
        return None
    
    ip = request.remote_addr
    status = check_access(ip)
    
    if status == 'allowed':
        return None
    
    # Prüfe ob die Anfrage von einem API-Client kommt (React Frontend)
    is_api_request = (
        request.accept_mimetypes.best == 'application/json'
        or request.path.startswith('/api/')
        or request.path.startswith('/chat')
        or request.path.startswith('/afterthought')
        or request.path.startswith('/clear_chat')
        or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    )
    
    if is_api_request:
        # JSON-Antwort für API-Clients (React Frontend)
        return jsonify({'success': False, 'error': 'access_denied', 'status': status}), 403
    
    # Redirect zum Wartebildschirm (React SPA oder Jinja Templates)
    return redirect(url_for('access.waiting_screen'))


def start_flask_server(host, port):
    """Startet den Flask-Server in einem separaten Thread."""
    app.run(host=host, port=port, debug=False, use_reloader=False)


# ═══════════════════════════════════════════════════════════════════════════
#  Vite Dev-Server (--dev Modus)
# ═══════════════════════════════════════════════════════════════════════════

_vite_process = None

def _get_dev_env():
    """Gibt ein environ-Dict zurück, in dem bin/node/ im PATH liegt."""
    root_dir = os.path.dirname(script_dir)
    local_node = os.path.join(root_dir, 'bin', 'node')
    env = os.environ.copy()
    if os.path.isdir(local_node):
        node_bin = local_node if sys.platform == 'win32' else os.path.join(local_node, 'bin')
        env['PATH'] = node_bin + os.pathsep + env.get('PATH', '')
    return env


def _find_npm():
    """Findet npm (System-PATH oder lokales bin/node/)."""
    root_dir = os.path.dirname(script_dir)
    local_node = os.path.join(root_dir, 'bin', 'node')
    # Lokales npm prüfen
    npm_local = os.path.join(local_node, 'npm.cmd' if sys.platform == 'win32' else 'bin/npm')
    if os.path.isfile(npm_local):
        return npm_local
    # System npm
    npm_name = 'npm.cmd' if sys.platform == 'win32' else 'npm'
    result = subprocess.run(
        ['where' if sys.platform == 'win32' else 'which', npm_name],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        return result.stdout.strip().splitlines()[0]
    return None


def _kill_port(port):
    """Beendet alle Prozesse, die den angegebenen Port belegen (Windows)."""
    if sys.platform != 'win32':
        return
    try:
        result = subprocess.run(
            ['netstat', '-ano'],
            capture_output=True, text=True
        )
        pids = set()
        for line in result.stdout.splitlines():
            if f':{port}' in line and 'LISTENING' in line:
                parts = line.split()
                if parts:
                    try:
                        pids.add(int(parts[-1]))
                    except ValueError:
                        pass
        for pid in pids:
            try:
                subprocess.run(
                    ['taskkill', '/F', '/PID', str(pid)],
                    capture_output=True
                )
                log.info("Port %s: Prozess %s beendet.", port, pid)
            except Exception:
                pass
    except Exception:
        pass


def start_vite_dev_server():
    """Startet den Vite Dev-Server (npm run dev) in einem eigenen Konsolenfenster."""
    global _vite_process
    root_dir = os.path.dirname(script_dir)
    frontend_dir = os.path.join(root_dir, 'frontend')
    npm_path = _find_npm()
    if not npm_path:
        log.warning("npm nicht gefunden – Vite Dev-Server kann nicht gestartet werden.")
        return False

    # Port 5173 freigeben falls noch ein alter Prozess läuft
    _kill_port(5173)

    log.info("Starte Vite Dev-Server (npm run dev) in separater Konsole...")
    kwargs = {
        'cwd': frontend_dir,
        'env': _get_dev_env(),
    }
    if sys.platform == 'win32':
        # Eigenes Konsolenfenster öffnen
        kwargs['creationflags'] = subprocess.CREATE_NEW_CONSOLE
    _vite_process = subprocess.Popen(
        [npm_path, 'run', 'dev'],
        **kwargs,
    )
    return True


def stop_vite_dev_server():
    """Stoppt den Vite Dev-Server, falls er läuft."""
    global _vite_process
    if _vite_process and _vite_process.poll() is None:
        _vite_process.terminate()
        try:
            _vite_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _vite_process.kill()
        _vite_process = None


if __name__ == '__main__':
    # Settings nur für Port vorladen (damit pywebview weiß welchen Port es braucht)
    import json
    settings_path = os.path.join(os.path.dirname(__file__), 'settings', 'server_settings.json')
    server_mode = 'local'
    server_port = 5000
    try:
        if os.path.exists(settings_path):
            with open(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                server_settings = settings.get('server_settings', {})
                server_mode = server_settings.get('SERVER_MODE', 'local')
                server_port = int(server_settings.get('SERVER_PORT', 5000))
    except Exception:
        pass
    
    host = '0.0.0.0' if server_mode == 'listen' else '127.0.0.1'
    
    # Prüfe ob PyWebView genutzt werden soll (--no-gui deaktiviert es)
    use_webview = '--no-gui' not in sys.argv
    dev_mode = '--dev' in sys.argv
    
    # Im Dev-Modus: Vite Dev-Server starten
    if dev_mode:
        start_vite_dev_server()
    
    if use_webview:
        try:
            import webview
            from utils.window_settings import load_window_settings, save_window_settings
            
            # Konsole verstecken - pywebview übernimmt die Anzeige
            hide_console_window()

            # AppUserModelID setzen, damit Windows die App als eigenständig erkennt
            # und das eigene Icon in der Taskleiste anzeigt (statt python.exe-Icon)
            try:
                from ctypes import windll
                windll.shell32.SetCurrentProcessExplicitAppUserModelID('PersonaUI.App')
            except Exception:
                pass

            def _patch_winforms_icon(ico_path):
                """Patcht die WinForms BrowserForm-Klasse, damit das eigene Icon verwendet wird."""
                if not os.path.isfile(ico_path):
                    return
                try:
                    import clr
                    clr.AddReference('System.Drawing')
                    from System.Drawing import Icon as WinIcon #type: ignore

                    from webview.platforms.winforms import BrowserView
                    _orig_init = BrowserView.BrowserForm.__init__

                    def _patched_init(self, window, cache_dir):
                        _orig_init(self, window, cache_dir)
                        try:
                            self.Icon = WinIcon(ico_path)
                        except Exception:
                            pass

                    BrowserView.BrowserForm.__init__ = _patched_init
                except Exception:
                    pass  # Nicht-Windows oder Import-Fehler → ignorieren
            
            
            # Lade gespeicherte Fenstereinstellungen
            win_settings = load_window_settings()
            
            # Icon-Pfad (bin/assets/persona_ui.ico)
            icon_path = os.path.join(
                os.path.dirname(script_dir), 'bin', 'assets', 'persona_ui.ico'
            )
            
            # 1) Splash-Fenster SOFORT öffnen - BEVOR irgendwas initialisiert wird
            window = webview.create_window(
                'PersonaUI',
                html=load_splash_html(),
                width=win_settings['width'],
                height=win_settings['height'],
                x=win_settings['x'],
                y=win_settings['y'],
                min_size=(800, 600),
                resizable=True,
                text_select=True,
            )
            
            # Startup im Hintergrund-Thread, startet wenn Fenster sichtbar wird
            boot_thread = threading.Thread(
                target=startup_sequence,
                args=(window, server_mode, server_port, start_flask_server, host, dev_mode),
                daemon=True,
            )
            
            def _on_shown():
                boot_thread.start()
            
            def _on_closing():
                """Speichert Fensterposition/-größe beim Schließen"""
                try:
                    save_window_settings(
                        width=window.width,
                        height=window.height,
                        x=window.x,
                        y=window.y
                    )
                except Exception:
                    pass  # Fehler beim Speichern ignorieren
            
            window.events.shown += _on_shown
            window.events.closing += _on_closing
            
            # Custom-Icon injizieren (pywebview 6.x ignoriert icon= unter Windows)
            _patch_winforms_icon(icon_path)
            
            # PyWebView starten (blockiert bis Fenster zu)
            webview.start(icon=icon_path)
            
            # Fenster geschlossen → Konsole wieder zeigen und alles beenden
            show_console_window()
            if dev_mode:
                stop_vite_dev_server()
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
            log.info("Fenster geschlossen. Server wird beendet.")
            os._exit(0)
            
        except ImportError:
            show_console_window()
            log.warning("PyWebView nicht installiert. Starte im Browser-Modus...")
            init_all_dbs()
            from utils.cortex_service import ensure_cortex_dirs
            ensure_cortex_dirs()
            from utils.settings_migration import migrate_settings
            migrate_settings()
            log.info("Server running at: http://%s:%s", host, server_port)
            log.info("Web UI & Backend developed by Sakushi-Dev")
            app.run(host=host, port=server_port, debug=False)
    else:
        # Fallback: Normaler Flask-Server ohne GUI-Fenster
        init_all_dbs()
        from utils.cortex_service import ensure_cortex_dirs
        ensure_cortex_dirs()
        from utils.settings_migration import migrate_settings
        migrate_settings()
        if dev_mode:
            log.info("Dev-Modus: Vite Dev-Server läuft auf http://localhost:5173")
            log.info("Flask-Backend auf http://%s:%s", host, server_port)
        else:
            log.info("Server running at: http://%s:%s", host, server_port)
        app.run(host=host, port=server_port, debug=False)


