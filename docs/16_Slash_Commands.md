# 16 — Slash Commands

> Discord-style `/command` system with a React command menu and backend handlers.

---

## Overview

PersonaUI supports **slash commands** in the chat input — typing `/` opens a command menu similar to Discord or Slack. Commands trigger special actions like rebuilding the frontend, resetting onboarding, or forcing a Cortex update.

---

## Architecture

```
Frontend                              Backend
┌──────────────────────┐              ┌────────────────────────┐
│ ChatInput.jsx        │              │ commands.py            │
│   └─ onInput('/')    │              │   POST /api/commands/  │
│      └─ SlashCommand │   HTTP POST  │     ├── rebuild-frontend│
│         Menu.jsx     │ ────────────→│     ├── reset-onboarding│
│         └─ command   │              │     └── cortex-update   │
│            Registry  │              └────────────────────────┘
└──────────────────────┘
```

---

## Frontend — Command Registry

**File:** `frontend/src/features/chat/slashCommands/commandRegistry.js`

Defines all available commands:

```javascript
export const commands = [
    {
        name: 'reload',
        description: 'Reload the application',
        icon: '🔄',
        action: () => window.location.reload(),
    },
    {
        name: 'rebuild',
        description: 'Rebuild the frontend',
        icon: '🏗️',
        action: async () => {
            await fetch('/api/commands/rebuild-frontend', { method: 'POST' });
        },
    },
    {
        name: 'onboarding',
        description: 'Reset and show onboarding wizard',
        icon: '🎓',
        action: async () => {
            await fetch('/api/commands/reset-onboarding', { method: 'POST' });
            window.location.href = '/onboarding';
        },
    },
    {
        name: 'cortex',
        description: 'Trigger a manual Cortex memory update',
        icon: '🧠',
        action: async () => {
            await fetch('/api/commands/cortex-update', { method: 'POST' });
        },
    },
];
```

### Built-In Commands

| Command | Icon | Action |
|---------|------|--------|
| `/reload` | 🔄 | Reloads the browser page |
| `/rebuild` | 🏗️ | Runs `build_frontend.bat` to rebuild React app |
| `/onboarding` | 🎓 | Resets onboarding and redirects to wizard |
| `/cortex` | 🧠 | Triggers immediate Cortex memory update |

---

## Frontend — Slash Command Menu

**File:** `frontend/src/features/chat/slashCommands/SlashCommandMenu.jsx`

### How It Works

1. User types `/` in the chat input
2. `ChatInput.jsx` detects the `/` prefix and renders `SlashCommandMenu`
3. The menu shows all matching commands (filtered by typed text)
4. User clicks a command or presses Enter
5. The command's `action()` function is executed
6. The input is cleared (command text is not sent as a chat message)

### UI

The menu appears as a floating dropdown above the chat input:

```
┌──────────────────────────┐
│ 🔄 /reload               │
│    Reload the application │
├──────────────────────────┤
│ 🏗️ /rebuild              │
│    Rebuild the frontend   │
├──────────────────────────┤
│ 🎓 /onboarding           │
│    Reset onboarding       │
├──────────────────────────┤
│ 🧠 /cortex               │
│    Manual Cortex update   │
└──────────────────────────┘
```

Features:
- **Fuzzy filtering** — Typing `/reb` matches `/rebuild`
- **Keyboard navigation** — Arrow keys + Enter
- **Auto-dismiss** — Menu closes when input loses focus or clears

---

## Backend — Command Handlers

**File:** `src/routes/commands.py` (~153 lines)

### `POST /api/commands/rebuild-frontend`

```python
@commands_bp.route('/api/commands/rebuild-frontend', methods=['POST'])
def rebuild_frontend():
    """Runs build_frontend.bat in a new console window."""
    bat_path = os.path.join(BASE_DIR, '..', 'bin', 'build_frontend.bat')
    subprocess.Popen(['cmd', '/c', 'start', bat_path], shell=True)
    return success_response(message='Frontend rebuild started')
```

Opens a new terminal window that runs the build script. The HTTP response returns immediately (non-blocking).

### `POST /api/commands/reset-onboarding`

```python
@commands_bp.route('/api/commands/reset-onboarding', methods=['POST'])
def reset_onboarding():
    """Resets onboarding.json so onboarding shows again."""
    onboarding_path = os.path.join(BASE_DIR, 'settings', 'onboarding.json')
    with open(onboarding_path, 'w') as f:
        json.dump({'completed': False}, f)
    return success_response(message='Onboarding reset')
```

### `POST /api/commands/cortex-update`

```python
@commands_bp.route('/api/commands/cortex-update', methods=['POST'])
def cortex_update():
    """Triggers an immediate Cortex update + resets the cycle counter."""
    persona_id = resolve_persona_id(session_id=request.json.get('session_id'))
    cortex_service = get_cortex_service()
    cortex_service.run_cortex_update(persona_id, session_id)
    # Reset cycle counter so next auto-update is fresh
    return success_response(message='Cortex update triggered')
```

---

## Adding New Commands

### 1. Register in Frontend

Add entry to `commandRegistry.js`:

```javascript
{
    name: 'mycommand',
    description: 'What it does',
    icon: '⚡',
    action: async () => {
        await fetch('/api/commands/my-command', { method: 'POST' });
    },
}
```

### 2. Add Backend Handler (if needed)

Add route to `src/routes/commands.py`:

```python
@commands_bp.route('/api/commands/my-command', methods=['POST'])
@handle_route_error('my-command')
def my_command():
    # Do something
    return success_response(message='Done')
```

### 3. Client-Only Commands

Commands that don't need backend interaction can be entirely client-side:

```javascript
{
    name: 'clear',
    description: 'Clear the input',
    icon: '🗑️',
    action: () => { /* client-side only */ },
}
```

---

## Related Documentation

- [04 — Routes & API](04_Routes_and_API.md) — Command endpoints
- [10 — Cortex Memory System](10_Cortex_Memory_System.md) — Cortex update triggered by `/cortex`
- [12 — Frontend React SPA](12_Frontend_React_SPA.md) — Chat page components
- [14 — Onboarding, Splash & Reset](14_Onboarding_Splash_and_Reset.md) — Onboarding triggered by `/onboarding`
