# Schritt 1A: Backend Memory-System entfernen

> **Ziel:** Alle Backend-Komponenten des alten Memory-Systems vollständig entfernen, ohne andere Funktionalität zu beeinträchtigen.

---

## Übersicht betroffener Dateien

| # | Datei | Aktion | Risiko |
|---|-------|--------|--------|
| 1 | `src/utils/database/memories.py` | **DATEI LÖSCHEN** | Niedrig |
| 2 | `src/utils/services/memory_service.py` | **DATEI LÖSCHEN** | Niedrig |
| 3 | `src/utils/prompt_engine/memory_context.py` | **DATEI LÖSCHEN** | Mittel |
| 4 | `src/routes/memory.py` | **DATEI LÖSCHEN** | Niedrig |
| 5 | `src/sql/memories.sql` | **DATEI LÖSCHEN** | Niedrig |
| 6 | `src/sql/schema.sql` | Memory-Tabelle + Indizes entfernen | Mittel |
| 7 | `src/sql/chat.sql` | Memory-Marker-Queries entfernen | Hoch |
| 8 | `src/utils/services/chat_service.py` | `_load_memory_context` + alle Memory-Referenzen entfernen | **Hoch** |
| 9 | `src/utils/provider.py` | `_memory_service` + `get_memory_service()` entfernen | Mittel |
| 10 | `src/utils/database/__init__.py` | Memory-Exports entfernen | Mittel |
| 11 | `src/utils/services/__init__.py` | `MemoryService`-Export entfernen | Niedrig |
| 12 | `src/routes/__init__.py` | `memory_bp` Import + Registrierung entfernen | Niedrig |
| 13 | `src/app.py` | Kommentar anpassen | Niedrig |
| 14 | `src/utils/database/chat.py` | Memory-Marker-Funktionen + `memorized`-Feld entfernen | **Hoch** |
| 15 | `src/utils/prompt_engine/engine.py` | `build_summary_prompt()` entfernen | Mittel |
| 16 | `src/utils/prompt_engine/migrator.py` | `memory_entries` aus KNOWN_PLACEHOLDERS entfernen | Niedrig |
| 17 | `src/instructions/prompts/memory_context.json` | **DATEI LÖSCHEN** | Niedrig |
| 18 | `src/instructions/prompts/summary_*.json` (7 Dateien) | **DATEIEN LÖSCHEN** | Niedrig |
| 19 | `tests/test_services/test_memory_service.py` | **DATEI LÖSCHEN** | Niedrig |
| 20 | `tests/test_provider.py` | Memory-Tests entfernen | Niedrig |
| 21 | `tests/conftest.py` | `memory_service` Fixture + `build_summary_prompt` Mock entfernen | Niedrig |
| 22 | `tests/test_services/test_chat_service.py` | `_load_memory_context` Mocks anpassen | Mittel |

---

## Detailplan pro Datei

---

### 1. `src/utils/database/memories.py` — DATEI LÖSCHEN

**Gesamte Datei löschen.** Enthält ausschließlich Memory-Funktionen:

| Zeile | Funktion |
|-------|----------|
| L18 | `save_memory(session_id, content, persona_id, start_message_id, end_message_id)` |
| L42 | `get_all_memories(active_only, persona_id)` |
| L73 | `get_active_memories(persona_id)` |
| L84 | `update_memory(memory_id, content, persona_id)` |
| L106 | `delete_memory(memory_id, persona_id)` |
| L142 | `toggle_memory_status(memory_id, persona_id)` |
| L164 | `set_last_memory_message_id(session_id, message_id, persona_id)` |
| L188 | `get_last_memory_message_id(session_id, persona_id)` |

**Imports die in dieser Datei verwendet werden (keine Cleanup nötig anderswo durch diese Datei selbst):**
```python
from typing import List, Dict, Any, Optional
from ..logger import log
from .connection import get_db_connection
from ..sql_loader import sql
```

---

### 2. `src/utils/services/memory_service.py` — DATEI LÖSCHEN

**Gesamte Datei löschen.** Enthält die `MemoryService`-Klasse (230 Zeilen):

