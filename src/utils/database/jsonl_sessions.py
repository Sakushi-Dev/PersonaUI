"""
Session Management (JSONL Implementation)

Parallel implementation of sessions.py using JSONL storage.
Handles:
- Creating/updating/deleting sessions
- Session queries and summaries
- Multi-persona session aggregation

IMPORTANT: This module exists PARALLEL to sessions.py.
It does NOT replace the SQLite implementation yet (that comes in Phase 2d).
"""

import os
from datetime import datetime
from typing import List, Dict, Any, Optional

from . import jsonl_store
from .connection import DATA_DIR
from ..logger import log


# ---------------------------------------------------------------------------
# Helper Functions (Private)
# ---------------------------------------------------------------------------

def _sessions_path(persona_id: str) -> str:
    """
    Returns the sessions.jsonl file path for a persona.
    
    Args:
        persona_id: Persona ID
        
    Returns:
        Path to sessions.jsonl file
    """
    return os.path.join(DATA_DIR, persona_id, "sessions", "sessions.jsonl")


def _messages_path(persona_id: str, session_id: int) -> str:
    """
    Returns the messages file path for a session.
    
    Args:
        persona_id: Persona ID
        session_id: Session ID
        
    Returns:
        Path to messages_{session_id}.jsonl file
    """
    return os.path.join(DATA_DIR, persona_id, "messages", f"messages_{session_id}.jsonl")


def _get_all_persona_ids() -> List[str]:
    """
    Scans DATA_DIR for persona subdirectories that contain sessions.jsonl.
    
    Returns:
        List of persona IDs with existing session files
    """
    persona_ids = []
    
    if not os.path.exists(DATA_DIR):
        return persona_ids
    
    try:
        for entry in os.listdir(DATA_DIR):
            entry_path = os.path.join(DATA_DIR, entry)
            
            # Only directories
            if not os.path.isdir(entry_path):
                continue
            
            # Only directories that contain sessions/sessions.jsonl
            sessions_file = os.path.join(entry_path, "sessions", "sessions.jsonl")
            if os.path.exists(sessions_file):
                persona_ids.append(entry)
    
    except OSError as e:
        log.warning("Error scanning persona directories: %s", e)
    
    return persona_ids


# ---------------------------------------------------------------------------
# Public API - 8 Functions (Identical signatures to sessions.py)
# ---------------------------------------------------------------------------

def create_session(title: str = "Neue Konversation", persona_id: str = "default") -> int:
    """
    Creates a new chat session.
    
    Args:
        title: Session title
        persona_id: Persona ID for this session
        
    Returns:
        ID of new session
    """
    path = _sessions_path(persona_id)
    session_id = jsonl_store.next_id(path)
    now = datetime.now().isoformat()
    
    record = {
        'id': session_id,
        'title': title,
        'persona_id': persona_id,
        'created_at': now,
        'updated_at': now
    }
    
    jsonl_store.append(path, record)
    return session_id


def get_all_sessions(persona_id: str = None) -> List[Dict[str, Any]]:
    """
    Gets all chat sessions, optionally filtered by persona.
    If persona_id=None, aggregates sessions from ALL persona directories.
    
    Args:
        persona_id: If given, only sessions from this persona
        
    Returns:
        List of session dictionaries, sorted by updated_at (newest first)
    """
    if persona_id is not None:
        # Query single persona directory
        sessions = jsonl_store.read_all(_sessions_path(persona_id))
        sessions.sort(key=lambda s: s.get('updated_at', ''), reverse=True)
        return sessions
    
    # Aggregate all persona directories
    all_sessions = []
    for pid in _get_all_persona_ids():
        sessions = jsonl_store.read_all(_sessions_path(pid))
        all_sessions.extend(sessions)
    
    # Sort by updated_at (newest first)
    all_sessions.sort(key=lambda s: s.get('updated_at', ''), reverse=True)
    return all_sessions


def get_persona_session_summary() -> List[Dict[str, Any]]:
    """
    Returns a summary of sessions per persona.
    (aggregated across all persona directories)
    
    Returns:
        List of dictionaries with persona_id, session_count, last_updated
    """
    summary = []
    
    for pid in _get_all_persona_ids():
        sessions = jsonl_store.read_all(_sessions_path(pid))
        session_count = len(sessions)
        
        if session_count > 0:
            # Find the latest updated_at timestamp
            last_updated = max(session.get('updated_at', '') for session in sessions)
            
            summary.append({
                'persona_id': pid,
                'session_count': session_count,
                'last_updated': last_updated
            })
    
    # Sort by last_updated (newest first)
    summary.sort(key=lambda s: s.get('last_updated', ''), reverse=True)
    return summary


def get_session_persona_id(session_id: int, persona_id: str = 'default') -> str:
    """
    Returns the persona_id of a session.
    
    Args:
        session_id: Session ID
        persona_id: Persona ID (determines which directory to query)
        
    Returns:
        persona_id as string or fallback to provided persona_id
    """
    session = get_session(session_id, persona_id)
    if session:
        return session.get('persona_id', persona_id)
    return persona_id


def get_session(session_id: int, persona_id: str = 'default') -> Optional[Dict[str, Any]]:
    """
    Gets a specific session.
    
    Args:
        session_id: Session ID
        persona_id: Persona ID
        
    Returns:
        Session dictionary or None
    """
    sessions = jsonl_store.read_filtered(
        _sessions_path(persona_id), 
        lambda s: s.get('id') == session_id
    )
    
    if sessions:
        return sessions[0]
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
        path = _sessions_path(persona_id)
        sessions = jsonl_store.read_all(path)
        found = False
        
        for session in sessions:
            if session.get('id') == session_id:
                session['title'] = title
                session['updated_at'] = datetime.now().isoformat()
                found = True
                break
        
        if not found:
            return False
        
        jsonl_store.rewrite(path, sessions)
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
        path = _sessions_path(persona_id)
        sessions = jsonl_store.read_all(path)
        
        # Filter out the session to delete
        sessions = [s for s in sessions if s.get('id') != session_id]
        
        # Rewrite sessions file
        jsonl_store.rewrite(path, sessions)
        
        # Delete associated messages file
        messages_file = _messages_path(persona_id, session_id)
        jsonl_store.delete_file(messages_file)
        
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
    sessions = jsonl_store.read_all(_sessions_path(persona_id))
    
    if not sessions:
        return None
    
    # Sort by updated_at (newest first)
    sessions.sort(key=lambda s: s.get('updated_at', ''), reverse=True)
    return sessions[0]['id']
