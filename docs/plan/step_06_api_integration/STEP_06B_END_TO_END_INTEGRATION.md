# Schritt 6B: End-to-End Integration

## Übersicht

Dieses Dokument beschreibt die **vollständige Verdrahtung** des Cortex-Systems — vom Server-Start über den Chat-Flow bis zum Persona-Lifecycle. Es dient als Integrations-Checkliste für die Zusammenführung aller Einzelschritte (1–6A) zu einem funktionierenden Gesamtsystem.

### Ziel

Nach Abschluss aller hier beschriebenen Änderungen:
- Startet PersonaUI mit Cortex statt Memory
- Erstellt und verwaltet Cortex-Verzeichnisse automatisch
- Lädt Cortex-Inhalte in den System-Prompt
- Triggert Background-Updates nach Tier-Schwellen
- Bietet UI-Zugriff auf Cortex-Dateien
- Migriert bestehende Installationen automatisch beim ersten Start

---

## 1. Server-Startup-Sequenz (Geordnet)

### 1.1 Boot-Prozess: Schritt für Schritt

```
init.py                          app.py                        startup.py
   │                                │                              │
   │── check_python_version() ─────►│                              │
   │── check_venv() ───────────────►│                              │
   │── check_dependencies() ───────►│                              │
   │                                │                              │
   │── launch app.py ──────────────►│                              │
   │                                │── Flask(__name__) ──────────►│
   │                                │── init_services() ──────────►│  (1)
   │                                │── register_routes(app) ─────►│  (2)
   │                                │                              │
   │                                │── if __main__:               │
   │                                │   ├── load server_settings   │
   │                                │   ├── create webview window  │
   │                                │   └── boot_thread.start() ──►│
   │                                │                              │── startup_sequence()
   │                                │                              │   ├── splash messages
   │                                │                              │   ├── check_for_update()
   │                                │                              │   ├── init_all_dbs()       (3)
   │                                │                              │   ├── ensure_cortex_dirs() (4) ← NEU
   │                                │                              │   ├── fun messages
   │                                │                              │   └── start_flask_server()
```

### 1.2 Startup-Operationen im Detail

| # | Operation | Datei | Was passiert | Cortex-Änderung |
|---|-----------|-------|-------------|-----------------|
| **(1)** | `init_services()` | `src/utils/provider.py` | Erstellt ApiClient, ChatService, **CortexService** | `MemoryService` → `CortexService` |
| **(2)** | `register_routes(app)` | `src/routes/__init__.py` | Registriert alle Blueprints inkl. **cortex_bp** | `memory_bp` → `cortex_bp` |
| **(3)** | `init_all_dbs()` | `src/utils/database/schema.py` | Erstellt/migriert SQLite-Tabellen | Memory-Tabellen werden **nicht mehr** erstellt |
| **(4)** | `ensure_cortex_dirs()` | `src/utils/cortex/` (NEU) | Erstellt `cortex/default/` + Dirs für alle existierenden Personas | **Komplett neu** |

### 1.3 `init_services()` — Vorher vs. Nachher

**Vorher (`src/utils/provider.py`):**
```python
def init_services(api_key: str = None):
    global _api_client, _chat_service, _memory_service
    from .api_request import ApiClient
    from .services import ChatService, MemoryService

    _api_client = ApiClient(api_key=api_key)
    _chat_service = ChatService(_api_client)
    _memory_service = MemoryService(_api_client)
```

**Nachher:**
```python
def init_services(api_key: str = None):
    global _api_client, _chat_service, _cortex_service
    from .api_request import ApiClient
    from .services import ChatService
    from .cortex.service import CortexService

    _api_client = ApiClient(api_key=api_key)
    _chat_service = ChatService(_api_client)
    _cortex_service = CortexService(_api_client)
```

**Accessor-Änderungen:**
```python
# ENTFERNT:
def get_memory_service(): ...

# NEU:
def get_cortex_service():
    """Gibt den CortexService zurück"""
    if _cortex_service is None:
        raise RuntimeError("CortexService nicht initialisiert – init_services() in app.py aufrufen")
    return _cortex_service
```

### 1.4 `register_routes()` — Vorher vs. Nachher

**Vorher (`src/routes/__init__.py`):**
```python
from routes.memory import memory_bp

def register_routes(app):
    ...
    app.register_blueprint(memory_bp)
    ...
```

**Nachher:**
```python
from routes.cortex import cortex_bp                          # ← NEU

def register_routes(app):
    ...
    # app.register_blueprint(memory_bp)                      # ← ENTFERNT
    app.register_blueprint(cortex_bp)                        # ← NEU
    ...
```

### 1.5 `init_all_dbs()` — Memory-Tabellen entfernt

Die Funktion erstellt weiterhin alle Persona-Datenbanken, aber:
- **ENTFERNT:** `CREATE TABLE IF NOT EXISTS memories` (wurde von Step 1 entfernt)
- **UNVERÄNDERT:** `CREATE TABLE IF NOT EXISTS messages`, `sessions`, `afterthoughts`

### 1.6 `ensure_cortex_dirs()` — Neue Startup-Funktion

**Einbindung in `startup.py`:**
```python
from utils.database import init_all_dbs
from utils.cortex.service import ensure_cortex_dirs          # ← NEU

def startup_sequence(window, server_mode, server_port, start_flask_fn, host):
    ...
    # Datenbanken initialisieren
    splash_type(window, '> Initialisiere Datenbanken...', 'default')
    init_all_dbs()
    splash_type(window, '  Datenbanken bereit.', 'info')

    # Cortex-Verzeichnisse sicherstellen                     ← NEU
    splash_type(window, '> Cortex-Verzeichnisse prüfen...', 'default')
    ensure_cortex_dirs()
    splash_type(window, '  Cortex bereit.', 'info')
    ...
```

