# 08 — Database Layer

> Per-persona SQLite databases, named SQL queries, schema management, and migrations.

---

## Overview

PersonaUI uses SQLite with a **per-persona database** architecture. Each persona has its own database file, keeping chat histories and sessions fully isolated.

```
src/utils/database/
├── __init__.py      Public API (re-exports)
├── connection.py    Connection management, schema init
├── chat.py          Chat message CRUD (~325 lines)
├── sessions.py      Session management (~244 lines)
├── persona.py       Persona DB lifecycle (~222 lines)
├── migration.py     Schema migrations (~133 lines)
└── schema.py        Schema utilities
```

---

## Per-Persona Databases

```
src/data/
├── main.db              Default persona database
├── persona_abc123.db    Custom persona "abc123"
├── persona_def456.db    Custom persona "def456"
└── ...
```

### Database Routing

```python
def get_db_path(persona_id='default') -> str:
    if persona_id == 'default' or not persona_id:
        return os.path.join(DATA_DIR, 'main.db')
    return os.path.join(DATA_DIR, f'persona_{persona_id}.db')
```

All database functions accept an optional `persona_id` parameter to target the correct database.

---

## Schema

**File:** `src/sql/schema.sql`

```sql
CREATE TABLE IF NOT EXISTS db_info (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS chat_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT DEFAULT 'Neue Konversation',
    persona_id TEXT DEFAULT 'default',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    is_user BOOLEAN NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    character_name TEXT DEFAULT 'Assistant',
    FOREIGN KEY (session_id) REFERENCES chat_sessions (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_session_id ON chat_messages(session_id);
```

### Tables

| Table | Purpose |
|-------|---------|
| `db_info` | Key-value store for DB metadata (e.g., `persona_id`) |
| `chat_sessions` | Chat sessions with titles and timestamps |
| `chat_messages` | Individual messages linked to sessions |

Cascading deletes: deleting a session automatically removes all its messages.

---

## Named SQL Queries

All SQL lives in `.sql` files under `src/sql/`, loaded via the SQL Loader (see [03 — Utils & Helpers](03_Utils_and_Helpers.md)).

### `chat.sql` — Message Queries

| Query Name | Purpose |
|------------|---------|
| `get_latest_session_id` | Get the most recent session ID |
| `get_chat_history` | Get messages for a session (paginated) |
| `get_message_count` | Count messages in a session |
| `get_conversation_context` | Get recent messages for API context |
| `insert_message` | Save a new message |
| `update_session_timestamp` | Update session's `updated_at` |
| `delete_all_messages` | Clear all messages in a session |
| `delete_all_sessions` | Delete all sessions |
| `get_total_message_count` | Total messages across all sessions |
| `get_max_message_id` | Highest message ID |
| `count_all_user_messages` | Count user messages only |
| `get_all_messages_count` | Total messages for all sessions |
| `get_all_messages_limited` | Limited message listing |
| `get_last_message` | Get the last message in a session |
| `delete_last_message` | Delete the last message |
| `update_last_message_text` | Edit last message text |
| `upsert_db_info` | Insert or update DB metadata |

### `sessions.sql` — Session Queries

| Query Name | Purpose |
|------------|---------|
| `create_session` | Create a new chat session |
| `get_all_sessions` | List all sessions |
| `get_session_by_id` | Get a specific session |
| `get_session_persona_id` | Get persona ID for a session |
| `update_session_title` | Rename a session |
| `delete_session` | Delete a session |
| `get_current_session_id` | Get the active session |
| `check_session_exists` | Check if session exists |
| `get_session_count_summary` | Session count per persona |

### `migrations.sql` — Migration Queries

| Query Name | Purpose |
|------------|---------|
| `check_last_memory_message_id` | Check if memory marker column exists |
| `add_last_memory_message_id` | Add memory marker column |
| `check_memory_message_ranges` | Check for range columns |
| `add_start_message_id` | Add range start column |
| `add_end_message_id` | Add range end column |

---

## Database Public API

**File:** `src/utils/database/__init__.py`

Re-exports all functions for clean imports:

```python
from utils.database import (
    # Connection
    get_db_connection, init_persona_db, get_all_persona_ids,
    
    # Chat
    get_chat_history, get_conversation_context, save_message,
    clear_chat_history, get_last_message, delete_last_message,
    update_last_message_text, get_message_count,
    
    # Sessions
    create_session, get_all_sessions, get_session,
    update_session_title, delete_session,
    
    # Persona
    create_persona_db, delete_persona_db, init_all_dbs,
)
```

---

## Connection Management

**File:** `src/utils/database/connection.py`

```python
def get_db_connection(persona_id='default') -> sqlite3.Connection:
    db_path = get_db_path(persona_id)
    conn = sqlite3.connect(db_path)
    conn.execute('PRAGMA foreign_keys = ON')  # Enable FK constraints
    return conn
```

Connections are **not pooled** — each function opens and closes its own connection. This is safe for SQLite's use case (single desktop user, low concurrency).

---

## Persona Database Lifecycle

**File:** `src/utils/database/persona.py`

```python
# Create a new persona database
create_persona_db('my_persona')  # Creates src/data/persona_my_persona.db

# Delete a persona database
delete_persona_db('my_persona')  # Removes the .db file

# Initialize all databases on startup
init_all_dbs()  # Creates main.db + migrates legacy chat.db if found
```

### Legacy Migration

If an old `chat.db` file exists (from before per-persona databases), `migrate_from_legacy_db()` moves its data into `main.db`.

---

## Schema Migrations

**File:** `src/utils/database/migration.py`

Migrations are defined as a list of operations that run on every persona database:

```python
MIGRATIONS = [
    {
        'id': 'add_last_memory_message_id',
        'description': 'Memory marker column for sessions',
        'check': 'migrations.check_last_memory_message_id',  # SQL query to check
        'apply': ['migrations.add_last_memory_message_id'],   # SQL queries to apply
    },
    {
        'id': 'add_memory_message_ranges',
        'description': 'Start/End Message-ID for memory ranges',
        'check': 'migrations.check_memory_message_ranges',
        'apply': ['migrations.add_start_message_id', 'migrations.add_end_message_id'],
    },
]
```

### How Migrations Work

1. On startup, `run_pending_migrations()` is called from `app.py`
2. For each persona database, iterates through `MIGRATIONS`
3. Runs the `check` query — if it indicates the migration is needed:
   - Executes all `apply` queries
   - Records the migration ID in `db_info` to prevent re-running
4. All checks use named SQL queries from `migrations.sql`

---

## Data Flow Example

```
User sends message:
    chat.py → save_message(session_id=1, "Hello", is_user=True, persona_id="default")
              → get_db_connection("default")  → opens main.db
              → cursor.execute(sql('chat.insert_message'), ...)
              → cursor.execute(sql('chat.update_session_timestamp'), ...)
              → conn.commit() → conn.close()
```

---

## Related Documentation

- [03 — Utils & Helpers](03_Utils_and_Helpers.md) — SQL Loader
- [05 — Chat System](05_Chat_System.md) — Message persistence
- [07 — Routes & API](04_Routes_and_API.md) — Session and chat endpoints
- [09 — Persona & Instructions](09_Persona_and_Instructions.md) — Persona lifecycle
