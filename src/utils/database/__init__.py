"""
Database Package - Public API

This module maintains backwards compatibility by re-exporting all functions
The database has been refactored into logical modules:
- connection: Legacy DB paths, connections (nur für Migration)
- persona: Persona DB management & legacy migration  
- jsonl_chat: Messages, history, context (JSONL-basiert)
- jsonl_sessions: Session management (JSONL-basiert)

SQLite wurde komplett durch JSONL ersetzt. Legacy SQLite-Module (chat.py, 
sessions.py, migration.py) wurden entfernt. Legacy-Funktionen sind nur
noch für Datenmigration verfügbar.

SQLite wurde komplett durch JSONL ersetzt. Legacy-Funktionen sind nur
noch für Datenmigration verfügbar.
"""

# Core connection & schema functions
from .connection import (
    get_db_path,
    get_db_connection, 
    get_all_persona_ids,
    DATA_DIR
)

from .schema import (
    init_persona_db,
    create_persona_db,
    delete_persona_db,
    init_all_dbs,
    find_session_persona,
)

# Legacy migration
from .persona import migrate_from_legacy_db

# Chat functions (JSONL)
from .jsonl_chat import (
    get_chat_history,
    get_message_count,
    get_conversation_context,
    save_message,
    clear_chat_history,
    get_total_message_count,
    get_max_message_id,
    get_last_message,
    delete_last_message,
    update_last_message_text,
)

# Session functions (JSONL)
from .jsonl_sessions import (
    create_session,
    get_all_sessions,
    get_persona_session_summary,
    get_session_persona_id,
    get_session,
    update_session_title,
    delete_session,
    get_current_session_id
)

# Legacy aliases for backwards compatibility
get_session_message_count = get_message_count

__all__ = [
    # Connection & Schema
    'get_db_path',
    'get_db_connection',
    'init_persona_db',
    'get_all_persona_ids',
    'DATA_DIR',
    
    # Persona Management
    'create_persona_db',
    'delete_persona_db', 
    'init_all_dbs',
    'find_session_persona',
    'migrate_from_legacy_db',
    
    # Chat Operations
    'get_chat_history',
    'get_message_count',
    'get_conversation_context',
    'save_message',
    'clear_chat_history',
    'get_total_message_count',
    'get_max_message_id',
    'get_last_message',
    'delete_last_message',
    'update_last_message_text',
    
    # Session Management
    'create_session',
    'get_all_sessions',
    'get_persona_session_summary',
    'get_session_persona_id', 
    'get_session',
    'update_session_title',
    'delete_session',
    'get_current_session_id',
    
    # Legacy aliases
    'get_session_message_count'
]
