<p align="center">
  <img src=".github/docs/media/personaui_loadingscreen.webp" alt="PersonaUI" width="100%">
</p>

<h1 align="center">PersonaUI</h1>

<p align="center">
  <strong>Where AI becomes human — one conversation at a time.</strong><br>
  A desktop application for creating AI companions with distinct personalities, emotional depth, and persistent memory.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.12+-blue?style=flat-square&logo=python&logoColor=white" alt="Python 3.12+">
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

You can customize startup behavior by editing `config/launch_options.txt`:

| Option | Effect |
|--------|--------|
| `--no-gui` | Runs without the desktop window. The app becomes accessible in your browser at `http://localhost:PORT`. |
| `--dev` | Starts the Vite development server for live frontend changes at `http://localhost:5173`. |

---

## What Makes PersonaUI Different


<p align="center"><strong>The Cortex — Persistent, Evolving Memory</strong></p>

<div align="center">
<table>
<tr>
<td width="300">
<img src="https://iili.io/qKrHYFI.png" alt="Cortex system" width="300">
</td>
<td>

Most AI chatbots forget everything once the conversation ends. PersonaUI gives each persona three files that represent its inner world:

- **Memory** — Recollections of past conversations and shared moments  
- **Soul** — Evolving self-understanding, values, and personal growth  
- **Relationship** — How the persona perceives and relates to you over time  

Written from the persona's own perspective and updated autonomously via tool use at configurable context thresholds (50 %, 75 %, 95 %). Viewable and editable through the in-app Cortex Overlay.

</td>
</tr>
</table>
</div>

<p align="center"><strong>Afterthoughts and Emotional Continuity</strong></p>

<div align="center">
<table>
<tr>
<td>

After sending a response, the AI may decide it has something to add — a follow-up message sent on its own, without any input from you.

- Independent follow-up messages with a 10-second timer, cancelable at any time
- Mood shifts naturally during conversation — excitement, concern, playfulness, frustration
- Emotional states carry over across messages, just as in a real interaction
- Makes conversations feel noticeably more human

</td>
<td width="300">
<img src="https://iili.io/qKrHEwG.png" alt="Afterthought system" width="300">
</td>
</tr>
</table>
</div>

<p align="center"><strong>Creating a Persona</strong></p>

<div align="center">
<table>
<tr>
<td width="300">
<img src="https://iili.io/qKrHGtf.png" alt="Creating a persona" width="300">
</td>
<td>

Each persona is defined by a set of properties you choose during creation:

- **Species** — Human, Transcendent Being, Elf, Robot, Alien, or Demon
- **Personality** — Friendly, protective, curious, wise, mysterious, or custom combinations
- **Expression style** — Normal speech, expressive actions, or casual texting
- **Knowledge areas** — Cooking, gaming, art, science, philosophy, or anything you define
- **Scenario** — The setting in which conversations take place

Every persona operates in its own isolated environment with dedicated Cortex files, chat history, and emotional state.

</td>
</tr>
</table>
</div>

<p align="center"><strong>Network Sharing and Privacy</strong></p>

<div align="center">
<table>
<tr>
<td>

All data lives exclusively on your machine — nothing is stored in the cloud. Despite full local privacy, you can still share access over your local network:

- IP-based access control with whitelist and blacklist
- QR code for quick mobile device connection
- Per-persona SQLite databases, easy to back up or delete
- No data leaves your computer except the API requests to Anthropic

</td>
<td width="300">
<img src="https://iili.io/qKrHc8X.png" alt="Network sharing" width="300">
</td>
</tr>
</table>
</div>

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

## Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **AI Engine** | Anthropic Claude (SDK 0.34+) | Response generation with tool-use support |
| **Backend** | Python 3.12+ with Flask 3.0+ | Application server and API |
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

**Backend** — 15 Flask blueprints: access, api, avatar, character, chat, commands, cortex, custom_specs, emoji, main, onboarding, react_frontend, sessions, settings, user_profile (~84 REST endpoints).

**Frontend** — A React 19 single-page application with three pages (Chat, Onboarding, Waiting), 20 reusable UI components, 21 overlay dialogs, 5 context providers, 8 custom hooks, and 13 API service modules. Includes a slash command system with autocomplete and keyboard navigation.

---

## Documentation

