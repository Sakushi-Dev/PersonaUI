"""
Chat Messages & History Management (JSONL Implementation)

Parallel implementation of chat.py using JSONL storage.
Handles:
- Saving and retrieving messages
- Chat history with pagination
- Conversation context for API
- Message counting and statistics

IMPORTANT: This module exists PARALLEL to chat.py.
It does NOT replace the SQLite implementation yet (that comes in Phase 2d).
"""

import os
import glob
from datetime import datetime
from typing import List, Dict, Any, Optional

from . import jsonl_store, jsonl_sessions
from .connection import DATA_DIR
from ..logger import log


# ---------------------------------------------------------------------------
# Helper Functions (Private)
# ---------------------------------------------------------------------------

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


def _sessions_path(persona_id: str) -> str:
    """
    Returns the sessions.jsonl file path for a persona.
    
    Args:
        persona_id: Persona ID
        
    Returns:
        Path to sessions.jsonl file
    """
    return os.path.join(DATA_DIR, persona_id, "sessions", "sessions.jsonl")


def _resolve_session_id(session_id: Optional[int], persona_id: str) -> Optional[int]:
    """
    Resolves session_id when None is passed.
    
    Args:
        session_id: Session ID or None
        persona_id: Persona ID
        
    Returns:
        Resolved session ID or None if no sessions exist
    """
    if session_id is not None:
        return session_id
    
    return jsonl_sessions.get_current_session_id(persona_id)


# ---------------------------------------------------------------------------
# Public API - 8 Functions (Identical signatures to chat.py)
# ---------------------------------------------------------------------------

def get_chat_history(limit: int = 30, session_id: int = None, offset: int = 0,
                     persona_id: str = 'default') -> List[Dict[str, Any]]:
    """
    Retrieves chat history from JSONL files.
    
    Args:
        limit: Maximum number of messages to return (default: 30)
        session_id: Session ID (if None, uses latest session)
        offset: Number of messages to skip (for pagination)
        persona_id: Persona ID (determines which directory to use)
        
    Returns:
        List of message dictionaries (oldest first, like original)
    """
    resolved_session_id = _resolve_session_id(session_id, persona_id)
    
    if resolved_session_id is None:
        return []
    
    path = _messages_path(persona_id, resolved_session_id)
    
    try:
        # Read newest first (reverse=True), then reverse to get oldest first
        records = jsonl_store.read_paginated(path, limit=limit, offset=offset, reverse=True)
        records.reverse()  # Now oldest of the loaded messages comes first
        
        # Convert to expected format
        messages = []
        for record in records:
            msg = {
                'id': record.get('id'),
                'message': record.get('message'),
                'is_user': bool(record.get('is_user', False)),
                'timestamp': record.get('timestamp'),
                'character_name': record.get('character_name', 'Assistant')
            }
            messages.append(msg)
        
        return messages
        
    except Exception as e:
        log.warning("Error reading chat history for session %s: %s", resolved_session_id, e)
        return []


