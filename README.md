<p align="center">
  <img src="media/personaui_loadingscreen.webp" alt="PersonaUI" width="100%">
</p>

<h1 align="center">PersonaUI</h1>

<p align="center">
  <strong>Where AI becomes human — one conversation at a time.</strong><br>
  A desktop application for creating AI companions with distinct personalities, emotional depth, and persistent memory.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue?style=flat-square&logo=python&logoColor=white" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/anthropic-Claude_API-blueviolet?style=flat-square" alt="Claude API">
  <img src="https://img.shields.io/badge/desktop-PyWebView-green?style=flat-square" alt="PyWebView">
  <img src="https://img.shields.io/badge/frontend-React_19_%2B_Vite-61DAFB?style=flat-square&logo=react&logoColor=white" alt="React 19 + Vite">
  <img src="https://img.shields.io/badge/i18n-EN_%7C_DE-orange?style=flat-square" alt="i18n: EN | DE">
  <img src="https://img.shields.io/badge/license-AGPL--3.0-red?style=flat-square" alt="AGPL-3.0">
</p>

---

## What Is PersonaUI?

PersonaUI is a local desktop application that lets you create and talk to AI characters — called *Personas*. Unlike typical chatbots, these personas remember previous conversations, develop their own emotional states, and grow over time. Every persona stores its data exclusively on your computer. Nothing is sent to external servers beyond the AI model requests themselves.

The application runs as a native desktop window (via PyWebView) with a modern React frontend. It connects to Anthropic's Claude API for generating responses, while all conversation data, memories, and settings remain local.

---

## Installation

There are two ways to get PersonaUI running on your machine: a one-click installer for Windows, or a manual setup for developers and Linux/macOS users.

### Prerequisites

