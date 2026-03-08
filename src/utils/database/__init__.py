"""
Database Package - Public API

JSONL-basiertes Datensystem:
- connection: Data directory, persona paths
- schema: Persona-Verzeichnis Lifecycle
- jsonl_store: Low-level JSONL read/write engine
- jsonl_chat: Messages, history, context
- jsonl_sessions: Session management
"""

# Core connection & schema functions
from .connection import (
    get_persona_dir,
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
    'get_persona_dir',
    'get_all_persona_ids',
    'DATA_DIR',
    'init_persona_db',
    'create_persona_db',
    'delete_persona_db',
    'init_all_dbs',
    'find_session_persona',
    
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
