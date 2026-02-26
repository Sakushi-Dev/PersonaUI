"""
Chat Routes - Nachrichtenaustausch und Chat-Verwaltung
"""
from flask import Blueprint, request, Response, stream_with_context
import json

from utils.database import (
    get_conversation_context, save_message, clear_chat_history,
    get_last_message, delete_last_message, update_last_message_text
)
from utils.config import load_character
from utils.logger import log
from utils.provider import get_chat_service, get_api_client, get_cortex_service
from utils.cortex.tier_checker import check_and_trigger_cortex_update
from utils.cortex.tier_tracker import reset_persona as reset_persona_cycle_state
from utils.cortex_service import TEMPLATES
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
    persona_language = user_profile.get('persona_language', 'english') or 'english'
    
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
                language=persona_language,
                user_name=user_name,
                api_model=api_model,
                api_temperature=api_temperature,
                ip_address=user_ip,
                experimental_mode=experimental_mode,
                persona_id=persona_id,
                session_id=session_id
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

                    # ═══ Cortex Trigger-Check VOR done-yield ═══
                    cortex_info = None
                    try:
                        cortex_info = check_and_trigger_cortex_update(
                            persona_id=persona_id,
                            session_id=session_id
                        )
                    except Exception as cortex_err:
                        log.warning("Cortex check failed (non-fatal): %s", cortex_err)

                    # done-Payload zusammenbauen
                    done_payload = {
                        'type': 'done',
                        'response': event_data['response'],
                        'stats': event_data['stats'],
                        'character_name': character_name
                    }

                    # Cortex-Info mitsenden (Progress + Trigger-Status)
                    if cortex_info:
                        done_payload['cortex'] = cortex_info

                    yield f"data: {json.dumps(done_payload)}\n\n"
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
    """Löscht die Chat-Historie und setzt Cortex-Dateien zurück."""
    persona_id = resolve_persona_id()
    clear_chat_history(persona_id)

    # Cortex-Dateien auf Templates zurücksetzen
    try:
        cortex = get_cortex_service()
        for filename, template_content in TEMPLATES.items():
            cortex.write_file(persona_id, filename, template_content)
        log.info("Cortex-Dateien zurückgesetzt für Persona: %s", persona_id)
    except Exception as e:
        log.warning("Cortex-Reset fehlgeschlagen für %s: %s", persona_id, e)

    # Cycle-State-Einträge für diese Persona entfernen
    reset_persona_cycle_state(persona_id)

    return success_response()


@chat_bp.route('/chat/last_message', methods=['DELETE'])
@handle_route_error('delete_last_message')
def api_delete_last_message():
    """Löscht die letzte Nachricht einer Session aus der DB."""
    session_id = request.args.get('session_id', type=int)
    persona_id = resolve_persona_id(session_id=session_id)

    if not session_id:
        return error_response('Session-ID fehlt')

    deleted = delete_last_message(session_id, persona_id)
    if not deleted:
        return error_response('Keine Nachricht gefunden', 404)

    return success_response(deleted_message=deleted)


@chat_bp.route('/chat/last_message', methods=['PUT'])
@handle_route_error('edit_last_message')
def api_edit_last_message():
    """Aktualisiert den Text der letzten Nachricht einer Session."""
    data = request.get_json()
    session_id = data.get('session_id')
    new_message = data.get('message', '').strip()
    persona_id = resolve_persona_id(session_id=session_id)

    if not session_id:
        return error_response('Session-ID fehlt')
    if not new_message:
        return error_response('Nachricht darf nicht leer sein')

    updated = update_last_message_text(session_id, new_message, persona_id)
    if not updated:
        return error_response('Nachricht nicht gefunden', 404)

    return success_response()


