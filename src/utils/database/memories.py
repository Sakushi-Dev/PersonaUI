"""
Memory-Management Operationen

CRUD für Erinnerungen, Memory-Marker Verwaltung.
"""

from typing import List, Dict, Any, Optional

from ..logger import log
from ..sql_loader import sql
from .connection import get_db_connection
from .chat import get_message_count


def save_memory(session_id: int, content: str, persona_id: str = 'default',
                start_message_id: int = None, end_message_id: int = None) -> int:
    """
    Speichert eine Memory-Zusammenfassung
    
    Args:
        session_id: ID der Session (kann None sein)
        content: Inhalt der Zusammenfassung
        persona_id: ID der Persona (bestimmt welche DB verwendet wird)
        start_message_id: Erste Nachrichten-ID die diese Memory abdeckt
        end_message_id: Letzte Nachrichten-ID die diese Memory abdeckt
        
    Returns:
        ID der gespeicherten Memory
    """
    conn = get_db_connection(persona_id)
    cursor = conn.cursor()
    
    cursor.execute(sql('memories.insert_memory'),
                   (session_id, persona_id, content, start_message_id, end_message_id))
    
    memory_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return memory_id


def get_all_memories(active_only: bool = False, persona_id: str = None) -> List[Dict[str, Any]]:
    """
    Holt alle Memories einer Persona
    
    Args:
        active_only: Nur aktive Memories zurückgeben
        persona_id: Persona-ID (bestimmt welche DB abgefragt wird)
        
    Returns:
        Liste von Memory-Dictionaries, sortiert nach Datum (neueste zuerst)
    """
    if persona_id is None:
        persona_id = 'default'
    
    conn = get_db_connection(persona_id)
    cursor = conn.cursor()
    
    if active_only:
        cursor.execute(sql('memories.get_active_memories'))
    else:
        cursor.execute(sql('memories.get_all_memories'))
    
    memories = []
    for row in cursor.fetchall():
        memories.append({
            'id': row[0],
            'session_id': row[1],
            'persona_id': row[2],
            'content': row[3],
            'created_at': row[4],
            'is_active': bool(row[5])
        })
    
    conn.close()
    return memories


def get_active_memories(persona_id: str = None) -> List[Dict[str, Any]]:
    """
    Holt alle aktiven Memories für die Verwendung im Chat
    
    Args:
        persona_id: Persona-ID
        
    Returns:
        Liste von aktiven Memory-Dictionaries
    """
    return get_all_memories(active_only=True, persona_id=persona_id)


def update_memory(memory_id: int, content: str, persona_id: str = 'default') -> bool:
    """
    Aktualisiert den Inhalt einer Memory
    
    Args:
        memory_id: ID der Memory
        content: Neuer Inhalt
        persona_id: ID der Persona
        
    Returns:
        True bei Erfolg, False bei Fehler
    """
    try:
        conn = get_db_connection(persona_id)
        cursor = conn.cursor()
        
        cursor.execute(sql('memories.update_memory_content'), (content, memory_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        log.error("Fehler beim Aktualisieren der Memory: %s", e)
        return False


def delete_memory(memory_id: int, persona_id: str = 'default') -> bool:
    """
    Löscht eine Memory und aktualisiert den Memory-Marker der zugehörigen Session.
    
    Args:
        memory_id: ID der Memory
        persona_id: ID der Persona
        
    Returns:
        True bei Erfolg, False bei Fehler
    """
    try:
        conn = get_db_connection(persona_id)
        cursor = conn.cursor()
        
        # Hole session_id der Memory bevor wir löschen
        cursor.execute(sql('memories.get_memory_session_id'), (memory_id,))
        row = cursor.fetchone()
        session_id = row[0] if row else None
        
        # Memory löschen
        cursor.execute(sql('memories.delete_memory'), (memory_id,))
        
        # Memory-Marker der Session neu berechnen basierend auf verbleibenden Memories
        if session_id is not None:
            cursor.execute(sql('memories.get_max_end_message_id'), (session_id,))
            max_row = cursor.fetchone()
            new_marker = max_row[0] if max_row and max_row[0] else None
            
            cursor.execute(sql('memories.update_session_memory_marker'), (new_marker, session_id))
            log.info("Memory-Marker nach Löschen neu berechnet: session=%s, new_marker=%s", session_id, new_marker)
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        log.error("Fehler beim Löschen der Memory: %s", e)
        return False


def toggle_memory_status(memory_id: int, persona_id: str = 'default') -> bool:
    """
    Schaltet den Aktiv-Status einer Memory um
    
    Args:
        memory_id: ID der Memory
        persona_id: ID der Persona
        
    Returns:
        True bei Erfolg, False bei Fehler
    """
    try:
        conn = get_db_connection(persona_id)
        cursor = conn.cursor()
        
        cursor.execute(sql('memories.toggle_memory_status'), (memory_id,))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        log.error("Fehler beim Umschalten des Memory-Status: %s", e)
        return False


def get_session_message_count(session_id: int = None, persona_id: str = 'default') -> int:
    """
    Gibt die Anzahl der Nachrichten in einer Session zurück
    
    Args:
        session_id: ID der Session (wenn None, wird die neueste Session verwendet)
        persona_id: ID der Persona
        
    Returns:
        Anzahl der Nachrichten
    """
    return get_message_count(session_id=session_id, persona_id=persona_id)


def set_last_memory_message_id(session_id: int, message_id: int, persona_id: str = 'default') -> bool:
    """
    Setzt den Memory-Marker für eine Session (letzte Nachrichten-ID, bis zu der
    eine Erinnerung erstellt wurde).
    
    Args:
        session_id: ID der Session
        message_id: ID der letzten erfassten Nachricht
        persona_id: ID der Persona
        
    Returns:
        True bei Erfolg
    """
    try:
        conn = get_db_connection(persona_id)
        cursor = conn.cursor()
        cursor.execute(sql('memories.set_last_memory_message_id'), (message_id, session_id))
        conn.commit()
        conn.close()
        log.info("Memory-Marker gesetzt: session=%s, last_msg_id=%s", session_id, message_id)
        return True
    except Exception as e:
        log.error("Fehler beim Setzen des Memory-Markers: %s", e)
        return False


def get_last_memory_message_id(session_id: int, persona_id: str = 'default') -> Optional[int]:
    """
    Holt den Memory-Marker für eine Session.
    
    Args:
        session_id: ID der Session
        persona_id: ID der Persona
        
    Returns:
        Letzte erfasste Nachrichten-ID oder None
    """
    conn = get_db_connection(persona_id)
    cursor = conn.cursor()
    cursor.execute(sql('memories.get_last_memory_message_id'), (session_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row and row[0] else None