**Was `ensure_cortex_dirs()` tut:**
1. Erstellt `instructions/personas/cortex/default/` mit Template-Dateien
2. Iteriert über `instructions/created_personas/*.json`
3. Erstellt für jede existierende Persona `cortex/custom/{persona_id}/` mit Templates
4. Überspringt bereits existierende Dateien (idempotent)

**Auch in den Fallback-Pfaden von `app.py`:**
```python
# Fallback: Normaler Flask-Server ohne GUI-Fenster
except ImportError:
    show_console_window()
    init_all_dbs()
    ensure_cortex_dirs()                                     # ← NEU
    app.run(host=host, port=server_port, debug=False)
else:
    init_all_dbs()
    ensure_cortex_dirs()                                     # ← NEU
    app.run(host=host, port=server_port, debug=False)
```

---

## 2. Runtime-Sequenz: Chat-Flow

### 2.1 Vollständiger Chat-Request (SOLL)

```
┌─────────┐       ┌──────────┐       ┌─────────────┐       ┌──────────────┐       ┌────────────┐       ┌───────────┐
│ Frontend │       │ chat.py  │       │ ChatService │       │CortexService │       │PromptEngine│       │ ApiClient │
└────┬─────┘       └─────┬────┘       └──────┬──────┘       └──────┬───────┘       └──────┬─────┘       └─────┬─────┘
     │                    │                   │                     │                      │                    │
     │ POST /chat_stream  │                   │                     │                      │                    │
     │ { message,         │                   │                     │                      │                    │
     │   session_id,      │                   │                     │                      │                    │
     │   persona_id }     │                   │                     │                      │                    │
     │───────────────────►│                   │                     │                      │                    │
     │                    │                   │                     │                      │                    │
     │                    │ resolve_persona_id│                     │                      │                    │
     │                    │──────────────────►│                     │                      │                    │
     │                    │                   │                     │                      │                    │
     │                    │ generate()        │                     │                      │                    │
     │                    │──►chat_stream()──►│                     │                      │                    │
     │                    │                   │                     │                      │                    │
     │                    │                   │ _load_cortex_context│                      │                    │
     │                    │                   │────────────────────►│                      │                    │
     │                    │                   │                     │ get_cortex_for_prompt │                    │
     │                    │                   │                     │ read memory.md       │                    │
     │                    │                   │                     │ read soul.md         │                    │
     │                    │                   │                     │ read relationship.md │                    │
     │                    │                   │◄────────────────────│                      │                    │
     │                    │                   │ { cortex_memory,    │                      │                    │
     │                    │                   │   cortex_soul,      │                      │                    │
     │                    │                   │   cortex_relationship}                     │                    │
     │                    │                   │                     │                      │                    │
     │                    │                   │ runtime_vars.update(cortex_data)            │                    │
     │                    │                   │                     │                      │                    │
     │                    │                   │ build_system_prompt(variant, runtime_vars) ─►│                    │
     │                    │                   │                     │  resolve {{cortex_*}} │                    │
     │                    │                   │◄────────────────────┼──────────────────────│                    │
     │                    │                   │ system_prompt mit   │                      │                    │
     │                    │                   │ Cortex-Block (2000) │                      │                    │
     │                    │                   │                     │                      │                    │
     │                    │                   │ _build_chat_messages() (UNVERÄNDERT)        │                    │
     │                    │                   │ first_assistant → history → user → prefill  │                    │
     │                    │                   │                     │                      │                    │
     │                    │                   │ api_client.stream(config) ──────────────────────────────────────►│
     │                    │                   │                     │                      │                    │
     │◄── SSE: chunk ─────│◄── chunk ─────────│◄───────────────────────────────────────────────── chunk ────────│
     │◄── SSE: chunk ─────│◄── chunk ─────────│◄───────────────────────────────────────────────── chunk ────────│
     │                    │                   │                     │                      │                    │
     │                    │ save_message(user) │ (beim 1. chunk)    │                      │                    │
     │                    │ save_message(bot)  │ (bei done)         │                      │                    │
     │                    │                   │                     │                      │                    │
     │                    │ ══ TIER-CHECK ═══ │                     │                      │                    │
     │                    │ check_and_trigger_cortex_update(        │                      │                    │
     │                    │   persona_id, session_id, context_limit)│                      │                    │
     │                    │                   │                     │                      │                    │
     │                    │ [Tier erreicht?]  │                     │                      │                    │
     │                    │ JA → Background-Thread: CortexUpdateService.execute_update()   │                    │
     │                    │                   │                     │                      │                    │
     │◄── SSE: done ──────│ { response, stats,│                     │                      │                    │
     │    cortex_update:  │   cortex_update } │                     │                      │                    │
     │    { tier, status }│                   │                     │                      │                    │
     │                    │                   │                     │                      │                    │
```

### 2.2 Schritt-für-Schritt-Erklärung

| # | Operation | Datei | Beschreibung |
|---|-----------|-------|-------------|
| 1 | Client sendet POST `/chat_stream` | Frontend | `{ message, session_id, persona_id, context_limit, ... }` |
| 2 | `resolve_persona_id()` | `routes/helpers.py` | Bestimmt persona_id aus Request, Session oder Active Fallback |
| 3 | `get_chat_service()` | `utils/provider.py` | Holt Singleton ChatService |
| 4 | `_load_cortex_context(persona_id)` | `services/chat_service.py` | **NEU:** Lädt Cortex-Dateien → Dict mit 3 Keys |
| 5 | `runtime_vars.update(cortex_data)` | `services/chat_service.py` | Cortex-Werte werden zu runtime_vars hinzugefügt |
| 6 | `build_system_prompt(variant, runtime_vars)` | `prompt_engine/engine.py` | Baut System-Prompt, `{{cortex_*}}` werden aufgelöst |
| 7 | `_build_chat_messages()` | `services/chat_service.py` | Messages: first_assistant → history → user → prefill |
| 8 | `api_client.stream(config)` | `api_request/client.py` | Anthropic API-Aufruf mit Streaming |
| 9 | SSE chunks → Client | `routes/chat.py` | Echtzeit-Streaming der Antwort |
| 10 | `save_message(user)` | Beim 1. Chunk | User-Nachricht in Persona-DB speichern |
| 11 | `save_message(bot)` | Bei Done | Bot-Antwort in Persona-DB speichern |
| 12 | `check_and_trigger_cortex_update()` | `cortex/tier_checker.py` | **NEU:** Prüft ob Tier-Schwelle erreicht |
| 13 | Background-Thread (optional) | `cortex/update_service.py` | **NEU:** `tool_use` API-Call zum Cortex-Update |
| 14 | SSE done mit `cortex_update` | `routes/chat.py` | **NEU:** Done-Event enthält Update-Status |

