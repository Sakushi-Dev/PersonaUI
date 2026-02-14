"""
API Routes - API-Key Verwaltung und Testing
"""
from flask import Blueprint, request
import os
import secrets
import json
from dotenv import load_dotenv
import anthropic
import qrcode
from io import BytesIO
import base64
from utils.settings_defaults import get_api_model_default
from utils.logger import log
from utils.provider import get_api_client
from routes.helpers import success_response, error_response, handle_route_error

api_bp = Blueprint('api', __name__)


@api_bp.route('/api/test_api_key', methods=['POST'])
@handle_route_error('test_api_key')
def test_api_key():
    """Testet einen Anthropic API-Key durch einen einfachen Test-Request"""
    data = request.get_json()
    api_key = data.get('api_key', '').strip()
    api_model = data.get('api_model') or get_api_model_default()
    
    if not api_key:
        return error_response('API-Key ist leer')
    
    if not api_key.startswith('sk-ant-api'):
        return error_response('Ungültiges API-Key Format')
    
    # Teste den API-Key mit einem einfachen Request (mit dem gewählten Modell)
    try:
        client = anthropic.Anthropic(api_key=api_key)
        
        # Einfacher Test-Request
        message = client.messages.create(
            model=api_model,
            max_tokens=10,
            messages=[
                {"role": "user", "content": "Hi"}
            ]
        )
        
        # Wenn wir hier ankommen, ist der Key gültig
        return success_response()
        
    except anthropic.AuthenticationError:
        return error_response('API-Key ist ungültig oder abgelaufen', 401)
    except anthropic.PermissionDeniedError:
        return error_response('Keine Berechtigung für diese API', 403)
    except anthropic.RateLimitError:
        return error_response('Rate Limit erreicht', 429)
    except Exception as e:
        return error_response(f'API-Fehler: {str(e)}', 500)


@api_bp.route('/api/check_api_status', methods=['GET'])
@handle_route_error('check_api_status')
def check_api_status():
    """Prüft ob ein API-Key konfiguriert ist (direkt in der .env Datei)"""
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    has_api_key = False
    
    # Prüfe ob .env existiert und einen API-Key enthält
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('ANTHROPIC_API_KEY='):
                    api_key = line.split('=', 1)[1].strip()
                    # Prüfe ob der Key nicht leer ist und ein gültiges Format hat
                    has_api_key = bool(api_key and len(api_key) > 10 and api_key.startswith('sk-'))
                    break
    
    return success_response(
        has_api_key=has_api_key,
        status='connected' if has_api_key else 'disconnected'
    )


@api_bp.route('/api/save_api_key', methods=['POST'])
@handle_route_error('save_api_key')
def save_api_key():
    """Speichert den API-Key in der .env Datei"""
    data = request.get_json()
    api_key = data.get('api_key', '').strip()
    
    if not api_key:
        return error_response('API-Key ist leer')
    
    # Pfad zur .env Datei
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    
    # Lese existierende .env oder erstelle neue
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    
    # Aktualisiere oder füge API-Key hinzu
    env_vars['ANTHROPIC_API_KEY'] = api_key
    
    # Stelle sicher, dass SECRET_KEY existiert
    if 'SECRET_KEY' not in env_vars:
        env_vars['SECRET_KEY'] = secrets.token_hex(32)
    
    # Schreibe .env Datei
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write('# Umgebungsvariablen - Automatisch generiert\n')
        for key, value in env_vars.items():
            f.write(f'{key}={value}\n')
    
    # WICHTIG: Aktualisiere zuerst os.environ direkt
    os.environ['ANTHROPIC_API_KEY'] = api_key
    
    # Dann lade auch die .env Datei neu (für zukünftige Prozesse)
    load_dotenv(env_path, override=True)
    
    # Aktualisiere den Claude API Client mit dem neuen Key
    api_client = get_api_client()
    if api_client:
        success = api_client.update_api_key(api_key)
        if not success:
            return error_response('Fehler beim Aktualisieren des API-Clients', 500)
        log.info("API-Key erfolgreich gespeichert und API Client aktualisiert")
    else:
        log.warning("api_client ist None")
    
    return success_response()


