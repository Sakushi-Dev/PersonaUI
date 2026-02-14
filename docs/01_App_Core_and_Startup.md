# 01 — App Core & Startup

## Overview

PersonaUI is a **desktop chat application** based on Flask + PyWebView that uses Anthropic's Claude API as the AI backend. The application enables creating and interacting with configurable AI personas through a native desktop interface.

---

## Startup Process (Bootstrap)

### Three-Stage Startup

```
PersonaUI.exe → bin\start.bat → src/init.py
  ├── Stage 1: Already in venv
  │     ├── Quick dependency check
  │     └── exec(app.py)  ← replaces the process (no subprocess overhead)
  ├── Stage 2: Not in venv
  │     ├── Check Python version (≥ 3.10)
  │     ├── Create .venv if needed
  │     └── Start app.py via subprocess in venv
  └── Stage 3: First installation
        ├── pip upgrade
        ├── Install requirements.txt
        └── Start app.py in venv
```

### `src/init.py` — Bootstrap Module

| Function | Description |
|----------|-------------|
| `main()` | Three-stage bootstrap process |
| `_load_launch_options()` | Reads `launch_options.txt` from project root |
| `_merge_launch_options()` | Inserts non-comment lines into `sys.argv` |

**Notable:** The `exec()` technique in Stage 1 completely replaces the `init.py` process with `app.py` — no double process overhead in the normal case.

**Dynamically loaded functions** from `splash_screen/utils/install.py` (via `importlib.util` to avoid import chains):
- `check_python_version()` — Validates Python 3.10+
- `check_venv()` / `check_dependencies()` / `install_dependencies()`
- `_get_venv_python()` / `_running_in_venv()` / `_get_requirements_path()`

---

## `src/app.py` — Main Application

### Module-Level Initialization (before `__main__`)

1. **`os.chdir(script_dir)`** — Set working directory to `src/`
2. **`ensure_env_file()`** — Create `.env` if not present
3. **`load_dotenv()`** — Load environment variables
4. **Flask app creation** — `SECRET_KEY` from `.env`, `json.sort_keys = False`
5. **Session configuration**: 7-day lifetime, HttpOnly, SameSite=Lax
6. **`init_services()`** — Initialize ApiClient, ChatService, MemoryService
7. **Jinja filter** `format_message` registered
8. **`register_routes(app)`** — Attach all Flask blueprints

### IP Access Control (`@app.before_request`)

`check_ip_access()` runs before **every** request. Exempt endpoints:
- Static files, `access.*` routes, `onboarding.*` routes, `/api/access/*`

Non-authorized IPs are redirected to `access.waiting_screen`.

### Startup Modes

| Mode | Description |
|------|-------------|
| **PyWebView** (default) | Native desktop window with splash screen → chat UI |
| **No-GUI** (`--no-gui`) | Pure Flask server in browser |
| **Fallback** | If `pywebview` not installed → browser mode |

### PyWebView Mode in Detail

```python
# Hide console window
hide_console_window()

# Load window settings (position, size)
load_window_settings()

# Splash screen as initial page
webview.Window(splash_html, ...)

# Startup sequence in background thread
startup_sequence → DB init → start Flask → navigate to chat

# On close: save window position/size
_on_closing → save_window_settings()
```

### Server Configuration

Read from `settings/server_settings.json`:
- **Port**: Default 5000
- **Mode**: `local` (127.0.0.1) or `listen` (0.0.0.0)

---

## Dependencies

### External Packages (`requirements.txt`)

| Package | Version | Purpose |
|---------|---------|---------|
| `flask` | ≥3.0.0 | Web framework |
| `anthropic` | ≥0.34.0 | Claude API SDK |
| `python-dotenv` | ≥1.0.0 | Load `.env` file |
| `pyyaml` | ≥6.0.1 | YAML parsing |
| `qrcode` | ≥7.4.2 | QR code generation for network access |
| `pillow` | ≥10.0.0 | Image processing (avatars, QR) |
| `pywebview` | ≥5.0.0 | Native desktop window |
| `pytest` | ≥8.0.0 | Testing |
| `pytest-mock` | ≥3.12.0 | Test mocking |

**Note:** No database driver needed — uses Python's built-in `sqlite3`. No frontend build system — vanilla JS.

### Internal Dependencies of `app.py`

```
app.py
  ├── utils/logger         → Logging
  ├── utils/database        → DB initialization
  ├── utils/provider        → Service initialization
  ├── utils/helpers         → format_message, ensure_env_file
  ├── utils/access_control  → IP access control
  ├── utils/window_settings → Window persistence
  ├── routes/               → All Flask blueprints
  └── splash_screen/        → Boot UI
```

### `launch_options.txt`

Enables persistent CLI flag configuration without editing batch files:
- `--no-gui` — Start without PyWebView window (currently the only documented option)

---

## Design Decisions

1. **Self-Bootstrapping**: `init.py` handles its own venv creation and dependency installation using only stdlib
2. **Process replacement**: `exec()` instead of subprocess for zero-overhead startup
3. **Graceful degradation**: PyWebView → browser fallback if not installed
4. **Windows-native integration**: `ctypes` Win32 API for console hiding and multi-monitor detection
5. **German codebase**: All comments, log messages, UI strings in German
