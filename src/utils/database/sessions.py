"""
Session-Management Operationen

CRUD für Chat-Sessions, Aggregation über Persona-DBs.
"""

from typing import List, Dict, Any

from ..logger import log
from ..sql_loader import sql
from .connection import get_db_connection
from .schema import get_all_persona_ids


def create_session(title: str = "Neue Konversation", persona_id: str = "default") -> int:
    """
    Erstellt eine neue Chat-Session
    
    Args:
        title: Titel der Session
        persona_id: ID der Persona für diese Session
        
    Returns:
        ID der neuen Session
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
    Holt alle Chat-Sessions, optional gefiltert nach Persona.
    Wenn persona_id=None, werden Sessions aus ALLEN Persona-DBs aggregiert.
    
    Args:
        persona_id: Wenn angegeben, nur Sessions dieser Persona
        
    Returns:
        Liste von Session-Dictionaries, sortiert nach updated_at (neueste zuerst)
    """
    if persona_id is not None:
        return _get_sessions_from_db(persona_id)
    
    # Alle Persona-DBs aggregieren
    all_sessions = []
    for pid in get_all_persona_ids():
        sessions = _get_sessions_from_db(pid)
        all_sessions.extend(sessions)
    
    # Nach updated_at sortieren (neueste zuerst)
    all_sessions.sort(key=lambda s: s.get('updated_at', ''), reverse=True)
    return all_sessions


def _get_sessions_from_db(persona_id: str) -> List[Dict[str, Any]]:
    """Holt alle Sessions aus einer bestimmten Persona-DB"""
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
        log.error("Fehler beim Laden der Sessions für Persona %s: %s", persona_id, e)
        return []


def get_persona_session_summary() -> List[Dict[str, Any]]:
    """
    Gibt eine Zusammenfassung der Sessions pro Persona zurück
    (aggregiert über alle Persona-DBs)
    
    Returns:
        Liste von Dictionaries mit persona_id, session_count, last_updated
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
    
    # Nach last_updated sortieren
    summary.sort(key=lambda s: s.get('last_updated', '') or '', reverse=True)
    return summary


def get_session_persona_id(session_id: int, persona_id: str = 'default') -> str:
    """
    Gibt die persona_id einer Session zurück.
    
    Args:
        session_id: ID der Session
        persona_id: ID der Persona (bestimmt welche DB abgefragt wird)
        
    Returns:
        persona_id als String oder 'default'
    """
    conn = get_db_connection(persona_id)
    cursor = conn.cursor()
    
    cursor.execute(sql('sessions.get_session_persona_id'), (session_id,))
    row = cursor.fetchone()
    conn.close()
    
    return row[0] if row and row[0] else persona_id


def get_session(session_id: int, persona_id: str = 'default') -> Dict[str, Any]:
    """
    Holt eine spezifische Session
    
    Args:
        session_id: ID der Session
        persona_id: ID der Persona
        
    Returns:
        Session-Dictionary oder None
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
    Aktualisiert den Titel einer Session
    
    Args:
        session_id: ID der Session
        title: Neuer Titel
        persona_id: ID der Persona
        
    Returns:
        True bei Erfolg, False bei Fehler
    """
    try:
        conn = get_db_connection(persona_id)
        cursor = conn.cursor()
        
        cursor.execute(sql('sessions.update_session_title'), (title, session_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        log.error("Fehler beim Aktualisieren des Session-Titels: %s", e)
        return False


def delete_session(session_id: int, persona_id: str = 'default') -> bool:
    """
    Löscht eine Session und alle zugehörigen Nachrichten
    
    Args:
        session_id: ID der Session
        persona_id: ID der Persona
        
    Returns:
        True bei Erfolg, False bei Fehler
    """
    try:
        conn = get_db_connection(persona_id)
        cursor = conn.cursor()
        
        # Nachrichten werden automatisch gelöscht (CASCADE)
        cursor.execute(sql('sessions.delete_session'), (session_id,))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        log.error("Fehler beim Löschen der Session: %s", e)
        return False


def get_current_session_id(persona_id: str = 'default') -> int:
    """
    Holt die ID der aktuellen (neuesten) Session einer Persona
    
    Args:
        persona_id: ID der Persona
        
    Returns:
        Session-ID oder None wenn keine Session existiert
    """
    conn = get_db_connection(persona_id)
    cursor = conn.cursor()
    
    cursor.execute(sql('sessions.get_current_session_id'))
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result else None
