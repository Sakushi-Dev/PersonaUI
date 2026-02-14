# 03 — Utils & Helpers

## Overview

The utility layer forms the **foundation** of the application. It provides logging, service management, access control, database access, API communication, and general helper functions.

---

## Architecture

```
Routes ──→ Route Helpers ──→ Services ──→ API Client ──→ Anthropic API
                │                │
                └── Config ◄─────┘
                │                │
                └── Database ◄───┘
                      │
                      └── SQL Loader ──→ .sql files
```

---

## `src/utils/__init__.py` — Package Facade

Re-exports the most commonly used symbols for convenient imports:

**From `.database`:** `init_all_dbs`, `get_chat_history`, `get_conversation_context`, `save_message`, `clear_chat_history`, `get_message_count`

**From `.api_request`:** `ApiClient`

**From `.config`:** `load_character`, `load_char_config`, `load_char_profile`, `save_char_config`, `build_character_description`, `build_character_description_from_config`, `get_available_char_options`, `load_avatar`, `save_avatar_config`

---

## Logger (`src/utils/logger.py`)

Central logging system. **Most imported module** in the entire project.

| Setting | Value |
|---------|-------|
| Logger name | `'personaui'` |
| Logger level | `DEBUG` |
| File handler level | `DEBUG` |
| Console handler level | `INFO` |
| Log file | `src/logs/personaui.log` |
| Max file size | 5 MB |
| Backup count | 3 rotating files |
| Format | `%(asctime)s %(levelname)-8s [%(name)s.%(module)s] %(message)s` |

**Pattern:** Singleton logger with handler deduplication guard. Propagation disabled (prevents double output).

---

## Provider (`src/utils/provider.py`) — Service Locator

Central **Service Locator** for all singleton services.

### Module-Level Singletons

| Variable | Type | Description |
|----------|------|-------------|
| `_api_client` | `ApiClient` | Anthropic API client |
| `_chat_service` | `ChatService` | Chat orchestration |
| `_memory_service` | `MemoryService` | Memory orchestration |
| `_prompt_engine` | `PromptEngine` | Template resolution |

### Functions

| Function | Description |
|----------|-------------|
| `init_services(api_key=None)` | Called once in `app.py` — creates ApiClient, ChatService, MemoryService |
| `get_api_client()` | Returns singleton, `RuntimeError` if not initialized |
| `get_chat_service()` | Returns singleton, `RuntimeError` if not initialized |
| `get_memory_service()` | Returns singleton, `RuntimeError` if not initialized |
| `get_prompt_engine()` | Lazy-initializes PromptEngine on first call |
| `reset_prompt_engine()` | Resets engine (for tests/reload) |

**Dependency flow:** `app.py → init_services() → provider stores singletons → routes call get_*() `

---

## Access Control (`src/utils/access_control.py`)

IP-based access control for multi-device/network usage. **397 lines.**

### Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `MAX_ATTEMPTS` | 3 | Max access attempts |
| `BLOCK_DURATION` | 300s | Block duration (5 min) |
| `PENDING_TIMEOUT` | 300s | Timeout for pending requests |

### In-Memory State (thread-safe via `threading.Lock`)

- `_pending_requests: dict` — `{ip: {timestamp, status}}`
- `_rate_limits: dict` — `{ip: {attempts, blocked_until}}`

### Functions

| Function | Returns | Description |
|----------|---------|-------------|
| `check_access(ip)` | `'allowed'\|'blocked'\|'rate_limited'\|'pending'\|'unknown'` | Main access check — local IPs always allowed |
| `request_access(ip)` | Status string | Submit access request |
| `approve_ip(ip)` | `bool` | Approve IP (add to whitelist) |
| `deny_ip(ip)` | `bool` | Block IP (add to blacklist) |
| `poll_access_status(ip)` | `'pending'\|'approved'\|'denied'\|'expired'` | Polling endpoint for external devices |
| `set_access_control_enabled(enabled)` | `bool` | Enable/disable access control |
| `get_pending_requests()` | `dict` | Current pending requests |
| `get_access_lists()` | `dict` | Whitelist and blacklist |