### 2.3 Cortex-Loading im ChatService — Detailflow

```python
# ChatService.chat_stream() — Relevanter Ausschnitt

def chat_stream(self, user_message, conversation_history, character_data,
                language, user_name, api_model, api_temperature,
                ip_address, experimental_mode, persona_id):
    variant = 'experimental' if experimental_mode else 'default'

    # ── CORTEX LADEN (ersetzt _load_memory_context) ──────────
    cortex_data = self._load_cortex_context(persona_id)

    # ── RUNTIME VARS (mit Cortex) ───────────────────────────
    runtime_vars = {
        'language': language,
        'ip_address': ip_address,
    }
    runtime_vars.update(cortex_data)
    # runtime_vars enthält jetzt:
    # { language, ip_address, cortex_memory, cortex_soul, cortex_relationship }

    # ── SYSTEM PROMPT BAUEN ─────────────────────────────────
    system_prompt = ''
    if self._engine:
        system_prompt = self._engine.build_system_prompt(variant, runtime_vars)
    # Cortex-Block erscheint als letzter Block (Order 2000) im System-Prompt

    # ── MESSAGES BAUEN (UNVERÄNDERT, aber ohne memory_context) ──
    messages, stats = self._build_chat_messages(
        user_message=user_message,
        conversation_history=conversation_history,
        char_name=character_data.get('char_name', 'Assistant'),
        user_name=user_name,
        nsfw_mode=experimental_mode,
        # ⚠️ ENTFERNT: memory_context=memory_text
    )
    ...
```

### 2.4 Error Handling — Dreistufiger Graceful Degradation

```
Stufe 1: Cortex-Loading fehlgeschlagen
   → Leere Strings für {{cortex_*}} → Chat funktioniert ohne Cortex
   → log.warning("Cortex-Kontext konnte nicht geladen werden: %s")

Stufe 2: Tier-Check fehlgeschlagen
   → Done-Event wird trotzdem gesendet (ohne cortex_update Feld)
   → log.warning("Cortex Tier-Check Fehler (non-fatal): %s")

Stufe 3: Background-Update fehlgeschlagen
   → Thread stirbt leise, nächster Tier-Check kann erneut triggern
   → log.error("Cortex-Update Exception: %s")
```

---

## 3. Konfigurationsdatei-Änderungen — Gesamtübersicht

### 3.1 Alle betroffenen Dateien

| Datei | Aktion | Details |
|-------|--------|---------|
| `src/settings/defaults.json` | **MODIFIZIERT** | `-memoriesEnabled` → `+cortexEnabled: true` |
| `src/settings/user_settings.json` | **MIGRIERT** | `memoriesEnabled` → `cortexEnabled` (automatisch) |
| `src/settings/cortex_settings.json` | **NEU** | Tier-Schwellwerte, enabled-Flag |
| `src/dev/prompts/prompt_manifest.json` | **MODIFIZIERT** | `+cortex_context` Eintrag, `-memory_context` |
| `src/dev/prompts/placeholder_registry.json` | **MODIFIZIERT** | `+cortex_memory`, `+cortex_soul`, `+cortex_relationship`, `-memory_entries` |
| `src/dev/prompts/domains/cortex_context.json` | **NEU** | Prompt-Template für Cortex-Block (Order 2000) |

### 3.2 `defaults.json` — Einzeländerung

```diff
{
    "apiModel": "claude-sonnet-4-5-20250929",
    ...
-   "memoriesEnabled": true,
+   "cortexEnabled": true,
    "nachgedankeMode": "off",
    ...
}
```

### 3.3 `user_settings.json` — Migration

Bestehende Installationen haben `"memoriesEnabled": true/false`. Beim ersten Start nach Update:

```python
def migrate_settings():
    """Migriert memoriesEnabled → cortexEnabled (einmalig)."""
    settings = load_user_settings()

    if 'memoriesEnabled' in settings:
        # Übernehme den alten Wert
        settings['cortexEnabled'] = settings.pop('memoriesEnabled')
        save_user_settings(settings)
        log.info("Settings migriert: memoriesEnabled → cortexEnabled = %s",
                 settings['cortexEnabled'])
```

### 3.4 `cortex_settings.json` — Neue Datei

```json
{
    "enabled": true,
    "tier_thresholds": {
        "tier_1": 50,
        "tier_2": 75,
        "tier_3": 95
    },
    "auto_update": true,
    "max_file_size_kb": 50
}
```

| Key | Typ | Default | Beschreibung |
|-----|-----|---------|-------------|
| `enabled` | bool | `true` | Cortex-System aktiv (Master-Switch) |
| `tier_thresholds.tier_1` | int | `50` | % von contextLimit für Tier 1 |
| `tier_thresholds.tier_2` | int | `75` | % von contextLimit für Tier 2 |
| `tier_thresholds.tier_3` | int | `95` | % von contextLimit für Tier 3 |
| `auto_update` | bool | `true` | Automatische Background-Updates aktiviert |
| `max_file_size_kb` | int | `50` | Max. Größe pro Cortex-Datei in KB |

