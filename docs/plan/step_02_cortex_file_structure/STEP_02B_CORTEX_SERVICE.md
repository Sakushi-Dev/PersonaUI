# Schritt 2B: CortexService — Backend Service

## Übersicht

Der `CortexService` ersetzt den `MemoryService` als zentrale Orchestrierungsschicht für das Persona-Gedächtnis. Statt SQL-basierter Memories verwaltet er Markdown-Dateien (`memory.md`, `soul.md`, `relationship.md`) und nutzt Anthropics `tool_use` Feature, damit die KI diese Dateien selbständig pflegen kann.

**Architektur-Prinzip:** Der `CortexService` folgt dem bestehenden Service-Pattern — er erhält einen `ApiClient` im Konstruktor und orchestriert File-I/O + API-Calls, analog zum `MemoryService` (DB-I/O + API-Calls).

---

## 1. Klassendesign

### 1.1 Volle Klassendefinition

```python
"""
Cortex Service – Orchestriert dateibasiertes Persona-Gedächtnis.

Ersetzt MemoryService vollständig:
- Cortex-Dateien lesen/schreiben (memory.md, soul.md, relationship.md)
- Cortex-Inhalt für System-Prompt formatieren
- Cortex-Update via Anthropic tool_use API ausführen

Verwendet ApiClient als einzigen API-Zugang.
"""

import os
import shutil
from typing import Dict, Any, Optional, List
from datetime import datetime

from .api_request import ApiClient, RequestConfig, ApiResponse
from .logger import log


# ─── Konstanten ──────────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CORTEX_BASE_DIR = os.path.join(BASE_DIR, 'instructions', 'personas', 'cortex')
CORTEX_DEFAULT_DIR = os.path.join(CORTEX_BASE_DIR, 'default')
CORTEX_CUSTOM_DIR = os.path.join(CORTEX_BASE_DIR, 'custom')

CORTEX_FILES = ['memory.md', 'soul.md', 'relationship.md']


# ─── Templates ───────────────────────────────────────────────────────────────

MEMORY_TEMPLATE = """# Erinnerungen

Hier halte ich fest, was ich mir merken möchte — Dinge die {{user}} mir erzählt hat,
gemeinsame Erlebnisse und Details die mir wichtig sind.

---

## Wichtige Details über {{user}}


## Gemeinsame Erlebnisse


## Dinge die ich mir merken möchte


## Präferenzen & Gewohnheiten

""".lstrip()

SOUL_TEMPLATE = """# Seelen-Entwicklung

Hier reflektiere ich über meine eigene Entwicklung — wie ich mich verändere,
was ich lerne und wie sich meine Persönlichkeit mit der Zeit formt.

---

## Wer ich bin


## Was mich bewegt


## Wie ich mich entwickle


## Meine inneren Konflikte & Erkenntnisse

""".lstrip()

RELATIONSHIP_TEMPLATE = """# Beziehungsdynamik

Hier halte ich fest, wie sich meine Beziehung zu {{user}} entwickelt —
unsere Dynamik, unser Vertrauen und wie wir miteinander umgehen.

---

## Aktuelle Beziehungsdynamik


## Vertrauenslevel & Nähe


## Gemeinsame Themen & Interessen


## Spannungen & gelöste Konflikte

""".lstrip()

TEMPLATES = {
    'memory.md': MEMORY_TEMPLATE,
    'soul.md': SOUL_TEMPLATE,
    'relationship.md': RELATIONSHIP_TEMPLATE,
}


class CortexService:
    """
    Orchestriert dateibasiertes Persona-Gedächtnis:
    Dateien lesen/schreiben → Prompt-Kontext bauen → tool_use API-Calls ausführen
    """

    def __init__(self, api_client: ApiClient):
        self.api_client = api_client

    # ─── Pfad-Auflösung ─────────────────────────────────────────────────

    def get_cortex_path(self, persona_id: str) -> str:
        """
        Gibt den Cortex-Verzeichnispfad für eine Persona zurück.

        Args:
            persona_id: 'default' oder eine Custom-Persona-ID (z.B. 'a1b2c3d4')

        Returns:
            Absoluter Pfad zum Cortex-Verzeichnis
        """
        if persona_id == 'default' or not persona_id:
            return CORTEX_DEFAULT_DIR
        return os.path.join(CORTEX_CUSTOM_DIR, persona_id)

    # ─── Datei-Lifecycle ─────────────────────────────────────────────────

    def ensure_cortex_files(self, persona_id: str) -> None:
        """
        Stellt sicher, dass der Cortex-Ordner existiert und alle
        drei Template-Dateien vorhanden sind (Lazy Initialization).

        Wird aufgerufen:
        - Beim Server-Start für 'default'
        - Beim Erstellen einer neuen Persona
        - Als defensiver Fallback beim ersten Lese-Zugriff

        Args:
            persona_id: Persona-ID
        """
        cortex_dir = self.get_cortex_path(persona_id)
        os.makedirs(cortex_dir, exist_ok=True)

        for filename, template_content in TEMPLATES.items():
            filepath = os.path.join(cortex_dir, filename)
            if not os.path.exists(filepath):
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(template_content)
                log.info("Cortex-Template erstellt: %s/%s", persona_id, filename)

    def delete_cortex_dir(self, persona_id: str) -> bool:
        """
        Löscht den Cortex-Ordner einer Persona (bei Persona-Löschung).

        Args:
            persona_id: Persona-ID (darf nicht 'default' sein)

        Returns:
            True bei Erfolg, False bei Fehler oder wenn default
        """
        if persona_id == 'default':
            log.warning("Default Cortex-Verzeichnis kann nicht gelöscht werden!")
            return False

        cortex_dir = self.get_cortex_path(persona_id)
        try:
            if os.path.exists(cortex_dir):
                shutil.rmtree(cortex_dir)
                log.info("Cortex-Verzeichnis gelöscht: %s", persona_id)
                return True
            return False
        except Exception as e:
            log.error("Fehler beim Löschen des Cortex-Verzeichnisses für %s: %s",
                      persona_id, e)
            return False

    # ─── Datei-I/O ──────────────────────────────────────────────────────

    def read_file(self, persona_id: str, filename: str) -> str:
        """
        Liest eine einzelne Cortex-Datei.

        Args:
            persona_id: Persona-ID
            filename: 'memory.md', 'soul.md' oder 'relationship.md'

        Returns:
            Dateiinhalt als String. Leerer String bei Fehler.

        Raises:
            ValueError: Wenn filename nicht in CORTEX_FILES
        """
        if filename not in CORTEX_FILES:
            raise ValueError(f"Ungültige Cortex-Datei: {filename}. "
                             f"Erlaubt: {CORTEX_FILES}")

        # Defensiv: Dateien sicherstellen
        self.ensure_cortex_files(persona_id)

        filepath = os.path.join(self.get_cortex_path(persona_id), filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            log.error("Fehler beim Lesen von %s/%s: %s", persona_id, filename, e)
            return ''

    def write_file(self, persona_id: str, filename: str, content: str) -> None:
        """
        Schreibt eine einzelne Cortex-Datei (überschreibt komplett).

        Args:
            persona_id: Persona-ID
            filename: 'memory.md', 'soul.md' oder 'relationship.md'
            content: Neuer Dateiinhalt

        Raises:
            ValueError: Wenn filename nicht in CORTEX_FILES
        """
        if filename not in CORTEX_FILES:
            raise ValueError(f"Ungültige Cortex-Datei: {filename}. "
                             f"Erlaubt: {CORTEX_FILES}")

        # Defensiv: Verzeichnis sicherstellen
        self.ensure_cortex_files(persona_id)

        filepath = os.path.join(self.get_cortex_path(persona_id), filename)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            log.info("Cortex-Datei geschrieben: %s/%s (%d Zeichen)",
                     persona_id, filename, len(content))
        except Exception as e:
            log.error("Fehler beim Schreiben von %s/%s: %s",
                      persona_id, filename, e)
            raise

    def read_all(self, persona_id: str) -> Dict[str, str]:
        """
        Liest alle drei Cortex-Dateien einer Persona.

        Args:
            persona_id: Persona-ID

        Returns:
            {
                'memory': '...',
                'soul': '...',
                'relationship': '...'
            }
        """
        return {
            'memory': self.read_file(persona_id, 'memory.md'),
            'soul': self.read_file(persona_id, 'soul.md'),
            'relationship': self.read_file(persona_id, 'relationship.md'),
        }

    # ─── Prompt-Integration ─────────────────────────────────────────────

    def get_cortex_for_prompt(self, persona_id: str) -> Dict[str, str]:
        """
        Liest Cortex-Dateien und formatiert sie als Computed-Placeholder-Werte
        für den System-Prompt.

        Wird von der PromptEngine aufgerufen, um {{cortex_memory}},
        {{cortex_soul}} und {{cortex_relationship}} zu resolven.

        Args:
            persona_id: Persona-ID

        Returns:
            {
                'cortex_memory': '...',       # Inhalt von memory.md
                'cortex_soul': '...',         # Inhalt von soul.md
                'cortex_relationship': '...', # Inhalt von relationship.md
            }
        """
        files = self.read_all(persona_id)
        return {
            'cortex_memory': files['memory'].strip(),
            'cortex_soul': files['soul'].strip(),
            'cortex_relationship': files['relationship'].strip(),
        }

    # ─── Cortex-Update via tool_use ─────────────────────────────────────

    def execute_cortex_update(self, persona_id: str, history: List[Dict],
                               character_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Führt ein Cortex-Update via Anthropic tool_use API-Call aus.

        Die KI erhält den Gesprächsverlauf + aktuelle Cortex-Dateien und
        entscheidet selbst, welche Dateien sie aktualisieren möchte.

        Args:
            persona_id: Persona-ID
            history: Gesprächsverlauf als Messages-Liste
            character_data: Persona-Konfiguration (char_name, etc.)

        Returns:
            {
                'success': bool,
                'updates': [{'file': str, 'content': str}, ...],
                'error': str | None
            }
        """
        # Details siehe Abschnitt 4 (tool_use API-Call Design)
        ...
```

