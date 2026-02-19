"""
Memory Management

Handles:
- Saving/updating/deleting memories
- Memory markers and ranges
- Active memory retrieval
"""

from typing import List, Dict, Any, Optional
from ..logger import log
from .connection import get_db_connection
from ..sql_loader import sql


def save_memory(session_id: int, content: str, persona_id: str = 'default',
                start_message_id: int = None, end_message_id: int = None) -> int:
    """
    Saves a memory summary.
    
    Args:
        session_id: Session ID (can be None)
        content: Summary content
        persona_id: Persona ID (determines which DB to use)
        start_message_id: First message ID that this memory covers
        end_message_id: Last message ID that this memory covers
        
    Returns:
        ID of saved memory
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
    Gets all memories for a persona.
    
    Args:
        active_only: Only return active memories
        persona_id: Persona ID (determines which DB to query)
        
    Returns:
        List of memory dictionaries, sorted by date (newest first)
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
    Gets all active memories for use in chat.
    
    Args:
        persona_id: Persona ID
        
    Returns:
        List of active memory dictionaries
    """
    return get_all_memories(active_only=True, persona_id=persona_id)


def update_memory(memory_id: int, content: str, persona_id: str = 'default') -> bool:
    """
    Updates a memory's content.
    
    Args:
        memory_id: Memory ID
        content: New content
        persona_id: Persona ID
        
    Returns:
        True on success, False on error
    """
    try:
        conn = get_db_connection(persona_id)
        cursor = conn.cursor()
        
        cursor.execute(sql('memories.update_memory_content'), (content, memory_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        log.error("Error updating memory: %s", e)
        return False


def delete_memory(memory_id: int, persona_id: str = 'default') -> bool:
    """
    Deletes a memory and updates the memory marker of the associated session.
    
    Args:
        memory_id: Memory ID
        persona_id: Persona ID
        
    Returns:
        True on success, False on error
    """
    try:
        conn = get_db_connection(persona_id)
        cursor = conn.cursor()
        
        # Get session_id of the memory before deleting
        cursor.execute(sql('memories.get_memory_session_id'), (memory_id,))
        row = cursor.fetchone()
        session_id = row[0] if row else None
        
        # Delete memory
        cursor.execute(sql('memories.delete_memory'), (memory_id,))
        
        # Recalculate session memory marker based on remaining memories
        if session_id is not None:
            cursor.execute(sql('memories.get_max_end_message_id'), (session_id,))
            max_row = cursor.fetchone()
            new_marker = max_row[0] if max_row and max_row[0] else None
            
            cursor.execute(sql('memories.update_session_memory_marker'), (new_marker, session_id))
            log.info("Memory marker recalculated after deletion: session=%s, new_marker=%s", session_id, new_marker)
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        log.error("Error deleting memory: %s", e)
        return False


def toggle_memory_status(memory_id: int, persona_id: str = 'default') -> bool:
    """
    Toggles a memory's active status.
    
    Args:
        memory_id: Memory ID
        persona_id: Persona ID
        
    Returns:
        True on success, False on error
    """
    try:
        conn = get_db_connection(persona_id)
        cursor = conn.cursor()
        
        cursor.execute(sql('memories.toggle_memory_status'), (memory_id,))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        log.error("Error toggling memory status: %s", e)
        return False


def set_last_memory_message_id(session_id: int, message_id: int, persona_id: str = 'default') -> bool:
    """
    Sets the memory marker for a session (last message ID up to which
    a memory was created).
    
    Args:
        session_id: Session ID
        message_id: ID of last captured message
        persona_id: Persona ID
        
    Returns:
        True on success
    """
    try:
        conn = get_db_connection(persona_id)
        cursor = conn.cursor()
        cursor.execute(sql('memories.set_last_memory_message_id'), (message_id, session_id))
        conn.commit()
        conn.close()
        log.info("Memory marker set: session=%s, last_msg_id=%s", session_id, message_id)
        return True
    except Exception as e:
        log.error("Error setting memory marker: %s", e)
        return False


def get_last_memory_message_id(session_id: int, persona_id: str = 'default') -> Optional[int]:
    """
    Gets the memory marker for a session.
    
    Args:
        session_id: Session ID
        persona_id: Persona ID
        
    Returns:
        Last captured message ID or None
    """
    conn = get_db_connection(persona_id)
    cursor = conn.cursor()
    cursor.execute(sql('memories.get_last_memory_message_id'), (session_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row and row[0] else None