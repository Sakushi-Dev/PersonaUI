# 12 — Frontend & Templates

## Overview

PersonaUI uses **Vanilla ES6 JavaScript modules**, Jinja2 templates, and CSS Custom Properties. No build system, no bundler — all JS files are loaded directly as ES6 modules.

---

## Architecture

```
src/templates/
  ├── chat.html          ← Main shell
  ├── onboarding.html    ← First-time setup
  ├── waiting.html       ← Access control
  ├── chat/              ← 18 partial templates
  └── onboarding/        ← 6 partial templates

src/static/
  ├── js/
  │     ├── chat.js      ← Main entry point (ChatApp)
  │     ├── onboarding.js ← Onboarding logic
  │     └── modules/     ← 12 manager modules
  ├── css/
  │     ├── chat.css     ← 6301-line main stylesheet
  │     ├── onboarding.css ← 1415 lines
  │     └── responsive.css ← ~100 lines
  └── images/
        ├── avatars/     ← 12 pre-made JPEG avatars
        └── custom/      ← User-uploaded avatars
```

---

## JavaScript Manager Architecture

### Entry Point: `chat.js` — ChatApp (754 Lines)

The `ChatApp` orchestrator creates and wires 12 managers:

```javascript
class ChatApp {
    constructor() {
        this.dom = new DOMManager();
        this.userSettings = new UserSettings();
        this.messageManager = new MessageManager(this);
        this.sessionManager = new SessionManager(this);
        this.settingsManager = new SettingsManager(this);
        this.avatarManager = new AvatarManager(this);
        this.memoryManager = new MemoryManager(this);
        this.qrCodeManager = new QRCodeManager(this);
        this.customSpecsManager = new CustomSpecsManager(this);
        this.accessControlManager = new AccessControlManager(this);
        this.userProfileManager = new UserProfileManager(this);
        this.debugPanel = new DebugPanel(this);
    }
}
```

### Manager Modules

| Module | Lines | Responsibility |
|--------|-------|----------------|
| **DOMManager** | 100 | DOM reference cache, centralizes all `getElementById` |
| **MessageManager** | 1471 | Chat messages, SSE streaming, afterthought timer, sound, token info |
| **SessionManager** | 638 | Sidebar navigation (messenger contacts), session CRUD, persona list, date formatting, soft reload |
| **SettingsManager** | 1949 | Persona CRUD with edit mode, API key, interface, API settings, server settings |
| **AvatarManager** | 575 | Gallery, upload, canvas-based crop with drag/zoom |
| **MemoryManager** | 733 | Memory button states, preview, CRUD, bubble marking |
| **UserSettings** | 155 | Server-synchronized settings (singleton, debounced) |
| **UserProfileManager** | 290 | Profile CRUD, live DOM updates |
| **QRCodeManager** | 160 | QR code generation, IP display |
| **CustomSpecsManager** | 501 | 5-category CRUD, AI autofill |
| **AccessControlManager** | 340 | Polling (3s), notifications, whitelist/blacklist |
| **DebugPanel** | 165 | Developer test tools |

---

## Chat Templates

### `chat.html` — Main Shell

- Loads CSS, dynamic background blobs
- Passes server state to JS via `window.*` globals:
  - `currentSessionId`, `activePersonaId`, `totalMessageCount`
  - `characterAvatar`, `userProfile`, `lastMemoryMessageId`
- Loads `chat.js` as ES6 module
- Dark mode IIFE prevents FOUC (Flash of Unstyled Content)
- Global `showNotification()` toast system

### Chat Partials (`templates/chat/`)

| Partial | Description |
|---------|-------------|
| `_header.html` | Avatar, character name, memory button, sound toggle, settings dropdown |
| `_sidebar.html` | Two-level navigation: personas (messenger contacts) → sessions (chat history) |
| `_chat_messages.html` | Message history with Jinja2 loop |
| `_chat_input.html` | Auto-resizing textarea + send button |
| `_loading.html` | Three-dot bounce spinner |
| `_overlay_persona_settings.html` | Persona contact list + creator/editor |
| `_overlay_interface_settings.html` | Live preview with colors/fonts |
| `_overlay_api_key.html` | API key input with test/save |
| `_overlay_api_settings.html` | Model, temperature, context limit |
| `_overlay_avatar_editor.html` | Gallery + upload + canvas crop |
| `_overlay_memory.html` | Create + manage memories |
| `_overlay_qr_code.html` | QR code + IP addresses |
| `_overlay_server_settings.html` | Server mode, access control |
| `_overlay_access_control.html` | Pending/whitelist/blacklist |
| `_overlay_user_profile.html` | Edit user profile |
| `_overlay_custom_specs.html` | Custom specs with 5 categories |
| `_overlay_debug.html` | Developer debug panel |
| `_overlay_credit_exhausted.html` | API credits exhausted |
| `_overlay_api_warning.html` | No API key configured |

