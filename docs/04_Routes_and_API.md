# 04 — Routes & API

## Overview

PersonaUI has **12 Flask blueprints** with a total of **71 endpoints**. All JSON endpoints use a unified response format and are wrapped with the `@handle_route_error` decorator.

---

## Blueprint Registration

Blueprints are registered in `src/routes/__init__.py` in a deliberate order:

1. `access_bp` — Must come first (access control middleware)
2. `onboarding_bp` — Before `main`, so `/onboarding` is reachable
3. `main_bp`, `chat_bp`, `character_bp`, `sessions_bp`, `api_bp`, `avatar_bp`, `memory_bp`, `settings_bp`, `custom_specs_bp`, `user_profile_bp`

---

## Unified Response Format

```json
// Success
{ "success": true, ...data }

// Error
{ "success": false, "error": "Error message", ...extra }
```

---

## Complete Endpoint Overview

### Main (`src/routes/main.py`)

| # | Method | Path | Function | Description |
|---|--------|------|----------|-------------|
| 1 | GET | `/` | `index()` | Render main chat page |

**`index()` logic:**
1. Onboarding check → redirect to `/onboarding` if needed
2. Load character data, user profile, avatar
3. Evaluate session parameters from query
4. Resolve persona ID for session
5. Switch persona if session belongs to a different persona
6. Load chat history and message count
7. Save greeting message as first bot message
8. Render `chat.html`

---

### Chat (`src/routes/chat.py`)

| # | Method | Path | Function | Description |
|---|--------|------|----------|-------------|
| 2 | POST | `/chat` | `chat()` | Non-streamed (stub/guard) |
| 3 | POST | `/chat_stream` | `chat_stream()` | Streamed chat via SSE |
| 4 | POST | `/clear_chat` | `clear_chat()` | Clear chat history |
| 5 | POST | `/afterthought` | `afterthought()` | Afterthought (decision + followup) |

**`/chat_stream` request:**
```json
{
  "message": "string",
  "session_id": 1,
  "api_model": "string?",
  "api_temperature": 0.7,
  "experimental_mode": false,
  "context_limit": 25
}
```

SSE events: `chunk` → `done` (with response + stats) → `error`

**`/afterthought` phases:**
- **`decision`**: Persona decides whether follow-up is needed (yes/no)
- **`followup`**: Streams the follow-up message (only on "yes")

---

### API (`src/routes/api.py`)

| # | Method | Path | Description |
|---|--------|------|-------------|
| 6 | POST | `/api/test_api_key` | Test API key |
| 7 | GET | `/api/check_api_status` | Check API status |
| 8 | POST | `/api/save_api_key` | Save API key to `.env` |
| 9 | GET | `/api/get_server_settings` | Server configuration |
| 10 | GET | `/api/get_local_ips` | Local IP addresses |
| 11 | POST | `/api/save_server_mode` | Save server mode |
| 12 | POST | `/api/generate_qr_code` | QR code as Base64 PNG |
| 13 | POST | `/api/save_and_restart_server` | Save and restart server |
| 14 | POST | `/api/prompts/reload` | Hot-reload prompt templates |

**Server restart mechanism:**
1. Writes `server_settings.json`
2. Creates `restart_server.bat` (waits 2s, restarts Python app)
3. Starts batch via `subprocess.Popen`
4. Terminates current process via `os._exit(0)`

---

### Character/Persona (`src/routes/character.py`)

| # | Method | Path | Description |
|---|--------|------|-------------|
| 15 | GET | `/get_char_config` | Current persona configuration |
| 16 | GET | `/get_available_options` | All persona spec options |
| 17 | POST | `/save_char_config` | Save persona configuration |
| 18 | GET | `/api/personas` | List all personas |
| 19 | POST | `/api/personas` | Create new persona |
| 20 | DELETE | `/api/personas/<id>` | Delete persona |
| 21 | PUT | `/api/personas/<id>` | Update persona (name immutable) |
| 22 | POST | `/api/personas/<id>/activate` | Activate persona |
| 23 | GET | `/api/personas/active` | Active persona ID |
| 24 | POST | `/api/personas/restore_default` | Restore default persona |
| 25 | POST | `/api/personas/background-autofill` | AI-generated background story |

---

### Memory (`src/routes/memory.py`)

| # | Method | Path | Description |
|---|--------|------|-------------|
| 26 | POST | `/api/memory/preview` | Memory preview |
| 27 | POST | `/api/memory/create` | Create memory |
| 28 | GET | `/api/memory/list` | All memories |
| 29 | PUT | `/api/memory/<id>` | Edit memory |
| 30 | DELETE | `/api/memory/<id>` | Delete memory |
| 31 | PATCH | `/api/memory/<id>/toggle` | Toggle status |
| 32 | GET | `/api/memory/check-availability/<sid>` | Creation availability |
| 33 | GET | `/api/memory/stats` | Memory statistics |

---

### Sessions (`src/routes/sessions.py`)