### 3.5 `prompt_manifest.json` — Neuer Block

```json
{
    "cortex_context": {
        "domain_file": "cortex_context.json",
        "order": 2000,
        "target": "system_prompt",
        "enabled": true,
        "description": "Cortex-Kontext — Erinnerungen, Seele, Beziehung",
        "requires_any": ["cortex_memory", "cortex_soul", "cortex_relationship"]
    }
}
```

**`requires_any`** — Der Block wird **nur** ausgegeben, wenn mindestens einer der drei Placeholders einen nicht-leeren Wert hat. Bei leeren Cortex-Dateien wird der gesamte Block (inkl. Rahmentext) weggelassen.

### 3.6 `placeholder_registry.json` — Neue Einträge

```json
{
    "cortex_memory": {
        "name": "Cortex Memory",
        "description": "Inhalt der memory.md — Faktenwissen, Vorlieben",
        "source": "runtime",
        "type": "string",
        "default": "",
        "category": "cortex",
        "resolve_phase": "runtime"
    },
    "cortex_soul": {
        "name": "Cortex Soul",
        "description": "Inhalt der soul.md — Persönlichkeitsentwicklung",
        "source": "runtime",
        "type": "string",
        "default": "",
        "category": "cortex",
        "resolve_phase": "runtime"
    },
    "cortex_relationship": {
        "name": "Cortex Relationship",
        "description": "Inhalt der relationship.md — Beziehungsdynamik",
        "source": "runtime",
        "type": "string",
        "default": "",
        "category": "cortex",
        "resolve_phase": "runtime"
    }
}
```

**Entfernte Einträge:**
- `memory_entries` — wird nicht mehr benötigt (alter Memory-Kontext)

---

## 4. Persona-Lifecycle

### 4.1 Übersicht aller Lifecycle-Events

```
┌──────────────────────────────────────────────────────────────────────┐
│                     PERSONA LIFECYCLE                                │
│                                                                      │
│  ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐ │
│  │  CREATE PERSONA  │   │ ACTIVATE PERSONA │   │  DELETE PERSONA  │ │
│  │                  │   │                  │   │                  │ │
│  │ 1. save JSON     │   │ 1. copy config   │   │ 1. delete JSON   │ │
│  │ 2. create DB  ─┐ │   │    to active/    │   │ 2. delete DB  ─┐ │ │
│  │ 3. create     ◄┘ │   │ 2. cortex files  │   │ 3. delete     ◄┘ │ │
│  │    cortex dir  ←  │   │    now point to  │   │    cortex dir  ← │ │
│  │    (NEU)          │   │    new persona   │   │    (NEU)         │ │
│  └──────────────────┘   └──────────────────┘   └──────────────────┘ │
│                                                                      │
│  ┌──────────────────┐                                                │
│  │ DEFAULT PERSONA  │                                                │
│  │                  │                                                │
│  │ Immer vorhanden: │                                                │
│  │ cortex/default/  │                                                │
│  │ ├── memory.md    │                                                │
│  │ ├── soul.md      │                                                │
│  │ └── relationship │                                                │
│  │        .md       │                                                │
│  └──────────────────┘                                                │
└──────────────────────────────────────────────────────────────────────┘
```

### 4.2 Persona erstellen (`save_created_persona`)

**Datei: `src/utils/config.py`**

```python
def save_created_persona(config_data: Dict[str, Any]) -> Optional[str]:
    try:
        persona_id = str(uuid.uuid4())[:8]
        ...
        # Erstelle die zugehörige Persona-Datenbank
        create_persona_db(persona_id)

        # ── NEU: Erstelle Cortex-Verzeichnis ─────────────
        from utils.cortex.service import create_cortex_dir
        create_cortex_dir(persona_id)
        # ─────────────────────────────────────────────────

        return persona_id
    except Exception as e:
        log.error("Fehler beim Speichern der Persona: %s", e)
        return None
```

**Was `create_cortex_dir(persona_id)` tut:**
1. Erstellt `instructions/personas/cortex/custom/{persona_id}/`
2. Schreibt Template-Dateien: `memory.md`, `soul.md`, `relationship.md`
3. Templates enthalten `{{user}}`-Placeholder (wird bei Prompt-Build aufgelöst)

### 4.3 Persona aktivieren (`activate_persona`)

**Keine Code-Änderung nötig.** Die `get_active_persona_id()` Funktion gibt die aktive Persona zurück, und der CortexService liest automatisch aus dem richtigen Verzeichnis:
- `persona_id == 'default'` → `cortex/default/`
- `persona_id == '{id}'` → `cortex/custom/{id}/`

### 4.4 Persona löschen (`delete_created_persona`)

**Datei: `src/utils/config.py`**

```python
def delete_created_persona(persona_id: str) -> bool:
    if persona_id == "default":
        return False
    ...
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            delete_persona_db(persona_id)

            # ── NEU: Cortex-Verzeichnis löschen ─────────
            from utils.cortex.service import delete_cortex_dir
            delete_cortex_dir(persona_id)
            # ─────────────────────────────────────────────

            return True
        return False
    except Exception as e:
        log.error("Fehler beim Löschen der Persona %s: %s", persona_id, e)
        return False
```

**Was `delete_cortex_dir(persona_id)` tut:**
1. `shutil.rmtree(cortex/custom/{persona_id}/)` — Löscht das komplette Verzeichnis
2. Log-Eintrag: `"Cortex-Verzeichnis gelöscht: {persona_id}"`
3. Gibt `True` zurück, `False` bei Fehler

### 4.5 Default-Persona