| Zeile | Methode |
|-------|---------|
| L29 | `class MemoryService` |
| L32 | `__init__(self, api_client)` |
| L44 | `_get_active_persona_id(self, persona_id)` |
| L53 | `_get_experimental_mode(self)` |
| L68 | `get_formatted_memories(self, persona_id, max_memories)` |
| L78 | `create_summary_preview(self, session_id, persona_id)` |
| L100 | `save_session_memory(self, session_id, persona_id)` |
| L148 | `save_custom_memory(self, session_id, content, persona_id)` |
| L174 | `_convert_messages(self, messages)` |
| L186 | `_create_summary(self, msg_list, persona_id)` |

**Imports die entfallen:**
```python
from ..api_request import ApiClient, RequestConfig
from ..prompt_engine.memory_context import format_memories_for_prompt
from ..database import (
    get_active_memories, save_memory, get_messages_since_marker,
    get_max_message_id, set_last_memory_message_id, get_last_memory_message_id,
)
```

---

### 3. `src/utils/prompt_engine/memory_context.py` — DATEI LÖSCHEN

**Gesamte Datei löschen.** Enthält eine einzige Funktion:

| Zeile | Funktion |
|-------|----------|
| L14 | `format_memories_for_prompt(memories, max_memories, engine)` |

**Wird importiert von:**
- `src/utils/services/memory_service.py` (L17) → wird ebenfalls gelöscht
- `src/utils/services/chat_service.py` (L15) → **Import entfernen**

---

### 4. `src/routes/memory.py` — DATEI LÖSCHEN

**Gesamte Datei löschen.** Enthält das `memory_bp` Blueprint mit allen API-Endpunkten:

| Zeile | Endpunkt | Route |
|-------|----------|-------|
| L24 | `preview_memory()` | `POST /api/memory/preview` |
| L56 | `create_memory()` | `POST /api/memory/create` |
| L95 | `list_memories()` | `GET /api/memory/list` |
| L113 | `update_memory()` | `PUT /api/memory/<id>` |
| L141 | `delete_memory()` | `DELETE /api/memory/<id>` |
| L158 | `toggle_memory_status()` | `PATCH /api/memory/<id>/toggle` |
| L175 | `check_memory_availability()` | `GET /api/memory/check-availability/<session_id>` |
| L238 | `get_memory_stats()` | `GET /api/memory/stats` |

**Imports die entfallen:**
```python
from utils.database import (
    get_all_memories, update_memory, delete_memory, toggle_memory_status,
    get_user_message_count_since_marker, get_last_memory_message_id,
    get_message_count, get_messages_since_marker, get_db_connection
)
from utils.provider import get_memory_service
from utils.config import get_active_persona_id
from routes.helpers import success_response, error_response, handle_route_error
```

---

### 5. `src/sql/memories.sql` — DATEI LÖSCHEN

**Gesamte Datei löschen.** Enthält alle Memory-SQL-Queries:

| Name | Beschreibung |
|------|-------------|
| `insert_memory` | Memory einfügen |
| `get_all_memories` | Alle Memories abrufen |
| `get_active_memories` | Aktive Memories abrufen |
| `update_memory_content` | Memory-Inhalt aktualisieren |
| `get_memory_session_id` | Session-ID einer Memory |
| `delete_memory` | Memory löschen |
| `get_max_end_message_id` | Max end_message_id (Marker-Neuberechnung) |
| `update_session_memory_marker` | Session-Memory-Marker aktualisieren |
| `toggle_memory_status` | Aktiv-Status umschalten |
| `set_last_memory_message_id` | Memory-Marker setzen |
| `get_last_memory_message_id` | Memory-Marker lesen |
| `upsert_db_info` | DB-Info setzen (⚠️ nicht memory-spezifisch, muss nach `chat.sql` verschoben werden) |

> **Achtung:** Das `upsert_db_info`-Query ist **nicht** memory-spezifisch. Es wird ggf. anderswo verwendet und muss vor dem Löschen nach `chat.sql` oder einer neuen `db_info.sql` verschoben werden. Vor dem Löschen prüfen, ob `sql('memories.upsert_db_info')` irgendwo aufgerufen wird.

---

### 6. `src/sql/schema.sql` — Memory-Schema entfernen