@api_bp.route('/api/get_server_settings', methods=['GET'])
@handle_route_error('get_server_settings')
def get_server_settings():
    """Gibt die aktuellen Server-Einstellungen zurück"""
    import socket
    
    settings_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'settings', 'server_settings.json')
    server_mode = 'local'  # default
    port = 5000  # default
    
    # Lese Server-Modus aus JSON
    if os.path.exists(settings_path):
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)
            server_settings = settings.get('server_settings', {})
            server_mode = server_settings.get('SERVER_MODE', 'local')
            port = int(server_settings.get('SERVER_PORT', 5000))
    
    result = {
        'server_mode': server_mode,
        'port': port
    }
    
    # Wenn Listen-Modus, füge IP-Adressen hinzu
    if server_mode == 'listen':
        result['ip_addresses'] = get_local_ip_addresses()
    
    return success_response(**result)


@api_bp.route('/api/get_local_ips', methods=['GET'])
@handle_route_error('get_local_ips')
def get_local_ips():
    """Gibt die lokalen IP-Adressen zurück"""
    ip_addresses = get_local_ip_addresses()
    
    # Get port from .env or use default
    port = 5000
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('SERVER_PORT='):
                    try:
                        port = int(line.split('=', 1)[1].strip())
                    except:
                        port = 5000
    
    return success_response(ip_addresses=ip_addresses, port=port)


@api_bp.route('/api/save_server_mode', methods=['POST'])
@handle_route_error('save_server_mode')
def save_server_mode():
    """Speichert den Server-Modus in der .env Datei"""
    data = request.get_json()
    server_mode = data.get('server_mode', 'local')
    
    if server_mode not in ['local', 'listen']:
        return error_response('Ungültiger Server-Modus')
    
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    
    # Lese existierende .env
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    
    # Update Server-Modus
    env_vars['SERVER_MODE'] = server_mode
    
    # Stelle sicher, dass Port existiert
    if 'SERVER_PORT' not in env_vars:
        env_vars['SERVER_PORT'] = '5000'
    
    # Schreibe .env Datei
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write('# Umgebungsvariablen - Automatisch generiert\n')
        for key, value in env_vars.items():
            f.write(f'{key}={value}\n')
    
    return success_response()


def get_local_ip_addresses():
    """Gibt nur die primäre IPv4-Adresse zurück"""
    import socket
    
    try:
        # Methode 1: Versuche die primäre IP durch Verbindung zu einem externen Server zu ermitteln
        primary_ip = None
        try:
            # Erstelle eine Socket-Verbindung (muss nicht tatsächlich verbinden)
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0)
            # Nutze Google DNS - es wird keine tatsächliche Verbindung aufgebaut
            s.connect(('8.8.8.8', 80))
            primary_ip = s.getsockname()[0]
            s.close()
            
            if primary_ip:
                return [primary_ip]
        except Exception:
            pass
        
        # Methode 2: Fallback - Sammle IPv4-Adressen über Hostname
        hostname = socket.gethostname()
        addr_info = socket.getaddrinfo(hostname, None)
        
        ipv4_addrs = []
        seen = set()
        for info in addr_info:
            ip = info[4][0]
            # Nur IPv4, keine localhost, Link-Local oder VPN-Adressen
            if (ip not in seen and 
                ':' not in ip and  # Nur IPv4
                not ip.startswith('127.') and 
                not ip.startswith('10.5.')):  # VPN-Adressen ausfiltern
                seen.add(ip)
                ipv4_addrs.append(ip)
        
        # Priorisierung nach häufigen privaten Netzwerkbereichen
        def ip_priority(ip):
            """Gibt Priorität zurück: niedrigere Zahl = höhere Priorität"""
            if ip.startswith('192.168.'):
                return 1  # Häufigstes privates Netzwerk
            elif ip.startswith('10.0.') or ip.startswith('10.1.'):
                return 2  # Häufiges privates Netzwerk
            elif ip.startswith('172.'):
                # Prüfe ob es im Bereich 172.16.0.0 - 172.31.255.255 ist
                try:
                    second_octet = int(ip.split('.')[1])
                    if 16 <= second_octet <= 31:
                        return 2  # Privates Netzwerk
                except:
                    pass
            return 3  # Andere IPs haben niedrigere Priorität
        
        # Sortiere IPv4-Adressen nach Priorität
        ipv4_addrs.sort(key=ip_priority)
        
        # Gebe nur die primäre Adresse zurück
        return ipv4_addrs[:1] if ipv4_addrs else []
        
    except Exception as e:
        log.error("Fehler beim Abrufen der IP-Adressen: %s", e)
        return []