def get_message_count(session_id: int = None, persona_id: str = 'default') -> int:
    """
    Gets the total number of messages for a session.
    
    Args:
        session_id: Session ID (if None, uses latest session)
        persona_id: Persona ID
        
    Returns:
        Number of messages
    """
    resolved_session_id = _resolve_session_id(session_id, persona_id)
    
    if resolved_session_id is None:
        return 0
    
    path = _messages_path(persona_id, resolved_session_id)
    
    try:
        return jsonl_store.count_lines(path)
    except Exception as e:
        log.warning("Error counting messages for session %s: %s", resolved_session_id, e)
        return 0


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
    resolved_session_id = _resolve_session_id(session_id, persona_id)
    
    if resolved_session_id is None:
        return []
    
    path = _messages_path(persona_id, resolved_session_id)
    
    try:
        # Get last N messages (chronological order)
        records = jsonl_store.read_last_n(path, n=limit)
        raw_count = len(records)
        
        log.debug("Context-History: session=%s, persona=%s, limit=%d, raw_count=%d",
                 resolved_session_id, persona_id, limit, raw_count)
        
        messages = []
        merged_count = 0
        
        for record in records:
            role = "user" if record.get('is_user', False) else "assistant"
            message_text = record.get('message', '')
            
            # Merge consecutive same roles (e.g. through Afterthought)
            # Claude API requires alternating user/assistant roles
            if messages and messages[-1]['role'] == role:
                messages[-1]['content'] += "\n\n" + message_text
                merged_count += 1
            else:
                messages.append({
                    'role': role,
                    'content': message_text
                })
        
        # Leading assistant messages (e.g. Auto First Message) are NOT removed,
        # so the AI knows it has already opened the conversation.
        # Claude API accepts messages that start with assistant,
        # when the system parameter is passed separately.

        if merged_count > 0:
            log.info("Context-History: %d messages merged. Final: %d msgs",
                     merged_count, len(messages))
        else:
            log.debug("Context-History: Final %d msgs", len(messages))
        
        return messages
        
    except Exception as e:
        log.warning("Error getting conversation context for session %s: %s", resolved_session_id, e)
        return []


def save_message(message: str, is_user: bool, character_name: str = 'Assistant',
                 session_id: int = None, persona_id: str = 'default') -> int:
    """
    Saves a message to JSONL files.
    
    Args:
        message: Message text
        is_user: True if message from user, False if from bot
        character_name: Character name
        session_id: Session ID (if None, uses latest session)
        persona_id: Persona ID
        
    Returns:
        ID of inserted message
    """
    resolved_session_id = session_id
    
    if resolved_session_id is None:
        resolved_session_id = jsonl_sessions.get_current_session_id(persona_id)
        if resolved_session_id is None:
            # Create new session if none exists
            resolved_session_id = jsonl_sessions.create_session(persona_id=persona_id)
    
    path = _messages_path(persona_id, resolved_session_id)
    
    try:
        # Generate next message ID
        msg_id = jsonl_store.next_id(path)
        
        # Create message record
        record = {
            "id": msg_id,
            "session_id": resolved_session_id,
            "message": message,
            "is_user": is_user,
            "timestamp": datetime.now().isoformat(),
            "character_name": character_name
        }
        
        # Append message
        jsonl_store.append(path, record)
        
        # Update session timestamp
        try:
            sp = _sessions_path(persona_id)
            all_sessions = jsonl_store.read_all(sp)
            for s in all_sessions:
                if s.get("id") == resolved_session_id:
                    s["updated_at"] = datetime.now().isoformat()
                    break
            jsonl_store.rewrite(sp, all_sessions)
        except Exception as e:
            log.warning("Error updating session timestamp: %s", e)
        
        return msg_id
        
    except Exception as e:
        log.error("Error saving message: %s", e)
        raise


def clear_chat_history(persona_id: str = 'default'):
    """
    Deletes all chat history for a persona.
    Removes all message files AND sessions.jsonl.
    """
    try:
        # Delete all message files
        message_pattern = os.path.join(DATA_DIR, persona_id, "messages", "messages_*.jsonl")
        for message_file in glob.glob(message_pattern):
            jsonl_store.delete_file(message_file)
        
        # Delete sessions file
        sessions_file = _sessions_path(persona_id)
        jsonl_store.delete_file(sessions_file)
        
        log.info("Cleared all chat history for persona: %s", persona_id)
        
    except Exception as e:
        log.error("Error clearing chat history: %s", e)


def get_total_message_count(persona_id: str = 'default') -> int:
    """
    Returns total number of all messages (across all sessions of a persona).
    
    Args:
        persona_id: Persona ID
        
    Returns:
        Total message count
    """
    try:
        total_count = 0
        message_pattern = os.path.join(DATA_DIR, persona_id, "messages", "messages_*.jsonl")
        
        for message_file in glob.glob(message_pattern):
            count = jsonl_store.count_lines(message_file)
            total_count += count
        
        return total_count
        
    except Exception as e:
        log.warning("Error counting total messages: %s", e)
        return 0