@chat_bp.route('/chat/regenerate', methods=['POST'])
@handle_route_error('regenerate')
def api_regenerate():
    """
    Regeneriert die letzte Bot-Antwort.
    1. Löscht die letzte Bot-Nachricht aus der DB
    2. Holt den Konversationskontext (endet jetzt mit der User-Nachricht)
    3. Streamt eine neue Bot-Antwort
    """
    data = request.get_json()
    session_id = data.get('session_id')
    api_model = data.get('api_model')
    api_temperature = data.get('api_temperature')
    experimental_mode = data.get('experimental_mode', False)
    context_limit = data.get('context_limit', 25)

    try:
        context_limit = int(context_limit)
    except (TypeError, ValueError):
        context_limit = 25
    context_limit = max(10, min(100, context_limit))

    persona_id = resolve_persona_id(session_id=session_id)
    user_ip = get_client_ip()

    if not session_id:
        return error_response('Session-ID fehlt')

    if not get_api_client().is_ready:
        return error_response('Kein API-Key konfiguriert', error_type='api_key_missing')

    # Letzte Nachricht prüfen (muss Bot-Nachricht sein)
    last_msg = get_last_message(session_id, persona_id)
    if not last_msg:
        return error_response('Keine Nachricht gefunden', 404)
    if last_msg['is_user']:
        return error_response('Letzte Nachricht ist keine Bot-Nachricht')

    # Bot-Nachricht löschen
    delete_last_message(session_id, persona_id)
    log.info("Regenerate: Letzte Bot-Nachricht gelöscht (id=%s, session=%s)", last_msg['id'], session_id)

    # Character- und User-Daten laden
    character = load_character()
    character_name = character.get('char_name', 'Assistant')
    user_profile = get_user_profile_data()
    user_name = user_profile.get('user_name', 'User') or 'User'
    persona_language = user_profile.get('persona_language', 'english') or 'english'

    # Konversationskontext holen (endet jetzt mit der User-Nachricht)
    conversation_history = get_conversation_context(
        limit=context_limit, session_id=session_id, persona_id=persona_id
    )

    if not conversation_history or conversation_history[-1]['role'] != 'user':
        return error_response('Keine User-Nachricht vor der Bot-Antwort gefunden')

    # Letzte User-Nachricht extrahieren (wird als user_message an chat_stream übergeben)
    user_message = conversation_history[-1]['content']
    conversation_history = conversation_history[:-1]

    def generate():
        chat_service = get_chat_service()
        try:
            for event_type, event_data in chat_service.chat_stream(
                user_message=user_message,
                conversation_history=conversation_history,
                character_data=character,
                language=persona_language,
                user_name=user_name,
                api_model=api_model,
                api_temperature=api_temperature,
                ip_address=user_ip,
                experimental_mode=experimental_mode,
                persona_id=persona_id,
                session_id=session_id
            ):
                if event_type == 'chunk':
                    yield f"data: {json.dumps({'type': 'chunk', 'text': event_data})}\n\n"
                elif event_type == 'done':
                    # Neue Bot-Antwort speichern
                    save_message(event_data['response'], False, character_name, session_id, persona_id=persona_id)

                    # ═══ Cortex Trigger-Check (identisch zu chat_stream) ═══
                    cortex_info = None
                    try:
                        cortex_info = check_and_trigger_cortex_update(
                            persona_id=persona_id,
                            session_id=session_id
                        )
                    except Exception as cortex_err:
                        log.warning("Cortex check failed (non-fatal): %s", cortex_err)

                    done_payload = {
                        'type': 'done',
                        'response': event_data['response'],
                        'stats': event_data['stats'],
                        'character_name': character_name
                    }
                    if cortex_info:
                        done_payload['cortex'] = cortex_info

                    yield f"data: {json.dumps(done_payload)}\n\n"
                elif event_type == 'error':
                    error_payload = {'type': 'error', 'error': event_data}
                    if event_data == 'credit_balance_exhausted':
                        error_payload['error_type'] = 'credit_balance_exhausted'
                    yield f"data: {json.dumps(error_payload)}\n\n"
        except Exception as e:
            log.error("Regenerate-Stream-Fehler: %s", e)
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


