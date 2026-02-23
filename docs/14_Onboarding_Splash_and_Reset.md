# 14 — Onboarding, Splash & Reset

> First-run wizard, retro splash screen, and factory reset — standalone PyWebView mini-apps.

---

## Overview

PersonaUI includes three standalone mini-applications that run as PyWebView windows. They are **separate from the main React SPA** and use self-contained HTML with inline CSS/JS.

```
src/splash_screen/     Retro terminal boot animation
src/reset_screen/      Factory reset tool
src/prompt_editor/     Prompt editing (see doc 13)
```

The **onboarding wizard** is part of the React SPA (not a standalone tool).

---

## Splash Screen

**Directory:** `src/splash_screen/`

```
splash_screen/
├── __init__.py
├── static/
└── templates/
```

### What It Does

A retro terminal-style boot animation that plays while the app initializes:

```
PersonaUI v2.0
> Initializing system.............. OK
> Loading persona engine........... OK
> Connecting to Anthropic API...... OK
> Starting web server.............. OK

Ready. Press any key to continue.
```

### Design

- **Typewriter effect** — Text appears character by character
- **Retro terminal aesthetic** — Green/white text on dark background, monospace font
- **Loading stages** — Each step maps to actual initialization tasks
- Displays in a PyWebView window that closes automatically when startup completes

### HTML Inlining

All CSS and JavaScript are embedded directly in the HTML template to work with PyWebView without external asset loading.

---

## Onboarding Wizard

**Location:** React SPA (`frontend/src/features/onboarding/`)

The onboarding wizard runs on first launch (when `onboarding.json` has `completed: false`).

### Steps

The wizard guides users through initial setup:

1. **Welcome** — Introduction to PersonaUI
2. **API Key** — Enter Anthropic API key
3. **User Profile** — Set user name and language
4. **Persona Setup** — Configure the default persona (or skip)
5. **Complete** — Summary and "Start chatting" button

### Flow

```
App.jsx checks /api/onboarding/status
    │
    ├── completed: true → Show ChatPage
    └── completed: false → Redirect to /onboarding
                             │
                             └── OnboardingPage.jsx
                                   ├── Step 1: Welcome
                                   ├── Step 2: API Key
                                   ├── Step 3: User Profile
                                   ├── Step 4: Persona
                                   └── Step 5: Done
                                         │
                                         └── POST /api/onboarding/complete
                                               → sets onboarding.json to {completed: true}
                                               → redirect to /
```

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/onboarding/status` | Check completion status |
| POST | `/api/onboarding/complete` | Mark as completed |

### Reset

The onboarding can be re-triggered via:
- Slash command `/onboarding` (calls `POST /api/commands/reset-onboarding`)
- Manually setting `completed: false` in `src/settings/onboarding.json`

---

## Factory Reset

**Directory:** `src/reset_screen/`

```
reset_screen/
├── __init__.py
├── static/
├── templates/
└── utils/
```

### What It Does

A standalone PyWebView tool that performs a complete factory reset, launched via `bin/reset.bat`.

### Reset Steps

The reset process follows a **9-step sequence**:

| # | Step | Action |
|---|------|--------|
| 1 | Confirm | User confirms they want to reset |
| 2 | Stop server | Kill running Flask/Vite processes |
| 3 | Clear databases | Delete all SQLite files in `src/data/` |
| 4 | Reset settings | Delete all JSON files in `src/settings/`, restore defaults |
| 5 | Reset persona | Restore `active/persona_config.json` from default |
| 6 | Clear created personas | Delete all files in `created_personas/` |
| 7 | Reset prompts | PromptEngine factory reset (restore `_defaults/`) |
| 8 | Clear Cortex | Reset all Cortex memory files to templates |
| 9 | Clear logs | Delete log files from `src/logs/` |

### Safety

- Confirmation dialog before proceeding
- Each step is shown with status (pending → running → done)
- Errors in one step don't prevent other steps from running
- Summary displayed after completion

### Design

- Same retro terminal aesthetic as the splash screen
- Step-by-step progress display
- Uses PyWebView's JS-Python bridge for executing reset operations

---

## Shared Patterns

All three mini-apps share common patterns:

### HTML Inlining

PyWebView works best with self-contained HTML. External CSS/JS files are embedded at build time:

```python
# Inline all assets into a single HTML string
html = template.render()  # Jinja2 template with embedded CSS/JS
webview.create_window('Title', html=html)
```

### PyWebView JS-Python Bridge

Python methods are exposed to JavaScript:

```python
class Api:
    def do_something(self, param):
        # Python code
        return result

window = webview.create_window('App', html=html, js_api=Api())
```

```javascript
// JavaScript in the HTML
const result = await pywebview.api.do_something('value');
```

### Standalone Execution

Each tool can run independently:

```bash
python src/prompt_editor/editor.py  # Prompt Editor
bin/reset.bat                        # Factory Reset
# Splash screen is launched automatically by app.py
```

---

## Related Documentation

- [01 — App Core & Startup](01_App_Core_and_Startup.md) — Splash screen during startup
- [12 — Frontend React SPA](12_Frontend_React_SPA.md) — Onboarding wizard in React
- [13 — Prompt Editor](13_Prompt_Editor.md) — Prompt Editor details
- [16 — Slash Commands](16_Slash_Commands.md) — `/onboarding` reset command
