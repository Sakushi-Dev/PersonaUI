# 00 — Project Summary

> PersonaUI — A desktop AI companion app with deep persona customization, long-term memory, and a modern React interface.

---

## Overview

PersonaUI is a **desktop-first AI chat application** that wraps the Anthropic Claude API in a richly customizable persona system. Users create AI characters with distinct personalities, knowledge areas, expression styles, and emotional behaviors — then chat with them through a polished React SPA served inside a PyWebView desktop window.

The project prioritizes **immersion over utility**: personas feel like characters, not assistants. A long-term memory system (Cortex) allows the AI to remember, reflect, and evolve across conversations.

---

## Architecture at a Glance

```
┌──────────────────────────────────────────────────────────────────┐
│                        PyWebView Window                          │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                 React SPA (Vite + React 19)                │  │
│  │  ChatPage · Overlays · Onboarding · Settings · Cortex      │  │
│  └──────────────────────┬─────────────────────────────────────┘  │
│                         │ HTTP / SSE                             │
│  ┌──────────────────────▼─────────────────────────────────────┐  │
│  │              Flask Backend (Python 3.12+)                  │  │
│  │                                                            │  │
│  │  Routes (15 Blueprints)                                    │  │
│  │    ├── main · chat · sessions · commands · cortex          │  │
│  │    ├── character · settings · avatar · emoji               │  │
│  │    ├── api · access · onboarding · user_profile            │  │
│  │    └── custom_specs · react_frontend                       │  │
│  │                                                            │  │
│  │  Services                                                  │  │
│  │    ├── ChatService   (message assembly + streaming)        │  │
│  │    ├── ApiClient     (Anthropic SDK wrapper)               │  │
│  │    ├── CortexService (long-term memory via tool_use)       │  │
│  │    └── PromptEngine  (JSON prompt templates + placeholders)│  │
│  │                                                            │  │
│  │  Data Layer                                                │  │
│  │    ├── SQLite (per-persona databases)                      │  │
│  │    ├── JSON settings (11 config files)                     │  │
│  │    └── Cortex files (memory.md, soul.md, relationship.md)  │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Desktop Shell** | PyWebView 5 (native window on Windows/macOS/Linux) |
| **Frontend** | React 19 · React Router 7 · Vite 7 · CSS Modules |
| **Backend** | Flask 3 · Flask-CORS · Python 3.12+ |
| **AI Provider** | Anthropic Claude API (streaming + tool_use) |
| **Database** | SQLite (per-persona, named SQL queries) |
| **Prompt System** | JSON template engine with dual manifests + placeholder resolution |
| **Memory** | Cortex — file-based long-term memory (Markdown) |
| **Testing** | pytest · pytest-mock · ~162 tests |

---

## Key Design Decisions

### 1. Desktop-First, Not Web-First
PyWebView wraps the React SPA in a native window. No Electron. The `--no-gui` flag allows browser-only mode for development or headless use.

### 2. React SPA (Single-Page Application)
The frontend is a standalone React 19 app built with Vite. In development, Vite's dev server runs on `:5173` with proxy to Flask on `:5000`. In production, Flask serves the built `frontend/dist/` assets directly.

### 3. Per-Persona SQLite Databases
Each persona gets its own SQLite database (`main.db` for default, `persona_{id}.db` for others). This keeps chat histories, sessions, and messages fully isolated per persona.

### 4. JSON Prompt Engine (Not Hardcoded Strings)
All prompt templates live as JSON files in `src/instructions/prompts/`. A dual-manifest system (system + user) allows deep customization without modifying defaults. Placeholders like `{{char_name}}` resolve in three phases: static → computed → runtime.

### 5. Cortex — File-Based Long-Term Memory
Instead of vector databases, Cortex uses three Markdown files per persona (`memory.md`, `soul.md`, `relationship.md`). Updates happen via Claude's `tool_use` API, giving the AI itself direct control over what it remembers and reflects upon.

### 6. SSE Streaming
Chat responses stream token-by-token via Server-Sent Events (`text/event-stream`). The afterthought system can trigger autonomous follow-up messages after a configurable delay.

### 7. Service Locator (Provider Pattern)
`provider.py` manages singleton instances of `ApiClient`, `ChatService`, `CortexService`, and `PromptEngine`. All services are lazily initialized on first access.

### 8. Zero-Configuration Bootstrap
`init.py` handles everything: creates the Python virtual environment, installs pip dependencies, downloads Node.js 22 if missing, runs `npm install`, and launches the Flask app. Users just double-click `bin/start.bat`.

---

## Module Dependency Graph

```
init.py (bootstrap)
    └── app.py (Flask)
            ├── Routes (15 blueprints)
            │     ├── chat.py ──→ ChatService ──→ ApiClient
            │     │                    │              └── Anthropic SDK
            │     │                    ├── PromptEngine
            │     │                    └── CortexService
            │     ├── commands.py
            │     ├── cortex.py ──→ CortexService
            │     ├── character.py ──→ config.py
            │     ├── settings.py ──→ JSON files
            │     └── react_frontend.py ──→ frontend/dist/
            │
            ├── Utils
            │     ├── config.py (persona loading)
            │     ├── database/ (SQLite per-persona)
            │     ├── prompt_engine/ (JSON templates)
            │     ├── cortex_service.py + cortex/ (memory)
            │     ├── logger.py (rotating files)
            │     ├── access_control.py (IP whitelist)
            │     └── helpers.py, time_context.py, sql_loader.py
            │
            └── Frontend (React SPA)
                  ├── features/ (ChatPage, Onboarding, Overlays)
                  ├── components/ (20 shared components)
                  ├── services/ (13 API modules)
                  ├── hooks/ (8 custom hooks)
                  ├── context/ (5 React contexts)
                  └── styles/ (CSS variables + themes)