def get_max_message_id(session_id: int, persona_id: str = 'default') -> Optional[int]:
    """
    Gets the highest message ID of a session.
    
    Args:
        session_id: Session ID
        persona_id: Persona ID
        
    Returns:
        Highest message ID or None
    """
    path = _messages_path(persona_id, session_id)
    
    try:
        last_records = jsonl_store.read_last_n(path, n=1)
        
        if not last_records:
            return None
        
        last_record = last_records[0]
        msg_id = last_record.get('id')
        
        if msg_id is not None:
            try:
                return int(msg_id)
            except (ValueError, TypeError):
                log.warning("Invalid message ID in last record: %s", msg_id)
                return None
        
        return None
        
    except Exception as e:
        log.warning("Error getting max message ID for session %s: %s", session_id, e)
        return None


def get_last_message(session_id: int, persona_id: str = 'default') -> Optional[Dict[str, Any]]:
    """
    Gets the last message of a session.
    
    Args:
        session_id: Session ID
        persona_id: Persona ID
        
    Returns:
        Message dict or None
    """
    path = _messages_path(persona_id, session_id)
    
    try:
        last_records = jsonl_store.read_last_n(path, n=1)
        
        if not last_records:
            return None
        
        record = last_records[0]
        
        return {
            'id': record.get('id'),
            'message': record.get('message'),
            'is_user': bool(record.get('is_user', False)),
            'timestamp': record.get('timestamp'),
            'character_name': record.get('character_name', 'Assistant')
        }
        
    except Exception as e:
        log.warning("Error getting last message for session %s: %s", session_id, e)
        return None


def delete_last_message(session_id: int, persona_id: str = "default") -> Optional[Dict[str, Any]]:
    """
    Deletes the last message of a session and returns its info.
    
    Args:
        session_id: Session ID
        persona_id: Persona ID
        
    Returns:
        Deleted message dict or None if no message found
    """
    path = _messages_path(persona_id, session_id)
    
    try:
        all_messages = jsonl_store.read_all(path)
        
        if not all_messages:
            return None
        
        # Find the last message (highest ID)
        last_message = max(all_messages, key=lambda m: m.get('id', 0))
        
        # Remove it from the list
        remaining = [m for m in all_messages if m.get('id') != last_message['id']]
        
        # Write back the remaining messages
        jsonl_store.rewrite(path, remaining)
        
        log.info("Letzte Nachricht geloescht: session=%s, msg_id=%s, is_user=%s", 
                session_id, last_message.get('id'), last_message.get('is_user'))
        
        # Return in expected format
        return {
            'id': last_message.get('id'),
            'message': last_message.get('message'),
            'is_user': bool(last_message.get('is_user', False)),
            'timestamp': last_message.get('timestamp'),
            'character_name': last_message.get('character_name', 'Assistant')
        }
        
    except Exception as e:
        log.warning("Error deleting last message for session %s: %s", session_id, e)
        return None


def update_last_message_text(session_id: int, new_text: str, persona_id: str = "default") -> bool:
    """
    Updates the text of the last message in a session.
    
    Args:
        session_id: Session ID
        new_text: New message text
        persona_id: Persona ID
        
    Returns:
        True if a message was updated, False otherwise
    """
    path = _messages_path(persona_id, session_id)
    
    try:
        all_messages = jsonl_store.read_all(path)
        
        if not all_messages:
            return False
        
        # Find the last message (highest ID)
        last_message = max(all_messages, key=lambda m: m.get('id', 0))
        
        # Update the message text
        last_message['message'] = new_text
        
        # Write back all messages (last_message is part of all_messages)
        jsonl_store.rewrite(path, all_messages)
        
        log.info("Letzte Nachricht aktualisiert: session=%s", session_id)
        
        return True
        
    except Exception as e:
        log.warning("Error updating last message for session %s: %s", session_id, e)
        return False