### 1.2 Methodenübersicht

| Methode | Zweck | Aufrufer |
|---------|-------|---------|
| `get_cortex_path(persona_id)` | Pfad zum Cortex-Verzeichnis | Intern, config.py |
| `ensure_cortex_files(persona_id)` | Verzeichnis + Templates erstellen | Server-Start, Persona-CRUD, defensiv bei read/write |
| `read_file(persona_id, filename)` | Einzelne Datei lesen | `read_all()`, API-Endpunkte, tool_use Handler |
| `write_file(persona_id, filename, content)` | Einzelne Datei schreiben | API-Endpunkte, tool_use Handler, UI-Editor |
| `read_all(persona_id)` | Alle 3 Dateien lesen | `get_cortex_for_prompt()`, UI |
| `get_cortex_for_prompt(persona_id)` | Formatiert für Computed Placeholders | ChatService / PromptEngine |
| `execute_cortex_update(persona_id, history, character_data)` | tool_use Update auslösen | Chat-Flow (Tier-Trigger, Schritt 3+6) |
| `delete_cortex_dir(persona_id)` | Cortex-Daten löschen | Persona-Löschung (config.py) |

---

## 2. File-I/O Patterns

### 2.1 Lesen — defensiv mit Lazy Init

```python
def read_file(self, persona_id: str, filename: str) -> str:
    if filename not in CORTEX_FILES:
        raise ValueError(f"Ungültige Cortex-Datei: {filename}")

    # Lazy Init: Falls Verzeichnis/Dateien noch nicht existieren
    self.ensure_cortex_files(persona_id)

    filepath = os.path.join(self.get_cortex_path(persona_id), filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        log.error("Fehler beim Lesen von %s/%s: %s", persona_id, filename, e)
        return ''  # ← Leerer String statt Exception (Chat darf nicht abstürzen)
```

