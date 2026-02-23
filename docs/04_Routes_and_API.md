# 04 — Routes & API

> Complete endpoint reference for all 15 Flask blueprints (~84 endpoints).

---

## Overview

PersonaUI's backend exposes its API through 15 Flask blueprints. All blueprints are registered in `src/routes/__init__.py` via `register_routes(app)`.

### Response Format

All API endpoints return a consistent JSON structure:

```json
// Success
{ "success": true, "data": { ... }, "message": "optional info" }

// Error
{ "success": false, "error": "error message", "error_type": "optional_type" }
```

### Registration Order

Blueprint registration order matters for URL matching:

```python
def register_routes(app):
    app.register_blueprint(react_bp)      # Static assets first
    app.register_blueprint(access_bp)     # Access control early
    app.register_blueprint(onboarding_bp) # /onboarding before catch-all
    app.register_blueprint(main_bp)       # / → React SPA
    app.register_blueprint(chat_bp)
    app.register_blueprint(character_bp)
    app.register_blueprint(sessions_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(avatar_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(custom_specs_bp)
    app.register_blueprint(user_profile_bp)
    app.register_blueprint(commands_bp)
    app.register_blueprint(cortex_bp)
    app.register_blueprint(emoji_bp)
```

---

## 1. Main — `main_bp`

**File:** `src/routes/main.py`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Serves the React SPA (`frontend/dist/index.html`) |

---

## 2. React Frontend — `react_bp`

**File:** `src/routes/react_frontend.py`