Die Default-Persona nutzt immer `cortex/default/`. Dieses Verzeichnis:
- Wird beim ersten Start automatisch erstellt (`ensure_cortex_dirs()`)
- Kann **nicht** gelöscht werden (Guard in `delete_cortex_dir`)
- Wird bei Reset neu erstellt (siehe Abschnitt 6.3)

### 4.6 Pfad-Auflösung

```python
def get_cortex_dir(persona_id: str) -> str:
    """Gibt den Cortex-Pfad für eine Persona zurück."""
    if persona_id == 'default':
        return CORTEX_DEFAULT_DIR            # cortex/default/
    return os.path.join(CORTEX_CUSTOM_DIR, persona_id)  # cortex/custom/{id}/
```

---

## 5. Frontend-Integration

### 5.1 CortexOverlay — Dateimanagement

```
┌──────────────────────────────────────────────────────────┐
│                   CortexOverlay.jsx                       │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  memory.md   │  │   soul.md    │  │relationship  │   │
│  │              │  │              │  │    .md       │   │
│  │ [Markdown    │  │ [Markdown    │  │ [Markdown    │   │
│  │  Editor]     │  │  Editor]     │  │  Editor]     │   │
│  │              │  │              │  │              │   │
│  │ [Speichern]  │  │ [Speichern]  │  │ [Speichern]  │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
│                                                          │
│  ┌─────────────────────────────────────────────────┐     │
│  │ Cortex-Einstellungen                            │     │
│  │ [✓] Cortex aktiviert                            │     │
│  │ Tier 1: [50]%  Tier 2: [75]%  Tier 3: [95]%    │     │
│  │ [✓] Auto-Update aktiv                           │     │
│  └─────────────────────────────────────────────────┘     │
│                                                          │
│  [Alle Dateien zurücksetzen] [Schließen]                 │
└──────────────────────────────────────────────────────────┘
```

### 5.2 Frontend-API-Aufrufe

| Aktion | HTTP-Methode | Endpoint | Body |
|--------|-------------|----------|------|
| Alle Dateien laden | GET | `/api/cortex/files?persona_id={id}` | — |
| Einzelne Datei laden | GET | `/api/cortex/file/{filename}?persona_id={id}` | — |
| Datei speichern | PUT | `/api/cortex/file/{filename}` | `{ persona_id, content }` |
| Datei zurücksetzen | POST | `/api/cortex/reset/{filename}` | `{ persona_id }` |
| Alle zurücksetzen | POST | `/api/cortex/reset` | `{ persona_id }` |
| Settings laden | GET | `/api/cortex/settings` | — |
| Settings speichern | PUT | `/api/cortex/settings` | `{ enabled, tier_thresholds, ... }` |

### 5.3 Cortex-Update-Indikator

Nach einem Chat-Response kann das Done-Event ein `cortex_update` Feld enthalten:

```json
{
    "type": "done",
    "response": "...",
    "stats": { ... },
    "character_name": "Luna",
    "cortex_update": {
        "tier": 1,
        "status": "started"
    }
}
```

**Frontend-Reaktion:**
1. Erhält `cortex_update` im Done-Event
2. Zeigt dezenten Indikator: _"Cortex wird aktualisiert..."_
3. Background-Update läuft serverseitig (kein Frontend-Polling nötig)
4. Bei nächstem Öffnen des CortexOverlays sind die aktualisierten Inhalte sichtbar

---

## 6. Migration — Erster Start nach Update

### 6.1 Automatischer Migrationspfad

```
Server startet → startup_sequence()
     │
     ├── init_all_dbs()
     │   └── Memory-Tabellen werden NICHT mehr erstellt
     │       (bestehende Tabellen bleiben in DB, werden aber ignoriert)
     │
     ├── ensure_cortex_dirs()
     │   ├── cortex/default/ erstellt (mit Templates)
     │   └── cortex/custom/{persona_id}/ für jede existierende Persona
     │
     ├── migrate_settings() ← NEU (einmalig)
     │   ├── user_settings.json: memoriesEnabled → cortexEnabled
     │   └── defaults.json: memoriesEnabled → cortexEnabled (schon im Code)
     │
     └── Flask-Server startet
         ├── register_routes(): cortex_bp statt memory_bp registriert
         └── init_services(): CortexService statt MemoryService
```

### 6.2 Was passiert mit alten Daten?

| Altes Artefakt | Was passiert |
|----------------|-------------|
| **SQL `memories`-Tabellen** | Bleiben in Persona-DBs, werden aber nie abgefragt. Kein aktives Löschen — minimales Risiko. |
| **`memoriesEnabled` in user_settings** | Wird automatisch zu `cortexEnabled` migriert. Alter Key wird entfernt. |
| **`memoriesEnabled` in defaults.json** | Wird im Code-Update durch `cortexEnabled` ersetzt. |
| **`/api/memory/*` Endpoints** | Nicht mehr registriert → 404. Frontend-Code (React) referenziert diese nicht mehr. |
| **`MemoryService`-Klasse** | Datei wird gelöscht (Step 1). Import in `provider.py` wird ersetzt. |
| **`memory_context.py`** | Datei wird gelöscht (Step 1). Kein Import mehr. |
| **`memory_entries` Placeholder** | Aus Registry entfernt. Falls in User-Manifest referenziert → wird leer aufgelöst. |

### 6.3 Idempotenz-Garantie

Alle Startup-Operationen sind **idempotent** — der Server kann beliebig oft neu gestartet werden:

| Operation | Idempotenz |
|-----------|-----------|
| `init_all_dbs()` | `CREATE TABLE IF NOT EXISTS` — überspringt bestehende |
| `ensure_cortex_dirs()` | `os.makedirs(..., exist_ok=True)` + Skip bestehender Dateien |
| `migrate_settings()` | Prüft `if 'memoriesEnabled' in settings` — läuft nur einmal |
| `register_routes()` | Blueprints werden pro App-Start registriert (kein State) |
| `init_services()` | Überschreibt globale Singletons (safe bei Restart) |

