"""
Chat-Nachrichten Operationen

CRUD für Chat-Messages, Conversation-Context und History-Abfragen.
"""

from typing import List, Dict, Any, Optional

from ..logger import log
from ..sql_loader import sql
from .connection import get_db_connection


def get_chat_history(limit: int = 30, session_id: int = None, offset: int = 0,
                     persona_id: str = 'default') -> List[Dict[str, Any]]:
    """
    Holt die Chat-Historie aus der Datenbank
    
    Args:
        limit: Maximale Anzahl der zurückzugebenden Nachrichten (Standard: 30)
        session_id: ID der Session (wenn None, wird die neueste Session verwendet)
        offset: Anzahl der zu überspringenden Nachrichten (für Pagination)
        persona_id: ID der Persona (bestimmt welche DB verwendet wird)
        
    Returns:
        Liste von Nachricht-Dictionaries (neueste zuerst, dann umgekehrt)
    """
    conn = get_db_connection(persona_id)
    cursor = conn.cursor()
    
    # Wenn keine session_id angegeben, hole die neueste Session
    if session_id is None:
        cursor.execute(sql('chat.get_latest_session_id'))
        result = cursor.fetchone()
        if result:
            session_id = result[0]
        else:
            conn.close()
            return []
    
    # Hole Memory-Ranges für diese Session (nur AKTIVE Memories mit Ranges)
    cursor.execute(sql('chat.get_memory_ranges'), (session_id,))
    memory_ranges = cursor.fetchall()
    
    # Fallback: Wenn keine Ranges vorhanden, nutze den alten Marker
    cursor.execute(sql('chat.get_session_memory_marker'), (session_id,))
    marker_row = cursor.fetchone()
    last_memory_message_id = marker_row[0] if marker_row and marker_row[0] else None
    
    # Hilfsfunktion: Prüfe ob eine Message-ID in einem der Memory-Ranges liegt
    def is_memorized(msg_id):
        if memory_ranges:
            for start_id, end_id in memory_ranges:
                if start_id <= msg_id <= end_id:
                    return True
            return False
        # Fallback für alte Memories ohne Ranges
        return last_memory_message_id is not None and msg_id <= last_memory_message_id
    
    cursor.execute(sql('chat.get_chat_history'), (session_id, limit, offset))
    
    # Umkehren, damit die älteste der geladenen Nachrichten zuerst kommt
    messages = []
    for row in reversed(cursor.fetchall()):
        msg = {
            'id': row[0],
            'message': row[1],
            'is_user': bool(row[2]),
            'timestamp': row[3],
            'character_name': row[4],
            'memorized': is_memorized(row[0])
        }
        messages.append(msg)
    
    conn.close()
    return messages


def get_message_count(session_id: int = None, persona_id: str = 'default') -> int:
    """
    Holt die Gesamtanzahl der Nachrichten für eine Session
    
    Args:
        session_id: ID der Session (wenn None, wird die neueste Session verwendet)
        persona_id: ID der Persona
        
    Returns:
        Anzahl der Nachrichten
    """
    conn = get_db_connection(persona_id)
    cursor = conn.cursor()
    
    if session_id is None:
        cursor.execute(sql('chat.get_latest_session_id'))
        result = cursor.fetchone()
        if result:
            session_id = result[0]
        else:
            conn.close()
            return 0
    
    cursor.execute(sql('chat.get_message_count'), (session_id,))
    
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_conversation_context(limit: int = 10, session_id: int = None,
                             persona_id: str = 'default') -> list:
    """
    Holt die letzten N Nachrichten für den Kontext der Claude API
    
    Args:
        limit: Anzahl der letzten Nachrichten
        session_id: ID der Session (wenn None, wird die neueste Session verwendet)
        persona_id: ID der Persona
        
    Returns:
        Liste von Nachrichten im Claude API Format
    """
    conn = get_db_connection(persona_id)
    cursor = conn.cursor()
    
    if session_id is None:
        cursor.execute(sql('chat.get_latest_session_id'))
        result = cursor.fetchone()
        if result:
            session_id = result[0]
        else:
            conn.close()
            return []
    
    cursor.execute(sql('chat.get_conversation_context'), (session_id, limit))
    
    raw_rows = list(reversed(cursor.fetchall()))
    raw_count = len(raw_rows)
    
    log.debug("Context-History: session=%s, persona=%s, limit=%d, raw_count=%d",
             session_id, persona_id, limit, raw_count)
    
    messages = []
    merged_count = 0
    for row in raw_rows:
        role = "user" if row[1] else "assistant"
        # Aufeinanderfolgende gleiche Rollen zusammenführen (z.B. durch Afterthought)
        # Claude API erfordert alternierende user/assistant Rollen
        if messages and messages[-1]['role'] == role:
            messages[-1]['content'] += "\n\n" + row[0]
            merged_count += 1
        else:
            messages.append({
                'role': role,
                'content': row[0]
            })
    
    # Leading assistant messages (z.B. Greeting) werden NICHT mehr entfernt,
    # damit die KI weiß, dass sie bereits begrüßt hat.
    # Die Claude API akzeptiert Messages die mit assistant beginnen,
    # wenn der system-Parameter separat übergeben wird.
    
    if merged_count > 0:
        log.info("Context-History: %d Nachrichten zusammengeführt. Final: %d msgs",
                 merged_count, len(messages))
    else:
        log.debug("Context-History: Final %d msgs", len(messages))
    
    conn.close()
    return messages


