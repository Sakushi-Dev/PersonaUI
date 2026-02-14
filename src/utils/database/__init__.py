"""
Datenbank-Package für die Chat-Anwendung

Per-Persona Datenbank-Architektur:
- data/main.db       → Standard-Persona ('default')
- data/persona_{id}.db → Erstellte Personas (z.B. persona_89c4558f.db)

Jede Persona hat ihre eigene SQLite-DB mit identischem Schema.
Beim Erstellen einer Persona wird die DB angelegt, beim Löschen entfernt.

Modul-Struktur:
- connection.py  → DB-Pfad & Verbindung (DATA_DIR, get_db_path, get_db_connection)
- schema.py      → Schema-Init, Persona-DB Lifecycle (init_all_dbs, create/delete_persona_db)
- migration.py   → Migrations-Framework (run_pending_migrations, MIGRATIONS Registry)
- chat.py        → Chat-Nachrichten CRUD & Context
- sessions.py    → Session-Management CRUD
- memories.py    → Memory-Management CRUD & Marker
"""

# === Connection ===
from .connection import (
    DATA_DIR,
    get_db_path,
    get_db_connection,
)

# === Schema & Initialisierung ===
from .schema import (
    init_persona_db,
    create_persona_db,
    delete_persona_db,
    get_all_persona_ids,
    init_all_dbs,
    find_session_persona,
)

# === Migration ===
from .migration import (
    run_pending_migrations,
)

# === Chat History ===
from .chat import (
    get_chat_history,
    get_message_count,
    get_conversation_context,
    save_message,
    clear_chat_history,
    get_total_message_count,
    get_max_message_id,
    get_user_message_count_since_marker,
    get_messages_since_marker,
)

# === Session Management ===
from .sessions import (
    create_session,
    get_all_sessions,
    get_persona_session_summary,
    get_session_persona_id,
    get_session,
    update_session_title,
    delete_session,
    get_current_session_id,
)

# === Memory Management ===
from .memories import (
    save_memory,
    get_all_memories,
    get_active_memories,
    update_memory,
    delete_memory,
    toggle_memory_status,
    get_session_message_count,
    set_last_memory_message_id,
    get_last_memory_message_id,
)

__all__ = [
    # Connection
    'DATA_DIR', 'get_db_path', 'get_db_connection',
    # Schema
    'init_persona_db', 'create_persona_db', 'delete_persona_db',
    'get_all_persona_ids', 'init_all_dbs', 'find_session_persona',
    # Migration
    'run_pending_migrations',
    # Chat
    'get_chat_history', 'get_message_count', 'get_conversation_context',
    'save_message', 'clear_chat_history', 'get_total_message_count',
    'get_max_message_id', 'get_user_message_count_since_marker',
    'get_messages_since_marker',
    # Sessions
    'create_session', 'get_all_sessions', 'get_persona_session_summary',
    'get_session_persona_id', 'get_session', 'update_session_title',
    'delete_session', 'get_current_session_id',
    # Memories
    'save_memory', 'get_all_memories', 'get_active_memories',
    'update_memory', 'delete_memory', 'toggle_memory_status',
    'get_session_message_count', 'set_last_memory_message_id',
    'get_last_memory_message_id',
]
