"""
Chat Routes - Nachrichtenaustausch und Chat-Verwaltung
"""
from flask import Blueprint, request, Response, stream_with_context
import json

from utils.database import get_conversation_context, save_message, clear_chat_history
from utils.config import load_character
from utils.logger import log
from utils.provider import get_chat_service, get_api_client
from routes.helpers import success_response, error_response, handle_route_error, resolve_persona_id, get_client_ip
from routes.user_profile import get_user_profile_data

chat_bp = Blueprint('chat', __name__)


@chat_bp.route('/chat', methods=['POST'])
@handle_route_error('chat')
def chat():
    """
    API-Endpoint für nicht-gestreamte Chat-Nachrichten.
    Normale Chat-Nachrichten sollten /chat_stream verwenden.
    """
    data = request.get_json()
    user_message = data.get('message', '').strip()
    
    if not user_message:
        return error_response('Leere Nachricht')
    
    # WICHTIG: Prüfe ZUERST ob API-Key vorhanden ist, BEVOR die Nachricht gespeichert wird
    if not get_api_client().is_ready:
        return error_response('Kein API-Key konfiguriert', error_type='api_key_missing')
    
    # Dieser Endpoint sollte nicht für normale Chat-Nachrichten verwendet werden
    # Normale Chat-Nachrichten sollten über /chat_stream laufen
    return error_response('Please use /chat_stream for normal chat messages')


@chat_bp.route('/chat_stream', methods=['POST'])
@handle_route_error('chat_stream')
def chat_stream():
    """API-Endpoint für gestreamte Chat-Nachrichten via SSE"""
    data = request.get_json()
    user_message = data.get('message', '').strip()
    session_id = data.get('session_id')
    api_model = data.get('api_model')
    api_temperature = data.get('api_temperature')
    experimental_mode = data.get('experimental_mode', False)
    
    # Persona-ID bestimmen (einheitlich über resolve_persona_id)
    persona_id = resolve_persona_id(session_id=session_id)
    
    log.info("Chat-Request: experimental_mode=%s, session=%s, persona=%s", experimental_mode, session_id, persona_id)
    
    # IP-Adresse ermitteln
    user_ip = get_client_ip()
    
    if not user_message:
        return error_response('Leere Nachricht')
    
    # API-Key Check
    if not get_api_client().is_ready:
        return error_response('Kein API-Key konfiguriert', error_type='api_key_missing')
    
    # Lade Charakterdaten
    character = load_character()
    character_name = character.get('char_name', 'Assistant')
    
    # User-Name aus Profil
    user_profile = get_user_profile_data()
    user_name = user_profile.get('user_name', 'User') or 'User'
    
    # Context Limit
    context_limit = data.get('context_limit', 25)
    try:
        context_limit = int(context_limit)
    except (TypeError, ValueError):
        context_limit = 25
    context_limit = max(10, min(100, context_limit))
    
    # Konversationskontext holen (mit persona_id für richtige DB!)
    conversation_history = get_conversation_context(limit=context_limit, session_id=session_id, persona_id=persona_id)
    
    def generate():
        chat_service = get_chat_service()
        user_msg_saved = False
        try:
            for event_type, event_data in chat_service.chat_stream(
                user_message=user_message,
                conversation_history=conversation_history,
                character_data=character,
                language='Deutsch',
                user_name=user_name,
                api_model=api_model,
                api_temperature=api_temperature,
                ip_address=user_ip,
                experimental_mode=experimental_mode,
                persona_id=persona_id
            ):
                if event_type == 'chunk':
                    # Benutzernachricht erst beim ersten erfolgreichen Chunk speichern
                    if not user_msg_saved:
                        save_message(user_message, True, character_name, session_id, persona_id=persona_id)
                        user_msg_saved = True
                    yield f"data: {json.dumps({'type': 'chunk', 'text': event_data})}\n\n"
                elif event_type == 'done':
                    # Bot-Antwort in Persona-DB speichern
                    save_message(event_data['response'], False, character_name, session_id, persona_id=persona_id)
                    yield f"data: {json.dumps({'type': 'done', 'response': event_data['response'], 'stats': event_data['stats'], 'character_name': character_name})}\n\n"
                elif event_type == 'error':
                    error_payload = {'type': 'error', 'error': event_data}
                    if event_data == 'credit_balance_exhausted':
                        error_payload['error_type'] = 'credit_balance_exhausted'
                    yield f"data: {json.dumps(error_payload)}\n\n"
        except Exception as e:
            log.error("Stream-Fehler: %s", e)
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )
    