| # | Method | Path | Description |
|---|--------|------|-------------|
| 34 | GET | `/api/sessions` | All sessions |
| 35 | GET | `/api/sessions/persona_summary` | Sessions per persona |
| 36 | POST | `/api/sessions/new` | New session |
| 37 | GET | `/api/sessions/<id>` | Load session |
| 38 | DELETE | `/api/sessions/<id>` | Delete session |
| 39 | GET | `/api/sessions/<id>/is_empty` | Check if session is empty |
| 40 | POST | `/api/sessions/<id>/load_more` | Paginated messages |

**Soft-Reload support:** Both `POST /api/sessions/new` (#36) and `GET /api/sessions/<id>` (#37) return additional data for client-side soft reload:
- `character` — `{ char_name, avatar, avatar_type }` for header/bubble updates
- `chat_history` — Full message list for re-rendering the chat area
- `total_message_count` — For the load-more button

---

### Settings (`src/routes/settings.py`)

| # | Method | Path | Description |
|---|--------|------|-------------|
| 41 | GET | `/api/user-settings` | User settings |
| 42 | PUT | `/api/user-settings` | Update settings |
| 43 | POST | `/api/user-settings/reset` | Reset to defaults |

> **Note:** Session titles are no longer AI-generated. Sessions are identified by their date instead.

---

### Access Control (`src/routes/access.py`)

| # | Method | Path | Access | Description |
|---|--------|------|--------|-------------|
| 44 | GET | `/access/waiting` | Public | Render waiting page |
| 45 | POST | `/api/access/request` | Public | Request access |
| 46 | GET | `/api/access/poll` | Public | Poll status |
| 47 | GET | `/api/access/pending` | Local | Pending requests |
| 48 | POST | `/api/access/approve` | Local | Approve IP |
| 49 | POST | `/api/access/deny` | Local | Block IP |
| 50 | GET | `/api/access/lists` | Local | White-/blacklist |
| 51 | POST | `/api/access/whitelist/remove` | Local | Remove from whitelist |
| 52 | POST | `/api/access/blacklist/remove` | Local | Remove from blacklist |
| 53 | POST | `/api/access/toggle` | Local | Toggle access control |

---

### Avatar (`src/routes/avatar.py`)

| # | Method | Path | Description |
|---|--------|------|-------------|
| 54 | GET | `/api/get_available_avatars` | Available avatars |
| 55 | POST | `/api/save_avatar` | Save avatar selection |
| 56 | POST | `/api/upload_avatar` | Upload avatar + crop |
| 57 | DELETE | `/api/delete_avatar/<filename>` | Delete avatar |
| 58 | POST | `/api/delete_custom_avatar` | Delete custom avatar (POST) |

**Upload processing:** Validates file type (png/jpg/jpeg/webp), max 10MB, crops to square, scales to 1024×1024, saves as JPEG (quality 90).

---

### Onboarding (`src/routes/onboarding.py`)

| # | Method | Path | Description |
|---|--------|------|-------------|
| 59 | GET | `/onboarding` | Onboarding page |
| 60 | POST | `/api/onboarding/complete` | Complete onboarding |

---

### User Profile (`src/routes/user_profile.py`)

| # | Method | Path | Description |
|---|--------|------|-------------|
| 61 | GET | `/api/user-profile` | User profile |
| 62 | PUT | `/api/user-profile` | Update profile |
| 63 | POST | `/api/user-profile/avatar/upload` | Upload user avatar |

---

### Custom Specs (`src/routes/custom_specs.py`)

| # | Method | Path | Description |
|---|--------|------|-------------|
| 64 | GET | `/api/custom-specs` | All custom specs |
| 65 | POST | `/api/custom-specs/persona-type` | Add persona type |
| 66 | POST | `/api/custom-specs/core-trait` | Add core trait |
| 67 | POST | `/api/custom-specs/knowledge` | Add knowledge area |
| 68 | POST | `/api/custom-specs/scenario` | Add scenario |
| 69 | POST | `/api/custom-specs/expression-style` | Add expression style |
| 70 | DELETE | `/api/custom-specs/<category>/<key>` | Delete custom spec |
| 71 | POST | `/api/custom-specs/autofill` | AI-generated spec fields |

---

## Cross-Cutting Patterns

### Error Handling
Every route is wrapped with `@handle_route_error('name')` — catches all exceptions, logs traceback, returns generic 500 error.

### Persona ID Resolution
`resolve_persona_id(session_id)` provides unified resolution: query param → body → session DB → active persona.

### Storage Layer Distribution

| Storage | Data |
|---------|------|
| SQLite (per persona) | Chat messages, sessions, memories |
| JSON files | Settings, persona configs, custom specs |
| `.env` file | API key, server mode |
| Filesystem | Avatar images |

### Service Layer Dependencies

```
Routes → get_chat_service()   → ChatService   (streaming, afterthought)
       → get_memory_service() → MemoryService (summarization)
       → get_api_client()     → ApiClient     (Anthropic API)
       → get_prompt_engine()  → PromptEngine  (template resolution)
```

### Rendered Templates

| Template | Route | Description |
|----------|-------|-------------|
| `chat.html` | `main.index` | Main chat interface |
| `waiting.html` | `access.waiting_screen` | Access control waiting page |
| `onboarding.html` | `onboarding.onboarding` | Initial setup |
