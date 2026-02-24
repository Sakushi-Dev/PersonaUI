# 12 — Frontend — React SPA

> React 19 single-page application with Vite, CSS Modules, context-based state, and feature-based architecture.

---

## Overview

PersonaUI's frontend is a **standalone React SPA** built with Vite. It replaces the legacy Jinja2/Vanilla JS frontend. In development, Vite serves the app on `:5173` with hot-reload; in production, Flask serves the built `frontend/dist/` assets.

### Stack

| Technology | Version | Purpose |
|-----------|---------|---------|
| React | 19 | UI framework |
| React Router | 7 | Client-side routing |
| Vite | 7 | Build tool + dev server |
| CSS Modules | — | Scoped component styles |
| CSS Variables | — | Theming (light/dark) |

**No additional dependencies** — no Redux, no Tailwind, no component library. The entire app runs on React, React Router, and React DOM only.

---

## Project Structure

```
frontend/
├── index.html              Entry HTML
├── package.json            Dependencies
├── vite.config.js          Vite configuration
├── eslint.config.js        Linting rules
├── public/
│   └── avatar/             Static avatar images
│       └── costum/         User-uploaded avatars
└── src/
    ├── main.jsx            React entry point
    ├── App.jsx             Root component + routing
    ├── components/         20 shared components
    ├── context/            5 React context providers
    ├── features/           Feature-based pages
    │   ├── chat/           Chat page + components
    │   ├── onboarding/     Onboarding wizard
    │   ├── overlays/       21 overlay panels
    │   └── waiting/        Waiting/access page
    ├── hooks/              8 custom hooks
    ├── services/           13 API service modules
    ├── styles/             Global CSS + themes
    ├── utils/              8 utility modules
    ├── data/               Static data (patch notes)
    └── locales/            i18n translations
```

---

## Entry Point & Routing

### `main.jsx`

```jsx
import { BrowserRouter } from 'react-router-dom';

// Global CSS layers (order matters)
import './styles/variables.css';
import './styles/themes/light.css';
import './styles/themes/dark.css';
import './styles/global.css';
import './styles/animations.css';
import './styles/responsive.css';

createRoot(document.getElementById('root')).render(
    <BrowserRouter>
        <App />
    </BrowserRouter>
);
```

### `App.jsx`

```jsx
// Lazy-loaded pages
const ChatPage = lazy(() => import('./features/chat/ChatPage'));
const OnboardingPage = lazy(() => import('./features/onboarding/OnboardingPage'));
const WaitingPage = lazy(() => import('./features/waiting/WaitingPage'));

function App() {
    // Check onboarding status on mount, redirect if incomplete
    
    return (
        <Routes>
            <Route path="/access/waiting" element={<WaitingPage />} />
            <Route path="/*" element={
                <AppProvider>
                    <Routes>
                        <Route path="/onboarding" element={<OnboardingPage />} />
                        <Route path="/" element={<ChatPage />} />
                    </Routes>
                </AppProvider>
            } />
        </Routes>
    );
}
```

**Key detail:** `WaitingPage` renders outside `AppProvider` because it doesn't need app context. This avoids loading settings/user data for unauthenticated devices.

---

## Context Providers

State management uses React Context (no Redux/Zustand):

### `AppProvider`

**File:** `frontend/src/context/AppProvider.jsx`

Wraps all other providers:

```jsx
<ThemeContext.Provider>
    <SettingsContext.Provider>
        <UserContext.Provider>
            <SessionContext.Provider>
                {children}
            </SessionContext.Provider>
        </UserContext.Provider>
    </SettingsContext.Provider>
</ThemeContext.Provider>
```

### Context Overview

| Context | File | Provides |
|---------|------|----------|
| **ThemeContext** | `ThemeContext.jsx` | `theme`, `setTheme`, CSS variable application |
| **SettingsContext** | `SettingsContext.jsx` | `settings`, `updateSetting`, `resetSettings` |
| **UserContext** | `UserContext.jsx` | `userProfile`, `updateProfile`, persona data |
| **SessionContext** | `SessionContext.jsx` | `sessions`, `activeSession`, `createSession`, `deleteSession`, message history |