The [`.github/docs/`](.github/docs/) directory contains detailed guides for every part of the system:

<details>
<summary>Complete Documentation Index</summary>

| # | Document | Focus Area |
|---|----------|------------|
| 00 | [Project Summary](.github/docs/00_Project_Summary.md) | Architecture, tech stack, design decisions |
| 01 | [App Core & Startup](.github/docs/01_App_Core_and_Startup.md) | Bootstrap chain, `init.py`, `app.py`, PyWebView |
| 02 | [Configuration & Settings](.github/docs/02_Configuration_and_Settings.md) | JSON settings, defaults, `.env`, config loading |
| 03 | [Utils & Helpers](.github/docs/03_Utils_and_Helpers.md) | Logger, provider, access control, SQL loader, helpers |
| 04 | [Routes & API](.github/docs/04_Routes_and_API.md) | 15 blueprints, ~84 REST endpoints |
| 05 | [Chat System](.github/docs/05_Chat_System.md) | SSE streaming, afterthought, message assembly |
| 06 | [Prompt Engine](.github/docs/06_Prompt_Engine.md) | JSON templates, manifests, placeholder resolution |
| 07 | [Prompt Builder](.github/docs/07_Prompt_Builder.md) | Legacy builder, engine delegation |
| 08 | [Database Layer](.github/docs/08_Database_Layer.md) | Per-persona SQLite, schema, migrations, SQL loader |
| 09 | [Persona & Instructions](.github/docs/09_Persona_and_Instructions.md) | Persona spec, config, CRUD, AI autofill |
| 10 | [Cortex Memory System](.github/docs/10_Cortex_Memory_System.md) | Long-term memory, tool_use, tier system |
| 11 | [Services Layer](.github/docs/11_Services_Layer.md) | ApiClient, ChatService, CortexService, Provider |
| 12 | [Frontend — React SPA](.github/docs/12_Frontend_React_SPA.md) | React architecture, components, services, hooks |
| 13 | [Prompt Editor](.github/docs/13_Prompt_Editor.md) | Standalone editor app, CRUD, preview |
| 14 | [Onboarding, Splash & Reset](.github/docs/14_Onboarding_Splash_and_Reset.md) | First-run wizard, splash screen, factory reset |
| 15 | [Tests & Quality](.github/docs/15_Tests_and_Quality.md) | Test architecture, fixtures, coverage |
| 16 | [Slash Commands](.github/docs/16_Slash_Commands.md) | Command system, registry, built-in commands |

</details>

---

## Troubleshooting

<details>
<summary><strong>Application won't start / Python not found</strong></summary>

