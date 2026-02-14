"""
IP-basierte Zugangskontrolle – Whitelist/Blacklist-System

Ersetzt das alte Login-System. Unbekannte IPs werden in eine Warteschlange gestellt,
bis der lokale Nutzer sie freigibt oder blockiert.
"""
import time
import threading
from utils.logger import log


# ===== In-Memory State =====
# Persistent gespeichert in server_settings.json: whitelist, blacklist
# Nur zur Laufzeit: pending requests, rate-limit tracker

_lock = threading.Lock()

# Warteschlange: { ip: { 'timestamp': float, 'status': 'pending'|'approved'|'denied' } }
_pending_requests = {}

# Rate-Limiting: { ip: { 'attempts': int, 'blocked_until': float } }
_rate_limits = {}

# Konstanten
MAX_ATTEMPTS = 3
BLOCK_DURATION = 300  # 5 Minuten in Sekunden
PENDING_TIMEOUT = 300  # Pending-Einträge nach 5 Minuten entfernen


# ===== Hilfsfunktionen =====

def _load_access_settings():
    """Lädt Whitelist/Blacklist aus server_settings.json"""
    import os
    import json
    settings_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'settings', 'server_settings.json')
    
    try:
        if os.path.exists(settings_path):
            with open(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                server = settings.get('server_settings', {})
                return {
                    'whitelist': server.get('IP_WHITELIST', []),
                    'blacklist': server.get('IP_BLACKLIST', []),
                    'access_control_enabled': server.get('ACCESS_CONTROL_ENABLED', True),
                    'server_mode': server.get('SERVER_MODE', 'local')
                }
    except Exception as e:
        log.error("Fehler beim Laden der Access-Settings: %s", e)
    
    return {
        'whitelist': [],
        'blacklist': [],
        'access_control_enabled': True,
        'server_mode': 'local'
    }


def _save_access_lists(whitelist, blacklist):
    """Speichert Whitelist/Blacklist in server_settings.json"""
    import os
    import json
    settings_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'settings', 'server_settings.json')
    
    try:
        settings = {'server_settings': {}}
        if os.path.exists(settings_path):
            with open(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
        
        if 'server_settings' not in settings:
            settings['server_settings'] = {}
        
        settings['server_settings']['IP_WHITELIST'] = whitelist
        settings['server_settings']['IP_BLACKLIST'] = blacklist
        
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
        
        return True
    except Exception as e:
        log.error("Fehler beim Speichern der Access-Lists: %s", e)
        return False


def is_local_ip(ip):
    """Prüft ob eine IP-Adresse lokal ist (localhost)"""
    return ip in ('127.0.0.1', 'localhost', '::1')


def _cleanup_expired():
    """Entfernt abgelaufene Pending-Einträge und Rate-Limits"""
    now = time.time()
    
    expired_pending = [
        ip for ip, data in _pending_requests.items()
        if now - data['timestamp'] > PENDING_TIMEOUT
    ]
    for ip in expired_pending:
        del _pending_requests[ip]
    
    expired_limits = [
        ip for ip, data in _rate_limits.items()
        if data.get('blocked_until', 0) < now and data.get('attempts', 0) >= MAX_ATTEMPTS
    ]
    for ip in expired_limits:
        del _rate_limits[ip]


# ===== Hauptfunktionen =====

def check_access(ip):
    """
    Prüft den Zugangsstatus einer IP-Adresse.
    
    Returns:
        'allowed'     – IP ist lokal oder in der Whitelist
        'blocked'     – IP ist in der Blacklist
        'rate_limited' – Zu viele Anfragen, muss warten
        'pending'     – Wartet auf Genehmigung
        'unknown'     – Neue IP, muss Zugang anfragen
    """
    # Lokale IPs haben immer Zugang
    if is_local_ip(ip):
        return 'allowed'
    
    settings = _load_access_settings()
    
    # Zugangskontrolle deaktiviert → alle erlaubt
    if not settings.get('access_control_enabled', True):
        return 'allowed'
    
    # Nur im Listen-Modus relevant
    if settings.get('server_mode', 'local') == 'local':
        return 'allowed'
    
    # Blacklist prüfen
    if ip in settings['blacklist']:
        return 'blocked'
    
    # Whitelist prüfen
    if ip in settings['whitelist']:
        return 'allowed'
    
    with _lock:
        _cleanup_expired()
        
        # Rate-Limit prüfen
        if ip in _rate_limits:
            limit_data = _rate_limits[ip]
            if limit_data.get('blocked_until', 0) > time.time():
                return 'rate_limited'
        
        # Bereits in Warteschlange?
        if ip in _pending_requests:
            status = _pending_requests[ip].get('status', 'pending')
            if status == 'approved':
                # Approved → Whitelist + aufräumen
                del _pending_requests[ip]
                return 'allowed'
            elif status == 'denied':
                # Denied → aufräumen
                del _pending_requests[ip]
                return 'blocked'
            return 'pending'
    
    return 'unknown'


def request_access(ip):
    """
    Stellt eine Zugangsanfrage für eine unbekannte IP.
    
    Returns:
        'pending'      – Anfrage wurde gestellt
        'rate_limited' – Zu viele Anfragen
        'already_pending' – Bereits in der Warteschlange
        'blocked'      – IP ist in der Blacklist
        'allowed'      – IP ist bereits in der Whitelist
    """
    if is_local_ip(ip):
        return 'allowed'
    
    settings = _load_access_settings()
    
    if ip in settings['blacklist']:
        return 'blocked'
    
    if ip in settings['whitelist']:
        return 'allowed'
    
    with _lock:
        _cleanup_expired()
        
        # Rate-Limit prüfen
        if ip in _rate_limits:
            limit_data = _rate_limits[ip]
            if limit_data.get('blocked_until', 0) > time.time():
                remaining = int(limit_data['blocked_until'] - time.time())
                log.warning("IP %s ist rate-limited. Noch %d Sekunden.", ip, remaining)
                return 'rate_limited'
        
        # Bereits pending?
        if ip in _pending_requests:
            status = _pending_requests[ip].get('status', 'pending')
            if status == 'pending':
                return 'already_pending'
            elif status == 'approved':
                del _pending_requests[ip]
                return 'allowed'
            elif status == 'denied':
                del _pending_requests[ip]
                return 'blocked'
        
        # Rate-Limit Zähler erhöhen
        if ip not in _rate_limits:
            _rate_limits[ip] = {'attempts': 0, 'blocked_until': 0}
        
        _rate_limits[ip]['attempts'] += 1
        
        if _rate_limits[ip]['attempts'] > MAX_ATTEMPTS:
            _rate_limits[ip]['blocked_until'] = time.time() + BLOCK_DURATION
            log.warning("IP %s hat Rate-Limit erreicht. Blockiert für %d Sekunden.", ip, BLOCK_DURATION)
            return 'rate_limited'
        
        # In Warteschlange aufnehmen
        _pending_requests[ip] = {
            'timestamp': time.time(),
            'status': 'pending'
        }
        
        log.info("Neue Zugangsanfrage von IP: %s (Versuch %d/%d)", 
                 ip, _rate_limits[ip]['attempts'], MAX_ATTEMPTS)
        
        return 'pending'


def approve_ip(ip):
    """Genehmigt eine IP und fügt sie zur Whitelist hinzu."""
    settings = _load_access_settings()
    
    # Zur Whitelist hinzufügen
    if ip not in settings['whitelist']:
        settings['whitelist'].append(ip)
    
    # Aus Blacklist entfernen (falls vorhanden)
    if ip in settings['blacklist']:
        settings['blacklist'].remove(ip)
    
    _save_access_lists(settings['whitelist'], settings['blacklist'])
    
    with _lock:
        # Pending-Status aktualisieren (damit Polling es mitbekommt)
        if ip in _pending_requests:
            _pending_requests[ip]['status'] = 'approved'
        
        # Rate-Limit zurücksetzen
        if ip in _rate_limits:
            del _rate_limits[ip]
    
    log.info("IP %s genehmigt und zur Whitelist hinzugefügt.", ip)
    return True


def deny_ip(ip):
    """Verweigert eine IP und fügt sie zur Blacklist hinzu."""
    settings = _load_access_settings()
    
    # Zur Blacklist hinzufügen
    if ip not in settings['blacklist']:
        settings['blacklist'].append(ip)
    
    # Aus Whitelist entfernen (falls vorhanden)
    if ip in settings['whitelist']:
        settings['whitelist'].remove(ip)
    
    _save_access_lists(settings['whitelist'], settings['blacklist'])
    
    with _lock:
        # Pending-Status aktualisieren
        if ip in _pending_requests:
            _pending_requests[ip]['status'] = 'denied'
        
        # Rate-Limit zurücksetzen
        if ip in _rate_limits:
            del _rate_limits[ip]
    
    log.info("IP %s abgelehnt und zur Blacklist hinzugefügt.", ip)
    return True


def remove_from_whitelist(ip):
    """Entfernt eine IP aus der Whitelist."""
    settings = _load_access_settings()
    
    if ip in settings['whitelist']:
        settings['whitelist'].remove(ip)
        _save_access_lists(settings['whitelist'], settings['blacklist'])
        log.info("IP %s aus Whitelist entfernt.", ip)
        return True
    return False


def remove_from_blacklist(ip):
    """Entfernt eine IP aus der Blacklist."""
    settings = _load_access_settings()
    
    if ip in settings['blacklist']:
        settings['blacklist'].remove(ip)
        _save_access_lists(settings['whitelist'], settings['blacklist'])
        log.info("IP %s aus Blacklist entfernt.", ip)
        return True
    return False


def get_pending_requests():
    """Gibt alle ausstehenden Zugangsanfragen zurück."""
    with _lock:
        _cleanup_expired()
        return {
            ip: {
                'timestamp': data['timestamp'],
                'status': data['status'],
                'waiting_seconds': int(time.time() - data['timestamp'])
            }
            for ip, data in _pending_requests.items()
            if data['status'] == 'pending'
        }


def get_access_lists():
    """Gibt Whitelist und Blacklist zurück."""
    settings = _load_access_settings()
    return {
        'whitelist': settings['whitelist'],
        'blacklist': settings['blacklist'],
        'access_control_enabled': settings['access_control_enabled']
    }


def poll_access_status(ip):
    """
    Polling-Endpunkt für externe Geräte.
    
    Returns:
        'pending'  – Noch keine Entscheidung
        'approved' – Zugang genehmigt
        'denied'   – Zugang verweigert
        'expired'  – Anfrage ist abgelaufen
    """
    if is_local_ip(ip):
        return 'approved'
    
    settings = _load_access_settings()
    
    # Bereits in Whitelist?
    if ip in settings['whitelist']:
        return 'approved'
    
    # Bereits in Blacklist?
    if ip in settings['blacklist']:
        return 'denied'
    
    with _lock:
        if ip in _pending_requests:
            return _pending_requests[ip].get('status', 'pending')
    
    return 'expired'


def set_access_control_enabled(enabled):
    """Aktiviert oder deaktiviert die Zugangskontrolle."""
    import os
    import json
    settings_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'settings', 'server_settings.json')
    
    try:
        settings = {'server_settings': {}}
        if os.path.exists(settings_path):
            with open(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
        
        if 'server_settings' not in settings:
            settings['server_settings'] = {}
        
        settings['server_settings']['ACCESS_CONTROL_ENABLED'] = enabled
        
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
        
        log.info("Zugangskontrolle %s.", "aktiviert" if enabled else "deaktiviert")
        return True
    except Exception as e:
        log.error("Fehler beim Setzen der Zugangskontrolle: %s", e)
        return False
