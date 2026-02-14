"""
API-Routen für Memory-Management
"""

from flask import Blueprint, request
from utils.database import (
    get_all_memories,
    update_memory,
    delete_memory,
    toggle_memory_status,
    get_user_message_count_since_marker,
    get_last_memory_message_id,
    get_message_count,
    get_messages_since_marker,
    get_db_connection
)
from utils.provider import get_memory_service
from utils.config import get_active_persona_id
from routes.helpers import success_response, error_response, handle_route_error

memory_bp = Blueprint('memory', __name__)


@memory_bp.route('/api/memory/preview', methods=['POST'])
@handle_route_error('preview_memory')
def preview_memory():
    """
    Generiert eine Memory-Zusammenfassung OHNE zu speichern (nur Vorschau)
    
    Erwartet JSON:
    {
        "session_id": int
    }
    
    Returns:
        JSON mit generiertem Memory-Content (OHNE zu speichern)
    """
    data = request.get_json()
    session_id = data.get('session_id')
    
    if not session_id:
        return error_response('session_id fehlt')
    
    # Hole die aktive Persona-ID
    persona_id = get_active_persona_id()
    
    # Generiere Zusammenfassung OHNE zu speichern via MemoryService
    summary = get_memory_service().create_summary_preview(session_id, persona_id=persona_id)
    
    if summary:
        return success_response(content=summary)
    else:
        return error_response('Keine Nachrichten zum Zusammenfassen vorhanden')


@memory_bp.route('/api/memory/create', methods=['POST'])
@handle_route_error('create_memory')
def create_memory():
    """
    Erstellt eine neue Memory-Zusammenfassung für eine Session
    
    Erwartet JSON:
    {
        "session_id": int,
        "content": str (optional - wenn gegeben, wird dieser Text gespeichert statt neu zu generieren)
    }
    
    Returns:
        JSON mit Memory-Informationen oder Fehler
    """
    data = request.get_json()
    session_id = data.get('session_id')
    custom_content = data.get('content')  # Optional: Vorgegebener Content
    
    if not session_id:
        return error_response('session_id fehlt')
    
    # Hole die aktive Persona-ID
    persona_id = get_active_persona_id()
    
    # Wenn Content übergeben wurde, speichere diesen direkt
    if custom_content:
        result = get_memory_service().save_custom_memory(session_id, custom_content, persona_id=persona_id)
    else:
        # Ansonsten: Erstelle und speichere Memory wie bisher
        result = get_memory_service().save_session_memory(session_id, persona_id=persona_id)
    
    if result['success']:
        return success_response(**{k: v for k, v in result.items() if k != 'success'})
    else:
        return error_response(result.get('error', 'Unbekannter Fehler'))



@memory_bp.route('/api/memory/list', methods=['GET'])
@handle_route_error('list_memories')
def list_memories():
    """
    Listet alle Memories auf (gefiltert nach aktiver Persona)
    
    Query-Parameter:
        persona_id: Optional - Persona-ID zum Filtern (Standard: aktive Persona)
    
    Returns:
        JSON-Array mit Memories der aktuellen Persona
    """
    # Hole persona_id aus Query-Parameter oder verwende aktive Persona
    persona_id = request.args.get('persona_id') or get_active_persona_id()
    memories = get_all_memories(persona_id=persona_id)
    return success_response(memories=memories)


@memory_bp.route('/api/memory/<int:memory_id>', methods=['PUT'])
@handle_route_error('update_memory')
def update_memory(memory_id):
    """
    Aktualisiert den Inhalt einer Memory
    
    Erwartet JSON:
    {
        "content": str
    }
    
    Returns:
        JSON mit Erfolgs-Status
    """
    data = request.get_json()
    content = data.get('content')
    
    if not content:
        return error_response('content fehlt')
    
    success = update_memory(memory_id, content, persona_id=get_active_persona_id())
    
    if success:
        return success_response()
    else:
        return error_response('Aktualisierung fehlgeschlagen')


@memory_bp.route('/api/memory/<int:memory_id>', methods=['DELETE'])
@handle_route_error('delete_memory')
def delete_memory(memory_id):
    """
    Löscht eine Memory
    
    Returns:
        JSON mit Erfolgs-Status
    """
    success = delete_memory(memory_id, persona_id=get_active_persona_id())
    
    if success:
        return success_response()
    else:
        return error_response('Löschen fehlgeschlagen')


