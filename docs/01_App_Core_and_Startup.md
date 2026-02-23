# 01 — App Core & Startup

> How PersonaUI bootstraps, configures Flask, and launches the desktop window.

---

## Startup Chain

PersonaUI uses a **two-stage startup** with an optional process replacement:

```
bin/start.bat
    └── python src/init.py
            ├── Stage 1: Environment Bootstrap (init.py)
            │     ├── Ensure Python venv exists
            │     ├── Install/update pip dependencies
            │     ├── Download Node.js 22 if missing
            │     ├── Run npm install in frontend/
            │     └── exec() → app.py (replaces process)
            │
            └── Stage 2: Flask Application (app.py)
                  ├── Create Flask app + CORS
                  ├── Init database schemas
                  ├── Init singleton services (Provider)
                  ├── Register 15 route blueprints
                  ├── Apply IP access control
                  ├── (--dev) Start Vite dev server
                  └── Launch PyWebView window (or --no-gui)
```

---

## Stage 1: `init.py` — Environment Bootstrap

**File:** `src/init.py` (~570 lines)

This is the **entry point** for all startup methods (`start.bat`, manual `python src/init.py`). Its job is to guarantee the runtime environment is ready before launching the actual app.

### What It Does

1. **Virtual Environment** — Creates `.venv/` if it doesn't exist using `python -m venv`
2. **Pip Dependencies** — Installs/upgrades packages from `requirements.txt` using the venv's pip
3. **Node.js** — If `node` is not found on PATH, downloads Node.js v22.14.0 to `bin/node/` and adds it to PATH
4. **npm Install** — Runs `npm install` in `frontend/` to ensure JS dependencies are present
5. **Process Replacement** — Uses `os.execv()` to replace itself with `app.py`, passing through any CLI arguments

### Launch Options

Read from `launch_options.txt` in the project root:

```
# PersonaUI – Launch Options
# Available: --no-gui, --dev
--no-gui
--dev
```

| Flag | Effect |
|------|--------|
| `--no-gui` | Skip PyWebView, open in browser only |
| `--dev` | Start Vite dev server for hot-reload development |

Options can also be passed as CLI arguments: `python src/init.py --dev --no-gui`

### Key Implementation Details

- Uses `subprocess` to run pip/npm commands, capturing output for logging
- Node.js download is platform-aware (Windows zip, Linux/macOS tar.gz)
- The `exec()` call replaces the current process entirely — `init.py` never returns after launching `app.py`
- If `init.py` fails at any stage, it prints a clear error and exits

---

## Stage 2: `app.py` — Flask Application

**File:** `src/app.py` (~374 lines)

### App Factory: `create_app()`

```python
def create_app():
    app = Flask(__name__)
    
    # CORS — allow React dev server
    CORS(app, resources={r"/*": {"origins": ["http://localhost:5173", "http://127.0.0.1:5173"]}})
    
    # Session config
    app.secret_key = os.urandom(24)
    
    # Initialize databases
    init_all_dbs()        # Per-persona SQLite schemas
    run_pending_migrations()  # Schema migrations
    
    # Initialize services (singleton via Provider)
    init_services()       # ApiClient, ChatService, CortexService, PromptEngine
    
    # Register all 15 route blueprints
    register_routes(app)
    
    # IP access control middleware
    apply_access_control(app)
    
    return app
```

### Service Initialization: `init_services()`

Creates singleton service instances and registers them with the Provider:

```python
def init_services():
    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    api_client = ApiClient(api_key)
    chat_service = ChatService(api_client)
    cortex_service = CortexService(api_client)
    
    Provider.set_api_client(api_client)
    Provider.set_chat_service(chat_service)
    Provider.set_cortex_service(cortex_service)
    # PromptEngine is lazily initialized on first access
```

### Vite Dev Server Management

When `--dev` is passed:

```python
def start_vite_dev_server():
    """Starts Vite in a new console window for hot-reload development."""
    frontend_dir = os.path.join(BASE_DIR, '..', 'frontend')
    subprocess.Popen(
        ['cmd', '/c', 'start', 'npm', 'run', 'dev'],
        cwd=frontend_dir, shell=True
    )
```

In dev mode, the React app is served by Vite on `:5173` which proxies API calls to Flask on `:5000`. In production, Flask serves `frontend/dist/` directly.

### PyWebView Desktop Window

```python
def launch_window(app):
    """Opens the PyWebView native window pointing to Flask."""
    url = f"http://127.0.0.1:{PORT}"
    
    if '--no-gui' in sys.argv:
        # Browser-only mode
        webbrowser.open(url)
        app.run(host='127.0.0.1', port=PORT)
    else:
        # Desktop window
        window = webview.create_window(
            'PersonaUI', url,
            width=width, height=height,
            x=x, y=y
        )
        webview.start()
```

Window position and size are persisted in `src/settings/window_settings.json` and restored on next launch.

### Startup Sequence (Complete)

```
1. create_app()
   ├── Flask() + CORS
   ├── init_all_dbs()          → SQLite schemas
   ├── run_pending_migrations() → DB migrations
   ├── init_services()          → ApiClient, ChatService, CortexService
   └── register_routes()        → 15 blueprints
   
2. Start Flask server (threaded, port 5000)

3. (if --dev) start_vite_dev_server()

4. (if --no-gui) open browser
   (else) open PyWebView window
   
5. On window close → save window position → exit
```

---

## File Reference

| File | Lines | Purpose |
|------|-------|---------|
| `src/init.py` | ~570 | Environment bootstrap (venv, pip, node, npm) |
| `src/app.py` | ~374 | Flask app creation, service init, window launch |
| `launch_options.txt` | 4 | CLI flags (`--no-gui`, `--dev`) |
| `bin/start.bat` | — | Windows launcher (calls `init.py`) |
| `bin/install_py12.bat` | — | Python 3.12 installer helper |
| `bin/reset.bat` | — | Factory reset launcher |
| `bin/update.bat` | — | Git pull + dependency update |

---

## Related Documentation

- [02 — Configuration & Settings](02_Configuration_and_Settings.md) — JSON settings loaded during startup
- [03 — Utils & Helpers](03_Utils_and_Helpers.md) — Provider pattern, logger
- [11 — Services Layer](11_Services_Layer.md) — Services initialized during startup
- [12 — Frontend React SPA](12_Frontend_React_SPA.md) — React app served by Flask
