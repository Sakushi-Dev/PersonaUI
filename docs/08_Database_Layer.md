# 08 — Database Layer

## Overview

PersonaUI uses **per-persona SQLite databases** for chat messages, sessions, and memories. Each persona gets its own database file, enabling clean isolation and easy deletion.

---

## Architecture

```
src/utils/database/
  ├── __init__.py        ← Re-exports 27 functions
  ├── connection.py      ← DB path and connection
  ├── schema.py          ← Schema init and persona DB management
  ├── migration.py       ← Registry-based migration framework
  ├── chat.py (333 L.)   ← Chat messages CRUD
  ├── sessions.py        ← Sessions CRUD
  └── memories.py        ← Memories CRUD

src/sql/
  ├── schema.sql         ← Full DB schema
  ├── chat.sql           ← 15 named chat queries
  ├── sessions.sql       ← 9 named session queries
  ├── memories.sql       ← 11 named memory queries
  └── migrations.sql     ← 5 migration queries
```

---

## Per-Persona Database Isolation

| Persona | Database File |
|---------|--------------|
| Default | `src/data/main.db` |
| Custom (UUID) | `src/data/persona_{uuid}.db` |

```python
def get_db_path(persona_id='default'):
    if persona_id == 'default':
        return os.path.join(DATA_DIR, 'main.db')
    return os.path.join(DATA_DIR, f'persona_{persona_id}.db')
```

Connections are created with `PRAGMA foreign_keys = ON`.

---

## Schema (`src/sql/schema.sql`)

### Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `db_info` | Key-value store for persona ID and migrations | `key TEXT PK`, `value TEXT` |
| `chat_sessions` | Session management | `id`, `title`, `persona_id`, `created_at`, `updated_at`, `last_memory_message_id` |
| `chat_messages` | Individual messages | `id`, `session_id FK`, `message`, `is_user BOOL`, `timestamp`, `character_name` |
| `memories` | Memory storage with message range | `id`, `session_id`, `persona_id`, `content`, `is_active BOOL`, `start_message_id`, `end_message_id` |

### Indexes

- `idx_session_id` on `chat_messages(session_id)`
- `idx_memory_session`, `idx_memory_active`, `idx_memory_persona` on `memories`

### Relationships

- `chat_messages.session_id` → `chat_sessions.id` (CASCADE DELETE)
- `last_memory_message_id` on sessions as a "marker" for incremental memory creation

---

## Named SQL Queries

### Chat Queries (`src/sql/chat.sql` — 15 Queries)

| Query | Description |
|-------|-------------|
| `get_latest_session_id` | Most recent session by `updated_at` |
| `get_memory_ranges` | Active memory ranges (non-null start/end) |
| `get_chat_history` | Paginated messages (DESC with LIMIT/OFFSET) |
| `get_conversation_context` | Last N messages for API context |
| `insert_message` | Save message |
| `get_messages_since_marker` | Messages after the last memory marker |
| `count_user_messages_since_marker` | User messages since last memory |
| `get_total_count` | Total message count |
| `get_max_message_id` | Highest message ID |

### Session Queries (`src/sql/sessions.sql` — 9 Queries)

| Query | Description |
|-------|-------------|
| `create_session` | Create new session |
| `get_all_sessions` | All sessions (sorted by `updated_at DESC`) |
| `get_session_by_id` | Single session |
| `update_session_title` | Update title |
| `delete_session` | Delete session (CASCADE) |
| `get_session_count_summary` | Summary per persona |

### Memory Queries (`src/sql/memories.sql` — 11 Queries)

| Query | Description |
|-------|-------------|
| `insert_memory` | Save memory with message range |
| `get_active_memories` / `get_all_memories` | Filtered by `is_active` |
| `toggle_memory_status` | `SET is_active = NOT is_active` |
| `get_max_end_message_id` | Marker recalculation |
| `update_session_memory_marker` | Update session-level marker |
| `upsert_db_info` | `INSERT OR REPLACE` for key-value metadata |

---

## Database Functions

### Connection & Schema (`connection.py`, `schema.py`)

