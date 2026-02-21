# 02 — Configuration & Settings

## Overview

PersonaUI uses a **three-layer configuration system**: Factory defaults (versioned) → User overrides (generated) → Runtime environment (`.env`). All settings are stored as JSON files in the `src/settings/` directory.

---

## Configuration Hierarchy

```
defaults.json (versioned, factory defaults)
  ↓ overridden by
user_settings.json (user overrides, generated at runtime)
  ↓ read via
settings_defaults.py (cached accessor with get_default())
  ↓ supplemented by
.env (API key, server mode, secret key)
```

---

## Settings Files

### `src/settings/defaults.json` — Factory Defaults

Versioned default settings shipped with updates:

| Key | Default Value | Description |
|-----|--------------|-------------|
| `apiModel` | `claude-sonnet-4-5-20250929` | Default AI model |
| `apiAutofillModel` | `claude-sonnet-4-5-20250929` | Model for autofill features |
| `apiModelOptions` | Array with 4 models | Available models with pricing data |
| `apiTemperature` | `"0.7"` | Creativity temperature |
| `contextLimit` | `"25"` | Max context messages |
| `darkMode` | `false` | Dark mode on/off |
| `dynamicBackground` | `true` | Animated background |
| `experimentalMode` | `false` | Experimental mode |
| `nachgedankeEnabled` | `false` | Afterthought system |
| `notificationSound` | `true` | Notification sound |
| `backgroundColor_dark/light` | Color hex | Background colors per mode |
| `bubbleFontFamily` | `"ubuntu"` | Chat font family |
| `bubbleFontSize` | `"18"` | Chat font size |
| `nonverbalColor` | `"#e4ba00"` | Color for *nonverbal* actions |

**Model options** contain `value`, `label`, `pricingName`, `inputPrice`, `outputPrice` — the UI uses this data for model selection and cost display.

### `src/settings/user_settings.json` — User Overrides

Same schema as `defaults.json`, but only contains values changed by the user. Generated at runtime and overlays the defaults.

### `src/settings/user_profile.json` — User Profile

```json
{
  "user_name": "Saiks",
  "user_avatar": "697be4bc18ac.jpeg",
  "user_avatar_type": "standard",
  "user_gender": "Männlich",
  "user_interested_in": ["Weiblich"],
  "user_info": ""
}
```

Used by the prompt builder for `{{user_name}}`, `{{user_gender}}` etc. injection into system prompts. Validations:
- `user_gender`: Only `Männlich`, `Weiblich`, `Divers` or `null`
- `user_interested_in`: Filtered to valid genders
- `user_info`: Max 500 characters
- `user_name`: Max 30 characters, default "User"

### `src/settings/onboarding.json` — Onboarding Status

```json
{ "completed": true }
```

Boolean flag. When `false`, users are guided through the initial setup. Onboarding routes are always exempt from access control.

### `src/settings/update_state.json` — Git Update Tracking

```json
{ "commit": "34257b246e27737987fdbc90aea91e326d073ce4" }
```

Stores the last seen Git commit hash. Compared with the remote HEAD on startup to indicate available updates.

### `src/settings/window_settings.json` — Window State

```json
{ "width": 1280, "height": 860, "x": 373, "y": 412 }
```

Saved on close and restored on next startup.

### `src/settings/server_settings.json` — Server Configuration

Contains `server_mode` (`local`/`listen`), `port`, whitelist/blacklist for access control.

---

## Settings Accessor (`src/utils/settings_defaults.py`)

### Functions

| Function | Description |
|----------|-------------|
| `load_defaults()` | Loads and caches `defaults.json` (singleton) |
| `get_default(key, fallback)` | Get a single default value |
| `get_api_model_default()` | Default API model |
| `get_api_model_options()` | Model list with pricing metadata |
| `get_autofill_model()` | AutoFill model (fallback to main model) |

**Pattern:** Singleton cache. Defaults are loaded once and never reloaded at runtime — changes to `defaults.json` require an app restart.

---

## Window Settings (`src/utils/window_settings.py`)

### Functions

| Function | Description |
|----------|-------------|
| `load_window_settings()` | Loads from JSON, validates position, returns defaults if missing |
| `save_window_settings(w, h, x, y)` | Sanitizes and saves to JSON |
| `_get_virtual_screen_bounds()` | Multi-monitor detection via Win32 API (`ctypes.windll.user32`) |
| `_sanitize_position(x, y, w, h)` | Validates coordinates on screen, detects minimized windows (`-32000`) |
| `_sanitize_size(w, h)` | Enforces minimum dimensions (400×300) |

**Windows-specific:** Uses Win32 API via `ctypes` for multi-monitor support. Off-screen detection is important because PyWebView can report `-32000` coordinates for minimized windows.

---

## Environment Variables (`.env`)

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Claude API key |
| `SECRET_KEY` | Flask session key (auto-generated via `secrets.token_hex(32)`) |
| `SERVER_MODE` | `local` or `listen` |
| `SERVER_PORT` | Server port (default 5000) |

The `.env` file is automatically created if not present (`ensure_env_file()`).

---

## Dependencies

```
settings_defaults.py ← defaults.json
                     ← Used by all routes and services
                     
window_settings.py   ← window_settings.json
                     ← Used by app.py (start/close)
                     ← Depends on ctypes (Win32 API)

user_profile.json    ← Used by prompt_builder (placeholder resolution)
                     ← Used by routes/user_profile.py (CRUD)
                     ← Used by routes/main.py (chat rendering)

user_settings.json   ← Used by routes/settings.py (CRUD)
                     ← Used by UserSettings.js (frontend sync)
```

---

## Design Decisions

1. **Layered config**: Factory defaults remain unchanged through updates, user overrides stored separately
2. **JSON over database**: Simple settings as JSON files, not in SQLite
3. **Singleton cache**: Defaults loaded only once for performance
4. **Defaults-only keys**: Certain keys (`apiModelOptions`, `apiAutofillModel`) are never persisted in `user_settings.json`
5. **Auto-creation**: Missing config files are automatically created with defaults
