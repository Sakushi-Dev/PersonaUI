"""
Session Routes - Session-Management für Chat-Verläufe
"""
from flask import Blueprint, request

from utils.database import (
    get_all_sessions, create_session, get_session,
    delete_session, get_chat_history, get_message_count,
    get_persona_session_summary
)
from utils.config import load_character, get_active_persona_id, activate_persona, load_char_config
from utils.cortex.tier_tracker import reset_session as reset_session_cycle_state
from routes.helpers import success_response, error_response, handle_route_error, resolve_persona_id

sessions_bp = Blueprint('sessions', __name__)


@sessions_bp.route('/api/sessions', methods=['GET'])
@handle_route_error('get_sessions')
def get_sessions():
    """Gibt alle Chat-Sessions zurück, optional gefiltert nach persona_id"""
    persona_id = request.args.get('persona_id', None)
    sessions = get_all_sessions(persona_id=persona_id)
    return success_response(sessions=sessions)


@sessions_bp.route('/api/sessions/persona_summary', methods=['GET'])
@handle_route_error('get_persona_summary')
def get_persona_summary():
    """Gibt eine Übersicht der Sessions pro Persona zurück"""
    summary = get_persona_session_summary()
    return success_response(summary=summary)


@sessions_bp.route('/api/sessions/new', methods=['POST'])
@handle_route_error('new_session')
def new_session():
    """Erstellt eine neue Chat-Session für die aktive Persona"""
    # Persona-ID aus Request oder aktive Persona verwenden
    data = request.get_json() or {}
    persona_id = data.get('persona_id') or get_active_persona_id()
    
    # Wenn die Session für eine andere Persona erstellt wird, aktiviere sie zuerst
    if persona_id != get_active_persona_id():
        activate_persona(persona_id)
    
    # Erstelle neue Session in der Persona-DB
    session_id = create_session(persona_id=persona_id)
    
    # Lade Charakterdaten
    character = load_character()
    
    # Prüfe ob Auto-First-Message aktiviert ist
    auto_first_message = character.get('start_msg_enabled', False)
    
    # Hole die erstellte Session
    session = get_session(session_id, persona_id=persona_id)
    
    # Lade Charakterdaten für Soft-Reload (Header + Chat-Bubbles)
    config = load_char_config()
    character_data = {
        'char_name': character.get('char_name', 'Assistant'),
        'avatar': config.get('avatar'),
        'avatar_type': config.get('avatar_type')
    }
    
    # Hole Chat-Historie
    chat_history = get_chat_history(session_id=session_id, persona_id=persona_id)
    
    # Gesamtanzahl Nachrichten für Load-More-Button
    total_message_count = get_message_count(session_id=session_id, persona_id=persona_id)
    
    return success_response(
        session=session,
        session_id=session_id,
        persona_id=persona_id,
        character=character_data,
        chat_history=chat_history,
        total_message_count=total_message_count,
        auto_first_message=auto_first_message
    )


@sessions_bp.route('/api/sessions/<int:session_id>', methods=['GET'])
@handle_route_error('get_session_data')
def get_session_data(session_id):
    """Lädt eine spezifische Session"""
    # Bestimme persona_id für DB-Zugriff
    persona_id = resolve_persona_id(session_id=session_id)
    
    # Hole Session-Daten aus der Persona-DB
    session = get_session(session_id, persona_id=persona_id)
    if not session:
        return error_response('Session nicht gefunden', 404)
    
    # Prüfe ob die Session einer anderen Persona gehört und aktiviere sie ggf.
    session_persona_id = session.get('persona_id', persona_id)
    current_persona_id = get_active_persona_id()
    persona_switched = False
    
    if session_persona_id != current_persona_id:
        activate_persona(session_persona_id)
        persona_switched = True
    
    # Hole Chat-Historie aus der Persona-DB
    chat_history = get_chat_history(session_id=session_id, persona_id=persona_id)
    
    total_message_count = get_message_count(session_id, persona_id=persona_id)
    
    # Lade Charakterdaten für Soft-Reload (Header + Chat-Bubbles)
    character = load_character()
    config = load_char_config()
    character_data = {
        'char_name': character.get('char_name', 'Assistant'),
        'avatar': config.get('avatar'),
        'avatar_type': config.get('avatar_type')
    }
    
    return success_response(
        session=session,
        chat_history=chat_history,
        total_message_count=total_message_count,
        persona_switched=persona_switched,
        persona_id=session_persona_id,
        character=character_data
    )


@sessions_bp.route('/api/sessions/<int:session_id>', methods=['DELETE'])
@handle_route_error('delete_session')
def delete_session_endpoint(session_id):
    """Löscht eine Session"""
    persona_id = resolve_persona_id(session_id=session_id)
    success = delete_session(session_id, persona_id=persona_id)
    
    if success:
        # Cycle-State-Eintrag für diese Session entfernen
        reset_session_cycle_state(persona_id, session_id)
        return success_response()
    else:
        return error_response('Fehler beim Löschen', 500)


@sessions_bp.route('/api/sessions/<int:session_id>/is_empty', methods=['GET'])
@handle_route_error('check_session_is_empty')
def check_session_is_empty(session_id):
    """Prüft ob eine Session leer ist (keine User-Nachrichten)"""
    persona_id = resolve_persona_id(session_id=session_id)
    chat_history = get_chat_history(session_id=session_id, persona_id=persona_id)
    
    # Zähle User-Nachrichten
    user_messages = [msg for msg in chat_history if msg.get('is_user', False)]
    
    # Session ist leer wenn es keine User-Nachrichten gibt
    is_empty = len(user_messages) == 0
    
    return success_response(
        is_empty=is_empty,
        message_count=len(chat_history),
        user_message_count=len(user_messages)
    )


@sessions_bp.route('/api/sessions/<int:session_id>/load_more', methods=['POST'])
@handle_route_error('load_more_messages')
def load_more_messages(session_id):
    """Lädt weitere ältere Nachrichten für eine Session"""
    data = request.get_json()
    offset = data.get('offset', 0)
    limit = data.get('limit', 30)
    persona_id = data.get('persona_id') or resolve_persona_id(session_id=session_id)
    
    # Hole weitere Nachrichten mit Offset aus der Persona-DB
    messages = get_chat_history(limit=limit, session_id=session_id, offset=offset, persona_id=persona_id)
    
    # Hole Gesamtanzahl
    total_count = get_message_count(session_id=session_id, persona_id=persona_id)
    
    return success_response(
        messages=messages,
        total_count=total_count,
        has_more=(offset + limit) < total_count
    )