**Zu entfernen (Zeilen 39–56):**
```sql
-- Memory-Tabelle für Erinnerungen
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    persona_id TEXT DEFAULT 'default',
    content TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    start_message_id INTEGER DEFAULT NULL,
    end_message_id INTEGER DEFAULT NULL
);

-- Indizes für Memory-Abfragen
CREATE INDEX IF NOT EXISTS idx_memory_session 
ON memories(session_id);

CREATE INDEX IF NOT EXISTS idx_memory_active 
ON memories(is_active);

CREATE INDEX IF NOT EXISTS idx_memory_persona 
ON memories(persona_id);
```

**Zusätzlich aus `chat_sessions`-Tabelle entfernen (Zeile 18):**
```sql
    last_memory_message_id INTEGER DEFAULT NULL
```

**Behalten:** Alles andere (`db_info`, `chat_sessions` ohne Marker-Spalte, `chat_messages`, Indizes).

---

### 7. `src/sql/chat.sql` — Memory-Marker-Queries entfernen

**Zu entfernen:**

| Zeile | Query-Name | Beschreibung |
|-------|-----------|-------------|
| L9–12 | `get_memory_ranges` | Memory-Ranges für Session abrufen |
| L15–17 | `get_session_memory_marker` | Memory-Marker einer Session |
| L68–70 | `count_user_messages_since_marker` | User-Messages seit Marker zählen |
| L78–80 | `get_messages_since_marker_count` | Messages seit Marker zählen |
| L86–91 | `get_messages_since_marker` | Messages seit Marker abrufen |

**Zu entfernen — SQL-Code-Blöcke:**

```sql
-- name: get_memory_ranges
-- Holt aktive Memory-Ranges für eine Session
SELECT start_message_id, end_message_id FROM memories 
WHERE session_id = ? AND is_active = 1
  AND start_message_id IS NOT NULL AND end_message_id IS NOT NULL;

-- name: get_session_memory_marker
-- Holt den Memory-Marker einer Session (Fallback)
SELECT last_memory_message_id FROM chat_sessions WHERE id = ?;
```

```sql
-- name: count_user_messages_since_marker
-- Zählt User-Nachrichten seit dem Memory-Marker
SELECT COUNT(*) FROM chat_messages 
WHERE session_id = ? AND is_user = 1 AND id > ?;
```

```sql
-- name: get_messages_since_marker_count
-- Zählt Nachrichten seit dem Marker
SELECT COUNT(*) FROM chat_messages WHERE session_id = ? AND id > ?;
```

```sql
-- name: get_messages_since_marker
-- Holt Nachrichten seit dem Marker (neueste zuerst, nach ID sortiert)
SELECT id, message, is_user, timestamp, character_name
FROM chat_messages 
WHERE session_id = ? AND id > ?
ORDER BY id DESC
LIMIT ?;
```

**Behalten:** `count_all_user_messages`, `get_all_messages_count`, `get_all_messages_limited` — diese werden ggf. noch als Fallback verwendet.

---

### 8. `src/utils/services/chat_service.py` — Memory-Referenzen entfernen

Dies ist die **kritischste Datei**. Memory ist tief in den Chat-Flow integriert.

#### 8a. Import entfernen (Zeile 15)

```python
# ENTFERNEN:
from ..prompt_engine.memory_context import format_memories_for_prompt
```

#### 8b. Methode `_load_memory_context` entfernen (Zeilen 42–57)

```python
# ENTFERNEN:
    def _load_memory_context(self, persona_id: str = None) -> str:
        """
        Lädt und formatiert Memories aus der DB.
        Zentrale Memory-Loading-Logik (statt 3x dupliziert).
        """
        try:
            from ..database import get_active_memories
            if persona_id is None:
                from ..config import get_active_persona_id
                persona_id = get_active_persona_id()
            memories = get_active_memories(persona_id=persona_id)
            return format_memories_for_prompt(memories, engine=self._engine)
        except Exception as e:
            log.warning("Memories konnten nicht geladen werden: %s", e)
            return ''
```

#### 8c. `_build_chat_messages` — Parameter `memory_context` entfernen