Serves built React assets and avatar files.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/vite.svg` | Vite favicon |
| GET | `/avatar/costum/<path:filename>` | Custom uploaded avatars |
| GET | `/avatar/<path:filename>` | Standard avatars (dist → public fallback) |

The blueprint also configures `/assets/*` as a static folder pointing to `frontend/dist/assets/`.

---

## 3. Chat — `chat_bp`

**File:** `src/routes/chat.py` (~530 lines)

Core chat functionality with SSE streaming.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/chat` | Non-streaming chat (redirects to `/chat_stream`) |
| POST | `/chat_stream` | **Main chat endpoint** — SSE streaming |
| POST | `/clear_chat` | Clear chat history for a session |
| DELETE | `/chat/last_message` | Delete the last message |
| PUT | `/chat/last_message` | Edit the last message text |
| POST | `/chat/regenerate` | Regenerate the last bot response |
| POST | `/afterthought` | Afterthought system (decision or followup phase) |
| POST | `/chat/auto_first_message` | Auto-generate first message for new chat |

### SSE Stream Format

`/chat_stream` returns `text/event-stream` with these event types:

```
data: {"type": "chunk", "content": "Hello"}     — Token fragment
data: {"type": "done", "content": "full text"}   — Stream complete
data: {"type": "error", "error": "message"}      — Error occurred
```

See [05 — Chat System](05_Chat_System.md) for details on streaming and afterthoughts.

---

## 4. API — `api_bp`

**File:** `src/routes/api.py`

API key management, server settings, QR codes, prompt reload.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/test_api_key` | Test an Anthropic API key |
| GET | `/api/check_api_status` | Check if API key is configured |
| POST | `/api/save_api_key` | Save API key to `.env` |
| GET | `/api/get_server_settings` | Get server settings (mode, port, IPs) |
| GET | `/api/get_local_ips` | List local network IPs |
| POST | `/api/save_server_mode` | Set server mode (local/listen) |
| POST | `/api/generate_qr_code` | Generate QR code (Base64 image) |
| POST | `/api/save_and_restart_server` | Save settings and restart server |
| POST | `/api/prompts/reload` | Hot-reload prompt templates |

---

## 5. Commands — `commands_bp`

**File:** `src/routes/commands.py`

Backend handlers for slash commands.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/commands/rebuild-frontend` | Run `build_frontend.bat` |
| POST | `/api/commands/reset-onboarding` | Reset onboarding wizard |
| POST | `/api/commands/cortex-update` | Trigger manual Cortex update |

See [16 — Slash Commands](16_Slash_Commands.md) for the full command system.

---

## 6. Character — `character_bp`

**File:** `src/routes/character.py`

Persona CRUD and configuration.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/get_char_config` | Get active persona config |
| GET | `/get_available_options` | Get persona spec options |
| POST | `/save_char_config` | Save persona settings |
| GET | `/api/personas` | List all personas |
| POST | `/api/personas` | Create new persona |
| DELETE | `/api/personas/<persona_id>` | Delete a persona |
| PUT | `/api/personas/<persona_id>` | Update a persona |
| POST | `/api/personas/<persona_id>/activate` | Set active persona |
| GET | `/api/personas/active` | Get active persona ID |
| POST | `/api/personas/restore_default` | Restore default persona |
| POST | `/api/personas/background-autofill` | AI-generate background story |

---

## 7. Sessions — `sessions_bp`

**File:** `src/routes/sessions.py`

Chat session management.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/sessions` | List all sessions (optional `?persona_id=`) |
| GET | `/api/sessions/persona_summary` | Session count per persona |
| POST | `/api/sessions/new` | Create new session |
| GET | `/api/sessions/<id>` | Get session with chat history |
| DELETE | `/api/sessions/<id>` | Delete session |
| GET | `/api/sessions/<id>/is_empty` | Check if session has no messages |
| POST | `/api/sessions/<id>/load_more` | Paginate older messages |

---

## 8. Avatar — `avatar_bp`

**File:** `src/routes/avatar.py`

Avatar upload and management.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/get_available_avatars` | List all avatars |
| POST | `/api/save_avatar` | Set persona avatar |
| POST | `/api/upload_avatar` | Upload custom avatar (1024×1024 JPEG crop) |
| DELETE | `/api/delete_avatar/<filename>` | Delete custom avatar |
| POST | `/api/delete_custom_avatar` | Delete custom avatar (POST variant) |
| POST | `/api/save_user_avatar` | Set user profile avatar |

---

## 9. Access Control — `access_bp`

**File:** `src/routes/access.py`

IP-based access control for remote connections.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/access/waiting` | Waiting screen for unapproved devices |
| POST | `/api/access/request` | Submit access request |
| GET | `/api/access/poll` | Poll request status |
| GET | `/api/access/pending` | List pending requests (local only) |
| POST | `/api/access/approve` | Approve IP |
| POST | `/api/access/deny` | Deny IP |
| GET | `/api/access/lists` | Get whitelist + blacklist |
| POST | `/api/access/whitelist/remove` | Remove from whitelist |
| POST | `/api/access/blacklist/remove` | Remove from blacklist |
| POST | `/api/access/toggle` | Enable/disable access control |

---

## 10. Settings — `settings_bp`

**File:** `src/routes/settings.py`

User settings CRUD.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/user-settings` | Get all settings (merged) |
| PUT | `/api/user-settings` | Update settings (partial) |
| POST | `/api/user-settings/reset` | Reset to defaults |

---

## 11. Custom Specs — `custom_specs_bp`

**File:** `src/routes/custom_specs.py`

User-defined persona specification options.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/custom-specs` | Get all custom specs |
| POST | `/api/custom-specs/persona-type` | Add persona type |
| POST | `/api/custom-specs/core-trait` | Add core trait |
| POST | `/api/custom-specs/knowledge` | Add knowledge area |
| POST | `/api/custom-specs/scenario` | Add scenario |
| POST | `/api/custom-specs/expression-style` | Add expression style |
| DELETE | `/api/custom-specs/<category>/<key>` | Delete spec entry |
| POST | `/api/custom-specs/autofill` | AI-generate spec field |

---

## 12. User Profile — `user_profile_bp`

**File:** `src/routes/user_profile.py`

User identity management.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/user-profile` | Get user profile |
| PUT | `/api/user-profile` | Update user profile |
| POST | `/api/user-profile/avatar/upload` | Upload user avatar |

---

## 13. Onboarding — `onboarding_bp`

**File:** `src/routes/onboarding.py`

First-run setup wizard.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/onboarding` | Onboarding page (serves React SPA) |
| POST | `/api/onboarding/complete` | Mark onboarding as done |
| GET | `/api/onboarding/status` | Check if onboarding completed |

---

## 14. Cortex — `cortex_bp`

**File:** `src/routes/cortex.py` (~313 lines)

Long-term memory file management.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/cortex/files` | Get all 3 cortex files |
| GET | `/api/cortex/file/<filename>` | Get single cortex file |
| PUT | `/api/cortex/file/<filename>` | Update cortex file content |
| POST | `/api/cortex/reset/<filename>` | Reset file to template |
| POST | `/api/cortex/reset` | Reset all cortex files |
| GET | `/api/cortex/settings` | Get cortex settings |
| PUT | `/api/cortex/settings` | Update cortex settings |

Allowed filenames: `memory.md`, `soul.md`, `relationship.md`.

---

## 15. Emoji — `emoji_bp`

**File:** `src/routes/emoji.py`

Emoji reaction tracking.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/emoji-usage` | Get emoji usage counts |
| PUT | `/api/emoji-usage` | Increment emoji count |

---

## Summary

| Blueprint | File | Endpoints | URL Prefix |
|-----------|------|-----------|------------|
| `main_bp` | main.py | 1 | `/` |
| `react_bp` | react_frontend.py | 3 | `/avatar/*`, `/assets/*` |
| `chat_bp` | chat.py | 8 | `/chat*`, `/afterthought` |
| `api_bp` | api.py | 9 | `/api/*` |
| `commands_bp` | commands.py | 3 | `/api/commands/*` |
| `character_bp` | character.py | 11 | `/api/personas/*`, legacy paths |
| `sessions_bp` | sessions.py | 7 | `/api/sessions/*` |
| `avatar_bp` | avatar.py | 6 | `/api/*avatar*` |
| `access_bp` | access.py | 10 | `/api/access/*` |
| `settings_bp` | settings.py | 3 | `/api/user-settings*` |
| `custom_specs_bp` | custom_specs.py | 8 | `/api/custom-specs/*` |
| `user_profile_bp` | user_profile.py | 3 | `/api/user-profile*` |
| `onboarding_bp` | onboarding.py | 3 | `/api/onboarding/*` |
| `cortex_bp` | cortex.py | 7 | `/api/cortex/*` |
| `emoji_bp` | emoji.py | 2 | `/api/emoji-usage` |
| **Total** | **15 files** | **84** | |

---

## Related Documentation

- [03 — Utils & Helpers](03_Utils_and_Helpers.md) — Response helpers, route decorators
- [05 — Chat System](05_Chat_System.md) — Chat and afterthought endpoint details
- [10 — Cortex Memory System](10_Cortex_Memory_System.md) — Cortex file system
- [12 — Frontend React SPA](12_Frontend_React_SPA.md) — Frontend services that call these endpoints