---

## 7. Integrations-Test-Szenarien

### 7.1 Startup-Tests

| # | Test | Erwartung | Priorität |
|---|------|-----------|-----------|
| S1 | **Frische Installation** — Kein `cortex/` Verzeichnis existiert | `ensure_cortex_dirs()` erstellt `cortex/default/` mit 3 Template-Dateien | Hoch |
| S2 | **Migration** — `user_settings.json` enthält `memoriesEnabled: true` | Nach Start: `cortexEnabled: true`, kein `memoriesEnabled` mehr | Hoch |
| S3 | **Bestehende Personas** — 3 Personas in `created_personas/` | `ensure_cortex_dirs()` erstellt `cortex/custom/{id}/` für alle 3 | Hoch |
| S4 | **Wiederholter Start** — Cortex-Dirs existieren bereits | Keine Fehler, keine Überschreibung bestehender Dateien | Hoch |
| S5 | **init_services()** — CortexService statt MemoryService | `get_cortex_service()` gibt valide Instanz zurück | Hoch |
| S6 | **register_routes()** — cortex_bp registriert | `/api/cortex/files` gibt 200 zurück, `/api/memory/list` gibt 404 | Mittel |

### 7.2 Chat-Flow-Tests

| # | Test | Erwartung | Priorität |
|---|------|-----------|-----------|
| C1 | **Chat mit leeren Cortex-Dateien** | Chat funktioniert, `{{cortex_*}}` → leere Strings, Cortex-Block wird weggelassen (requires_any) | Hoch |
| C2 | **Chat mit befüllten Cortex-Dateien** | Cortex-Inhalt erscheint im System-Prompt (letzter Block) | Hoch |
| C3 | **Chat mit deaktiviertem Cortex** (`cortexEnabled: false`) | Kein CortexService-Aufruf, keine `{{cortex_*}}` in runtime_vars | Hoch |
| C4 | **Tier-Check auslösen** — 50% von context_limit erreicht | `cortex_update: { tier: 1, status: 'started' }` im Done-Event | Hoch |
| C5 | **Done-Event ohne Tier** — Unter Schwellwert | Kein `cortex_update` Feld im Done-Event | Mittel |
| C6 | **Cortex-Loading Fehler** — `cortex/` nicht lesbar | Graceful Degradation: leere Strings, Chat funktioniert | Mittel |
| C7 | **Tier-Check Fehler** — Exception in `check_and_trigger_cortex_update` | Done-Event wird trotzdem gesendet (ohne cortex_update) | Mittel |
| C8 | **memory_context nicht mehr in first_assistant** | `first_assistant` enthält keinen Memory-Block mehr (nur Prefill-Impersonation) | Hoch |
| C9 | **Stats ohne memory_est** | Stats-Dict enthält kein `memory_est` Feld mehr | Mittel |

### 7.3 Persona-Lifecycle-Tests

| # | Test | Erwartung | Priorität |
|---|------|-----------|-----------|
| P1 | **Persona erstellen** | DB erstellt UND `cortex/custom/{id}/` mit 3 Templates | Hoch |
| P2 | **Persona aktivieren** | Nächster Chat liest aus `cortex/custom/{id}/` | Hoch |
| P3 | **Persona löschen** | DB gelöscht UND `cortex/custom/{id}/` gelöscht | Hoch |
| P4 | **Default-Persona löschen** | Wird abgelehnt (`return False`). `cortex/default/` bleibt. | Mittel |
| P5 | **Persona ohne Cortex-Dir** — Legacy-Persona | `ensure_cortex_dir()` wird lazy aufgerufen, Dir wird erstellt | Mittel |

### 7.4 Frontend-Tests

| # | Test | Erwartung | Priorität |
|---|------|-----------|-----------|
| F1 | **CortexOverlay öffnen** | 3 Dateien werden via `/api/cortex/files` geladen | Hoch |
| F2 | **Datei bearbeiten + speichern** | PUT `/api/cortex/file/memory.md` → 200, nächster Chat nutzt neuen Inhalt | Hoch |
| F3 | **Datei zurücksetzen** | POST `/api/cortex/reset/memory.md` → Template-Inhalt | Mittel |
| F4 | **Alle zurücksetzen** | POST `/api/cortex/reset` → alle 3 Templates | Mittel |
| F5 | **Cortex-Settings ändern** | PUT `/api/cortex/settings` → Tier-Werte gespeichert | Mittel |
| F6 | **Update-Indikator** | `cortex_update` im Done-Event → UI zeigt Indikator | Niedrig |

### 7.5 End-to-End-Tests

| # | Test | Erwartung | Priorität |
|---|------|-----------|-----------|
| E1 | **Kompletter Flow: Start → Chat → Cortex-Update → Verify** | Server startet, Chat funktioniert, Tier wird ausgelöst, Cortex-Dateien werden aktualisiert | Hoch |
| E2 | **Migration-Flow: Alter State → Update → Start → Chat** | memoriesEnabled migriert, Cortex-Dirs erstellt, Chat nutzt Cortex | Hoch |
| E3 | **Multi-Persona: Erstellen → Aktivieren → Chat → Wechseln → Chat** | Jede Persona hat eigene Cortex-Dateien, Chat liest korrekte Dateien | Hoch |

---

## 8. Troubleshooting Guide

### 8.1 Startup-Probleme