- **An Anthropic API key** — You can create one at [console.anthropic.com](https://console.anthropic.com/). The onboarding wizard will ask for it on first launch.
- **Git** (optional) — Needed if you want to clone the repository. You can also download the project as a ZIP file directly from GitHub.

Python is required to run the application, but on Windows PersonaUI can install it for you automatically (see Option A below).

### Step 1 — Get the Project

There are two ways to download the project files onto your computer:

**With Git** (recommended if you want easy updates later):

1. Press `Win + R`, type `cmd`, and hit Enter. This opens the Windows command prompt.
2. Check if Git is installed by typing:
   ```
   git --version
   ```
   If you see a version number (e.g. `git version 2.43.0`), Git is ready. If you get an error like *'git' is not recognized*, install Git first:
   - Go to [git-scm.com/downloads](https://git-scm.com/downloads) and download the Windows installer.
   - Run the installer. You can keep all default settings — just click **Next** until the installation finishes.
   - Close the command prompt and open a new one (`Win + R` → `cmd` → Enter), so that the new Git installation is recognized.
3. Navigate to the folder where you want the project to live. For example, to put it on your Desktop:
   ```
   cd %USERPROFILE%\Desktop
   ```
4. Download the project:
   ```
   git clone https://github.com/Sakushi-Dev/PersonaUI.git
   ```
   This creates a new folder called `PersonaUI` containing all project files.

**Without Git**: Go to [github.com/Sakushi-Dev/PersonaUI](https://github.com/Sakushi-Dev/PersonaUI), click the green **Code** button, select **Download ZIP**, and extract the archive to a folder of your choice.

### Step 2 — Start the Application

#### Option A: Windows — Double-click to start

The project includes a **`PersonaUI.exe`** in the project root (or `bin/start.bat` as the equivalent batch file). This is not a traditional installer — it is a lightweight batch script converted to an EXE using *Bat To Exe Converter*. When you run it, the script:

1. Looks for an existing Python installation (virtual environment, system Python, or `py` launcher).
2. If no Python is found, it automatically downloads and installs **Python 3.12** for you.
3. Creates a virtual environment (`.venv`) and installs all pip dependencies.
4. Downloads Node.js v22 if it is not present and installs the frontend npm packages.
5. Builds the React frontend and launches the application.

You can also run `bin/start.bat` directly — it behaves identically.

Additional scripts in `bin/`: `update.bat` (pulls the latest version via Git), `reset.bat` (factory reset with confirmation dialog), `prompt_editor.bat` (launches the standalone prompt editor).

#### Option B: Manual Setup (All Platforms)

If you prefer full control, or you are on Linux/macOS:

```bash
cd PersonaUI
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
python src/init.py
```

The init script takes care of everything from here: downloading Node.js if needed, installing npm packages, building the frontend, and starting the app.

### Launch Options

You can customize startup behavior by editing `launch_options.txt` in the project root:

| Option | Effect |
|--------|--------|
| `--no-gui` | Runs without the desktop window. The app becomes accessible in your browser at `http://localhost:PORT`. |
| `--dev` | Starts the Vite development server for live frontend changes at `http://localhost:5173`. |

---

## What Makes PersonaUI Different

### The Cortex — Persistent, Evolving Memory

Most AI chatbots forget everything once the conversation ends. PersonaUI takes a fundamentally different approach with its **Cortex system**. Each persona maintains three files that represent its inner world:

- **Memory** — Concrete recollections of past conversations, events, and shared moments
- **Soul** — The persona's evolving self-understanding, values, and personal growth
- **Relationship** — How the persona perceives and relates to you over time

These files are written in Markdown, from the persona's own perspective. The AI updates them autonomously using Anthropic's tool-use feature whenever the conversation reaches configurable context thresholds (for example at 50 %, 75 %, or 95 % of the context limit). You can view and edit all three files at any time through the in-app Cortex Overlay.

### Emotional Continuity

Personas don't just respond neutrally. Their mood shifts naturally during a conversation — they can become excited, concerned, playful, or frustrated — and these emotional states carry over across messages, just as they would in a real interaction.

### Afterthoughts

Sometimes, after sending a response, the AI decides it has something to add. After a short pause it sends a follow-up message on its own, without any input from you. This small detail makes conversations feel noticeably more natural.

### Complete Privacy

All data — conversations, memories, settings, avatars — lives exclusively on your machine. Each persona has its own isolated SQLite database. Nothing is stored in the cloud, and no data leaves your computer except for the API requests to Anthropic.

---

## Features

| Feature | Description |
|---------|-------------|
| **Cortex Memory System** | Three-file memory architecture (Memory, Soul, Relationship), updated autonomously via tool use |
| **Afterthought System** | The AI independently decides whether to send a follow-up message (10-second timer, cancelable) |
| **8-Step Onboarding** | Guided first-launch setup: profile, API key, context settings, Cortex config, UI preferences |
| **Slash Commands** | Type `/` in the chat to access commands with autocomplete — extensible for both frontend and backend |
| **36 Prompt Templates** | JSON-based personality templates with three-phase placeholder resolution |
| **Prompt Editor** | A standalone visual tool for inspecting and editing how prompt components combine |
| **19 Overlay Dialogs** | In-app panels for API settings, Cortex editing, avatar management, persona configuration, and more |
| **Custom Specifications** | Five specification categories to fine-tune persona behavior beyond the defaults |
| **Network Sharing** | Share access over your local network with IP-based access control and QR code for mobile devices |
| **Internationalization** | Full i18n support — currently available in English and German |

---

## Creating a Persona

Each persona is defined by a set of properties you choose during creation:

- **Species** — Human, Transcendent Being, Elf, Robot, Alien, or Demon
- **Personality** — Friendly, protective, curious, spontaneous, wise, mysterious, or custom combinations
- **Expression style** — Normal speech, expressive *actions*, or casual modern texting
- **Knowledge areas** — Cooking, gaming, art, science, philosophy, or anything you define
- **Scenario** — The setting in which your conversations take place

Every persona operates in its own isolated environment with dedicated Cortex files, chat history, and emotional state — completely independent from your other personas.

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **AI Engine** | Anthropic Claude (SDK 0.34+) | Response generation with tool-use support |
| **Backend** | Python 3.10+ with Flask 3.0+ | Application server and API |
| **Desktop** | PyWebView 5.x | Native desktop window without Electron overhead |
| **Frontend** | React 19, Vite 7, React Router 7 | Single-page application with hot module replacement |
| **Storage** | SQLite (one database per persona) | Local-only storage, easy to back up or delete |
| **Streaming** | Server-Sent Events (SSE) | Real-time message streaming from the AI |
| **Localization** | Custom `useLanguage` hook | Feature-scoped locale files for EN and DE |

---

## Architecture

```
+-------------------------------------------------------+
|                      PyWebView                        |
|                                                       |
|  +-----------+  +------------+  +-----------------+   |
|  |  Splash   |  |    Chat    |  |  Prompt Editor  |   |
|  |  Screen   |  |   (React)  |  |  (Standalone)   |   |
|  +-----+-----+  +-----+------+  +-------+---------+   |
|        |              |                  |            |
|   startup.py    Flask Routes        EditorApi         |
|        |              |                  |            |
|        +--------------+------------------+            |
|                       |                               |
|              +--------+--------+                      |
|              |    Services     |                      |
|              | Chat - Cortex   |                      |
|              +--------+--------+                      |
|                       |                               |
|         +-------------+-------------+                 |
|         |             |             |                 |
|    PromptEngine   ApiClient    Database               |
|    (36 Templates) (Anthropic)  (SQLite)               |
+-------------------------------------------------------+
```

**Backend** — 16 Flask blueprints: access, api, avatar, character, chat, commands, cortex, custom_specs, emoji, helpers, main, onboarding, react_frontend, sessions, settings, user_profile.

**Frontend** — A React 19 single-page application with three pages (Chat, Onboarding, Waiting), 20 reusable UI components, 19 overlay dialogs, 5 context providers, and 13 API service modules. Includes a slash command system with autocomplete and keyboard navigation.

---

## Documentation

The [`docs/`](docs/) directory contains detailed guides for every part of the system:

<details>
<summary>Complete Documentation Index</summary>

| # | Document | Focus Area |
|---|----------|------------|
| 00 | [Project Summary](docs/00_Project_Summary.md) | Architecture, philosophy, design decisions |
| 01 | [App Core & Startup](docs/01_App_Core_and_Startup.md) | Bootstrap process, PyWebView, init sequence |
| 02 | [Configuration & Settings](docs/02_Configuration_and_Settings.md) | Settings hierarchy, JSON files, defaults |
| 03 | [Utils & Helpers](docs/03_Utils_and_Helpers.md) | Logger, provider, access control, SQL loader |
| 04 | [Routes & API](docs/04_Routes_and_API.md) | 16 blueprints, REST endpoints |
| 05 | [Chat System](docs/05_Chat_System.md) | SSE streaming, afterthought system |
| 06 | [Prompt Engine](docs/06_Prompt_Engine.md) | Placeholder resolution, validation |
| 07 | [Prompt Builder](docs/07_Prompt_Builder.md) | Facade pattern, variants |
| 08 | [Database Layer](docs/08_Database_Layer.md) | Per-persona SQLite, schema, migrations |
| 09 | [Persona & Instructions](docs/09_Persona_and_Instructions.md) | Specifications, custom specs, lifecycle |
| 11 | [Services Layer](docs/11_Services_Layer.md) | ChatService, CortexService, ApiClient |
| 12 | [Frontend & Templates](docs/12_Frontend_and_Templates.md) | React SPA, components, Jinja2 templates |
| 13 | [Prompt Editor](docs/13_Prompt_Editor.md) | Standalone editor, EditorApi |
| 14 | [Onboarding, Splash & Reset](docs/14_Onboarding_Splash_and_Reset.md) | Lifecycle screens |
| 15 | [Tests & Quality](docs/15_Tests_and_Quality.md) | Test strategy, reliability |
| 16 | [Slash Commands](docs/16_Slash_Commands.md) | Command system with autocomplete |

</details>

---

## Contributing

Contributions are welcome. The `dev` branch is the main working branch for new features and improvements.

- The documentation covers the full codebase, making it straightforward to get oriented.
- Automated tests protect against regressions.
- Current priorities: Cortex system refinement, React frontend polish, additional language support, performance optimization for large conversation histories.

---

## License

PersonaUI is licensed under the **GNU Affero General Public License v3.0** (AGPL-3.0).

---

<p align="center">
  <em>Built by</em>
  <a href="https://github.com/Sakushi-Dev">Sakushi-Dev</a>
</p>

<p align="center">
  <sub>
    <em>If PersonaUI is useful to you, consider giving the project a star on GitHub.</em>
  </sub>
</p>