"""
Chat Messages & History Management

Handles:
- Saving and retrieving messages
- Chat history with pagination
- Conversation context for API
- Message counting and statistics
"""

from typing import List, Dict, Any, Optional
from ..logger import log
from .connection import get_db_connection
from ..sql_loader import sql


def get_chat_history(limit: int = 30, session_id: int = None, offset: int = 0,
                     persona_id: str = 'default') -> List[Dict[str, Any]]:
    """
    Retrieves chat history from the database.
    
    Args:
        limit: Maximum number of messages to return (default: 30)
        session_id: Session ID (if None, uses latest session)
        offset: Number of messages to skip (for pagination)
        persona_id: Persona ID (determines which DB to use)
        
    Returns:
        List of message dictionaries (newest first, then reversed)
    """
    conn = get_db_connection(persona_id)
    cursor = conn.cursor()
    
    # If no session_id given, get the latest session
    if session_id is None:
        cursor.execute(sql('chat.get_latest_session_id'))
        result = cursor.fetchone()
        if result:
            session_id = result[0]
        else:
            conn.close()
            return []
    
    # Get memory ranges for this session (only ACTIVE memories with ranges)
    cursor.execute(sql('chat.get_memory_ranges'), (session_id,))
    memory_ranges = cursor.fetchall()
    
    # Fallback: If no ranges available, use old marker
    cursor.execute(sql('chat.get_session_memory_marker'), (session_id,))
    marker_row = cursor.fetchone()
    last_memory_message_id = marker_row[0] if marker_row and marker_row[0] else None
    
    # Helper function: Check if a message ID is in any memory range
    def is_memorized(msg_id):
        if memory_ranges:
            for start_id, end_id in memory_ranges:
                if start_id <= msg_id <= end_id:
                    return True
            return False
        # Fallback for old memories without ranges
        return last_memory_message_id is not None and msg_id <= last_memory_message_id
    
    cursor.execute(sql('chat.get_chat_history'), (session_id, limit, offset))
    
    # Reverse so oldest of the loaded messages comes first
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
    Gets the total number of messages for a session.
    
    Args:
        session_id: Session ID (if None, uses latest session)
        persona_id: Persona ID
        
    Returns:
        Number of messages
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
    Gets the last N messages for Claude API context.
    
    Args:
        limit: Number of recent messages
        session_id: Session ID (if None, uses latest session)
        persona_id: Persona ID
        
    Returns:
        List of messages in Claude API format
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
        # Merge consecutive same roles (e.g. through Afterthought)
        # Claude API requires alternating user/assistant roles
        if messages and messages[-1]['role'] == role:
            messages[-1]['content'] += "\n\n" + row[0]
            merged_count += 1
        else:
            messages.append({
                'role': role,
                'content': row[0]
            })
    
    # Leading assistant messages (e.g. Greeting) are NOT removed,
    # so the AI knows it has already greeted.
    # Claude API accepts messages that start with assistant,
    # when the system parameter is passed separately.

    if merged_count > 0:
        log.info("Context-History: %d messages merged. Final: %d msgs",
                 merged_count, len(messages))
    else:
        log.debug("Context-History: Final %d msgs", len(messages))
    
    conn.close()
    return messages


def save_message(message: str, is_user: bool, character_name: str = 'Assistant',
                 session_id: int = None, persona_id: str = 'default') -> int:
    """
    Saves a message to the database.
    
    Args:
        message: Message text
        is_user: True if message from user, False if from bot
        character_name: Character name
        session_id: Session ID (if None, uses latest session)
        persona_id: Persona ID
        
    Returns:
        ID of inserted message
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
    """Deletes all chat history for a persona."""
    conn = get_db_connection(persona_id)
    cursor = conn.cursor()
    cursor.execute(sql('chat.delete_all_messages'))
    cursor.execute(sql('chat.delete_all_sessions'))
    conn.commit()
    conn.close()


def get_total_message_count(persona_id: str = 'default') -> int:
    """Returns total number of all messages (across all sessions of a persona)."""
    conn = get_db_connection(persona_id)
    cursor = conn.cursor()
    cursor.execute(sql('chat.get_total_message_count'))
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_max_message_id(session_id: int, persona_id: str = 'default') -> Optional[int]:
    """
    Gets the highest message ID of a session.
    
    Args:
        session_id: Session ID
        persona_id: Persona ID
        
    Returns:
        Highest message ID or None
    """
    conn = get_db_connection(persona_id)
    cursor = conn.cursor()
    cursor.execute(sql('chat.get_max_message_id'), (session_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row and row[0] else None


def get_user_message_count_since_marker(session_id: int, persona_id: str = 'default') -> int:
    """
    Counts user messages since the last memory marker.
    If no marker is set, counts all user messages.
    
    Args:
        session_id: Session ID
        persona_id: Persona ID
        
    Returns:
        Number of user messages since marker
    """
    conn = get_db_connection(persona_id)
    cursor = conn.cursor()
    
    # Get marker
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
    Gets only messages AFTER the last memory marker.
    If no marker is set, returns all messages.
    Limited to max `limit` messages (default: 100).
    
    Args:
        session_id: Session ID
        persona_id: Persona ID
        limit: Maximum number of messages (default: 100)
        
    Returns:
        Dict with 'messages' (list), 'total' (total count since marker), 'truncated' (bool)
    """
    conn = get_db_connection(persona_id)
    cursor = conn.cursor()
    
    # Get marker
    cursor.execute(sql('chat.get_session_memory_marker'), (session_id,))
    marker_row = cursor.fetchone()
    marker = marker_row[0] if marker_row and marker_row[0] else None
    
    # Count total since marker
    if marker:
        cursor.execute(sql('chat.get_messages_since_marker_count'), (session_id, marker))
    else:
        cursor.execute(sql('chat.get_all_messages_count'), (session_id,))
    total = cursor.fetchone()[0]
    truncated = total > limit
    
    # Get the last `limit` messages since marker (newest ones, so nothing important is missing)
    if marker:
        cursor.execute(sql('chat.get_messages_since_marker'), (session_id, marker, limit))
    else:
        cursor.execute(sql('chat.get_all_messages_limited'), (session_id, limit))
    
    # Reverse for chronological order
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