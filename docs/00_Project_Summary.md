# 00 — Project Summary: PersonaUI

## What is PersonaUI?

PersonaUI is a **desktop chat application** for interacting with configurable AI personas. The app combines a local Python server (Flask) with a native desktop interface (PyWebView) and communicates with the Anthropic Claude API for AI responses.

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.10+, Flask ≥3.0 |
| Desktop | PyWebView 5.3.2 (native window) |
| AI API | Anthropic Claude (anthropic SDK ≥0.34) |
| Database | SQLite (isolated per persona) |
| Frontend | Vanilla ES6 JavaScript modules, Jinja2 templates |
| Styling | CSS Custom Properties, Glassmorphism, Dark Mode |
| Tests | pytest, ~162 tests |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│                  PyWebView                       │
│   ┌─────────┐  ┌──────────┐  ┌──────────────┐  │
│   │ Splash  │  │   Chat   │  │ Prompt Editor│  │
│   │ Screen  │  │  (Flask) │  │  (Standalone) │  │
│   └────┬────┘  └────┬─────┘  └──────┬───────┘  │
│        │            │               │           │
│   startup.py   Flask Routes    EditorApi        │
│        │            │               │           │
│        └────────────┼───────────────┘           │
│                     │                           │
│              ┌──────┴──────┐                    │
│              │  Services   │                    │
│              │ Chat│Memory │                    │
│              └──────┬──────┘                    │
│                     │                           │
│         ┌───────────┼───────────┐               │
│         │           │           │               │
│    PromptEngine  ApiClient  Database            │
│    (36 Prompts)  (Anthropic) (SQLite)           │
└─────────────────────────────────────────────────┘
```

---

## Core Features

### 1. Multi-Persona Chat
- Unlimited personas with individual personalities
- Per-persona isolated SQLite databases
- Personas defined via JSON specification (5 custom spec categories)
- AI autofill for persona attributes

### 2. Advanced Prompt System
- **36 domain files** with JSON-based prompt templates
- **3-phase placeholder resolution** (static → computed → runtime)
- **Dual manifest system**: System prompts (immutable) + User prompts (editable)
- **Variants**: Default vs. Experimental mode
- **Standalone visual Prompt Editor**

### 3. Afterthought System
- AI autonomously decides whether a follow-up is needed
- 10-second timer (cancelable)
- Separate AI call for inner dialogue
- Visually distinct afterthought message

### 4. Memory System
- AI-generated summaries of past conversations
- Manual/custom memories
- Marker-based tracking (which messages have already been summarized)
- Formatted memories as context for future conversations

### 5. Desktop Integration
- Native window (no browser)
- Splash screen with typewriter console
- 5-step onboarding wizard
- Factory reset via dedicated window
- QR code for network access

### 6. Server Modes
- **Normal**: Localhost-only access
- **Server**: LAN access with optional access control
- Whitelist/blacklist system

---

## Module Dependency Graph

```
init.py (Bootstrap)
  └── app.py (Flask App Factory)
        ├── 12 Blueprints (71 endpoints)
        ├── Provider (Service Locator)
        │     ├── ApiClient → Anthropic SDK
        │     ├── ChatService → ApiClient + PromptEngine
        │     └── MemoryService → ApiClient + PromptEngine
        ├── Config → JSON files (6 total)
        ├── Database → SQLite (per persona)
        ├── PromptEngine → JSON prompt files (36 total)
        ├── Logger → Rotating File Handler
        └── Helpers → Utilities
```

---

## Data Management

| Data Type | Location | Format |
|-----------|----------|--------|
| Settings | `src/settings/*.json` | JSON (6 files) |
| Persona Specs | `src/instructions/personas/` | JSON |
| Prompt Templates | `src/instructions/prompts/` | JSON (36 files) |
| Chat History | `src/data/{persona_id}/` | SQLite |
| Memories | `src/data/{persona_id}/` | SQLite |
| Sessions | `src/data/{persona_id}/` | SQLite |
| Avatars | `src/static/images/custom/` | JPEG |
| Logs | `src/logs/` | Rotating Text |

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| **PyWebView over Electron** | Lightweight, Python-native integration |
| **Per-Persona SQLite** | Complete data isolation, easy backup/deletion |
| **Service Locator (Provider)** | Avoids circular imports, centralized dependency management |
| **JSON instead of DB for prompts** | Version-controllable, manually editable, Git-friendly |
| **No build system (frontend)** | Simplicity, no toolchain dependencies |
| **Dual manifest system** | System prompts separate from user changes → safe updates |
| **SSE over WebSocket** | Simpler, one-way streaming sufficient for chat |
| **Vanilla JS Manager pattern** | Clear feature isolation without framework overhead |

---

## Documentation Index

| # | Document | Contents |
|---|----------|----------|
| 00 | **Project Summary** | This document — overview and architecture |
| 01 | [App Core & Startup](01_App_Core_and_Startup.md) | Bootstrap, PyWebView, Flask init, startup sequence |
| 02 | [Configuration & Settings](02_Configuration_and_Settings.md) | Config hierarchy, JSON files, defaults |
| 03 | [Utils & Helpers](03_Utils_and_Helpers.md) | Logger, provider, access control, SQL loader |
| 04 | [Routes & API](04_Routes_and_API.md) | 12 blueprints, 71 endpoints, REST conventions |
| 05 | [Chat System](05_Chat_System.md) | SSE streaming, afterthought, message assembly |
| 06 | [Prompt Engine](06_Prompt_Engine.md) | 1335-line engine, placeholders, validation |
| 07 | [Prompt Builder](07_Prompt_Builder.md) | Legacy bridge, facade pattern, variants |
| 08 | [Database Layer](08_Database_Layer.md) | Per-persona SQLite, schema, migrations |
| 09 | [Persona & Instructions](09_Persona_and_Instructions.md) | Specifications, custom specs, lifecycle |
| 10 | [Memory System](10_Memory_System.md) | Pipeline, markers, formatting |
| 11 | [Services Layer](11_Services_Layer.md) | ChatService, MemoryService, ApiClient |
| 12 | [Frontend & Templates](12_Frontend_and_Templates.md) | 12 JS managers, CSS, Jinja2 templates |
| 13 | [Prompt Editor](13_Prompt_Editor.md) | Standalone editor, EditorApi, compositor |
| 14 | [Onboarding, Splash & Reset](14_Onboarding_Splash_and_Reset.md) | Lifecycle screens |
| 15 | [Tests & Quality](15_Tests_and_Quality.md) | 162 tests, fixtures, architecture enforcement |

---

## Project Statistics

| Metric | Value |
|--------|-------|
| Python files | ~60 |
| JavaScript modules | ~25 |
| CSS files | 5 |
| Jinja2 templates | ~30 |
| JSON configurations | ~45 |
| SQL files | 5 |
| Flask blueprints | 12 |
| API endpoints | 71 |
| Prompt templates | 36 |
| Tests | ~162 |
| Test fixtures | 15 |
