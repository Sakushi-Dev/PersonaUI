"""
Database Package - Public API

This module maintains backwards compatibility by re-exporting all functions
that were previously in the monolithic database.py file.

The database has been refactored into logical modules:
- connection: DB paths, connections, schema
- persona: Persona DB management & migration  
- chat: Messages, history, context
- sessions: Session management
- memories: Memory management
"""

# Core connection & schema functions
from .connection import (
    get_db_path,
    get_db_connection, 
    init_db_schema,
    init_persona_db,
    get_all_persona_ids,
    DATA_DIR
)

# Persona management functions
from .persona import (
    create_persona_db,
    delete_persona_db,
    init_all_dbs,
    find_session_persona,
    migrate_from_legacy_db
)

# Chat functions
from .chat import (
    get_chat_history,
    get_message_count,
    get_conversation_context,
    save_message,
    clear_chat_history,
    get_total_message_count,
    get_max_message_id,
    get_user_message_count_since_marker,
    get_messages_since_marker
)

# Session functions  
from .sessions import (
    create_session,
    get_all_sessions,
    get_persona_session_summary,
    get_session_persona_id,
    get_session,
    update_session_title,
    delete_session,
    get_current_session_id
)

# Memory functions
from .memories import (
    save_memory,
    get_all_memories,
    get_active_memories,
    update_memory,
    delete_memory,
    toggle_memory_status,
    set_last_memory_message_id,
    get_last_memory_message_id
)

# Legacy aliases for backwards compatibility
get_session_message_count = get_message_count

__all__ = [
    # Connection & Schema
    'get_db_path',
    'get_db_connection',
    'init_db_schema', 
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
    'get_user_message_count_since_marker',
    'get_messages_since_marker',
    
    # Session Management
    'create_session',
    'get_all_sessions',
    'get_persona_session_summary',
    'get_session_persona_id', 
    'get_session',
    'update_session_title',
    'delete_session',
    'get_current_session_id',
    
    # Memory Management
    'save_memory',
    'get_all_memories',
    'get_active_memories',
    'update_memory',
    'delete_memory',
    'toggle_memory_status',
    'set_last_memory_message_id',
    'get_last_memory_message_id',
    
    # Legacy aliases
    'get_session_message_count'
]