| Problem | Symptom | Ursache | Lösung |
|---------|---------|---------|--------|
| **CortexService nicht initialisiert** | `RuntimeError: CortexService nicht initialisiert` | `init_services()` wurde nicht aufgerufen oder `CortexService`-Import fehlgeschlagen | Prüfe Import in `provider.py`: `from .cortex.service import CortexService` |
| **cortex_bp nicht registriert** | 404 auf `/api/cortex/*` | Import-Fehler in `routes/__init__.py` | Prüfe `from routes.cortex import cortex_bp` und `register_blueprint(cortex_bp)` |
| **Cortex-Dirs nicht erstellt** | Leere Cortex-Dateien im Chat, CortexOverlay zeigt Templates | `ensure_cortex_dirs()` nicht aufgerufen | Prüfe Aufruf in `startup.py` nach `init_all_dbs()` |
| **Memory-Endpoints noch erreichbar** | `/api/memory/list` gibt 200 statt 404 | `memory_bp` noch registriert | Prüfe `routes/__init__.py`: `memory_bp` Import und `register_blueprint` entfernt |
| **Settings-Migration nicht gelaufen** | `memoriesEnabled` statt `cortexEnabled` in Settings | `migrate_settings()` nicht aufgerufen | Prüfe Aufruf in Startup-Sequenz oder manuell `cortexEnabled` in `user_settings.json` setzen |

### 8.2 Chat-Probleme

| Problem | Symptom | Ursache | Lösung |
|---------|---------|---------|--------|
| **Cortex-Inhalt nicht im Prompt** | Persona "erinnert" sich nicht | `_load_cortex_context()` gibt leere Strings zurück | 1. Prüfe ob Dateien existieren: `cortex/custom/{id}/memory.md` etc. 2. Prüfe ob `cortexEnabled: true` in user_settings.json |
| **Cortex-Block fehlt komplett** | Kein Cortex-Abschnitt im System-Prompt (auch bei befüllten Dateien) | Manifest-Eintrag fehlt oder `requires_any` schlägt fehl | Prüfe `prompt_manifest.json` → `cortex_context` Eintrag vorhanden und `enabled: true` |
| **Memory-Content noch in first_assistant** | Alter Memory-Text vor History | `_load_memory_context()` noch aktiv oder `memory_context` Parameter nicht entfernt | Prüfe `chat_service.py`: `_load_memory_context` gelöscht, `_build_chat_messages` ohne `memory_context` |
| **Kein Tier-Check nach Chat** | `cortex_update` nie im Done-Event | Import fehlt oder Exception wird verschluckt | Prüfe Import `from utils.cortex.tier_checker import check_and_trigger_cortex_update` in `chat.py` |
| **Tier feuert nicht** | Message-Count über Schwelle, aber kein Update | Tier wurde bereits für diese Session gefeuert | Prüfe `tier_tracker.py` → `get_fired_tiers()` für Session. Reset bei neuer Session. |

### 8.3 Persona-Probleme

| Problem | Symptom | Ursache | Lösung |
|---------|---------|---------|--------|
| **Neue Persona hat keine Cortex-Dateien** | CortexOverlay zeigt Templates, keine Speicherung | `create_cortex_dir()` nicht in `save_created_persona()` | Prüfe config.py → `create_cortex_dir(persona_id)` nach `create_persona_db()` |
| **Gelöschte Persona hinterlässt Cortex-Dir** | `cortex/custom/{id}/` existiert noch | `delete_cortex_dir()` nicht aufgerufen oder Fehler | Prüfe config.py → `delete_cortex_dir(persona_id)` nach `delete_persona_db()` |
| **Falscher Cortex geladen** | Persona A zeigt Erinnerungen von Persona B | `persona_id` falsch aufgelöst | Prüfe `resolve_persona_id()` → Session-Mapping korrekt? |
| **Default-Cortex wird für Custom-Persona geladen** | Alle Personas teilen dieselben Erinnerungen | `get_cortex_dir()` gibt immer `default` zurück | Prüfe ob `persona_id` korrekt an `_load_cortex_context()` übergeben wird |

### 8.4 Frontend-Probleme

| Problem | Symptom | Ursache | Lösung |
|---------|---------|---------|--------|
| **CortexOverlay lädt nicht** | Leerer Overlay, Netzwerk-Fehler | `cortex_bp` nicht registriert oder CORS-Problem | Prüfe Netzwerk-Tab → `/api/cortex/files` → Status Code |
| **Speichern schlägt fehl** | PUT → 500 | Dateisystem-Berechtigung oder falscher Pfad | Prüfe Server-Logs → CortexService `write_file()` Exception |
| **Update-Indikator zeigt nie** | Kein visuelles Feedback nach Tier-Auslösung | Frontend parst `cortex_update` nicht | Prüfe Chat-Event-Handler → `done` Event → `cortex_update` Feld auswerten |

### 8.5 Diagnose-Befehle

```bash
# Prüfe ob Cortex-Verzeichnisse existieren
ls src/instructions/personas/cortex/
ls src/instructions/personas/cortex/default/
ls src/instructions/personas/cortex/custom/

# Prüfe Settings-Migration
cat src/settings/user_settings.json | grep -E "memories|cortex"

# Prüfe ob cortex_bp registriert ist (Flask route listing)
python -c "from app import app; print([rule.rule for rule in app.url_map.iter_rules() if 'cortex' in rule.rule])"

# Prüfe Cortex-Dateien für eine bestimmte Persona
cat src/instructions/personas/cortex/custom/{persona_id}/memory.md

# Prüfe Manifest
cat src/dev/prompts/prompt_manifest.json | python -m json.tool | grep cortex

# Prüfe Registry
cat src/dev/prompts/placeholder_registry.json | python -m json.tool | grep cortex
```

---

## 9. Abhängigkeitsmatrix — Alle Schritte

### 9.1 Welcher Schritt liefert was?