- Make sure **Python 3.12+** is installed and added to your `PATH`. Verify with `python --version` in a terminal.
- On Windows, the `start.bat` / `PersonaUI.exe` script tries to detect Python automatically. If it fails, install Python manually from [python.org](https://www.python.org/downloads/) and check **"Add Python to PATH"** during installation.
- If you use a virtual environment, make sure it is activated before running any commands:
  ```
  # Windows
  .venv\Scripts\activate

  # Linux / macOS
  source .venv/bin/activate
  ```

</details>

<details>
<summary><strong>Blank window / PyWebView doesn't render</strong></summary>

- PyWebView relies on the system's WebView2 runtime on Windows. If you see a blank or white window, install the [Microsoft Edge WebView2 Runtime](https://developer.microsoft.com/en-us/microsoft-edge/webview2/).
- Make sure the frontend was built successfully. Check that the `frontend/dist/` folder exists and contains files. If not, rebuild it:
  ```
  cd frontend
  npm install
  npm run build
  ```
- Try launching with `--no-gui` in `config/launch_options.txt` to open the app in your browser instead. This helps isolate whether the issue is PyWebView or the app itself.

</details>

<details>
<summary><strong>Window opens off-screen or at wrong position</strong></summary>

- After changing your monitor setup (disconnecting a display, changing resolution), the app window may open off-screen because it restores the last saved position.
- **Fix:** Delete `src/settings/window_settings.json` and restart PersonaUI. The window will open centered with default dimensions.

</details>

<details>
<summary><strong>API key errors / "Authentication failed"</strong></summary>

- Verify your Anthropic API key is correct and active at [console.anthropic.com](https://console.anthropic.com/).
- Re-enter your API key through the **in-app settings** (API overlay). The key is stored in the `src/.env` file and can also be edited manually if needed.
- The key format must start with `sk-ant-api`. If the onboarding wizard rejects your key, double-check for leading/trailing spaces.
- Ensure your API key has sufficient credits. You can check your usage and billing at the Anthropic console. If you see a `credit_balance_exhausted` error, you need to add credits to your Anthropic account.
- After changing the key via the in-app settings, it takes effect immediately — no restart required.

</details>

<details>
<summary><strong>Port already in use</strong></summary>

- The default port is **5000** (configurable via `src/settings/server_settings.json`). If you see an error like `Address already in use` or `OSError: [Errno 98]`, another process is occupying the port.
- On Windows, find and kill the blocking process:
  ```
  netstat -ano | findstr :5000
  taskkill /PID <PID> /F
  ```
- On Linux/macOS:
  ```
  lsof -i :5000
  kill -9 <PID>
  ```
- This commonly happens when a previous PersonaUI instance didn't shut down cleanly.

</details>

<details>
<summary><strong>Frontend build fails / Node.js not found</strong></summary>

- The init script downloads Node.js v22 automatically. If this fails (e.g. due to network restrictions or firewall blocks), install Node.js manually from [nodejs.org](https://nodejs.org/).
- Delete `frontend/node_modules/` and `frontend/package-lock.json`, then retry:
  ```
  cd frontend
  rm -rf node_modules package-lock.json
  npm install
  npm run build
  ```
- On Windows, long file paths in `node_modules` can cause issues. Enable long paths:
  ```
  git config --system core.longpaths true
  ```

</details>

<details>
<summary><strong>Database errors / corrupt chat history</strong></summary>

- Each persona has its own SQLite database (`src/data/main.db` for the default persona, `src/data/persona_<uuid>.db` for custom ones). If a specific persona's chat is broken, try deleting its database file and restarting the app. The database will be recreated automatically (note: chat history for that persona will be lost).
- If you see migration errors after an update, make sure you are running the latest version — database migrations are applied automatically on startup.
- **Orphaned database files:** If you deleted a persona's JSON definition manually but its database file still exists, it will not be cleaned up automatically. You can safely delete any `.db` file in `src/data/` that no longer corresponds to an existing persona.

</details>

<details>
<summary><strong>Cortex memory not updating</strong></summary>

- The Cortex system updates persona memory (Memory, Soul, Relationship files) via background API calls triggered at configurable context thresholds (50 %, 75 %, 95 %). If memory seems stale:
  - Check that Cortex is enabled in the Cortex settings overlay.
  - Cortex updates have a **30-second cooldown** between triggers — rapid messages may skip updates.
  - Background cortex updates fail silently if the API call errors out (e.g. insufficient credits, network issue). Check `src/logs/personaui.log` for warnings.
  - Each Cortex file is capped at **8,000 characters**. Excess content is silently truncated.
- Cortex update calls use additional API credits — one extra API request per update cycle.
- If `src/settings/cycle_state.json` becomes corrupt, delete it. It will be recreated with default values, which may trigger an immediate cortex update on the next conversation.

</details>

<details>
<summary><strong>Onboarding keeps restarting</strong></summary>

- The onboarding wizard is controlled by `src/settings/onboarding.json`. If this file is missing, empty, or corrupt (e.g. due to a crash during write), the onboarding will re-trigger on the next launch.
- **Fix:** Create or fix the file manually:
  ```json
  {"completed": true, "disclaimer_accepted": true}
  ```
- This also applies after a factory reset — the onboarding is intentionally shown again.

</details>

<details>
<summary><strong>Settings corruption / app behaves unexpectedly</strong></summary>

- PersonaUI stores settings as JSON files in `src/settings/`. If any of these files become malformed (e.g. crash during write, accidental manual edit), the app may fail to start or behave unexpectedly.
- **Fix:** Delete the corrupt settings file. PersonaUI recreates most settings files with defaults on the next launch. Key files:
  - `user_settings.json` — User preferences
  - `cortex_settings.json` — Cortex system configuration
  - `window_settings.json` — Window position and size
  - `onboarding.json` — Onboarding completion state
  - `cycle_state.json` — Cortex trigger tracking
  - `user_profile.json` — User name, avatar, language
- The `defaults.json` file contains static defaults shipped with the app — do not modify or delete it.

</details>

<details>
<summary><strong>Avatar upload fails</strong></summary>

- Avatar uploads require **Pillow** (included in `requirements.txt`). If Pillow is not installed, the upload will fail. Reinstall dependencies with `pip install -r requirements.txt`.
- Maximum upload size is **10 MB**. Images are automatically cropped and resized to 1024×1024 JPEG.
- Custom avatars are stored in `frontend/public/avatar/costum/`. If this directory is missing, create it manually.
- Custom avatars are **deleted by a factory reset**. Back them up before resetting if needed.

</details>

<details>
<summary><strong>Network sharing not working</strong></summary>

- Make sure both devices are on the **same local network** (same Wi-Fi / LAN).
- Check your **firewall settings** — the port PersonaUI uses (default: 5000) must be allowed for incoming connections.
- On Windows, you may need to allow Python (or the specific port) through Windows Defender Firewall:
  - Open **Windows Security → Firewall & network protection → Allow an app through firewall**
  - Add `python.exe` (from your `.venv/Scripts/` folder) or allow the port manually.
- Verify the correct local IP is displayed. You can check with `ipconfig` (Windows) or `ifconfig` / `ip addr` (Linux/macOS).
- If you are locked out by the IP whitelist/blacklist, edit or delete `src/settings/server_settings.json` and restart.

</details>

<details>
<summary><strong>Streaming interruptions / incomplete responses</strong></summary>

- PersonaUI uses Server-Sent Events (SSE) for real-time message streaming. Long responses can be interrupted by:
  - **Proxies or firewalls** with idle-connection timeouts — if you're behind a corporate proxy, try connecting directly.
  - **Unstable network connections** — the stream will error out and the partial response is shown.
- If streaming frequently breaks, try switching to `--no-gui` mode and using a modern browser, which tends to handle SSE more reliably.
- Check `src/logs/personaui.log` for detailed error messages from the streaming endpoint.

</details>

<details>
<summary><strong>Windows Defender / Antivirus blocks PersonaUI.exe</strong></summary>

- The `PersonaUI.exe` is a batch script converted with *Bat To Exe Converter*. Some antivirus tools flag this as suspicious — it is a **false positive**.
- You can add an exception for the PersonaUI folder in your antivirus settings, or simply use `bin/start.bat` directly instead of the EXE.

</details>

<details>
<summary><strong>Git update fails / merge conflicts</strong></summary>

- If `bin/update.bat` or `git pull` fails with merge conflicts, you likely have local changes that conflict with the update.
- **Important:** `bin/update.bat` uses `git reset --hard origin/main` internally — this **discards all local code changes**. Settings and persona data in `.gitignore`d directories are not affected.
- To update manually while preserving local changes:
  ```
  git stash
  git pull
  git stash pop   # re-apply your changes (may need manual conflict resolution)
  ```
- **Settings and persona data are never overwritten** by Git updates — they live in directories that are `.gitignore`d.

</details>

<details>
<summary><strong>CORS errors in dev mode</strong></summary>

- When running with `--dev`, the Vite dev server runs on `http://localhost:5173` while the Flask backend runs on a different port. CORS is pre-configured for this setup.
- If you still see CORS errors, make sure you're accessing the frontend through `http://localhost:5173` (not through the Flask port).
- Clear your browser cache or try an incognito window — stale service workers can cause unexpected CORS issues.

</details>

<details>
<summary><strong>Checking logs for errors</strong></summary>

- PersonaUI writes detailed logs to `src/logs/personaui.log` (rotating file, 5 MB max, 3 backups).
- When reporting a bug or debugging an issue, check this log file first — it contains stack traces, API errors, and background task failures that are not visible in the UI.
- Console output (when running from a terminal) also shows INFO-level messages and above.

</details>

<details>
<summary><strong>Factory reset</strong></summary>

- If nothing else helps, you can perform a full factory reset using `bin/reset.bat` (or `python src/reset.py`).
- This deletes all personas, databases, settings, chat history, custom avatars, Cortex memory, logs, and caches — effectively returning PersonaUI to its first-launch state.
- **Back up** any data you want to keep before resetting:
  - `src/data/` — Databases (chat history)
  - `src/settings/` — All settings
  - `src/instructions/created_personas/` — Custom persona definitions
  - `frontend/public/avatar/costum/` — Custom avatars

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
