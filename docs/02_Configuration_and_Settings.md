# 02 — Configuration & Settings

> How PersonaUI manages settings: JSON files, defaults, user overrides, and environment variables.

---

## Three-Layer Configuration Model

PersonaUI uses a cascading configuration strategy:

```
Layer 1 (lowest priority): defaults.json          — Factory defaults, never edited by user
Layer 2:                    user_settings.json     — User overrides (saved via UI)
Layer 3 (highest priority): .env                   — Environment variables (API keys, secrets)
```

When a setting is read, the system checks `user_settings.json` first, then falls back to `defaults.json`. Environment variables (loaded via `python-dotenv`) override everything for sensitive values like API keys.

---

## Settings Files

All settings live in `src/settings/`:

| File | Purpose | Edited By |
|------|---------|-----------|
| `defaults.json` | Factory defaults for all settings | Developers only |
| `user_settings.json` | User overrides (theme, model, language, etc.) | UI / API |
| `server_settings.json` | Server config (host, port, access control) | UI / API |
| `user_profile.json` | User's name, persona language preference | UI |
| `cortex_settings.json` | Cortex memory enabled/disabled, update frequency | UI |
| `model_options.json` | Available AI models and their display names | Developers |
| `onboarding.json` | Onboarding completed flag | System |
| `window_settings.json` | PyWebView window position/size | System (auto-saved) |
| `cycle_state.json` | Cortex update cycle tracking | System |
| `emoji_usage.json` | Emoji usage tracking for personas | System |
| `update_state.json` | App update state | System |

### `defaults.json` — Factory Defaults

Contains the complete set of default values. Key sections:

```json
{
    "api_model": "claude-sonnet-4-20250514",
    "api_temperature": 0.7,
    "api_max_tokens": 4096,
    "context_limit": 25,
    "theme": "dark",
    "language": "en",
    "cortexEnabled": true,
    "cortexFrequency": "medium",
    "afterthoughtEnabled": true,
    "afterthoughtDelay": 15,
    "experimentalMode": false,
    "streamingEnabled": true
}
```

### `user_settings.json` — User Overrides

Only contains values the user has explicitly changed. Missing keys fall back to `defaults.json`:

```json
{
    "api_model": "claude-sonnet-4-20250514",
    "theme": "light",
    "language": "de"
}
```

### `user_profile.json` — User Identity

```json
{
    "user_name": "Alex",
    "persona_language": "english",
    "avatar": null
}
```

The `persona_language` field determines the language the AI persona speaks. This is separate from the UI language (`language` in settings).

---

## Config Access Pattern

### Backend: `settings_defaults.py`

Provides accessor functions that implement the three-layer cascade:

```python
def get_setting(key, default=None):
    """Read from user_settings.json, fallback to defaults.json."""
    user_val = _read_json('user_settings.json').get(key)
    if user_val is not None:
        return user_val
    return _read_json('defaults.json').get(key, default)

def get_api_model_default():
    return get_setting('api_model', 'claude-sonnet-4-20250514')
```

### Backend: `config.py`

The larger config module (`~802 lines`) handles persona-specific configuration:

```python
def load_character(persona_id=None):
    """Load the active persona's configuration."""
    # Returns dict with char_name, persona_type, traits, knowledge, etc.

def save_character(data, persona_id=None):
    """Save persona configuration changes."""

def get_active_persona_id():
    """Get the ID of the currently active persona."""

def get_config_path(relative_path):
    """Resolve a path relative to src/ directory."""
```

### Frontend: `SettingsContext`

React context that fetches settings from the API and provides them to all components:

```jsx
const { settings, updateSetting } = useSettings();
// settings.theme, settings.language, settings.api_model, etc.
```

---

## Environment Variables (`.env`)

The `.env` file is auto-created by `helpers.py:ensure_env_file()` on first run:

```env
ANTHROPIC_API_KEY=sk-ant-...
```

| Variable | Purpose | Required |
|----------|---------|----------|
| `ANTHROPIC_API_KEY` | Claude API key | Yes (for chat) |

The API key can also be set via the UI (Settings overlay), which writes to `.env`.

---

## Settings Migration

**File:** `src/utils/settings_migration.py`

When the app updates, new settings may be introduced or old ones renamed. The migration system handles this:

```python
def migrate_settings():
    """Check user_settings.json against defaults.json schema."""
    # Remove deprecated keys
    # Add new keys with default values
    # Rename changed keys
```

Migrations run automatically on startup.

---

## Window Settings

**File:** `src/utils/window_settings.py`

Persists PyWebView window position and size between sessions:

```json
{
    "x": 100,
    "y": 50,
    "width": 1200,
    "height": 800
}
```

Values are saved on window close and restored on next launch using Win32 API calls where available.

---

## Settings API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/settings` | Get all settings (merged defaults + user) |
| `POST` | `/api/settings` | Update setting(s) |
| `GET` | `/api/settings/defaults` | Get factory defaults only |
| `POST` | `/api/settings/reset` | Reset to factory defaults |
| `GET` | `/api/model-options` | Get available AI models |

See [04 — Routes & API](04_Routes_and_API.md) for the complete endpoint reference.

---

## Related Documentation

- [01 — App Core & Startup](01_App_Core_and_Startup.md) — Settings loaded during startup
- [03 — Utils & Helpers](03_Utils_and_Helpers.md) — `.env` file creation
- [09 — Persona & Instructions](09_Persona_and_Instructions.md) — Persona-specific configuration
- [12 — Frontend React SPA](12_Frontend_React_SPA.md) — SettingsContext consumer
