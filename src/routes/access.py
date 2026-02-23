"""
Access Routes – IP-basierte Zugangskontrolle

Endpunkte für:
- Zugangsanfrage stellen (externe Geräte)
- Polling des Zugangsstatus (externe Geräte)
- Genehmigen/Ablehnen von IPs (lokaler Nutzer)
- Whitelist/Blacklist verwalten (lokaler Nutzer)
"""
from flask import Blueprint, request

from utils.access_control import (
    request_access, poll_access_status, approve_ip, deny_ip,
    get_pending_requests, get_access_lists, remove_from_whitelist,
    remove_from_blacklist, is_local_ip, set_access_control_enabled
)
from routes.helpers import success_response, error_response, handle_route_error
from utils.logger import log
from routes.react_frontend import serve_react_app


access_bp = Blueprint('access', __name__)


# ===== Externe Geräte: Zugang anfragen und Status prüfen =====

@access_bp.route('/access/waiting')
def waiting_screen():
    """Zeigt den Wartebildschirm für externe Geräte (React SPA)."""
    return serve_react_app()


@access_bp.route('/api/access/request', methods=['POST'])
@handle_route_error('access_request')
def access_request():
    """
    Externes Gerät stellt eine Zugangsanfrage.
    Wird automatisch von der Waiting-Seite aufgerufen.
    """
    ip = request.remote_addr
    
    result = request_access(ip)
    
    if result == 'allowed':
        return success_response(status='approved', message='Zugang gewährt')
    elif result == 'blocked':
        return success_response(status='denied', message='Zugang verweigert')
    elif result == 'rate_limited':
        return success_response(status='rate_limited', message='Zu viele Anfragen. Bitte warte 5 Minuten.')
    elif result == 'already_pending':
        return success_response(status='pending', message='Anfrage wartet auf Genehmigung')
    else:  # pending
        return success_response(status='pending', message='Zugangsanfrage gesendet. Warte auf Genehmigung...')


@access_bp.route('/api/access/poll', methods=['GET'])
@handle_route_error('access_poll')
def access_poll():
    """
    Externes Gerät prüft den Status seiner Zugangsanfrage.
    Wird per Polling alle 2 Sekunden aufgerufen.
    """
    ip = request.remote_addr
    
    status = poll_access_status(ip)
    
    messages = {
        'pending': 'Warte auf Genehmigung...',
        'approved': 'Zugang genehmigt!',
        'denied': 'Zugang verweigert.',
        'expired': 'Anfrage abgelaufen. Bitte erneut versuchen.'
    }
    
    return success_response(status=status, message=messages.get(status, ''))


# ===== Lokaler Nutzer: Anfragen verwalten =====

@access_bp.route('/api/access/pending', methods=['GET'])
@handle_route_error('access_pending')
def get_pending():
    """Gibt alle ausstehenden Zugangsanfragen zurück (nur für lokalen Nutzer)."""
    if not is_local_ip(request.remote_addr):
        return error_response('Nur vom lokalen Gerät zugänglich', 403)
    
    pending = get_pending_requests()
    return success_response(pending=pending)


@access_bp.route('/api/access/approve', methods=['POST'])
@handle_route_error('access_approve')
def approve():
    """Genehmigt eine IP-Adresse (nur für lokalen Nutzer)."""
    if not is_local_ip(request.remote_addr):
        return error_response('Nur vom lokalen Gerät zugänglich', 403)
    
    data = request.get_json()
    ip = data.get('ip', '').strip()
    
    if not ip:
        return error_response('IP-Adresse fehlt')
    
    approve_ip(ip)
    return success_response(message=f'IP {ip} genehmigt')


@access_bp.route('/api/access/deny', methods=['POST'])
@handle_route_error('access_deny')
def deny():
    """Verweigert eine IP-Adresse (nur für lokalen Nutzer)."""
    if not is_local_ip(request.remote_addr):
        return error_response('Nur vom lokalen Gerät zugänglich', 403)
    
    data = request.get_json()
    ip = data.get('ip', '').strip()
    
    if not ip:
        return error_response('IP-Adresse fehlt')
    
    deny_ip(ip)
    return success_response(message=f'IP {ip} blockiert')


# ===== Lokaler Nutzer: Listen verwalten =====

@access_bp.route('/api/access/lists', methods=['GET'])
@handle_route_error('access_lists')
def get_lists():
    """Gibt Whitelist und Blacklist zurück (nur für lokalen Nutzer)."""
    if not is_local_ip(request.remote_addr):
        return error_response('Nur vom lokalen Gerät zugänglich', 403)
    
    lists = get_access_lists()
    return success_response(**lists)


@access_bp.route('/api/access/whitelist/remove', methods=['POST'])
@handle_route_error('access_whitelist_remove')
def whitelist_remove():
    """Entfernt eine IP aus der Whitelist (nur für lokalen Nutzer)."""
    if not is_local_ip(request.remote_addr):
        return error_response('Nur vom lokalen Gerät zugänglich', 403)
    
    data = request.get_json()
    ip = data.get('ip', '').strip()
    
    if not ip:
        return error_response('IP-Adresse fehlt')
    
    if remove_from_whitelist(ip):
        return success_response(message=f'IP {ip} aus Whitelist entfernt')
    return error_response(f'IP {ip} nicht in Whitelist gefunden')


@access_bp.route('/api/access/blacklist/remove', methods=['POST'])
@handle_route_error('access_blacklist_remove')
def blacklist_remove():
    """Entfernt eine IP aus der Blacklist (nur für lokalen Nutzer)."""
    if not is_local_ip(request.remote_addr):
        return error_response('Nur vom lokalen Gerät zugänglich', 403)
    
    data = request.get_json()
    ip = data.get('ip', '').strip()
    
    if not ip:
        return error_response('IP-Adresse fehlt')
    
    if remove_from_blacklist(ip):
        return success_response(message=f'IP {ip} aus Blacklist entfernt')
    return error_response(f'IP {ip} nicht in Blacklist gefunden')


@access_bp.route('/api/access/toggle', methods=['POST'])
@handle_route_error('access_toggle')
def toggle_access_control():
    """Aktiviert/deaktiviert die Zugangskontrolle (nur für lokalen Nutzer)."""
    if not is_local_ip(request.remote_addr):
        return error_response('Nur vom lokalen Gerät zugänglich', 403)
    
    data = request.get_json()
    enabled = data.get('enabled', True)
    
    if set_access_control_enabled(enabled):
        return success_response(
            enabled=enabled,
            message=f'Zugangskontrolle {"aktiviert" if enabled else "deaktiviert"}'
        )
    return error_response('Fehler beim Ändern der Zugangskontrolle')