**Signatur ändern (Zeile 59–60):**
```python
# VORHER:
    def _build_chat_messages(self, user_message: str, conversation_history: list,
                              memory_context: str, char_name: str, user_name: str,
                              nsfw_mode: bool, pending_afterthought: str = None) -> tuple:

# NACHHER:
    def _build_chat_messages(self, user_message: str, conversation_history: list,
                              char_name: str, user_name: str,
                              nsfw_mode: bool, pending_afterthought: str = None) -> tuple:
```

**Docstring anpassen (Zeile 65):**
```python
# VORHER:
        - first_assistant: Memory + Prefill-Impersonation

# NACHHER:
        - first_assistant: Prefill-Impersonation
```

**`first_assistant`-Block vereinfachen (Zeilen 112–140):**
```python
# VORHER:
            if position == 'first_assistant':
                # Memory + Prefill-Impersonation kombiniert
                first_parts = []
                if memory_context:
                    first_parts.append(memory_context)
                if prefill_imp_text:
                    first_parts.append(prefill_imp_text)
                # ... (komplexe Logik mit dialog_injections und first_parts)

# NACHHER:
            if position == 'first_assistant':
                # Prefill-Impersonation
                first_parts = []
                if prefill_imp_text:
                    first_parts.append(prefill_imp_text)
                # ... (gleiche Logik, aber ohne memory_context)
```

**Kommentare bereinigen (Zeile 149–150, 156):**
```python
# ENTFERNEN alle Referenzen auf "Memory" in Kommentaren:
#   "(z.B. Memory + Greeting)"
#   "Memory → Greeting"
```

#### 8d. `chat_stream` — Memory-Loading entfernen (Zeilen 264–271)

```python
# ENTFERNEN:
        # 2. Memories laden
        memory_context = ''
        memory_tokens_est = 0
        if include_memories:
            memory_context = self._load_memory_context(persona_id)
            if memory_context:
                memory_tokens_est = len(memory_context)
```

**Aufruf von `_build_chat_messages` anpassen (Zeile 273–276):**
```python
# VORHER:
        messages, msg_stats = self._build_chat_messages(
            user_message, conversation_history, memory_context,
            char_name, user_name, experimental_mode,
            pending_afterthought=pending_afterthought
        )

# NACHHER:
        messages, msg_stats = self._build_chat_messages(
            user_message, conversation_history,
            char_name, user_name, experimental_mode,
            pending_afterthought=pending_afterthought
        )
```

**Parameter `include_memories` aus `chat_stream`-Signatur entfernen (Zeile 240):**
```python
# VORHER:
    def chat_stream(self, ..., include_memories: bool = True, ...)

# NACHHER:
    def chat_stream(self, ..., ...)  # include_memories entfällt
```

**Stats-Berechnung bereinigen (Zeilen 305–316):**
```python
# VORHER:
                total_est = system_prompt_est + memory_tokens_est + msg_stats['history_est'] + ...
                yield ('done', {
                    'response': event.data['response'],
                    'stats': {
                        ...
                        'memory_est': memory_tokens_est,
                        ...
                    }
                })

# NACHHER:
                total_est = system_prompt_est + msg_stats['history_est'] + ...
                yield ('done', {
                    'response': event.data['response'],
                    'stats': {
                        ...
                        # memory_est entfällt
                        ...
                    }
                })
```

#### 8e. `afterthought_decision` — Memory-Loading entfernen (Zeilen 368–374)

```python
# ENTFERNEN:
            # Memories laden (zentral, nicht dupliziert)
            memory_context = self._load_memory_context(persona_id)

            # Nachrichtenverlauf + innere Dialog-Anweisung
            messages = []
            if memory_context:
                messages.append({'role': 'assistant', 'content': memory_context})

# ERSETZEN MIT:
            messages = []
```

#### 8f. `afterthought_followup` — Memory-Loading entfernen (Zeilen 475–482)

```python
# ENTFERNEN:
            # Memories laden (zentral)
            memory_context = self._load_memory_context(persona_id)

            # Nachrichtenverlauf + Followup-Anweisung
            messages = []
            if memory_context:
                messages.append({'role': 'assistant', 'content': memory_context})

# ERSETZEN MIT:
            messages = []
```

---

### 9. `src/utils/provider.py` — MemoryService entfernen

**Zu entfernen/ändern:**

