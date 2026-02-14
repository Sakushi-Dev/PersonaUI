# 14 — Onboarding, Splash Screen & Reset Screen

## Overview

PersonaUI has three special PyWebView screens for its lifecycle: **Splash Screen** (boot), **Onboarding** (first-time setup), and **Reset Screen** (factory reset). Splash and Reset are native PyWebView windows; Onboarding is a Flask-rendered page.

---

## Splash Screen (`src/splash_screen/`)

### Purpose

Displayed during app startup (PyWebView window, not Flask-served). Shows console output in retro terminal style with typewriter effect.

### Files

| File | Description |
|------|-------------|
| `__init__.py` | HTML bundling + exports: `load_splash_html()`, `hide_console_window()`, `show_console_window()`, `startup_sequence()` |
| `templates/splash.html` | Layout: glow-bloom effect, console, title "PERSONA UI" + spinner |
| `static/splash.css` | Dark theme (#0a0a0a), 1200px radial gradient glow, typewriter animation |
| `static/splash.js` | `addLog()`, `typeLine()`, `typeLineWithBar()`, queue system for sequential output |
| `utils/startup.py` | `startup_sequence()` — main boot logic |
| `utils/console.py` | Windows `ctypes`: `hide_console_window()` / `show_console_window()` |

### Startup Sequence (`startup.py`)

```
1. Update check (compares local Git hash with remote)
2. DB initialization (init_all_dbs)
3. Fun persona-specific loading messages
   e.g. "{name}'s emotions are loading"
4. Start Flask server in background thread
5. Socket polling until server responds
6. PyWebView navigates to http://127.0.0.1:{port}
```

### Communication: Python → JS

```python
# Python calls JS via evaluate_js():
window.evaluate_js(f"typeLine('{text}', '{css_class}')")
window.evaluate_js(f"typeLineWithBar('{text}', '{css_class}', {duration})")
time.sleep(delay)  # Synchronized with typewriter animation
```

### Visual Design

- **Background**: #0a0a0a with pulsating radial gradient (glow bloom)
- **Console**: Radial mask (transparent center → opaque edges)
- **Log colors**: info=green, warn=yellow, error=red, fun=purple
- **Progress bar**: Gradient fill (purple → green)

---

## Onboarding (`src/routes/onboarding.py` + Templates)

### Purpose

5-step first-time setup wizard on initial launch. Checks `onboarding.json` for `completed: true`.

### Steps

| Step | Template | Description |
|------|----------|-------------|
| 1 | `_step_welcome.html` | Logo, title, 3 feature highlights, "Start setup" button |
| 2 | `_step_profile.html` | Avatar, name, type grid, gender chips, interest chips, about-me |
| 3 | `_step_interface.html` | Live preview, dark mode, colors, nonverbal color |
| 4 | `_step_api.html` | Context limit, afterthought toggle, API key input + test |
| 5 | `_step_finish.html` | Two variants: with API key (celebration) / without (explore mode) |

### Avatar Gallery (`_avatar_gallery.html`)

Inline overlay with:
- Drop zone for drag & drop
- File input
- Avatar grid with pre-made avatars
- Crop step with canvas + preview circle

### Onboarding Completion

```javascript
// onboarding.js → finishOnboarding()
1. PUT /api/user-profile     → Save profile
2. PUT /api/user-settings    → Save settings
3. POST /api/save_api_key    → Save API key (if provided)
4. POST /api/onboarding/complete → Mark as completed
5. window.location.href = '/' → Redirect to chat page
```

### Styling (`onboarding.css` — 1415 Lines)

- Dedicated design token system (`--ob-*` variables)
- Step cards with slide-in animation, glassmorphism
- Progress bar with gradient fill
- Responsive: 680px breakpoint

---

## Reset Screen (`src/reset_screen/`)

### Purpose

Native PyWebView window for factory reset. Invoked via `src/reset.py`.

### Files

| File | Description |
|------|-------------|
| `__init__.py` | HTML bundling, exports `reset_sequence()` |
| `templates/reset.html` | Confirmation dialog + finish buttons |
| `static/reset.css` | **Red** color scheme (glow in red/orange) |
| `static/reset.js` | Bridge variables, confirmation logic |
| `utils/reset.py` | 9-step reset process |

### Reset Process (9 Steps)

```
1. Delete databases
2. Remove .env
3. Reset settings files
4. Delete created personas
   → Farewell messages: "{name} waves goodbye"
5. Delete custom avatars
6. Reset active persona
7. Delete custom specs
8. Delete logs
9. Clear __pycache__
```

### Python ↔ JS Communication

```python
# Python polls JS variables:
confirmed = window.evaluate_js("isConfirmed()")
cancelled = window.evaluate_js("isCancelled()")

# JS sets bridge variables:
function onConfirm() {
    _confirmed = true;
    // Hides confirmation box, shows spinner
}
```

### Visual Design

- Identical layout to splash, but **red color scheme**
- Confirmation box: "All data will be irreversibly deleted"
- Cancel (dark) + Confirm (red) buttons
- Finish buttons: Start (green), Close (gray)

---

## Shared Patterns

### HTML Inlining

All three screens (splash, reset, editor) use the same bundling pattern:

```python
def load_html():
    html = read('template.html')
    html = html.replace('{{CSS}}', read('style.css'))
    html = html.replace('{{JS}}', read('script.js'))
    return html
```

Everything in a single HTML string for PyWebView (avoids `file://` issues with `webview.create_window(html=...)`).

### Typewriter Engine

Splash and reset share the same typewriter engine:
- `addLog(text)` — Instant log with auto-color detection
- `typeLine(text, cls)` — Queued typewriter at 18ms/character
- `typeLineWithBar(text, cls, duration)` — Typewriter + animated progress bar
- Queue system (`_typeQueue`, `_processQueue`) for sequential output

### Windows Native Integration

`console.py` uses `ctypes.windll.user32`:
- `ShowWindow(hwnd, 0)` — Hide console window
- `ShowWindow(hwnd, 5)` — Show console window

---

## Dependencies

```
Splash Screen
  ├── PyWebView (native window)
  ├── startup.py → init_all_dbs, load_character, server start
  ├── console.py → ctypes (Windows)
  └── update_check.py → update_state.json, Git

Onboarding
  ├── Flask (render_template, redirect)
  ├── onboarding.json (status file)
  ├── onboarding.js → /api/user-profile, /api/user-settings, /api/save_api_key
  └── Standalone CSS (onboarding.css)

Reset Screen
  ├── PyWebView (native window)
  ├── reset.py → filesystem operations
  └── console.py → ctypes (Windows)
```
