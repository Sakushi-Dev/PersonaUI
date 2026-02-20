"""
Main Routes - Hauptseite und statische Ressourcen
"""
from flask import Blueprint, render_template, request, redirect, url_for
import os

from utils.database import (
    get_chat_history, save_message, get_current_session_id,
    get_all_sessions, get_message_count, get_session_persona_id
)
from utils.config import load_character, load_char_config, get_active_persona_id, activate_persona
from routes.helpers import resolve_persona_id
from routes.user_profile import get_user_profile_data
from routes.onboarding import is_onboarding_complete
from routes.react_frontend import has_react_build, serve_react_app

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Hauptseite mit Chat-Interface (React SPA oder Jinja-Fallback)"""
    # React-Build vorhanden → SPA ausliefern
    if has_react_build():
        return serve_react_app()

    # Legacy Jinja-Fallback
    # Prüfe ob Onboarding abgeschlossen ist
    if not is_onboarding_complete():
        return redirect(url_for('onboarding.onboarding'))

    character = load_character()
    user_profile = get_user_profile_data()
    
    # Avatar-Daten aus der aktiven persona_config laden
    config = load_char_config()
    avatar_data = {
        'avatar': config.get('avatar'),
        'avatar_type': config.get('avatar_type')
    }
    
    # Aktive Persona ID
    active_persona_id = get_active_persona_id()
    
    # Merge Avatar-Daten mit Charakter-Daten für Template-Kompatibilität
    character.update(avatar_data)
    
    # Hole Session ID und Persona aus Query-Parametern
    session_id = request.args.get('session', type=int)
    session_persona_id = resolve_persona_id(session_id)
    
    # Hole Sessions der aktiven Persona für die Sidebar (JS lädt dynamisch per API nach)
    all_sessions = get_all_sessions(persona_id=session_persona_id)
    
    # Wenn eine Session-ID angegeben wurde, prüfe ob sie existiert
    if session_id is not None:
        session_exists = any(s['id'] == session_id for s in all_sessions)
        if not session_exists:
            # Session existiert nicht in dieser Persona-DB
            if all_sessions:
                session_id = all_sessions[0]['id']
            else:
                return render_template('chat.html', 
                                     character=character,
                                     chat_history=[],
                                     current_session_id=None,
                                     sessions=[],
                                     show_welcome=True,
                                     total_message_count=0,
                                     active_persona_id=active_persona_id,
                                     user_profile=user_profile)
    
    # Wenn keine Session-ID angegeben und keine Sessions existieren
    if session_id is None and not all_sessions:
        return render_template('chat.html', 
                             character=character,
                             chat_history=[],
                             current_session_id=None,
                             sessions=[],
                             show_welcome=True,
                             total_message_count=0,
                             active_persona_id=active_persona_id,
                             user_profile=user_profile)
    
    # Wenn keine Session-ID angegeben, verwende die neueste
    if session_id is None and all_sessions:
        session_id = all_sessions[0]['id']
    
    # Prüfe ob die Session einer anderen Persona gehört und wechsle ggf.
    if session_id and session_persona_id != active_persona_id:
        activate_persona(session_persona_id)
        active_persona_id = session_persona_id
        # Lade Character und Config neu mit der neuen Persona
        character = load_character()
        config = load_char_config()
        avatar_data = {
            'avatar': config.get('avatar'),
            'avatar_type': config.get('avatar_type')
        }
        character.update(avatar_data)
    
    chat_history = get_chat_history(session_id=session_id, persona_id=active_persona_id) if session_id else []
    total_count = get_message_count(session_id=session_id, persona_id=active_persona_id) if session_id else 0
    
    # Wenn Session vorhanden aber keine Chat-Historie, speichere Greeting (falls aktiviert)
    if session_id and not chat_history:
        greeting = character.get('greeting')
        if greeting:
            character_name = character.get('char_name', 'Assistant')
            save_message(greeting, False, character_name, session_id, persona_id=active_persona_id)
            chat_history = get_chat_history(session_id=session_id, persona_id=active_persona_id)
            total_count = get_message_count(session_id=session_id, persona_id=active_persona_id)
    
    return render_template('chat.html', 
                         character=character,
                         chat_history=chat_history,
                         current_session_id=session_id,
                         sessions=all_sessions,
                         show_welcome=False,
                         total_message_count=total_count,
                         active_persona_id=active_persona_id,
                         user_profile=user_profile)


# Avatar-Bilder werden jetzt über Flask's static-Ordner serviert:
# Standard-Avatare: /static/images/avatars/
# Custom-Avatare:   /static/images/custom/