| Zeile | Code | Aktion |
|-------|------|--------|
| L10 | `from utils.provider import get_api_client, get_chat_service, get_memory_service` | `get_memory_service` aus Docstring-Beispiel entfernen |
| L18 | `_memory_service = None` | **Entfernen** |
| L29 | `global _api_client, _chat_service, _memory_service` | `_memory_service` entfernen |
| L31 | `from .services import ChatService, MemoryService` | `MemoryService` entfernen |
| L35 | `_memory_service = MemoryService(_api_client)` | **Entfernen** |
| L52–56 | `def get_memory_service(): ...` | **Gesamte Funktion entfernen** |

**Vorher:**
```python
_memory_service = None

def init_services(api_key: str = None):
    global _api_client, _chat_service, _memory_service
    from .services import ChatService, MemoryService
    _api_client = ApiClient(api_key=api_key)
    _chat_service = ChatService(_api_client)
    _memory_service = MemoryService(_api_client)

def get_memory_service():
    if _memory_service is None:
        raise RuntimeError("MemoryService nicht initialisiert")
    return _memory_service
```

**Nachher:**
```python
def init_services(api_key: str = None):
    global _api_client, _chat_service
    from .services import ChatService
    _api_client = ApiClient(api_key=api_key)
    _chat_service = ChatService(_api_client)
```

---

### 10. `src/utils/database/__init__.py` — Memory-Exports entfernen

**Zu entfernen (Zeilen 67–75):**
```python
# Memory functions
from .memories import (
    save_memory,
    get_all_memories,
    get_active_memories,
    update_memory,
    delete_memory,
    toggle_memory_status,
    set_last_memory_message_id,
    get_last_memory_message_id
)
```

**Zu entfernen aus `__all__` (Zeilen 117–124):**
```python
    # Memory Management
    'save_memory',
    'get_all_memories',
    'get_active_memories',
    'update_memory',
    'delete_memory',
    'toggle_memory_status',
    'set_last_memory_message_id',
    'get_last_memory_message_id',
```

**Zusätzlich prüfen:** `get_messages_since_marker` und `get_user_message_count_since_marker` werden aus `chat.py` exportiert. Diese sind Memory-Marker-abhängig → entfernen aus Exports und `__all__`:
```python
# ENTFERNEN aus chat-Imports:
    get_user_message_count_since_marker,
    get_messages_since_marker,

# ENTFERNEN aus __all__:
    'get_user_message_count_since_marker',
    'get_messages_since_marker',
```

---

### 11. `src/utils/services/__init__.py` — MemoryService-Export entfernen

**Vorher:**
```python
"""
Services Package – Orchestrierungsschicht.

Exportiert:
- ChatService: Chat + Afterthought Orchestrierung
- MemoryService: Memory-Summary Erstellung + Orchestrierung
"""

from .chat_service import ChatService
from .memory_service import MemoryService

__all__ = [
    'ChatService',
    'MemoryService',
]
```

**Nachher:**
```python
"""
Services Package – Orchestrierungsschicht.

Exportiert:
- ChatService: Chat + Afterthought Orchestrierung
"""

from .chat_service import ChatService

__all__ = [
    'ChatService',
]
```

---

### 12. `src/routes/__init__.py` — Blueprint-Registrierung entfernen

**Zu entfernen (Zeile 11):**
```python
from routes.memory import memory_bp
```

**Zu entfernen (Zeile 37):**
```python
    app.register_blueprint(memory_bp)
```

---

### 13. `src/app.py` — Kommentar anpassen

**Zeile 52 ändern:**
```python
# VORHER:
# Initialisiere Services (API-Client, Chat-Service, Memory-Service)

# NACHHER:
# Initialisiere Services (API-Client, Chat-Service)
```

---

### 14. `src/utils/database/chat.py` — Memory-Marker-Logik entfernen

#### 14a. `get_chat_history()` — Memory-Ranges und `memorized`-Feld entfernen (Zeilen 44–75)

