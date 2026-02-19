"""
Session Management

Handles:
- Creating/updating/deleting sessions
- Session queries and summaries
- Multi-persona session aggregation
"""

from typing import List, Dict, Any, Optional
from ..logger import log
from .connection import get_db_connection, get_all_persona_ids
from ..sql_loader import sql


def create_session(title: str = "Neue Konversation", persona_id: str = "default") -> int:
    """
    Creates a new chat session.
    
    Args:
        title: Session title
        persona_id: Persona ID for this session
        
    Returns:
        ID of new session
    """
    conn = get_db_connection(persona_id)
    cursor = conn.cursor()
    
    cursor.execute(sql('sessions.create_session'), (title, persona_id))
    
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return session_id


def get_all_sessions(persona_id: str = None) -> List[Dict[str, Any]]:
    """
    Gets all chat sessions, optionally filtered by persona.
    If persona_id=None, aggregates sessions from ALL persona DBs.
    
    Args:
        persona_id: If given, only sessions from this persona
        
    Returns:
        List of session dictionaries, sorted by updated_at (newest first)
    """
    if persona_id is not None:
        # Query single persona DB
        return _get_sessions_from_db(persona_id)
    
    # Aggregate all persona DBs
    all_sessions = []
    for pid in get_all_persona_ids():
        sessions = _get_sessions_from_db(pid)
        all_sessions.extend(sessions)
    
    # Sort by updated_at (newest first)
    all_sessions.sort(key=lambda s: s.get('updated_at', ''), reverse=True)
    return all_sessions


def _get_sessions_from_db(persona_id: str) -> List[Dict[str, Any]]:
    """Gets all sessions from a specific persona DB."""
    try:
        conn = get_db_connection(persona_id)
        cursor = conn.cursor()
        
        cursor.execute(sql('sessions.get_all_sessions'))
        
        sessions = []
        for row in cursor.fetchall():
            sessions.append({
                'id': row[0],
                'title': row[1],
                'created_at': row[2],
                'updated_at': row[3],
                'persona_id': row[4] if row[4] else persona_id
            })
        
        conn.close()
        return sessions
    except Exception as e:
        log.error("Error loading sessions for persona %s: %s", persona_id, e)
        return []


def get_persona_session_summary() -> List[Dict[str, Any]]:
    """
    Returns a summary of sessions per persona.
    (aggregated across all persona DBs)
    
    Returns:
        List of dictionaries with persona_id, session_count, last_updated
    """
    summary = []
    
    for pid in get_all_persona_ids():
        try:
            conn = get_db_connection(pid)
            cursor = conn.cursor()
            
            cursor.execute(sql('sessions.get_session_count_summary'))
            
            row = cursor.fetchone()
            conn.close()
            
            if row and row[0] > 0:
                summary.append({
                    'persona_id': pid,
                    'session_count': row[0],
                    'last_updated': row[1]
                })
        except Exception:
            continue
    
    # Sort by last_updated
    summary.sort(key=lambda s: s.get('last_updated', '') or '', reverse=True)
    return summary


def get_session_persona_id(session_id: int, persona_id: str = 'default') -> str:
    """
    Returns the persona_id of a session.
    
    Args:
        session_id: Session ID
        persona_id: Persona ID (determines which DB to query)
        
    Returns:
        persona_id as string or 'default'
    """
    conn = get_db_connection(persona_id)
    cursor = conn.cursor()
    
    cursor.execute(sql('sessions.get_session_persona_id'), (session_id,))
    row = cursor.fetchone()
    conn.close()
    
    return row[0] if row and row[0] else persona_id


def get_session(session_id: int, persona_id: str = 'default') -> Optional[Dict[str, Any]]:
    """
    Gets a specific session.
    
    Args:
        session_id: Session ID
        persona_id: Persona ID
        
    Returns:
        Session dictionary or None
    """
    conn = get_db_connection(persona_id)
    cursor = conn.cursor()
    
    cursor.execute(sql('sessions.get_session_by_id'), (session_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            'id': row[0],
            'title': row[1],
            'created_at': row[2],
            'updated_at': row[3],
            'persona_id': row[4] if row[4] else persona_id
        }
    return None


def update_session_title(session_id: int, title: str, persona_id: str = 'default') -> bool:
    """
    Updates a session's title.
    
    Args:
        session_id: Session ID
        title: New title
        persona_id: Persona ID
        
    Returns:
        True on success, False on error
    """
    try:
        conn = get_db_connection(persona_id)
        cursor = conn.cursor()
        
        cursor.execute(sql('sessions.update_session_title'), (title, session_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        log.error("Error updating session title: %s", e)
        return False


def delete_session(session_id: int, persona_id: str = 'default') -> bool:
    """
    Deletes a session and all associated messages.
    
    Args:
        session_id: Session ID
        persona_id: Persona ID
        
    Returns:
        True on success, False on error
    """
    try:
        conn = get_db_connection(persona_id)
        cursor = conn.cursor()
        
        # Messages are automatically deleted (CASCADE)
        cursor.execute(sql('sessions.delete_session'), (session_id,))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        log.error("Error deleting session: %s", e)
        return False


def get_current_session_id(persona_id: str = 'default') -> Optional[int]:
    """
    Gets the ID of the current (newest) session for a persona.
    
    Args:
        persona_id: Persona ID
        
    Returns:
        Session ID or None if no session exists
    """
    conn = get_db_connection(persona_id)
    cursor = conn.cursor()
    
    cursor.execute(sql('sessions.get_current_session_id'))
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result else None