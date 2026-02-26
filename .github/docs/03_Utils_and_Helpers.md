# 03 — Utils & Helpers

> Shared utilities: logging, service provider, access control, SQL loading, and helper functions.

---

## Overview

The `src/utils/` directory contains all shared infrastructure. These modules are used across routes, services, and the prompt system.

```
src/utils/
├── logger.py              Log system (rotating files + console)
├── provider.py            Singleton service locator
├── access_control.py      IP whitelist/blacklist + rate limiting
├── sql_loader.py          Named SQL query loader
├── helpers.py             .env creation, message formatting
├── time_context.py        Localized date/time for prompts
├── config.py              Persona config (see doc 09)
├── settings_defaults.py   Settings accessor (see doc 02)
├── settings_migration.py  Settings schema migration
├── window_settings.py     PyWebView window position
├── cortex_service.py      Cortex orchestration (see doc 10)
├── api_request/           ApiClient package (see doc 11)
├── services/              ChatService package (see doc 11)
├── prompt_engine/         Prompt engine package (see doc 06)
├── database/              Database package (see doc 08)
└── cortex/                Cortex subsystem (see doc 10)
```

---

## Logger — `logger.py`

Provides a single `log` instance used throughout the application:

```python
from utils.logger import log

log.info("Server started on port %d", port)
log.warning("Cortex update failed: %s", error)
log.error("Database connection error: %s", e)
```

### Configuration

| Setting | Value |
|---------|-------|
| **Log File** | `src/logs/personaui.log` |
| **Rotation** | 5 MB max, 3 backup files |
| **Console** | Colored output (INFO+) |
| **File Level** | DEBUG (captures everything) |
| **Format** | `[YYYY-MM-DD HH:MM:SS] LEVEL — message` |

The logger creates the `logs/` directory automatically. Both file and console handlers are attached to the same `log` instance.

---

## Provider — `provider.py`

Implements the **Service Locator pattern** for singleton access to core services:

```python
from utils.provider import get_api_client, get_chat_service, get_cortex_service, get_prompt_engine

# Usage anywhere in the codebase:
client = get_api_client()       # → ApiClient instance
chat = get_chat_service()       # → ChatService instance
cortex = get_cortex_service()   # → CortexService instance
engine = get_prompt_engine()    # → PromptEngine instance
```

### How It Works

```python
class Provider:
    _api_client = None
    _chat_service = None
    _cortex_service = None
    _prompt_engine = None
    
    @classmethod
    def set_api_client(cls, client):
        cls._api_client = client
    
    @classmethod
    def get_api_client(cls):
        return cls._api_client
```

- Services are set once during `app.py:init_services()` at startup
- `PromptEngine` is lazy-initialized on first `get_prompt_engine()` call
- Module-level functions (`get_api_client()`, etc.) delegate to `Provider` class methods

---

## Access Control — `access_control.py`

**File:** `src/utils/access_control.py` (~397 lines)

Manages IP-based access control for the Flask server. Useful when running in `--no-gui` mode where the app is accessible via browser.

### Features

| Feature | Description |
|---------|-------------|
| **IP Whitelist** | Only listed IPs can access the app |
| **IP Blacklist** | Block specific IPs |
| **Pending Queue** | Unknown IPs go to a pending approval queue |
| **Rate Limiting** | Configurable request rate limits per IP |
| **Bypass for localhost** | `127.0.0.1` always allowed |

### Configuration

Stored in `src/settings/server_settings.json`:

```json
{
    "access_control_enabled": false,
    "whitelist": ["127.0.0.1"],
    "blacklist": [],
    "pending": [],
    "rate_limit": 60
}
```

### Integration

Applied as Flask middleware in `app.py`:

```python
from utils.access_control import apply_access_control
apply_access_control(app)  # Registers before_request hook
```

---

## SQL Loader — `sql_loader.py`

**File:** `src/utils/sql_loader.py` (~150 lines)

Loads named SQL queries from `.sql` files using a comment-based convention:

### SQL File Convention

