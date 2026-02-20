import os
import sys
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
                args=(window, server_mode, server_port, start_flask_server, host),
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
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
            log.info("Fenster geschlossen. Server wird beendet.")
            os._exit(0)
            
        except ImportError:
            show_console_window()
            log.warning("PyWebView nicht installiert. Starte im Browser-Modus...")
            init_all_dbs()
            log.info("Server running at: http://%s:%s", host, server_port)
            log.info("Web UI & Backend developed by Sakushi-Dev")
            app.run(host=host, port=server_port, debug=False)
    else:
        # Fallback: Normaler Flask-Server ohne GUI-Fenster
        init_all_dbs()
        app.run(host=host, port=server_port, debug=False)