@api_bp.route('/api/generate_qr_code', methods=['POST'])
@handle_route_error('generate_qr_code')
def generate_qr_code():
    """Generiert einen QR-Code als Base64-Bild"""
    data = request.get_json()
    url = data.get('url', '')
    
    if not url:
        return error_response('URL fehlt')
    
    # Erstelle QR-Code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    
    # Erstelle Bild
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Konvertiere zu Base64
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    return success_response(qr_code=f'data:image/png;base64,{img_base64}')


@api_bp.route('/api/save_and_restart_server', methods=['POST'])
@handle_route_error('save_and_restart_server')
def save_and_restart_server():
    """Speichert Server-Einstellungen und startet den Server neu"""
    import sys
    import subprocess
    import signal
    
    data = request.get_json()
    server_mode = data.get('server_mode', 'local')
    
    if server_mode not in ['local', 'listen']:
        return error_response('Ungültiger Server-Modus')
    
    settings_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'settings', 'server_settings.json')
    
    # Lese existierende Einstellungen
    settings = {'server_settings': {}}
    if os.path.exists(settings_path):
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)
    
    # Stelle sicher, dass server_settings existiert
    if 'server_settings' not in settings:
        settings['server_settings'] = {}
    
    # Update Server-Modus
    settings['server_settings']['SERVER_MODE'] = server_mode
    
    # Stelle sicher, dass Port existiert
    if 'SERVER_PORT' not in settings['server_settings']:
        settings['server_settings']['SERVER_PORT'] = 5000
    
    # Schreibe JSON-Datei
    with open(settings_path, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=4, ensure_ascii=False)
    
    # Erstelle Restart-Batch-Skript das im SELBEN Fenster läuft
    restart_script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'restart_server.bat')
    with open(restart_script_path, 'w', encoding='utf-8') as f:
        f.write('@echo off\n')
        f.write('echo Server wird neu gestartet...\n')
        f.write('timeout /t 2 /nobreak >nul\n')  # Warte 2 Sekunden
        f.write('cd /d "%~dp0src"\n')  # Wechsel ins src Verzeichnis
        # Aktiviere venv und starte app.py direkt (wie start.bat)
        f.write('call ..\\.venv\\Scripts\\activate.bat\n')
        f.write('python app.py\n')
        f.write('if errorlevel 1 pause\n')  # Pause nur bei Fehler
        f.write('cd ..\n')  # Zurück ins Hauptverzeichnis
        f.write('del "%~f0"\n')  # Lösche das Skript selbst
    
    # Starte das Batch-Skript und beende dann diesen Python-Prozess
    # Das Skript läuft im Hintergrund weiter und startet Python im aktuellen Fenster neu
    subprocess.Popen(['start', '/B', 'cmd', '/c', restart_script_path], 
                    shell=True,
                    cwd=os.path.dirname(os.path.dirname(__file__)))
    
    # Beende den aktuellen Python-Prozess nach kurzer Verzögerung
    def shutdown():
        import time
        time.sleep(0.5)
        os._exit(0)
    
    import threading
    threading.Thread(target=shutdown, daemon=True).start()
    
    return success_response(message='Server wird neu gestartet...')


# ===== Prompt Engine Reload =====

@api_bp.route('/api/prompts/reload', methods=['POST'])
@handle_route_error('reload_prompts')
def reload_prompts():
    """Prompts neu laden ohne App-Neustart."""
    from utils.provider import get_prompt_engine
    engine = get_prompt_engine()
    if engine is None:
        return error_response('PromptEngine nicht verfügbar', 503)

    engine.reload()
    errors = engine.load_errors
    if errors:
        return success_response(
            message='Prompts neu geladen (mit Warnungen)',
            warnings=errors
        )
    return success_response(message='Prompts erfolgreich neu geladen')

