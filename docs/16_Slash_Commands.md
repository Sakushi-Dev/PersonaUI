# 16 — Slash Command System

## Overview

PersonaUI includes a **slash command system** that enables users to execute special commands by typing `/command` in the chat input. Commands can perform frontend actions (like `/reload`) or trigger server-side operations (like `/rebuild`).

The system provides an intuitive auto-complete interface with keyboard and mouse navigation, similar to Discord or Slack.

---

## Architecture

```
Frontend Components:
  ChatInput.jsx              ← Main input with slash command detection
    ├── SlashCommandMenu.jsx ← Floating autocomplete popup
    └── slashCommands/
          ├── index.js        ← Main exports
          ├── slashCommandRegistry.js ← Command registry & filtering
          └── builtinCommands.js      ← Default commands (/reload, /rebuild)

Backend Support:
  routes/commands.py          ← API endpoints for server-side commands
    └── /api/commands/*       ← Individual command handlers
```

**Command Flow:**
```
User types "/" → Chat input detects → Shows command menu → User selects → Command executes
                    ↓
Frontend command = Direct execution
Server command = API call to /api/commands/*
```

---

## Frontend Implementation

### 1. Command Registry (`slashCommandRegistry.js`)

Central registry for all slash commands:

```javascript
// Register a new command
register({
  name: 'reload',
  description: 'Reload the page',
  execute({ args }) {
    window.location.reload();
  }
});

// Query available commands
const commands = getCommands('rel'); // Returns commands matching "rel"
const cmd = findCommand('reload');   // Find exact command
```

#### Registry API

| Function | Description |
|----------|-------------|
| `register(cmd)` | Add new command to registry |
| `getCommands(query?)` | Get all commands, optionally filtered |
| `findCommand(name)` | Find command by exact name |

#### Command Object Structure

```javascript
{
  name: string,        // Command keyword (without "/")
  description: string, // Short description for UI
  execute: function    // Handler function: ({ args: string }) => void
}
```

### 2. Built-in Commands (`builtinCommands.js`)

Default commands shipped with PersonaUI:

| Command | Description | Type |
|---------|-------------|------|
| `/reload` | Reload the browser page | Frontend |
| `/rebuild` | Trigger frontend build script | Backend API |

**Adding New Built-in Commands:**
```javascript
register({
  name: 'clear',
  description: 'Clear chat history',
  execute({ args }) {
    // Implementation here
  },
});
```

### 3. Chat Input Integration (`ChatInput.jsx`)

The main chat input component handles slash command detection and execution:

#### Key Features

- **Auto-detection**: Monitors input for leading `/` character
- **Live filtering**: Shows matching commands as user types
- **Keyboard navigation**: Arrow keys + Enter for selection
- **Mouse support**: Click to select commands
- **Seamless fallback**: Normal message sending if no command matches

#### State Management

```javascript
const [cmdMenuOpen, setCmdMenuOpen] = useState(false);
const [cmdSelectedIdx, setCmdSelectedIdx] = useState(0);

// Query extraction: "/reload server" → query = "reload"
const cmdQuery = useMemo(() => {
  if (!text.startsWith('/')) return null;
  return text.slice(1).split(' ')[0];
}, [text]);

// Filtered command list
const filteredCmds = useMemo(() => {
  if (cmdQuery === null) return [];
  return getCommands(cmdQuery);
}, [cmdQuery]);
```

#### Keyboard Controls

| Key | Action |
|-----|--------|
| `/` | Start command mode |
| `ArrowUp` / `ArrowDown` | Navigate command list |
| `Enter` | Execute selected command |
| `Escape` | Cancel command mode |
| `Tab` | Auto-complete command name |

### 4. Command Menu UI (`SlashCommandMenu.jsx`)

Floating popup that appears above the chat input:

#### Features

- **Auto-positioning**: Appears above input when commands are available
- **Visual feedback**: Highlighted selection with hover states
- **Scroll handling**: Selected item always visible
- **Mouse interaction**: Click to execute, hover to highlight

#### Props Interface

```javascript
<SlashCommandMenu
  commands={filteredCmds}     // Array of command objects
  selectedIndex={cmdSelectedIdx} // Currently highlighted index
  onSelect={selectCommand}    // (cmd) => void
  onHover={setCmdSelectedIdx} // (index) => void
  visible={cmdMenuOpen}       // Boolean
/>
```

---

## Backend Support (`routes/commands.py`)

Server-side commands that require backend processing get their own API endpoints.

### Current Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/commands/rebuild-frontend` | Trigger frontend build script |

### Example: Rebuild Frontend Command

```python
@commands_bp.route('/api/commands/rebuild-frontend', methods=['POST'])
@handle_route_error('rebuild_frontend')
def rebuild_frontend():
    """Start build_frontend.bat in separate console window."""
    
    if not os.path.isfile(_BUILD_SCRIPT):
        return error_response('Build script not found', 404)
    
    # Start as detached process with own console window
    subprocess.Popen([
        'cmd', '/c', 'start', 
        'PersonaUI - Frontend Build', 
        'cmd', '/c', _BUILD_SCRIPT
    ], cwd=_PROJECT_ROOT)
    
    return success_response(message='Build script started')
```