def save_message(message: str, is_user: bool, character_name: str = 'Assistant',
                 session_id: int = None, persona_id: str = 'default') -> int:
    """
    Speichert eine Nachricht in der Datenbank
    
    Args:
        message: Der Nachrichtentext
        is_user: True wenn Nachricht vom User, False wenn vom Bot
        character_name: Name des Charakters
        session_id: ID der Session (wenn None, wird die neueste Session verwendet)
        persona_id: ID der Persona
        
    Returns:
        ID der eingefügten Nachricht
    """
    from .sessions import create_session
    
    conn = get_db_connection(persona_id)
    cursor = conn.cursor()
    
    if session_id is None:
        cursor.execute(sql('chat.get_latest_session_id'))
        result = cursor.fetchone()
        if result:
            session_id = result[0]
        else:
            conn.close()
            session_id = create_session(persona_id=persona_id)
            conn = get_db_connection(persona_id)
            cursor = conn.cursor()
    
    cursor.execute(sql('chat.insert_message'), (session_id, message, is_user, character_name))
    
    # Update session's updated_at timestamp
    cursor.execute(sql('chat.update_session_timestamp'), (session_id,))
    
    message_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return message_id


def clear_chat_history(persona_id: str = 'default'):
    """Löscht die gesamte Chat-Historie einer Persona"""
    conn = get_db_connection(persona_id)
    cursor = conn.cursor()
    cursor.execute(sql('chat.delete_all_messages'))
    cursor.execute(sql('chat.delete_all_sessions'))
    conn.commit()
    conn.close()


def get_total_message_count(persona_id: str = 'default') -> int:
    """Gibt die Gesamtanzahl aller Nachrichten zurück (über alle Sessions einer Persona)"""
    conn = get_db_connection(persona_id)
    cursor = conn.cursor()
    cursor.execute(sql('chat.get_total_message_count'))
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_max_message_id(session_id: int, persona_id: str = 'default') -> Optional[int]:
    """
    Holt die höchste Nachrichten-ID einer Session.
    
    Args:
        session_id: ID der Session
        persona_id: ID der Persona
        
    Returns:
        Höchste Message-ID oder None
    """
    conn = get_db_connection(persona_id)
    cursor = conn.cursor()
    cursor.execute(sql('chat.get_max_message_id'), (session_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row and row[0] else None


def get_user_message_count_since_marker(session_id: int, persona_id: str = 'default') -> int:
    """
    Zählt die User-Nachrichten seit dem letzten Memory-Marker.
    Wenn kein Marker gesetzt ist, werden alle User-Nachrichten gezählt.
    
    Args:
        session_id: ID der Session
        persona_id: ID der Persona
        
    Returns:
        Anzahl der User-Nachrichten seit Marker
    """
    conn = get_db_connection(persona_id)
    cursor = conn.cursor()
    
    # Hole Marker
    cursor.execute(sql('chat.get_session_memory_marker'), (session_id,))
    marker_row = cursor.fetchone()
    marker = marker_row[0] if marker_row and marker_row[0] else None
    
    if marker:
        cursor.execute(sql('chat.count_user_messages_since_marker'), (session_id, marker))
    else:
        cursor.execute(sql('chat.count_all_user_messages'), (session_id,))
    
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_messages_since_marker(session_id: int, persona_id: str = 'default', limit: int = 100) -> Dict[str, Any]:
    """
    Holt nur die Nachrichten NACH dem letzten Memory-Marker.
    Wenn kein Marker gesetzt ist, werden alle Nachrichten zurückgegeben.
    Begrenzt auf max `limit` Nachrichten (Standard: 100).
    
    Args:
        session_id: ID der Session
        persona_id: ID der Persona
        limit: Maximale Anzahl Nachrichten (Standard: 100)
        
    Returns:
        Dict mit 'messages' (Liste), 'total' (Gesamtzahl seit Marker), 'truncated' (bool)
    """
    conn = get_db_connection(persona_id)
    cursor = conn.cursor()
    
    # Hole Marker
    cursor.execute(sql('chat.get_session_memory_marker'), (session_id,))
    marker_row = cursor.fetchone()
    marker = marker_row[0] if marker_row and marker_row[0] else None
    
    # Zähle Gesamtzahl seit Marker
    if marker:
        cursor.execute(sql('chat.get_messages_since_marker_count'), (session_id, marker))
    else:
        cursor.execute(sql('chat.get_all_messages_count'), (session_id,))
    total = cursor.fetchone()[0]
    truncated = total > limit
    
    # Hole die letzten `limit` Nachrichten seit Marker (die neuesten, damit nichts Wichtiges fehlt)
    if marker:
        cursor.execute(sql('chat.get_messages_since_marker'), (session_id, marker, limit))
    else:
        cursor.execute(sql('chat.get_all_messages_limited'), (session_id, limit))
    
    # Umkehren für chronologische Reihenfolge
    messages = []
    for row in reversed(cursor.fetchall()):
        messages.append({
            'id': row[0],
            'message': row[1],
            'is_user': bool(row[2]),
            'timestamp': row[3],
            'character_name': row[4]
        })
    
    conn.close()
    return {'messages': messages, 'total': total, 'truncated': truncated}