@chat_bp.route('/afterthought', methods=['POST'])
@handle_route_error('afterthought')
def afterthought():
    """
    Nachgedanke-System: Innerer Dialog der Persona.
    Phase 1: Entscheidung ob die Persona etwas ergänzen möchte.
    Phase 2: Falls ja, streame die Ergänzung.
    """
    # Guard: Nachgedanke muss aktiviert sein
    from routes.settings import _load_settings
    user_settings = _load_settings()
    nachgedanke_mode = user_settings.get('nachgedankeMode', 'off')
    if nachgedanke_mode == 'off' or not nachgedanke_mode:
        return success_response(decision=False, inner_dialogue='', blocked=True)

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
    afterthought_persona_language = afterthought_profile.get('persona_language', 'english') or 'english'
    
    # Konversationskontext holen (aus Persona-DB)
    conversation_history = get_conversation_context(limit=context_limit, session_id=session_id, persona_id=persona_id)
    
    chat_service = get_chat_service()
    
    if phase == 'decision':
        # Phase 1: Innerer Dialog - Entscheidung
        result = chat_service.afterthought_decision(
            conversation_history=conversation_history,
            character_data=character,
            elapsed_time=elapsed_time,
            language=afterthought_persona_language,
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
                    language=afterthought_persona_language,
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


@chat_bp.route('/chat/auto_first_message', methods=['POST'])
@handle_route_error('auto_first_message')
def auto_first_message():
    """
    Generiert automatisch die erste Nachricht für einen neuen Chat.
    Wird aufgerufen wenn start_msg_enabled=True und ein neuer Chat geöffnet wird.
    Sendet einen internen Prompt an die API und streamt die Antwort als SSE.
    """
    data = request.get_json()
    session_id = data.get('session_id')
    api_model = data.get('api_model')
    api_temperature = data.get('api_temperature')
    experimental_mode = data.get('experimental_mode', False)

    # Persona-ID bestimmen
    persona_id = resolve_persona_id(session_id=session_id)

    log.info("Auto-First-Message: session=%s, persona=%s", session_id, persona_id)

    # API-Key Check
    if not get_api_client().is_ready:
        return error_response('Kein API-Key konfiguriert', error_type='api_key_missing')

    # Lade Charakterdaten
    character = load_character()
    character_name = character.get('char_name', 'Assistant')

    # Prüfe ob Auto-First-Message aktiviert ist
    if not character.get('start_msg_enabled', False):
        return error_response('Auto First Message ist nicht aktiviert')

    # User-Name und Sprache aus Profil
    user_profile = get_user_profile_data()
    user_name = user_profile.get('user_name', 'User') or 'User'
    persona_language = user_profile.get('persona_language', 'english') or 'english'

    # IP-Adresse ermitteln
    user_ip = get_client_ip()

    # Interner Prompt für die erste Nachricht (wird NICHT als User-Message gespeichert)
    internal_prompt = (
        f"A new conversation has been opened. Write how {character_name} "
        f"would open this conversation or scenario. Stay fully in character. "
        f"Do not mention that this is a new conversation explicitly. "
        f"Just start naturally as {character_name} would."
    )

    # Leere Konversationshistorie (es ist ein neuer Chat)
    conversation_history = []

    def generate():
        chat_service = get_chat_service()
        try:
            for event_type, event_data in chat_service.chat_stream(
                user_message=internal_prompt,
                conversation_history=conversation_history,
                character_data=character,
                language=persona_language,
                user_name=user_name,
                api_model=api_model,
                api_temperature=api_temperature,
                ip_address=user_ip,
                experimental_mode=experimental_mode,
                persona_id=persona_id,
                session_id=session_id
            ):
                if event_type == 'chunk':
                    yield f"data: {json.dumps({'type': 'chunk', 'text': event_data})}\n\n"
                elif event_type == 'done':
                    # Speichere NUR die Bot-Antwort als erste Nachricht (kein User-Message)
                    save_message(event_data['response'], False, character_name, session_id, persona_id=persona_id)

                    done_payload = {
                        'type': 'done',
                        'response': event_data['response'],
                        'stats': event_data['stats'],
                        'character_name': character_name,
                        'is_auto_first_message': True
                    }
                    yield f"data: {json.dumps(done_payload)}\n\n"
                elif event_type == 'error':
                    error_payload = {'type': 'error', 'error': event_data}
                    yield f"data: {json.dumps(error_payload)}\n\n"
        except Exception as e:
            log.error("Auto-First-Message Stream-Fehler: %s", e)
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