```python
# ENTFERNEN (Zeilen 44–62):
    # Get memory ranges for this session (only ACTIVE memories with ranges)
    cursor.execute(sql('chat.get_memory_ranges'), (session_id,))
    memory_ranges = cursor.fetchall()
    
    # Fallback: If no ranges available, use old marker
    cursor.execute(sql('chat.get_session_memory_marker'), (session_id,))
    marker_row = cursor.fetchone()
    last_memory_message_id = marker_row[0] if marker_row and marker_row[0] else None
    
    # Helper function: Check if a message ID is in any memory range
    def is_memorized(msg_id):
        if memory_ranges:
            for start_id, end_id in memory_ranges:
                if start_id <= msg_id <= end_id:
                    return True
            return False
        # Fallback for old memories without ranges
        return last_memory_message_id is not None and msg_id <= last_memory_message_id

# ENTFERNEN aus message-dict (Zeile 74):
            'memorized': is_memorized(row[0])
```

#### 14b. `get_user_message_count_since_marker()` — Gesamte Funktion entfernen (Zeilen 257–285)

```python
# ENTFERNEN:
def get_user_message_count_since_marker(session_id: int, persona_id: str = 'default') -> int:
    """Counts user messages since the last memory marker. ..."""
    # ... gesamte Funktion
```

#### 14c. `get_messages_since_marker()` — Gesamte Funktion entfernen (Zeilen 377–425)

```python
# ENTFERNEN:
def get_messages_since_marker(session_id: int, persona_id: str = 'default', limit: int = 100) -> Dict[str, Any]:
    """Gets only messages AFTER the last memory marker. ..."""
    # ... gesamte Funktion
```

---

### 15. `src/utils/prompt_engine/engine.py` — `build_summary_prompt()` entfernen

**Zu entfernen (Zeilen 587–630+):**
```python
    def build_summary_prompt(self, variant: str = 'default',
                              runtime_vars: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Baut System-Prompt und Prefill für Memory-Zusammenfassungen."""
        # ... gesamte Methode
```

---

### 16. `src/utils/prompt_engine/migrator.py` — Placeholder entfernen

**Zeile 34 ändern:**
```python
# VORHER:
        'prompt_id_3', 'memory_entries'

# NACHHER:
        'prompt_id_3'
```

---

### 17. Prompt-JSON-Dateien — LÖSCHEN

| Datei | Beschreibung |
|-------|-------------|
| `src/instructions/prompts/memory_context.json` | Memory-Kontext Template |
| `src/instructions/prompts/summary_impersonation.json` | Summary Impersonation |
| `src/instructions/prompts/summary_persona_block.json` | Summary Persona Block |
| `src/instructions/prompts/summary_prefill_impersonation.json` | Summary Prefill |
| `src/instructions/prompts/summary_remember.json` | Summary Remember |
| `src/instructions/prompts/summary_char_description.json` | Summary Char Description |
| `src/instructions/prompts/summary_system_rule.json` | Summary System Rule |
| `src/instructions/prompts/summary_user_prompt.json` | Summary User Prompt |

**Zusätzlich:** Summary-Einträge aus den Manifest-Dateien entfernen:
- `src/instructions/prompts/_meta/prompt_manifest.json`
- `src/instructions/prompts/_defaults/_meta/prompt_manifest.json`
- `src/instructions/prompts/_defaults/summary_user_prompt.json` und weitere `_defaults/summary_*.json`

---

### 18. Test-Dateien

#### 18a. `tests/test_services/test_memory_service.py` — DATEI LÖSCHEN

Gesamte Datei (113 Zeilen) enthält ausschließlich Memory-Tests.

#### 18b. `tests/test_provider.py` — Memory-Tests entfernen

**Zu entfernen:**
- `test_get_memory_service_after_init` (Zeile 50–58)
- `test_get_memory_service_before_init_raises` (Zeile 73–77)
- Alle `patch('utils.services.MemoryService')` aus bestehenden Tests entfernen/anpassen

#### 18c. `tests/conftest.py` — Memory-Fixtures entfernen

**Zu entfernen (um Zeile 233–238):**
```python
    # build_summary_prompt returns dict with system_prompt + prefill
    mock_engine.build_summary_prompt.return_value = {
        ...
    }
    # resolve_prompt for summary_user_prompt
```

**Zusätzlich:** `memory_service` Fixture und `sample_memories` Fixture entfernen.

#### 18d. `tests/test_services/test_chat_service.py` — Mocks anpassen