| Komponente | Erstellt in | Verwendet in |
|------------|-------------|-------------|
| Memory-System entfernt | **Step 1** | Step 2, 6A, 6B |
| `CortexService`-Klasse | **Step 2B** | Step 3C, 4A, 6A |
| `cortex_bp` Blueprint | **Step 2C** | Step 5, 6B |
| `cortex_settings.json` | **Step 2C** | Step 3B, 5A |
| File-Tool Definitionen | **Step 3A** | Step 3C, 6A |
| `tier_checker.py` | **Step 3B** | Step 6A |
| `CortexUpdateService` | **Step 3C** | Step 6A |
| Cortex Placeholders (Registry) | **Step 4A** | Step 4B, 4C |
| `cortex_context.json` Template | **Step 4B** | Step 4C |
| Manifest + Engine Integration | **Step 4C** | Step 6A |
| CortexOverlay.jsx | **Step 5A** | Step 6B (Frontend) |
| Chat-Flow Modifikation | **Step 6A** | Step 6B (Runtime) |
| Startup-Verdrahtung | **Step 6B** | — (Finale Integration) |

### 9.2 Implementierungs-Reihenfolge

```
Step 1: Remove Old Memory
  │
  ├──► Step 2B: CortexService
  │       │
  │       ├──► Step 2C: Cortex API Routes
  │       │       │
  │       │       └──► Step 5A: CortexOverlay.jsx
  │       │
  │       └──► Step 3A: File Tool Definitions
  │               │
  │               ├──► Step 3B: Activation Tier Logic
  │               │
  │               └──► Step 3C: CortexUpdateService
  │
  ├──► Step 4A: Computed Placeholders
  │       │
  │       └──► Step 4B: Prompt Templates
  │               │
  │               └──► Step 4C: Engine Integration
  │
  └──► Step 6A: Chat-Flow Modifikation
          │
          └──► Step 6B: End-to-End Integration (dieses Dokument)
                  │
                  └──► Step 7: Final Review
```

---

## 10. Checkliste für die Implementierung

### 10.1 Backend-Verdrahtung

- [ ] `src/utils/provider.py` — `MemoryService` → `CortexService`, neuer Accessor `get_cortex_service()`
- [ ] `src/routes/__init__.py` — `memory_bp` → `cortex_bp`
- [ ] `src/splash_screen/utils/startup.py` — `ensure_cortex_dirs()` nach `init_all_dbs()`
- [ ] `src/app.py` — `ensure_cortex_dirs()` in Fallback-Pfaden (no-gui, ImportError)
- [ ] `src/utils/config.py` — `save_created_persona()`: + `create_cortex_dir(persona_id)`
- [ ] `src/utils/config.py` — `delete_created_persona()`: + `delete_cortex_dir(persona_id)`
- [ ] `src/settings/defaults.json` — `memoriesEnabled` → `cortexEnabled`
- [ ] `src/settings/cortex_settings.json` — Neue Datei mit Tier-Schwellwerten
- [ ] Settings-Migration — `memoriesEnabled` → `cortexEnabled` beim ersten Start

### 10.2 Prompt-System

- [ ] `placeholder_registry.json` — 3 Cortex-Placeholders hinzufügen, `memory_entries` entfernen
- [ ] `prompt_manifest.json` — `cortex_context` Block hinzufügen (Order 2000, requires_any)
- [ ] `cortex_context.json` — Neue Domain-Datei mit Template-Text
- [ ] `engine.py` — `requires_any`-Prüfung in `build_system_prompt()` (Step 4C)

### 10.3 Chat-Flow

- [ ] `chat_service.py` — `_load_cortex_context()` statt `_load_memory_context()`
- [ ] `chat_service.py` — `runtime_vars.update(cortex_data)` vor `build_system_prompt()`
- [ ] `chat_service.py` — `memory_context` Parameter aus `_build_chat_messages()` entfernen
- [ ] `chat_service.py` — `memory_est` aus Stats entfernen
- [ ] `chat.py` — Tier-Check in `generate()` bei `chat_stream()` und `api_regenerate()`
- [ ] `chat.py` — `cortex_update` in Done-Event-Payload

### 10.4 Frontend

- [ ] Memory-Komponenten entfernt (Step 1)
- [ ] CortexOverlay.jsx implementiert (Step 5A)
- [ ] cortexApi Service implementiert (Step 5A)
- [ ] Chat-Event-Handler parst `cortex_update` Feld
- [ ] Cortex-Update-Indikator im Chat-UI

### 10.5 Tests

- [ ] Startup-Tests (S1–S6)
- [ ] Chat-Flow-Tests (C1–C9)
- [ ] Persona-Lifecycle-Tests (P1–P5)
- [ ] Frontend-Tests (F1–F6)
- [ ] End-to-End-Tests (E1–E3)

---

## 11. Zusammenfassung

| Aspekt | Detail |
|--------|--------|
| **Startup** | `init_services()` → CortexService, `ensure_cortex_dirs()` → Verzeichnisse, `register_routes()` → cortex_bp |
| **Runtime** | ChatService lädt Cortex → runtime_vars → PromptEngine → System-Prompt mit Cortex-Block (Order 2000) |
| **Tier-System** | Nach jedem Chat: Tier-Check → bei Schwelle: Background-Thread → tool_use API-Call → Dateien aktualisiert |
| **Persona-Lifecycle** | Create → + cortex dir, Delete → - cortex dir, Activate → automatische Pfad-Auflösung |
| **Configuration** | `cortexEnabled` in user_settings, `cortex_settings.json` für Tiers, Manifest + Registry für Placeholders |
| **Migration** | Automatisch: `memoriesEnabled` → `cortexEnabled`, Cortex-Dirs für bestehende Personas erstellt |
| **Error Handling** | Dreistufig: Load → Tier-Check → Background-Update, jeweils mit Graceful Degradation |
| **Geänderte Dateien** | ~10 Backend-Dateien, ~3 Config-Dateien, ~5 Prompt-Dateien, ~3 Frontend-Dateien |
| **Abhängigkeiten** | Steps 1–6A müssen abgeschlossen sein, Step 7 (Final Review) folgt |