**Pattern:** Hybrid persistence — whitelist/blacklist stored in JSON, pending requests and rate limits in-memory only.

**Flow:** Unknown IP → `request_access()` → local user sees request → `approve_ip()`/`deny_ip()` → external device polls `poll_access_status()`

---

## Time Context (`src/utils/time_context.py`)

| Function | Description |
|----------|-------------|
| `get_german_weekday(date)` | German weekday names (`"Montag"`, `"Dienstag"`, etc.) |
| `get_time_context(ip_address)` | Formatted date/time/weekday for prompt injection |

Used by the Prompt Engine for `{{current_date}}`, `{{current_time}}`, `{{current_weekday}}` template variables.

---

## SQL Loader (`src/utils/sql_loader.py`)

Named SQL query loading system. Externalizes SQL into `.sql` files.

### Functions

| Function | Description |
|----------|-------------|
| `sql(query_path)` | Main API — `sql('chat.get_chat_history')` → loads `src/sql/chat.sql` on first access |
| `load_schema()` | Loads `schema.sql` as raw text |
| `reload()` | Clears all caches (for development/tests) |
| `preload_all()` | Eager-loads all `.sql` files |

**Convention:** SQL files use `-- name: query_name` comments as delimiters. Query paths use dot notation: `'module.query_name'` → file `module.sql`, query `query_name`.

---

## General Helpers (`src/utils/helpers.py`)

| Function | Description |
|----------|-------------|
| `ensure_env_file()` | Creates `.env` with empty `ANTHROPIC_API_KEY` and random `SECRET_KEY` |
| `format_message(message)` | Formats DB messages for display — `*text*` → `<span class="non_verbal">`, code blocks → HTML |
| `_extract_code_blocks(text)` | Internal: Replaces code blocks with placeholders |
| `_insert_code_blocks_html(text, blocks)` | Internal: Replaces placeholders with HTML-escaped code |

**Note:** Code block extraction/insertion is **duplicated** in `response_cleaner.py` — `helpers.py` for stored messages, `response_cleaner.py` for fresh API responses.

---

## Route Helpers (`src/routes/helpers.py`)

Shared utilities for all routes.

| Function | Description |
|----------|-------------|
| `success_response(status_code=200, **data)` | Standard success response `{'success': True, ...}` |
| `error_response(message, status_code=400)` | Standard error response `{'success': False, 'error': msg}` |
| `handle_route_error(endpoint_name)` | Decorator: Wraps route functions with try/catch, logs errors |
| `resolve_persona_id(session_id)` | Multi-source persona ID resolution: query param → JSON body → session DB → active persona |
| `get_client_ip()` | Client IP (considers `X-Forwarded-For` for proxies) |

**Pattern:** The `handle_route_error` decorator is a **cross-cutting concern** — every route can be wrapped with it for uniform error handling.

---

## Dependency Diagram

```
                    ┌──────────────┐
                    │  logger.py   │  ← Imported by ALL modules
                    └──────────────┘
                           │
    ┌──────────┬───────────┼───────────┬──────────────┐
    │          │           │           │              │
┌───────┐ ┌────────┐ ┌─────────┐ ┌────────────┐ ┌──────────┐
│helpers│ │provider│ │config   │ │access_ctrl │ │sql_loader│
└───────┘ └────────┘ └─────────┘ └────────────┘ └──────────┘
              │           │                          │
         ┌────┴────┐      │                    ┌─────┴─────┐
         │Services │      │                    │ database/ │
         └─────────┘      │                    └───────────┘
              │           │                          │
         ┌────┴────┐      │                    ┌─────┴─────┐
         │ApiClient│      │                    │ .sql Files│
         └─────────┘      │                    └───────────┘
              │           │
         ┌────┴──────────┴──┐
         │   Anthropic API  │
         └──────────────────┘
```