### Usage Pattern

```jsx
import { useSettings } from '../hooks/useSettings';
import { useSession } from '../hooks/useSession';

function MyComponent() {
    const { settings } = useSettings();
    const { activeSession, sendMessage } = useSession();
    // ...
}
```

---

## Feature Pages

### Chat Page — `features/chat/`

The main interface. Contains the chat conversation, message input, and sidebar.

```
features/chat/
├── ChatPage.jsx              Main page component
├── ChatPage.module.css       Page-level styles
├── components/               Chat-specific components
│   ├── ChatMessages.jsx      Message list
│   ├── ChatInput.jsx         Input bar with slash commands
│   ├── ChatSidebar.jsx       Session list sidebar
│   ├── MessageBubble.jsx     Individual message display
│   └── ...
├── hooks/                    Chat-specific hooks
│   └── useChatStream.js      SSE streaming hook
└── slashCommands/            Slash command system
    ├── SlashCommandMenu.jsx  Command dropdown
    └── commandRegistry.js    Command definitions
```

### Onboarding Page — `features/onboarding/`

First-run wizard for setting up API key, user profile, and persona.

```
features/onboarding/
├── OnboardingPage.jsx
├── OnboardingPage.module.css
├── components/
└── steps/                    Individual wizard steps
```

### Overlays — `features/overlays/`

Modal/panel components accessible from the main chat page:

| Overlay | Purpose |
|---------|---------|
| `SettingsOverlay` | Theme, language, model, temperature |
| `ApiSettingsOverlay` | API key management |
| `PersonaOverlay` | Persona config editing |
| `PersonaListOverlay` | Persona switching |
| `CortexOverlay` | View/edit Cortex memory files |
| `SessionOverlay` | Session management |
| `AvatarOverlay` | Avatar selection/upload |
| `UserProfileOverlay` | User name, language |
| `AccessControlOverlay` | IP whitelist/blacklist |
| `DebugOverlay` | Debug information |
| `CustomSpecsOverlay` | Custom persona specs |
| `PatchNotesOverlay` | Version changelog |
| ... | *(21 overlays total)* |

### Waiting Page — `features/waiting/`

Shown to remote devices awaiting access approval.

---

## Shared Components

**Directory:** `frontend/src/components/` — 20 reusable components

| Component | Purpose |
|-----------|---------|
| `Avatar` | Avatar image display |
| `AvatarCropper` | Image crop interface for avatar upload |
| `Button` | Styled button |
| `ChipSelector` | Multi-select chip/tag picker |
| `CloseButton` | Overlay close button |
| `ColorPicker` | Color selection widget |
| `ConfirmDialog` | Confirmation modal |
| `Dropdown` | Select dropdown |
| `DynamicBackground` | Animated background effects |
| `ErrorBoundary` | React error boundary |
| `FormGroup` | Form field wrapper |
| `Icons` | SVG icon components |
| `InterfacePreview` | UI preview component |
| `Overlay` | Base overlay/modal component |
| `Slider` | Range slider |
| `Spinner` | Loading spinner |
| `StaticBackground` | Static background effects |
| `TagSelector` | Tag picker |
| `Toast` | Notification toast |
| `Toggle` | Toggle switch |

---

## Services — API Layer

**Directory:** `frontend/src/services/` — 13 modules

Each module wraps `fetch()` calls to the Flask backend:

| Service | API Prefix | Purpose |
|---------|-----------|---------|
| `apiClient.js` | — | Base fetch wrapper with error handling |
| `chatApi.js` | `/chat*` | Chat streaming, messages, afterthought |
| `sessionApi.js` | `/api/sessions/*` | Session CRUD |
| `personaApi.js` | `/api/personas/*`, `/get_char_config` | Persona management |
| `settingsApi.js` | `/api/user-settings*` | Settings CRUD |
| `userProfileApi.js` | `/api/user-profile*` | User profile |
| `avatarApi.js` | `/api/*avatar*` | Avatar upload/management |
| `cortexApi.js` | `/api/cortex/*` | Cortex files and settings |
| `accessApi.js` | `/api/access/*` | Access control |
| `onboardingApi.js` | `/api/onboarding/*` | Onboarding status |
| `customSpecsApi.js` | `/api/custom-specs/*` | Custom specs CRUD |
| `serverApi.js` | `/api/*server*` | Server settings |
| `emojiApi.js` | `/api/emoji-usage` | Emoji tracking |