**Zeile 31 und 68** — `patch.object(chat_service, '_load_memory_context', return_value='')` → Entfernen, da die Methode nicht mehr existiert.

**Zeile 57** — `'memory_est': 200` → Entfernen aus erwarteten Stats.

---

## Datenbank-Migration

### Schema-Änderungen

1. **`memories`-Tabelle droppen:**
   ```sql
   DROP TABLE IF EXISTS memories;
   ```

2. **`last_memory_message_id`-Spalte aus `chat_sessions` entfernen:**
   ```sql
   -- SQLite unterstützt kein ALTER TABLE DROP COLUMN vor Version 3.35.0
   -- Für ältere Versionen: Tabelle neu erstellen
   CREATE TABLE chat_sessions_new (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       title TEXT DEFAULT 'Neue Konversation',
       persona_id TEXT DEFAULT 'default',
       created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
       updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
   );
   INSERT INTO chat_sessions_new SELECT id, title, persona_id, created_at, updated_at FROM chat_sessions;
   DROP TABLE chat_sessions;
   ALTER TABLE chat_sessions_new RENAME TO chat_sessions;
   ```

3. **Indizes entfernen:**
   ```sql
   DROP INDEX IF EXISTS idx_memory_session;
   DROP INDEX IF EXISTS idx_memory_active;
   DROP INDEX IF EXISTS idx_memory_persona;
   ```

### Migration-Strategie

- Erstelle eine Migration-Datei `src/sql/migrations/001_remove_memories.sql`
- Führe die Migration beim App-Start aus (oder einmalig manuell)
- **Alle existierenden Per-Persona-DBs müssen migriert werden** (jede Persona hat ihre eigene SQLite-Datei)

---

## Reihenfolge der Entfernung (Abhängigkeiten)

Die Reihenfolge ist kritisch, um keine Import-Fehler zu erzeugen:

```
Phase 1: Routes (API-Schicht)
  ├── 1. src/routes/memory.py                → LÖSCHEN
  └── 2. src/routes/__init__.py              → memory_bp entfernen

Phase 2: Service-Schicht
  ├── 3. src/utils/services/memory_service.py → LÖSCHEN
  ├── 4. src/utils/services/__init__.py       → MemoryService entfernen
  └── 5. src/utils/provider.py               → _memory_service + get_memory_service() entfernen

Phase 3: Chat-Service (Memory-Integration)
  └── 6. src/utils/services/chat_service.py  → _load_memory_context, memory_context Parameter,
                                                include_memories Parameter, Stats entfernen

Phase 4: Database-Schicht
  ├── 7. src/utils/database/memories.py       → LÖSCHEN
  ├── 8. src/utils/database/chat.py           → Memory-Marker-Funktionen entfernen
  ├── 9. src/utils/database/__init__.py       → Memory-Exports entfernen
  ├── 10. src/sql/memories.sql                → LÖSCHEN (upsert_db_info vorher verschieben!)
  ├── 11. src/sql/chat.sql                    → Memory-Marker-Queries entfernen
  └── 12. src/sql/schema.sql                  → memories Tabelle + Marker-Spalte entfernen

Phase 5: Prompt Engine
  ├── 13. src/utils/prompt_engine/memory_context.py → LÖSCHEN
  ├── 14. src/utils/prompt_engine/engine.py    → build_summary_prompt() entfernen
  ├── 15. src/utils/prompt_engine/migrator.py  → memory_entries Placeholder entfernen
  └── 16. src/instructions/prompts/            → memory_context.json + summary_*.json LÖSCHEN
                                                  + Manifest-Einträge bereinigen

Phase 6: App-Einstiegspunkt
  └── 17. src/app.py                          → Kommentar anpassen

Phase 7: Tests
  ├── 18. tests/test_services/test_memory_service.py → LÖSCHEN
  ├── 19. tests/test_provider.py               → Memory-Tests entfernen
  ├── 20. tests/conftest.py                    → Fixtures entfernen
  └── 21. tests/test_services/test_chat_service.py → Mocks anpassen

Phase 8: Datenbank-Migration (Runtime)
  └── 22. Migration-Script für existierende DBs ausführen
```

---

## Risikobewertung

### 🔴 Hohes Risiko