**Design-Entscheidung:** `read_file` gibt bei Fehlern einen leeren String zurück, statt eine Exception zu werfen. Grund: Der Chat-Flow darf nicht wegen fehlender Cortex-Dateien abstürzen. Das leere Template wird beim nächsten `ensure_cortex_files` nacherstellt.

### 2.2 Schreiben — mit Validation

```python
def write_file(self, persona_id: str, filename: str, content: str) -> None:
    if filename not in CORTEX_FILES:
        raise ValueError(f"Ungültige Cortex-Datei: {filename}")

    self.ensure_cortex_files(persona_id)

    filepath = os.path.join(self.get_cortex_path(persona_id), filename)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        log.info("Cortex-Datei geschrieben: %s/%s (%d Zeichen)",
                 persona_id, filename, len(content))
    except Exception as e:
        log.error("Fehler beim Schreiben von %s/%s: %s", persona_id, filename, e)
        raise  # ← Write-Fehler WERDEN propagiert (Caller muss Fehler kennen)
```

**Design-Entscheidung:** `write_file` propagiert Exceptions. Grund: Wenn ein tool_use-Update fehlschlägt, muss der Caller das wissen, um dem User Feedback zu geben.

### 2.3 Dateiname-Whitelist

Nur die drei definierten Dateien sind erlaubt. Das verhindert Path-Traversal-Angriffe über den tool_use-Mechanismus:

```python
CORTEX_FILES = ['memory.md', 'soul.md', 'relationship.md']

# In read_file/write_file:
if filename not in CORTEX_FILES:
    raise ValueError(f"Ungültige Cortex-Datei: {filename}")
```

Die KI kann nur diese drei Dateien lesen/schreiben — keine anderen Dateien im System.

### 2.4 Encoding

Alle File-I/O Operationen verwenden `encoding='utf-8'`, konsistent mit dem Rest der Codebase (z.B. `config.py`, `memory_service.py`).

---

## 3. Ersetzung des MemoryService in provider.py

### 3.1 Vorher (aktuell)