@memory_bp.route('/api/memory/<int:memory_id>/toggle', methods=['PATCH'])
@handle_route_error('toggle_memory_status')
def toggle_memory_status(memory_id):
    """
    Schaltet den Aktiv-Status einer Memory um
    
    Returns:
        JSON mit Erfolgs-Status
    """
    success = toggle_memory_status(memory_id, persona_id=get_active_persona_id())
    
    if success:
        return success_response()
    else:
        return error_response('Status-Änderung fehlgeschlagen')


@memory_bp.route('/api/memory/check-availability/<int:session_id>', methods=['GET'])
@handle_route_error('check_memory_availability')
def check_memory_availability(session_id):
    """
    Prüft ob der Memory-Button aktiviert werden soll.
    Erfordert mindestens 10 User-Nachrichten seit dem letzten Memory-Marker.
    Gibt zusätzlich Kontext-Limit-Informationen zurück.
    
    Returns:
        JSON mit availability-Status, message_count, context_limit_warning
    """
    persona_id = request.args.get('persona_id') or get_active_persona_id()
    context_limit = request.args.get('context_limit', 25, type=int)
    
    # User-Nachrichten seit letztem Marker zählen
    user_msg_since_marker = get_user_message_count_since_marker(session_id, persona_id=persona_id)
    total_count = get_message_count(session_id=session_id, persona_id=persona_id)
    last_marker = get_last_memory_message_id(session_id, persona_id=persona_id)
    
    # Memory-Kontext-Info: Wie viele Nachrichten würden an die API gehen?
    memory_context = get_messages_since_marker(session_id, persona_id=persona_id)
    memory_context_truncated = memory_context.get('truncated', False)
    memory_context_total = memory_context.get('total', 0)
    memory_context_used = len(memory_context.get('messages', []))
    
    # Mindestens 10 User-Nachrichten seit Marker erforderlich
    min_threshold = 10
    available = user_msg_since_marker >= min_threshold
    
    # Kontext-Limit-Warnung: Nachrichten seit Marker vs. context_limit
    # Nur relevant wenn genug Nachrichten seit Marker vorhanden sind
    messages_since_marker = total_count
    if last_marker:
        # Zähle alle Nachrichten (user + bot) seit dem Marker
        conn = get_db_connection(persona_id)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT COUNT(*) FROM chat_messages WHERE session_id = ? AND id > ?',
            (session_id, last_marker)
        )
        messages_since_marker = cursor.fetchone()[0]
        conn.close()
    
    context_limit_ratio = messages_since_marker / max(context_limit, 1)
    # Warnungen nur wenn Button auch verfügbar ist (>= 10 User-Msgs)
    context_limit_warning = available and context_limit_ratio >= 0.8
    context_limit_critical = available and context_limit_ratio >= 0.95
    
    return success_response(
        available=available,
        message_count=total_count,
        user_messages_since_marker=user_msg_since_marker,
        min_threshold=min_threshold,
        has_previous_memory=last_marker is not None,
        context_limit_warning=context_limit_warning,
        context_limit_critical=context_limit_critical,
        context_limit_ratio=round(context_limit_ratio, 2),
        memory_context_truncated=memory_context_truncated,
        memory_context_total=memory_context_total,
        memory_context_used=memory_context_used
    )


@memory_bp.route('/api/memory/stats', methods=['GET'])
@handle_route_error('get_memory_stats')
def get_memory_stats():
    """
    Gibt Statistiken über Memories zurück (aktive/gesamt) - gefiltert nach Persona
    
    Query-Parameter:
        persona_id: Optional - Persona-ID zum Filtern (Standard: aktive Persona)
    
    Returns:
        JSON mit Statistiken
    """
    persona_id = request.args.get('persona_id') or get_active_persona_id()
    all_memories = get_all_memories(persona_id=persona_id)
    active_count = sum(1 for m in all_memories if m['is_active'])
    total_count = len(all_memories)
    
    return success_response(
        active_count=active_count,
        total_count=total_count,
        limit=30
    )