```

---

## Project Statistics

| Metric | Count |
|--------|-------|
| Python source files | ~60 |
| Flask blueprints | 15 |
| API endpoints | ~75 |
| Prompt template files | 32 (+32 defaults) |
| React components | ~50 (20 shared + ~30 feature) |
| Frontend services | 13 |
| Custom hooks | 8 |
| Context providers | 5 |
| SQL named queries | ~35 |
| Tests | ~162 |
| Supported languages | 10+ (i18n) |

---

## Documentation Index

| # | Document | Covers |
|---|----------|--------|
| **00** | Project Summary *(this file)* | Architecture, tech stack, design decisions |
| **01** | [App Core & Startup](01_App_Core_and_Startup.md) | Bootstrap chain, `init.py`, `app.py`, PyWebView |
| **02** | [Configuration & Settings](02_Configuration_and_Settings.md) | JSON settings, defaults, `.env`, config loading |
| **03** | [Utils & Helpers](03_Utils_and_Helpers.md) | Logger, provider, access control, SQL loader, helpers |
| **04** | [Routes & API](04_Routes_and_API.md) | All 15 blueprints, endpoint reference |
| **05** | [Chat System](05_Chat_System.md) | SSE streaming, afterthought, message assembly |
| **06** | [Prompt Engine](06_Prompt_Engine.md) | JSON templates, manifests, placeholder resolution |
| **08** | [Database Layer](08_Database_Layer.md) | Per-persona SQLite, schema, migrations, SQL loader |
| **09** | [Persona & Instructions](09_Persona_and_Instructions.md) | Persona spec, config, CRUD, AI autofill |
| **10** | [Cortex Memory System](10_Cortex_Memory_System.md) | Long-term memory, tool_use, tier system |
| **11** | [Services Layer](11_Services_Layer.md) | ApiClient, ChatService, CortexService, Provider |
| **12** | [Frontend — React SPA](12_Frontend_React_SPA.md) | React architecture, components, services, hooks |
| **13** | [Prompt Editor](13_Prompt_Editor.md) | Standalone editor app, CRUD, preview |
| **14** | [Onboarding, Splash & Reset](14_Onboarding_Splash_and_Reset.md) | First-run wizard, splash screen, factory reset |
| **15** | [Tests & Quality](15_Tests_and_Quality.md) | Test architecture, fixtures, coverage |
| **16** | [Slash Commands](16_Slash_Commands.md) | Command system, registry, built-in commands |

---

## Quick Start

```bash
# Clone and run (Windows)
git clone https://github.com/your-repo/PersonaUI.git
cd PersonaUI
bin\start.bat

# Or manually
python src/init.py          # Bootstraps everything, launches app
python src/app.py --dev     # Dev mode (Vite hot-reload on :5173)
python src/app.py --no-gui  # Browser-only mode (no PyWebView)
```

**Requirements:** Python 3.12+, Node.js 22+ (auto-downloaded if missing), Anthropic API key.