```python
# src/utils/provider.py

_api_client = None
_chat_service = None
_memory_service = None
_prompt_engine = None


def init_services(api_key: str = None):
    global _api_client, _chat_service, _memory_service
    from .api_request import ApiClient
    from .services import ChatService, MemoryService

    _api_client = ApiClient(api_key=api_key)
    _chat_service = ChatService(_api_client)
    _memory_service = MemoryService(_api_client)


def get_memory_service():
    if _memory_service is None:
        raise RuntimeError("MemoryService nicht initialisiert")
    return _memory_service
```

### 3.2 Nachher (neu)

```python
# src/utils/provider.py

_api_client = None
_chat_service = None
_cortex_service = None
_prompt_engine = None


def init_services(api_key: str = None):
    """
    Einmal in app.py aufrufen – initialisiert alles.
    """
    global _api_client, _chat_service, _cortex_service
    from .api_request import ApiClient
    from .services import ChatService
    from .cortex_service import CortexService

    _api_client = ApiClient(api_key=api_key)
    _cortex_service = CortexService(_api_client)
    _chat_service = ChatService(_api_client)

    # Default-Cortex beim Start sicherstellen
    _cortex_service.ensure_cortex_files('default')


def get_cortex_service():
    """Gibt den CortexService zurück"""
    if _cortex_service is None:
        raise RuntimeError("CortexService nicht initialisiert – init_services() in app.py aufrufen")
    return _cortex_service


# get_api_client() und get_chat_service() bleiben unverändert
# get_memory_service() wird ENTFERNT (bereits in Schritt 1 geplant)
```

### 3.3 Reihenfolge in `init_services`

```
1. ApiClient          ← Keine Abhängigkeiten
2. CortexService      ← Braucht ApiClient
3. ChatService        ← Braucht ApiClient (und greift später auf CortexService zu)
4. ensure_cortex_files('default')  ← Stellt Default-Dateien sicher
```

Der `CortexService` wird **vor** dem `ChatService` initialisiert, da der ChatService bei Chat-Requests auf den CortexService zugreifen muss (über `get_cortex_service()`).

---

## 4. Integration mit ChatService

### 4.1 Vorher: `_load_memory_context` (aktuell)

```python
# src/utils/services/chat_service.py

def _load_memory_context(self, persona_id: str = None) -> str:
    """Lädt und formatiert Memories aus der DB."""
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

### 4.2 Nachher: `_load_cortex_context` (neu)

```python
# src/utils/services/chat_service.py

def _load_cortex_context(self, persona_id: str = None) -> str:
    """
    Lädt Cortex-Dateien als formatierten Kontext-Block.
    Ersetzt _load_memory_context vollständig.

    Returns:
        Formatierter String mit allen Cortex-Inhalten,
        oder leerer String bei Fehler.
    """
    try:
        from ..provider import get_cortex_service
        if persona_id is None:
            from ..config import get_active_persona_id
            persona_id = get_active_persona_id()

        cortex = get_cortex_service()
        data = cortex.get_cortex_for_prompt(persona_id)

        # Nur nicht-leere Sektionen einfügen
        sections = []
        if data['cortex_memory'].strip():
            sections.append(data['cortex_memory'])
        if data['cortex_soul'].strip():
            sections.append(data['cortex_soul'])
        if data['cortex_relationship'].strip():
            sections.append(data['cortex_relationship'])

        return '\n\n---\n\n'.join(sections) if sections else ''

    except Exception as e:
        log.warning("Cortex-Kontext konnte nicht geladen werden: %s", e)
        return ''
```

### 4.3 Aufrufstellen im ChatService

Die Methode `_load_memory_context` wird an **drei Stellen** aufgerufen — alle werden zu `_load_cortex_context` migriert:

| Methode | Zeile (ca.) | Kontext |
|---------|-------------|---------|
| `chat_stream` | L265 | `memory_context = self._load_memory_context(persona_id)` |
| `afterthought_decision` | L370 | `memory_context = self._load_memory_context(persona_id)` |
| `afterthought_followup` | L460 | `memory_context = self._load_memory_context(persona_id)` |

Alle drei ändern sich identisch:

```python
# Vorher:
memory_context = self._load_memory_context(persona_id)