```sql
-- name: get_chat_history
SELECT id, message, is_user, timestamp, character_name
FROM chat_messages
WHERE session_id = ?
ORDER BY id DESC
LIMIT ? OFFSET ?

-- name: insert_message
INSERT INTO chat_messages (session_id, message, is_user, character_name)
VALUES (?, ?, ?, ?)
```

### Usage

```python
from utils.sql_loader import sql

# Dot notation: file.query_name
cursor.execute(sql('chat.get_chat_history'), (session_id, limit, offset))
cursor.execute(sql('sessions.create_session'), (title, persona_id))
```

### How It Works

1. On first call to `sql('chat.get_chat_history')`, loads `src/sql/chat.sql`
2. Parses all `-- name: xyz` blocks into a dictionary
3. Caches all queries — subsequent calls are instant dict lookups
4. Raises `KeyError` if query name not found

### Schema Loading

```python
from utils.sql_loader import load_schema

schema_sql = load_schema()  # Returns full src/sql/schema.sql content
cursor.executescript(schema_sql)
```

---

## Helpers — `helpers.py`

**File:** `src/utils/helpers.py` (~108 lines)

Small utility functions used across the backend:

### `ensure_env_file()`

Creates the `.env` file on first run if it doesn't exist:

```python
def ensure_env_file():
    env_path = os.path.join(BASE_DIR, '.env')
    if not os.path.exists(env_path):
        with open(env_path, 'w') as f:
            f.write('ANTHROPIC_API_KEY=\n')
```

### `format_message(text)`

Formats AI response text with HTML markup for non-verbal actions and code blocks:

```python
def format_message(text):
    # *actions* → <span class="non_verbal">actions</span>
    # ```code``` → <div class="code-block">...</div>
    return formatted_text
```

> **Note:** This function generates HTML that the React frontend may render via `dangerouslySetInnerHTML`. The frontend also has its own `formatMessage.js` utility.

### `extract_code_blocks(text)`

Extracts fenced code blocks from markdown text, returning a list of `(language, code)` tuples.

---

## Time Context — `time_context.py`

**File:** `src/utils/time_context.py` (~90 lines)

Provides localized date, time, and weekday strings for prompt placeholders:

```python
from utils.time_context import get_time_context

context = get_time_context()
# {'current_date': '23. Februar 2026', 'current_time': '14:30', 'current_weekday': 'Montag'}
```

### Supported Languages

German, English, French, Spanish, Italian, Portuguese, Russian, Japanese, Chinese, Korean.

The language is determined from the user profile's `persona_language` setting.

### Used By

The `PlaceholderResolver` in the PromptEngine calls these functions to fill `{{current_date}}`, `{{current_time}}`, and `{{current_weekday}}` placeholders.

---

## Route Helpers — `routes/helpers.py`

**File:** `src/routes/helpers.py` (~100 lines)

Shared utilities for all route blueprints:

### Unified Response Format

```python
def success_response(data=None, message=None, status=200):
    return jsonify({'success': True, 'data': data, 'message': message}), status

def error_response(message, error_type=None, status=400):
    return jsonify({'success': False, 'error': message, 'error_type': error_type}), status
```

### Error Handling Decorator

```python
@handle_route_error('chat')
def chat():
    # If any exception occurs, returns error_response() automatically
    # Logs the error via logger
```

### Persona Resolution

```python
def resolve_persona_id(session_id=None):
    """Determine the active persona ID from session or active config."""

def get_client_ip():
    """Get the client's IP address (supports X-Forwarded-For)."""
```

---

## Related Documentation

- [02 — Configuration & Settings](02_Configuration_and_Settings.md) — Settings files and defaults
- [04 — Routes & API](04_Routes_and_API.md) — Routes that use these helpers
- [06 — Prompt Engine](06_Prompt_Engine.md) — Time context and placeholders
- [08 — Database Layer](08_Database_Layer.md) — SQL loader usage
- [11 — Services Layer](11_Services_Layer.md) — Provider pattern consumers