| Function | Description |
|----------|-------------|
| `get_db_path(persona_id)` | Resolve database path |
| `get_db_connection(persona_id)` | Connection with foreign keys |
| `init_persona_db(persona_id)` | Create/open DB file + initialize schema |
| `create_persona_db(persona_id)` | New persona DB + migrations |
| `delete_persona_db(persona_id)` | Delete DB file (protects `'default'`) |
| `get_all_persona_ids()` | Scans `data/` for DBs |
| `init_all_dbs()` | Server start: initialize all DBs + migrations |
| `find_session_persona(session_id)` | Searches all persona DBs for a session ID |

### Chat (`chat.py` — 333 Lines)

| Function | Description |
|----------|-------------|
| `get_chat_history(limit, session_id, offset, persona_id)` | History with `memorized` flag |
| `get_conversation_context(limit, session_id, persona_id)` | Claude API format, merges consecutive same-role messages |
| `save_message(message, is_user, character_name, session_id, persona_id)` | Insert message, auto-create session |
| `clear_chat_history(persona_id)` | Delete all messages and sessions |
| `get_messages_since_marker(session_id, persona_id, limit)` | Messages after memory marker |

**Important:** `get_conversation_context` merges consecutive same-role messages (e.g. from afterthought), because the Claude API requires alternating user/assistant roles.

### Sessions (`sessions.py`)

| Function | Description |
|----------|-------------|
| `create_session(title, persona_id)` | New chat session |
| `get_all_sessions(persona_id)` | If `None`: aggregates across **all** persona DBs |
| `get_persona_session_summary()` | Aggregates `{persona_id, session_count, last_updated}` |
| `update_session_title(session_id, title, persona_id)` | Update title |
| `delete_session(session_id, persona_id)` | Delete session (CASCADE deletes messages) |

### Memories (`memories.py`)

| Function | Description |
|----------|-------------|
| `save_memory(session_id, content, persona_id, start_message_id, end_message_id)` | With message range |
| `get_all_memories(active_only, persona_id)` | All or only active |
| `toggle_memory_status(memory_id, persona_id)` | Toggle active/inactive |
| `delete_memory(memory_id, persona_id)` | Delete + recalculate marker |
| `set_last_memory_message_id(session_id, message_id, persona_id)` | Set marker |

**Important:** `delete_memory` recalculates the session memory marker by finding the highest `end_message_id` among remaining memories.

---

## Migration Framework

Registry-based migration system in `migration.py`:

| Migration ID | Description |
|--------------|-------------|
| `add_last_memory_message_id` | Adds memory marker column to sessions |
| `add_memory_message_ranges` | Adds start/end message IDs to memories |

### Process

```python
MIGRATIONS = [
    {
        'id': 'add_last_memory_message_id',
        'check': 'SELECT last_memory_message_id FROM chat_sessions LIMIT 1',
        'apply': ['ALTER TABLE chat_sessions ADD COLUMN last_memory_message_id INTEGER']
    }
]
```

1. Checks `db_info` table whether migration has already been applied
2. Runs check SQL (catches error = column missing)
3. Applies apply SQL
4. Marks as applied in `db_info`
5. Runs across **all** persona DBs on server start

---

## SQL Loader Convention

SQL files use `-- name: query_name` comments as delimiters:

```sql
-- name: get_chat_history
-- Description: Loads paginated chat messages
SELECT * FROM chat_messages WHERE session_id = ? ORDER BY id DESC LIMIT ? OFFSET ?;

-- name: insert_message
-- Description: Inserts a new message
INSERT INTO chat_messages (session_id, message, is_user, character_name) VALUES (?, ?, ?, ?);
```

Access via `sql('chat.get_chat_history')` — module.query_name.

---

## Dependencies

```
database/
  ├── connection.py (foundation — all others import from here)
  ├── schema.py     ← sql_loader, logger
  ├── migration.py  ← sql_loader, schema.get_all_persona_ids
  ├── chat.py       ← sql_loader, connection
  ├── sessions.py   ← sql_loader, connection, schema
  └── memories.py   ← sql_loader, connection, chat.get_message_count

Consumers:
  ├── Routes (chat, sessions, memory, main, character)
  ├── ChatService
  ├── MemoryService
  └── app.py (init_all_dbs on startup)
```