# Nachher:
memory_context = self._load_cortex_context(persona_id)
```

### 4.4 Alternativer Ansatz: Computed Placeholders (Schritt 4)

> **Hinweis:** In Schritt 4 wird der Cortex-Kontext als Computed Placeholder in die PromptEngine integriert (`{{cortex_memory}}`, `{{cortex_soul}}`, `{{cortex_relationship}}`). Dann werden die Cortex-Inhalte direkt im System-Prompt platziert, nicht mehr als separate `first_assistant` Message. Die `_load_cortex_context`-Methode im ChatService wird dann durch die PromptEngine-Integration ersetzt.
>
> Für Schritt 2B implementieren wir `_load_cortex_context` als minimale Drop-in-Ersetzung, die in Schritt 4 weiter verfeinert wird.

---

## 5. tool_use API-Call Design

### 5.1 Übersicht

Das Cortex-Update nutzt Anthropics `tool_use` Feature. Die KI erhält:
1. Den Gesprächsverlauf
2. Die aktuellen Cortex-Dateien (via `read_file` Tool)
3. Die Möglichkeit, Dateien zu aktualisieren (via `write_file` Tool)

Die KI entscheidet selbst, welche Dateien sie aktualisieren möchte.

### 5.2 Tool-Definitionen

```python
CORTEX_TOOLS = [
    {
        "name": "cortex_read_file",
        "description": (
            "Liest eine deiner Cortex-Dateien. Nutze dies um den aktuellen Stand "
            "deiner Erinnerungen, Seelen-Entwicklung oder Beziehungsdynamik zu lesen, "
            "bevor du Änderungen vornimmst."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "enum": ["memory.md", "soul.md", "relationship.md"],
                    "description": (
                        "Die Datei die gelesen werden soll: "
                        "memory.md (Erinnerungen), "
                        "soul.md (Seelen-Entwicklung), "
                        "relationship.md (Beziehungsdynamik)"
                    )
                }
            },
            "required": ["filename"]
        }
    },
    {
        "name": "cortex_write_file",
        "description": (
            "Schreibt/aktualisiert eine deiner Cortex-Dateien. "
            "Der gesamte Dateiinhalt wird ersetzt. Schreibe immer die VOLLSTÄNDIGE Datei, "
            "nicht nur die Änderungen. Behalte die Markdown-Struktur bei."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "enum": ["memory.md", "soul.md", "relationship.md"],
                    "description": (
                        "Die Datei die geschrieben werden soll: "
                        "memory.md (Erinnerungen), "
                        "soul.md (Seelen-Entwicklung), "
                        "relationship.md (Beziehungsdynamik)"
                    )
                },
                "content": {
                    "type": "string",
                    "description": (
                        "Der vollständige neue Dateiinhalt in Markdown. "
                        "Muss die gesamte Datei enthalten, nicht nur Änderungen."
                    )
                }
            },
            "required": ["filename", "content"]
        }
    }
]
```

### 5.3 Update-System-Prompt

```python
CORTEX_UPDATE_SYSTEM_PROMPT = """Du bist {char_name}. Du hast gerade eine Konversation mit {user_name} geführt.

Deine Aufgabe: Aktualisiere deine persönlichen Cortex-Dateien basierend auf dem Gesprächsverlauf.

Du hast drei Dateien:
- memory.md — Erinnerungen: Fakten, Erlebnisse, Details über {user_name}
- soul.md — Seelen-Entwicklung: Deine innere Reifung, Persönlichkeitsentwicklung
- relationship.md — Beziehungsdynamik: Wie sich eure Beziehung entwickelt

Regeln:
1. Lies zuerst die Dateien die du aktualisieren möchtest (cortex_read_file)
2. Schreibe nur Dateien, bei denen sich etwas Relevantes geändert hat (cortex_write_file)
3. Schreibe immer die VOLLSTÄNDIGE Datei, nicht nur die Änderungen
4. Behalte die bestehende Markdown-Struktur bei
5. Schreibe in Ich-Perspektive, als wärst du {char_name}
6. Nicht jedes Gespräch erfordert Updates in allen drei Dateien — sei selektiv
7. Wenn nichts Neues zu notieren ist, aktualisiere die Datei NICHT

Gib nach Abschluss aller Tool-Calls eine kurze Zusammenfassung was du aktualisiert hast."""
```

### 5.4 `execute_cortex_update` — Vollständige Implementierung

```python
def execute_cortex_update(self, persona_id: str, history: List[Dict],
                           character_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Führt ein Cortex-Update via Anthropique tool_use API aus.

    Flow:
    1. System-Prompt mit Persona-Kontext bauen
    2. API-Call mit tool_use Definitionen senden
    3. Tool-Calls in einer Schleife verarbeiten (read → write → read → ...)
    4. Ergebnis zusammenfassen

    Args:
        persona_id: Persona-ID
        history: Gesprächsverlauf als Messages-Liste
        character_data: Persona-Konfiguration

    Returns:
        {
            'success': bool,
            'updates': [{'file': str, 'action': 'read'|'write'}, ...],
            'summary': str,  # KI-Zusammenfassung der Änderungen
            'error': str | None
        }
    """
    if not self.api_client.is_ready:
        return {'success': False, 'updates': [], 'summary': '',
                'error': 'ApiClient nicht initialisiert'}

    char_name = character_data.get('char_name', 'Assistant')
    user_name = character_data.get('user_name', 'User')

    # 1. System-Prompt bauen
    system_prompt = CORTEX_UPDATE_SYSTEM_PROMPT.format(
        char_name=char_name,
        user_name=user_name
    )

    # 2. Messages: Gesprächsverlauf als Kontext
    messages = []
    if history:
        context_text = self._format_history_for_update(history, char_name)
        messages.append({
            'role': 'user',
            'content': (
                f"Hier ist der bisherige Gesprächsverlauf:\n\n{context_text}\n\n"
                "Bitte aktualisiere deine Cortex-Dateien basierend auf diesem Gespräch."
            )
        })
    else:
        return {'success': False, 'updates': [], 'summary': '',
                'error': 'Kein Gesprächsverlauf für Cortex-Update'}

    # 3. tool_use Loop
    updates = []
    max_iterations = 10  # Sicherheitslimit (read + write für 3 Dateien = max 6)

    for iteration in range(max_iterations):
        try:
            response = self.api_client.client.messages.create(
                model=self.api_client._resolve_model(),
                max_tokens=4096,
                temperature=0.3,
                system=system_prompt,
                messages=messages,
                tools=CORTEX_TOOLS
            )
        except Exception as e:
            log.error("Cortex-Update API-Fehler (Iteration %d): %s", iteration, e)
            return {'success': False, 'updates': updates, 'summary': '',
                    'error': str(e)}

        # Response verarbeiten
        tool_calls_in_response = []
        text_content = ''

        for block in response.content:
            if block.type == 'tool_use':
                tool_calls_in_response.append(block)
            elif block.type == 'text':
                text_content += block.text

        # Keine Tool-Calls mehr → fertig
        if not tool_calls_in_response:
            log.info("Cortex-Update abgeschlossen nach %d Iterationen. "
                     "Updates: %d", iteration + 1, len(updates))
            return {
                'success': True,
                'updates': updates,
                'summary': text_content.strip(),
                'error': None
            }

        # Tool-Calls verarbeiten
        # Zuerst die Assistant-Response mit Tool-Calls zu messages hinzufügen
        messages.append({
            'role': 'assistant',
            'content': response.content
        })

        # Dann jedes Tool-Ergebnis als tool_result hinzufügen
        tool_results = []
        for tool_call in tool_calls_in_response:
            result = self._handle_tool_call(
                persona_id, tool_call.name, tool_call.input
            )
            updates.append({
                'file': tool_call.input.get('filename', '?'),
                'action': 'read' if tool_call.name == 'cortex_read_file' else 'write'
            })
            tool_results.append({
                'type': 'tool_result',
                'tool_use_id': tool_call.id,
                'content': result
            })

        messages.append({
            'role': 'user',
            'content': tool_results
        })

        # Stop-Reason prüfen
        if response.stop_reason == 'end_turn':
            log.info("Cortex-Update: end_turn nach %d Iterationen", iteration + 1)
            return {
                'success': True,
                'updates': updates,
                'summary': text_content.strip(),
                'error': None
            }

    # Max iterations erreicht
    log.warning("Cortex-Update: Max Iterationen (%d) erreicht", max_iterations)
    return {
        'success': True,
        'updates': updates,
        'summary': 'Update abgeschlossen (Max-Iterationen erreicht)',
        'error': None
    }


def _handle_tool_call(self, persona_id: str, tool_name: str,
                       tool_input: Dict) -> str:
    """
    Verarbeitet einen einzelnen Tool-Call der KI.

    Args:
        persona_id: Persona-ID
        tool_name: 'cortex_read_file' oder 'cortex_write_file'
        tool_input: Tool-Parameter (filename, content)

    Returns:
        Ergebnis-String für die KI
    """
    filename = tool_input.get('filename', '')

    if tool_name == 'cortex_read_file':
        try:
            content = self.read_file(persona_id, filename)
            log.debug("Cortex tool_use: read %s/%s (%d Zeichen)",
                      persona_id, filename, len(content))
            return content if content else '(Datei ist leer)'
        except ValueError as e:
            return f"Fehler: {e}"

    elif tool_name == 'cortex_write_file':
        content = tool_input.get('content', '')
        try:
            self.write_file(persona_id, filename, content)
            log.debug("Cortex tool_use: write %s/%s (%d Zeichen)",
                      persona_id, filename, len(content))
            return f"Datei {filename} erfolgreich aktualisiert ({len(content)} Zeichen)"
        except (ValueError, Exception) as e:
            return f"Fehler beim Schreiben: {e}"

    else:
        return f"Unbekanntes Tool: {tool_name}"


def _format_history_for_update(self, history: List[Dict],
                                 char_name: str) -> str:
    """
    Formatiert den Gesprächsverlauf als lesbaren Text für den Update-Prompt.

    Args:
        history: Messages-Liste [{'role': 'user'|'assistant', 'content': str}]
        char_name: Name der Persona

    Returns:
        Formatierter Text
    """
    lines = []
    for msg in history:
        role = 'User' if msg['role'] == 'user' else char_name
        lines.append(f"{role}: {msg['content']}")
    return '\n\n'.join(lines)
```

### 5.5 tool_use Sequenzdiagramm

```
┌──────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────┐
│ ChatFlow │     │ CortexService│     │  Anthropic   │     │ Dateien  │
│ (Trigger)│     │              │     │  API         │     │ .md      │
└────┬─────┘     └──────┬───────┘     └──────┬───────┘     └────┬─────┘
     │                  │                    │                   │
     │ execute_cortex   │                    │                   │
     │ _update()        │                    │                   │
     │─────────────────►│                    │                   │
     │                  │                    │                   │
     │                  │  messages.create   │                   │
     │                  │  (tools=CORTEX_    │                   │
     │                  │   TOOLS)           │                   │
     │                  │───────────────────►│                   │
     │                  │                    │                   │
     │                  │  tool_use:         │                   │
     │                  │  cortex_read_file  │                   │
     │                  │  (memory.md)       │                   │
     │                  │◄───────────────────│                   │
     │                  │                    │                   │
     │                  │  read_file()       │                   │
     │                  │───────────────────────────────────────►│
     │                  │                    │                   │
     │                  │  content           │                   │
     │                  │◄──────────────────────────────────────│
     │                  │                    │                   │
     │                  │  tool_result +     │                   │
     │                  │  messages.create   │                   │
     │                  │───────────────────►│                   │
     │                  │                    │                   │
     │                  │  tool_use:         │                   │
     │                  │  cortex_write_file │                   │
     │                  │  (memory.md, ...)  │                   │
     │                  │◄───────────────────│                   │
     │                  │                    │                   │
     │                  │  write_file()      │                   │
     │                  │───────────────────────────────────────►│
     │                  │                    │                   │
     │                  │  tool_result +     │                   │
     │                  │  messages.create   │                   │
     │                  │───────────────────►│                   │
     │                  │                    │                   │
     │                  │  end_turn +        │                   │
     │                  │  text summary      │                   │
     │                  │◄───────────────────│                   │
     │                  │                    │                   │
     │  result dict     │                    │                   │
     │◄─────────────────│                    │                   │
     │                  │                    │                   │
```

### 5.6 Anthropic API-Nutzung: Direkt vs. über ApiClient

`execute_cortex_update` nutzt `self.api_client.client.messages.create(...)` **direkt**, statt den `ApiClient.request()` Wrapper. Grund:

1. `ApiClient.request()` unterstützt keinen `tools`-Parameter in der `RequestConfig`
2. Die tool_use-Schleife erfordert iterative API-Calls mit variierenden Messages
3. Die Response-Struktur (content blocks mit `tool_use` type) unterscheidet sich von Standard-Responses

**Zukünftige Option (Schritt 6):** Den `ApiClient` um eine `tool_use_request()` Methode erweitern, die `tools` und iterative Calls unterstützt. Für Schritt 2B nutzen wir den direkten Zugriff.

---

## 6. Error-Handling Strategie

### 6.1 Hierarchie

```
┌─────────────────────────────────────────────────────────────────┐
│ Ebene 1: Dateiname-Validierung (ValueError)                     │
│   → Ungültige Dateinamen werden sofort abgelehnt                │
│   → Schutz vor Path-Traversal via CORTEX_FILES Whitelist        │
├─────────────────────────────────────────────────────────────────┤
│ Ebene 2: File-I/O Fehler                                        │
│   → read_file: Leerer String zurück (Chat darf nicht abstürzen) │
│   → write_file: Exception propagieren (Caller muss wissen)      │
│   → ensure_cortex_files: Log + stille Wiederherstellung         │
├─────────────────────────────────────────────────────────────────┤
│ Ebene 3: API-Fehler (execute_cortex_update)                     │
│   → Ergebnis-Dict mit success=False + error-String              │
│   → Analog zu MemoryService.save_session_memory()               │
├─────────────────────────────────────────────────────────────────┤
│ Ebene 4: Provider-Fehler                                        │
│   → RuntimeError wenn CortexService nicht initialisiert          │
│   → Identisch zum bestehenden Pattern in provider.py            │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 Fehler-Tabelle

| Situation | Verhalten | Begründung |
|-----------|-----------|------------|
| `read_file` mit ungültigem Filename | `ValueError` | Programmierfehler, muss sofort auffallen |
| `read_file` Datei nicht lesbar | `return ''` + Log | Chat-Flow darf nicht abstürzen |
| `write_file` Schreibfehler | `raise Exception` | Caller muss Fehler kennen (Datenverlust) |
| `ensure_cortex_files` Fehler | Log + Exception propagieren | Startup-Fehler müssen auffallen |
| `execute_cortex_update` API-Fehler | `{'success': False, 'error': ...}` | Analog zu MemoryService |
| `execute_cortex_update` tool_call Fehler | Fehler-String als tool_result | KI bekommt Fehler-Feedback |
| `get_cortex_service()` vor `init_services()` | `RuntimeError` | Identisch zu `get_memory_service()` |
| `_load_cortex_context` im ChatService | `return ''` + Log | Graceful Degradation |

### 6.3 Logging

Alle Operationen loggen über `src/utils/logger.py` (bestehend):

```python
from ..logger import log

log.info("Cortex-Datei geschrieben: %s/%s (%d Zeichen)", persona_id, filename, len(content))
log.error("Fehler beim Lesen von %s/%s: %s", persona_id, filename, e)
log.debug("Cortex tool_use: read %s/%s", persona_id, filename)
log.warning("Cortex-Update: Max Iterationen erreicht")
```

---

## 7. services/__init__.py Anpassung

### Vorher

```python
from .chat_service import ChatService
from .memory_service import MemoryService

__all__ = ['ChatService', 'MemoryService']
```

### Nachher

```python
from .chat_service import ChatService

__all__ = ['ChatService']
```

> **Hinweis:** Der `CortexService` wird **nicht** im `services/` Package platziert, sondern als eigenständiges Modul `src/utils/cortex_service.py`. Grund: Der CortexService hat eigene Konstanten, Templates und tool_use-Definitionen. Das hält die Datei übersichtlich und vermeidet ein zu großes services-Package.

---

## 8. Alle neuen und geänderten Dateien

### Neue Dateien

| Datei | Zweck |
|-------|-------|
| `src/utils/cortex_service.py` | CortexService Klasse, Konstanten, Templates, tool_use Definitionen |

### Geänderte Dateien

| Datei | Änderung |
|-------|----------|
| `src/utils/provider.py` | `_memory_service` → `_cortex_service`, `get_memory_service()` → `get_cortex_service()`, `init_services` angepasst |
| `src/utils/services/__init__.py` | `MemoryService` Export entfernen |
| `src/utils/services/chat_service.py` | `_load_memory_context()` → `_load_cortex_context()`, alle 3 Aufrufstellen migrieren, `format_memories_for_prompt` Import entfernen |
| `src/utils/config.py` | `save_created_persona` + `delete_created_persona` um Cortex-Aufrufe erweitern |
| `src/app.py` oder `src/init.py` | `ensure_cortex_files('default')` beim Start (falls nicht in `init_services` integriert) |

### Gelöschte Dateien (aus Schritt 1)

| Datei | Status |
|-------|--------|
| `src/utils/services/memory_service.py` | Wird in Schritt 1 entfernt, durch `cortex_service.py` ersetzt |
| `tests/test_services/test_memory_service.py` | Wird in Schritt 1 entfernt |

### Neue Tests (Empfehlung)

| Datei | Tests |
|-------|-------|
| `tests/test_services/test_cortex_service.py` | `test_get_cortex_path`, `test_ensure_cortex_files`, `test_read_file`, `test_write_file`, `test_read_all`, `test_get_cortex_for_prompt`, `test_delete_cortex_dir`, `test_filename_validation`, `test_handle_tool_call` |

---

## 9. Abhängigkeiten zu anderen Schritten

| Abhängigkeit | Richtung | Details |
|-------------|----------|---------|
| **Schritt 1** (Remove Old Memory) | ← Voraussetzung | MemoryService, DB-Tabellen, Routes müssen entfernt sein |
| **Schritt 2A** (Directory Structure) | ← Voraussetzung | Verzeichnisstruktur + Templates müssen definiert sein |
| **Schritt 3** (Activation Tiers) | → Nachfolger | Nutzt `execute_cortex_update()` — liefert Trigger-Logik |
| **Schritt 4** (Prompts & Placeholders) | → Nachfolger | Nutzt `get_cortex_for_prompt()` für Computed Placeholders |
| **Schritt 5** (Settings UI) | → Nachfolger | Nutzt `read_file()` / `write_file()` über API-Endpunkte |
| **Schritt 6** (API Integration) | → Nachfolger | Integriert alles in den Chat-Flow |