### SSE Streaming

The `chatApi.js` module handles SSE streaming for chat:

```javascript
export function streamChat(message, sessionId, options) {
    return fetch('/chat_stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, session_id: sessionId, ...options })
    });
    // Returns ReadableStream, consumed by useChatStream hook
}
```

---

## Custom Hooks

**Directory:** `frontend/src/hooks/` — 8 hooks

| Hook | Purpose |
|------|---------|
| `useApi` | Generic API call wrapper with loading/error state |
| `useDebounce` | Debounced value for search/input |
| `useLanguage` | i18n language accessor |
| `useOverlay` | Overlay open/close state management |
| `usePolling` | Periodic API polling |
| `useSession` | Session context accessor |
| `useSettings` | Settings context accessor |
| `useTheme` | Theme context accessor |

---

## Styling

### CSS Architecture

```
styles/
├── variables.css    CSS custom properties (spacing, colors, typography)
├── global.css       Base styles, resets
├── animations.css   Keyframe animations
├── responsive.css   Breakpoint media queries
└── themes/
    ├── light.css    Light theme variable overrides
    └── dark.css     Dark theme variable overrides
```

### Theming

Themes work via CSS custom properties:

```css
/* variables.css */
:root {
    --bg-primary: #1a1a2e;
    --text-primary: #e0e0e0;
}

/* themes/light.css */
[data-theme="light"] {
    --bg-primary: #ffffff;
    --text-primary: #1a1a1a;
}
```

The `ThemeContext` applies `data-theme` to the document root.

### CSS Modules

Each component has its own `.module.css` file:

```jsx
import styles from './ChatPage.module.css';

function ChatPage() {
    return <div className={styles.container}>...</div>;
}
```

---

## Internationalization (i18n)

**Directory:** `frontend/src/locales/`

```
locales/
├── chat/          Chat page translations
├── common/        Shared translations
├── onboarding/    Onboarding translations
└── overlays/      Overlay translations
```

Each folder contains JSON files per language (e.g., `en.json`, `de.json`).

**Utility:** `frontend/src/utils/i18n.js` provides the `t()` translation function.

**Supported UI Languages:** English, German, and more (extensible).

---

## Vite Configuration

**File:** `frontend/vite.config.js`

```javascript
export default defineConfig({
    server: {
        host: '127.0.0.1',
        port: 5173,
        proxy: {
            '/api': 'http://localhost:5000',
            '/chat': 'http://localhost:5000',
            '/chat_stream': 'http://localhost:5000',
            '/afterthought': 'http://localhost:5000',
            '/clear_chat': 'http://localhost:5000',
            '/get_char_config': 'http://localhost:5000',
            '/save_char_config': 'http://localhost:5000',
            '/get_available_options': 'http://localhost:5000',
        }
    }
});
```

In dev mode, Vite proxies all API calls to Flask on `:5000`. In production, there's no proxy — Flask serves everything.

---

## Build & Deploy

```bash
# Development
cd frontend
npm run dev          # Vite dev server on :5173

# Production build
npm run build        # Output to frontend/dist/

# Flask serves frontend/dist/ in production
# See react_frontend.py blueprint
```

---

## Related Documentation

- [01 — App Core & Startup](01_App_Core_and_Startup.md) — Vite dev server startup
- [04 — Routes & API](04_Routes_and_API.md) — Backend endpoints consumed by services
- [05 — Chat System](05_Chat_System.md) — SSE streaming protocol
- [14 — Onboarding, Splash & Reset](14_Onboarding_Splash_and_Reset.md) — Onboarding page
- [16 — Slash Commands](16_Slash_Commands.md) — Command system in ChatInput