| Bereich | Risiko | Mitigation |
|---------|--------|-----------|
| **ChatService `_build_chat_messages`** | Die `first_assistant`-Position baut Memory + Prefill zusammen. Ohne Memory wird ggf. kein erster Assistant-Block mehr erzeugt, was die Nachrichten-Reihenfolge (user/assistant-Alternation) brechen kann. | Sorgfältig testen: Was passiert wenn `first_parts` **leer** ist und keine `dialog_injections` vorliegen? Der `first_assistant`-Block erzeugt dann **nichts** → History muss direkt beginnen. |
| **ChatService `chat_stream` Stats** | Frontend erwartet `memory_est` im Stats-Objekt. Wenn das Feld verschwindet, könnten JS-Fehler auftreten. | Frontend-Code prüfen, ob `memory_est` optional gelesen wird (ggf. `?.` oder Default). |
| **`get_chat_history` `memorized`-Feld** | Frontend verwendet das `memorized`-Feld um Memory-Indikatoren an Nachrichten anzuzeigen. Entfernung erzeugt ggf. fehlende UI-Elemente. | Erst in Schritt 1B (Frontend) entfernen – **oder** das Feld vorübergehend hardcoded auf `false` setzen. |
| **`include_memories` Parameter in Route-Aufrufen** | Wenn `routes/chat.py` den Parameter `include_memories=True` an `chat_stream` übergibt, muss dieser Aufruf angepasst werden. | Alle Aufrufer von `chat_stream` suchen und `include_memories` entfernen. |

### 🟡 Mittleres Risiko

| Bereich | Risiko | Mitigation |
|---------|--------|-----------|
| **`upsert_db_info` in `memories.sql`** | Dieses Query ist generisch und wird möglicherweise woanders via `sql('memories.upsert_db_info')` aufgerufen. | Vor dem Löschen codebase-weite Suche nach `upsert_db_info` durchführen. Ggf. nach `schema.sql` oder `db_info.sql` verschieben. |
| **DB-Migration bei existierenden Nutzern** | SQLite `ALTER TABLE DROP COLUMN` funktioniert erst ab Version 3.35.0. Ältere Versionen brauchen Tabellenrekonstruktion. | Python's `sqlite3`-Modul-Version prüfen. Migration robust implementieren. |
| **`afterthought_decision` / `afterthought_followup`** | Beide Methoden laden aktuell Memory-Kontext. Ohne Memory fehlt dem Afterthought der Langzeit-Kontext. | Akzeptabler Verlust – wird durch Cortex-System ersetzt. |

### 🟢 Niedriges Risiko

| Bereich | Risiko | Mitigation |
|---------|--------|-----------|
| **Prompt-JSON-Dateien** | Summary-Prompts werden nur von MemoryService verwendet. | Einfach löschbar nach Service-Entfernung. |
| **Test-Dateien** | Tests sind isoliert. | Löschen/Anpassen nach Code-Änderungen. |
| **Manifest-Bereinigung** | Summary-Einträge im Manifest haben keine Seiteneffekte. | Einträge mit `category: 'summary'` entfernen. |

---

## Frontend-Hinweis (Schritt 1B)

Die folgenden Frontend-Dateien müssen in **Schritt 1B** behandelt werden (nicht in diesem Schritt):

| Datei | Beschreibung |
|-------|-------------|
| `frontend/src/services/memoryApi.js` | Memory-API-Aufrufe |
| `frontend/src/features/overlays/MemoryOverlay.jsx` | Memory-Verwaltungs-UI |
| `frontend/src/features/overlays/DebugOverlay.jsx` | Memory-Debug-Anzeige |
| `frontend/src/features/overlays/index.js` | `MemoryOverlay` Export |

---

## Checkliste nach Entfernung

- [ ] `python -m pytest` — alle Tests bestehen
- [ ] App startet ohne Import-Fehler
- [ ] Chat-Stream funktioniert (ohne Memory)
- [ ] Afterthought funktioniert (ohne Memory)
- [ ] Keine `500`-Fehler auf ehemaligen `/api/memory/*`-Routen (404 erwartet)
- [ ] `grep -r "memory" src/` zeigt keine verwaisten Referenzen
- [ ] Datenbank-Migration wurde für alle Persona-DBs ausgeführt