---

## CSS Architecture

### Main Stylesheet (`chat.css` — 6301 Lines)

**Design System:**
- CSS Custom Properties for theming (`--overlay-*` variables)
- Glassmorphism: `backdrop-filter: blur(25px)` + semi-transparent backgrounds
- Dark mode: Dual approach with `body.dark-mode` + `html.dark-mode-early` (FOUC prevention)
- Dynamic background: Animated gradient blobs (`@keyframes blob-float-*`)

**Key Features:**
- Chat messages: User right-aligned (row-reverse), bot left-aligned
- `.non_verbal` spans with `--nonverbal-color`
- `.memorized` class: Blue border + "in-memory" label
- Code blocks: Dark background, green text (`#6ff700`)
- Sidebar: Messenger-style contact list with online indicator, avatars, last activity
- Session list: Date-based (no AI-generated titles), with creation and modification dates
- Persona overlay: Contact-list style instead of card grid, with inline edit/delete buttons
- Toast system: Type-colored notifications (info/success/warning/error)

### Per-Mode Color Storage

Light and dark modes store independent color schemes:
```javascript
backgroundColor_light: "#a3baff"
backgroundColor_dark: "#1a2332"
colorGradient1_light: "#66cfff"
colorGradient1_dark: "#2a3f5f"
```

### Responsive Design (`responsive.css`)

Breakpoint at 768px:
- Sidebar hidden
- Header layout adjusted (name hidden)
- Message bubble max-width reduced
- Persona grid collapsed to single column

---

## Backend Communication

### SSE Streaming

```javascript
// MessageManager.js
const response = await fetch('/chat_stream', { method: 'POST', body: ... });
const reader = response.body.getReader();
// Processes "data: {json}\n\n" events
```

Event types: `chunk`, `done`, `error`

### REST CRUD

All entity operations via standard `fetch()` with JSON payloads.

### Debounced Settings

`UserSettings.set()` debounces server writes by 300ms.

### Polling

- Access control: every 3s (list mode)
- Waiting page: every 2s

### Server Restart

`saveServerSettings()` includes a 30-second health-check loop that polls `/api/check_api_status`.

---

## Notable Patterns

1. **No build system**: Vanilla ES6 modules loaded directly
2. **Manager pattern**: Each feature area as a dedicated manager class
3. **Clone-to-remove-listeners**: `element.cloneNode(true)` + `replaceChild` for event listener cleanup
4. **Live DOM updates**: Profile changes update all user messages without page reload
5. **Soft reload**: Session and persona switching updates header, chat bubbles, URL, and global state in-place without full page reload. `SessionManager` receives `messageManager` and `memoryManager` references for cross-manager coordination
6. **Web Audio API**: Notification sound generated programmatically (D5 587Hz + G5 784Hz)
7. **FOUC prevention**: Dark mode loaded in `<head>` before body renders
8. **German UI language**: All user-facing text in German, no i18n system
9. **Canvas-based crop**: Drag, zoom (mouse wheel + touch pinch), preview circle

---

## Dependencies

```
chat.js (Orchestrator)
  ├── DOMManager (DOM cache)
  ├── UserSettings (settings sync)
  ├── MessageManager → /chat_stream, /afterthought (SSE)
  ├── SessionManager → /api/sessions/* (REST)
  ├── SettingsManager → /api/*, /get_*, /save_* (REST)
  ├── AvatarManager → /api/upload_avatar, /api/save_avatar
  ├── MemoryManager → /api/memory/* (REST)
  ├── QRCodeManager → /api/generate_qr_code
  ├── CustomSpecsManager → /api/custom-specs/*
  ├── AccessControlManager → /api/access/*
  ├── UserProfileManager → /api/user-profile/*
  └── DebugPanel → Various debug endpoints
```
