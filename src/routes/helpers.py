"""
Route Helpers - Einheitliche Response-Formate, Fehlerbehandlung und gemeinsame Hilfsfunktionen
"""
import traceback
from functools import wraps
from flask import jsonify, request

from utils.config import get_active_persona_id
from utils.database import find_session_persona
from utils.logger import log


# ===== Einheitliche Response-Funktionen =====

def success_response(status_code=200, **data):
    """
    Erzeugt eine einheitliche Erfolgs-Antwort.
    
    Verwendung:
        return success_response(personas=personas_list)
        return success_response(title=title, status_code=201)
    
    Gibt zurück:
        {'success': True, ...data}, status_code
    """
    return jsonify({'success': True, **data}), status_code


def error_response(message, status_code=400, **extra):
    """
    Erzeugt eine einheitliche Fehler-Antwort.
    
    Verwendung:
        return error_response('Leere Nachricht')
        return error_response('Nicht gefunden', 404)
        return error_response('API-Key fehlt', 400, error_type='api_key_missing')
    
    Gibt zurück:
        {'success': False, 'error': message, ...extra}, status_code
    """
    return jsonify({'success': False, 'error': message, **extra}), status_code


# ===== Einheitliche Fehlerbehandlung =====

def handle_route_error(endpoint_name):
    """
    Decorator für einheitliche Fehlerbehandlung in Route-Funktionen.
    
    Fängt alle Exceptions, loggt sie einheitlich und gibt eine
    standardisierte Fehlerantwort zurück.
    
    Verwendung:
        @bp.route('/api/example', methods=['GET'])
        @handle_route_error('get_example')
        def get_example():
            ...
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                error_details = traceback.format_exc()
                log.error("Fehler in %s: %s", endpoint_name, e)
                log.debug("Traceback [%s]: %s", endpoint_name, error_details)
                return error_response('Server-Fehler', 500)
        return wrapper
    return decorator


# ===== Persona-ID-Auflösung =====

def resolve_persona_id(session_id=None):
    """
    Bestimmt die persona_id aus verschiedenen Quellen (einheitlich für alle Routes).
    
    Reihenfolge:
    1. Query-Parameter 'persona_id'
    2. JSON-Body 'persona_id'
    3. Session-Lookup via find_session_persona(session_id)
    4. Fallback: get_active_persona_id()
    
    Args:
        session_id: Optionale Session-ID für den Lookup
    
    Returns:
        persona_id als String
    """
    # Aus Query-Parameter
    pid = request.args.get('persona_id')
    if pid:
        return pid

    # Aus JSON-Body
    if request.is_json:
        data = request.get_json(silent=True)
        if data and data.get('persona_id'):
            return data['persona_id']

    # Per Session-Lookup
    if session_id is not None:
        found = find_session_persona(session_id)
        if found:
            return found

    # Aktive Persona als Fallback
    return get_active_persona_id()


# ===== Gemeinsame Request-Hilfsfunktionen =====

def get_client_ip():
    """
    Ermittelt die IP-Adresse des Clients (berücksichtigt Proxies).
    
    Returns:
        IP-Adresse als String
    """
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip and ',' in ip:
        ip = ip.split(',')[0].strip()
    return ip