### Adding New Backend Commands

1. **Add route handler** in `commands.py`
2. **Register frontend command** that calls the API
3. **Handle errors** appropriately

```python
@commands_bp.route('/api/commands/my-command', methods=['POST'])
def my_command():
    # Server-side logic here
    return success_response(data={'result': 'success'})
```

```javascript
register({
  name: 'mycommand',
  description: 'Do something on server',
  async execute({ args }) {
    const response = await fetch('/api/commands/my-command', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ args })
    });
    const result = await response.json();
    console.log('Command result:', result);
  }
});
```

---

## Usage Examples

### Simple Frontend Command

```javascript
// Clear chat history
register({
  name: 'clear',
  description: 'Clear the current chat',
  execute() {
    // Clear messages from UI state
    messageManager.clearMessages();
    console.log('[SlashCommand] Chat cleared');
  }
});
```

### Command with Arguments

```javascript
// Set persona
register({
  name: 'persona',
  description: 'Switch to a different persona',
  execute({ args }) {
    const personaName = args.trim();
    if (!personaName) {
      alert('Usage: /persona <name>');
      return;
    }
    
    // Switch persona logic
    personaManager.switchTo(personaName);
  }
});
```

### Async Server Command

```javascript
// Deploy application
register({
  name: 'deploy',
  description: 'Deploy the application',
  async execute() {
    try {
      const response = await fetch('/api/commands/deploy', { 
        method: 'POST' 
      });
      const result = await response.json();
      
      if (result.success) {
        alert('Deployment started successfully');
      } else {
        alert(`Deployment failed: ${result.error}`);
      }
    } catch (error) {
      alert(`Network error: ${error.message}`);
    }
  }
});
```

---

## User Interface

### Command Discovery

- Type `/` in chat input to enter command mode
- Commands appear in floating menu above input
- Menu shows command name and description
- Live filtering as you type more characters

### Command Execution

- **Keyboard**: Navigate with arrows, press Enter to execute
- **Mouse**: Click on any command to execute
- **Auto-complete**: Tab key fills in command name
- **Arguments**: Continue typing after command name for arguments

### Visual States

- **Menu open**: Floating popup with command list
- **Command selected**: Highlighted background on selected item
- **No matches**: Menu disappears when no commands match
- **Executing**: Normal loading states for async commands

---

## File Structure

```
frontend/src/features/chat/
├── components/ChatInput/
│   ├── ChatInput.jsx           ← Main input with command support
│   ├── SlashCommandMenu.jsx    ← Command popup menu
│   └── *.module.css           ← Styling
└── slashCommands/
    ├── index.js               ← Main exports
    ├── slashCommandRegistry.js ← Registry system
    └── builtinCommands.js     ← Default commands

src/routes/
└── commands.py                ← Backend command handlers
```

---

## Extension Points

### Adding New Commands

1. **Frontend-only commands**: Add to `builtinCommands.js`
2. **Server commands**: Add route to `commands.py` + frontend caller
3. **Plugin system**: Import command modules in application startup

### Command Categories

Commands can be logically grouped:

```javascript
// Utility commands
register({ name: 'reload', category: 'utility', ... });
register({ name: 'clear', category: 'utility', ... });

// Developer commands  
register({ name: 'rebuild', category: 'dev', ... });
register({ name: 'deploy', category: 'dev', ... });

// Chat commands
register({ name: 'persona', category: 'chat', ... });
register({ name: 'mood', category: 'chat', ... });
```

### Advanced Features

- **Command aliases**: Multiple names for same command
- **Permission checks**: Restrict commands based on user role
- **Help system**: Auto-generated help from command metadata
- **Command history**: Track and suggest previously used commands

---

## Best Practices

### Command Design

- **Keep names short**: Easy to type and remember
- **Clear descriptions**: Help users discover functionality
- **Handle errors gracefully**: Show user-friendly error messages
- **Validate arguments**: Check required parameters before execution

### Implementation Guidelines

- **Async commands**: Use proper loading states and error handling
- **Resource cleanup**: Cancel ongoing operations when appropriate
- **User feedback**: Always indicate command execution status
- **Consistent naming**: Follow established conventions

### Performance Considerations

- **Lazy loading**: Only load commands when needed
- **Debounced filtering**: Avoid excessive filtering on rapid typing
- **Memory management**: Clean up command references appropriately

---

**📝 Document Version:** 1.0  
**Created:** 2026-02-20  
**Purpose:** Complete guide to PersonaUI's slash command system

> The slash command system makes PersonaUI more powerful and developer-friendly by providing quick access to application functions through an intuitive chat interface.