@chat_bp.route('/clear_chat', methods=['POST'])
@handle_route_error('clear_chat')
def clear_chat():
    """Löscht die Chat-Historie"""
    clear_chat_history()
    return success_response()


@chat_bp.route('/afterthought', methods=['POST'])
@handle_route_error('afterthought')
def afterthought():
    """
    Nachgedanke-System: Innerer Dialog der Persona.
    Phase 1: Entscheidung ob die Persona etwas ergänzen möchte.
    Phase 2: Falls ja, streame die Ergänzung.
    """
    data = request.get_json()
    session_id = data.get('session_id')
    elapsed_time = data.get('elapsed_time', '10 Sekunden')
    phase = data.get('phase', 'decision')  # 'decision' oder 'followup'
    inner_dialogue = data.get('inner_dialogue', '')
    api_model = data.get('api_model')
    api_temperature = data.get('api_temperature')
    experimental_mode = data.get('experimental_mode', False)
    context_limit = data.get('context_limit', 25)
    context_limit = max(10, min(100, context_limit))
    
    # Persona-ID bestimmen (einheitlich über resolve_persona_id)
    persona_id = resolve_persona_id(session_id=session_id)
    
    # IP-Adresse ermitteln
    user_ip = get_client_ip()
    
    if not get_api_client().is_ready:
        return error_response('API nicht verfügbar')
    
    # Lade Charakterdaten
    character = load_character()
    character_name = character.get('char_name', 'Assistant')
    
    # User-Name aus Profil
    afterthought_profile = get_user_profile_data()
    afterthought_user_name = afterthought_profile.get('user_name', 'User') or 'User'
    
    # Konversationskontext holen (aus Persona-DB)
    conversation_history = get_conversation_context(limit=context_limit, session_id=session_id, persona_id=persona_id)
    
    chat_service = get_chat_service()
    
    if phase == 'decision':
        # Phase 1: Innerer Dialog - Entscheidung
        result = chat_service.afterthought_decision(
            conversation_history=conversation_history,
            character_data=character,
            elapsed_time=elapsed_time,
            language='Deutsch',
            user_name=afterthought_user_name,
            api_model=api_model,
            api_temperature=api_temperature,
            ip_address=user_ip,
            nsfw_mode=experimental_mode,
            persona_id=persona_id
        )
        
        return success_response(
            decision=result['decision'],
            inner_dialogue=result['inner_dialogue'],
            error=result.get('error')
        )
    
    elif phase == 'followup':
        # Phase 2: Ergänzung streamen
        if not inner_dialogue:
            return error_response('Kein innerer Dialog vorhanden')
        
        def generate():
            try:
                for event_type, event_data in chat_service.afterthought_followup(
                    conversation_history=conversation_history,
                    character_data=character,
                    inner_dialogue=inner_dialogue,
                    elapsed_time=elapsed_time,
                    language='Deutsch',
                    user_name=afterthought_user_name,
                    api_model=api_model,
                    api_temperature=api_temperature,
                    ip_address=user_ip,
                    nsfw_mode=experimental_mode,
                    persona_id=persona_id
                ):
                    if event_type == 'chunk':
                        yield f"data: {json.dumps({'type': 'chunk', 'text': event_data})}\n\n"
                    elif event_type == 'done':
                        # Speichere die Ergänzung in der Persona-DB
                        save_message(event_data['response'], False, character_name, session_id, persona_id=persona_id)
                        yield f"data: {json.dumps({'type': 'done', 'response': event_data['response'], 'stats': event_data['stats'], 'character_name': character_name})}\n\n"
                    elif event_type == 'error':
                        yield f"data: {json.dumps({'type': 'error', 'error': event_data})}\n\n"
            except Exception as e:
                log.error("Nachgedanke Stream-Fehler: %s", e)
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
        
        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
                'Connection': 'keep-alive'
            }
        )
        
    else:
        return error_response(f'Unbekannte Phase: {phase}')
