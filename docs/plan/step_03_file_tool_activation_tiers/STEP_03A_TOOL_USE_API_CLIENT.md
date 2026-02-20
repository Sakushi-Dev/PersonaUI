# Schritt 3A: Tool-Use Support im API Client

## Übersicht

Der Cortex-Update-Mechanismus nutzt Anthropics `tool_use` Feature, um der KI zu ermöglichen, Cortex-Dateien (`memory.md`, `soul.md`, `relationship.md`) eigenständig zu lesen und zu schreiben. Dies geschieht über einen **separaten, nicht-streamenden API-Call** — der normale Chat-Stream bleibt unverändert.

Der bestehende `ApiClient` wird um eine neue Methode `tool_request()` erweitert, die den Tool-Call-Loop (Request → tool_use → Execute → tool_result → Repeat) vollständig kapselt. Die bestehenden Methoden `request()` und `stream()` bleiben **unverändert**.

**Wichtig:** Tool-Use wird **niemals** im Chat-Stream verwendet. Es ist ausschließlich für Cortex-Updates bestimmt, die als eigenständiger Non-Streaming-Request ablaufen.

---

## 1. Aktueller Stand des API-Clients

### Bestehende Dateien

| Datei | Zweck |
|-------|-------|
| `src/utils/api_request/types.py` | `RequestConfig`, `ApiResponse`, `StreamEvent` Dataclasses |
| `src/utils/api_request/client.py` | `ApiClient` mit `request()` (sync) und `stream()` (SSE) |
| `src/utils/api_request/__init__.py` | Package-Exports |
| `src/utils/api_request/response_cleaner.py` | Post-Processing für API-Antworten |

### Bestehende `RequestConfig`

```python
@dataclass
class RequestConfig:
    system_prompt: str
    messages: List[Dict[str, str]]
    model: Optional[str] = None
    max_tokens: int = 500
    temperature: float = 0.7
    stream: bool = False
    prefill: Optional[str] = None
    request_type: str = 'generic'
```

### Bestehende `ApiResponse`

```python
@dataclass
class ApiResponse:
    success: bool
    content: str = ''
    error: Optional[str] = None
    usage: Optional[Dict[str, int]] = None
    raw_response: Any = None
    stop_reason: Optional[str] = None
```

### Bestehende `request()` Methode (vereinfacht)

```python
def request(self, config: RequestConfig) -> ApiResponse:
    response = self.client.messages.create(
        model=model,
        max_tokens=config.max_tokens,
        temperature=config.temperature,
        system=config.system_prompt,
        messages=messages
    )
    content = response.content[0].text.strip()
    return ApiResponse(success=True, content=content, ...)
```

**Problem:** Die aktuelle `request()` Methode:
- Übergibt kein `tools` Array an die API
- Greift blind auf `response.content[0].text` zu — bei `tool_use` Responses enthält `content` aber `ToolUseBlock`-Objekte statt Text
- Hat keinen Loop für Tool-Call → Tool-Result → Weiter

**Kein bestehendes `tool`-Handling:** Eine Suche im gesamten `src/utils/api_request/` Verzeichnis ergibt keine Treffer für `tool_use`, `tool_result` oder `tool_call`. Tool-Use muss komplett neu implementiert werden.

---

## 2. Erweiterung von `RequestConfig`

### Neues Feld: `tools`

```python
@dataclass
class RequestConfig:
    """Konfiguration für einen API-Request"""
    system_prompt: str
    messages: List[Dict[str, str]]
    model: Optional[str] = None
    max_tokens: int = 500
    temperature: float = 0.7
    stream: bool = False
    prefill: Optional[str] = None
    request_type: str = 'generic'
    tools: Optional[List[Dict[str, Any]]] = None   # ← NEU: Tool-Definitionen für tool_use
```

### Änderung in `src/utils/api_request/types.py`

```python
"""
Typen und Konfiguration für API-Requests.

Zentrale Dataclasses für einheitliche Request-Konfiguration und Response-Struktur.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class RequestConfig:
    """Konfiguration für einen API-Request"""
    system_prompt: str
    messages: List[Dict[str, str]]
    model: Optional[str] = None           # None → Default aus settings
    max_tokens: int = 500
    temperature: float = 0.7
    stream: bool = False                  # True nur für Chat + Afterthought-Followup
    prefill: Optional[str] = None         # Wird als letzte assistant-message angehängt
    request_type: str = 'generic'         # 'chat', 'afterthought_decision', 'afterthought_followup',
                                          # 'memory_summary', 'spec_autofill', 'session_title', 'test',
                                          # 'cortex_update'  ← NEU
    tools: Optional[List[Dict[str, Any]]] = None   # Tool-Definitionen für Anthropic tool_use
                                                     # Nur verwendet bei request_type='cortex_update'


@dataclass
class ApiResponse:
    """Einheitliche Response-Struktur für Non-Stream Requests"""
    success: bool
    content: str = ''
    error: Optional[str] = None
    usage: Optional[Dict[str, int]] = None  # {'input_tokens': x, 'output_tokens': y}
    raw_response: Any = None                # Originale Anthropic-Response (optional)
    stop_reason: Optional[str] = None
    tool_results: Optional[List[Dict[str, Any]]] = None  # ← NEU: Ergebnisse aller Tool-Calls


@dataclass
class StreamEvent:
    """Event innerhalb eines Streams"""
    event_type: str    # 'chunk', 'done', 'error'
    data: Any          # str (chunk), dict (done), str (error)
```

### Erklärung der Änderungen

| Feld | Typ | Zweck |
|------|-----|-------|
| `RequestConfig.tools` | `Optional[List[Dict]]` | Anthropic Tool-Definitionen (nur für Cortex-Updates) |
| `ApiResponse.tool_results` | `Optional[List[Dict]]` | Log aller ausgeführten Tool-Calls mit Ergebnissen |

---

## 3. Anthropic SDK — Tool-Use Patterns

### 3.1 Tool-Definition Format

Die Anthropic API erwartet Tool-Definitionen in diesem Format:

```python
tools = [
    {
        "name": "read_file",
        "description": "Liest den aktuellen Inhalt einer Cortex-Datei.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "enum": ["memory.md", "soul.md", "relationship.md"],
                    "description": "Name der Cortex-Datei"
                }
            },
            "required": ["filename"]
        }
    },
    {
        "name": "write_file",
        "description": "Schreibt neuen Inhalt in eine Cortex-Datei. Überschreibt den gesamten Inhalt.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "enum": ["memory.md", "soul.md", "relationship.md"],
                    "description": "Name der Cortex-Datei"
                },
                "content": {
                    "type": "string",
                    "description": "Der neue vollständige Inhalt der Datei (Markdown)"
                }
            },
            "required": ["filename", "content"]
        }
    }
]
```

### 3.2 API-Call mit Tools

```python
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    system="...",
    tools=tools,
    messages=messages
)
```

### 3.3 Response-Struktur bei `tool_use`

Wenn Claude ein Tool aufrufen will, hat die Response:
- `stop_reason = "tool_use"`
- `content` enthält eine Mischung aus `TextBlock` und `ToolUseBlock` Objekten

```python
# response.stop_reason == "tool_use"
# response.content == [
#     TextBlock(type='text', text='Ich werde die Memory-Datei aktualisieren...'),
#     ToolUseBlock(type='tool_use', id='toolu_abc123', name='write_file',
#                  input={'filename': 'memory.md', 'content': '# Erinnerungen\n...'})
# ]
```

### 3.4 Tool-Result zurücksenden

Nach lokaler Ausführung des Tools muss das Ergebnis als `tool_result` Message zurückgesendet werden:

```python
# 1. Gesamte assistant-Antwort als Message anhängen
messages.append({
    "role": "assistant",
    "content": response.content   # ← content Array direkt (TextBlock + ToolUseBlock)
})

# 2. Tool-Results als user-Message
messages.append({
    "role": "user",
    "content": [
        {
            "type": "tool_result",
            "tool_use_id": "toolu_abc123",     # ← ID aus dem ToolUseBlock
            "content": "Datei erfolgreich geschrieben."
        }
    ]
})

# 3. Nächsten API-Call machen
response = client.messages.create(
    model="...",
    max_tokens=4096,
    system="...",
    tools=tools,
    messages=messages
)
```

### 3.5 `end_turn` — Abschluss

Wenn Claude keine weiteren Tools aufrufen möchte, kommt:
- `stop_reason = "end_turn"`
- `content` enthält nur `TextBlock` (oder ist leer)

---

## 4. Neue Methode: `tool_request()`

### 4.1 Tool-Call Loop Pattern

```
┌─────────────────────────────────────────┐
│         tool_request(config, executor)   │
│                                         │
│  1. API-Call mit tools=[...]            │
│         ↓                               │
│  2. stop_reason == "tool_use"?          │
│     ├─ JA:                              │
│     │   a) ToolUseBlocks extrahieren    │
│     │   b) executor(name, input) rufen  │
│     │   c) assistant + tool_result      │
│     │      an messages anhängen         │
│     │   d) → zurück zu Schritt 1        │
│     │                                   │
│     └─ NEIN (end_turn / max_tokens):    │
│        a) Text aus content extrahieren  │
│        b) ApiResponse zurückgeben       │
│                                         │
│  MAX_TOOL_ROUNDS = 10 (Sicherheit)     │
└─────────────────────────────────────────┘
```

### 4.2 Tool-Executor Callback

Die `tool_request()` Methode bekommt einen `executor` Callback, der die tatsächliche Tool-Ausführung übernimmt. So bleibt der ApiClient **unabhängig** von der Cortex-Logik:

```python
from typing import Callable, Tuple

# Typ: (tool_name, tool_input) → (success, result_text)
ToolExecutor = Callable[[str, dict], Tuple[bool, str]]
```

Der Cortex-Service stellt den konkreten Executor bereit (Schritt 6), z.B.:

```python
def cortex_tool_executor(tool_name: str, tool_input: dict) -> tuple[bool, str]:
    """Führt Cortex-Tools aus: read_file, write_file"""
    if tool_name == "read_file":
        content = cortex_service.read_file(persona_id, tool_input["filename"])
        return True, content
    elif tool_name == "write_file":
        cortex_service.write_file(persona_id, tool_input["filename"], tool_input["content"])
        return True, "Datei erfolgreich geschrieben."
    else:
        return False, f"Unbekanntes Tool: {tool_name}"
```

### 4.3 Vollständige Implementierung

```python
# In src/utils/api_request/client.py

# Am Anfang der Datei — neuer Import:
from typing import Generator, Callable, Tuple

# Typ-Alias für den Tool-Executor Callback
ToolExecutor = Callable[[str, dict], Tuple[bool, str]]

# Sicherheitslimit für Tool-Call Rounds
MAX_TOOL_ROUNDS = 10


class ApiClient:
    # ... bestehende Methoden bleiben unverändert ...

    def tool_request(
        self,
        config: RequestConfig,
        executor: ToolExecutor
    ) -> ApiResponse:
        """
        API-Request mit Tool-Use Loop. Verwendet für:
        - Cortex-Updates (Dateien lesen/schreiben via tool_use)

        Der Loop läuft so lange, bis die API mit stop_reason='end_turn'
        antwortet oder MAX_TOOL_ROUNDS erreicht ist.

        Args:
            config: RequestConfig mit tools=[...] und allen Parametern
            executor: Callback (tool_name, tool_input) → (success, result_text)
                      Führt die tatsächliche Tool-Logik aus (z.B. Cortex-Dateien lesen/schreiben)

        Returns:
            ApiResponse mit:
                - content: Finaler Text der KI (nach allen Tool-Calls)
                - tool_results: Liste aller ausgeführten Tool-Calls mit Ergebnissen
                - usage: Kumulierte Token-Usage über alle Rounds
                - stop_reason: 'end_turn', 'max_tokens', oder 'max_tool_rounds'
        """
        if not self.is_ready:
            return ApiResponse(
                success=False,
                error='ApiClient nicht initialisiert – kein API-Key konfiguriert'
            )

        if not config.tools:
            return ApiResponse(
                success=False,
                error='tool_request() benötigt config.tools – keine Tool-Definitionen angegeben'
            )

        model = self._resolve_model(config.model)
        messages = self._prepare_messages(config)
        all_tool_results = []
        total_input_tokens = 0
        total_output_tokens = 0

        try:
            for round_num in range(1, MAX_TOOL_ROUNDS + 1):
                log.info(
                    "Tool-Request Round %d/%d für %s",
                    round_num, MAX_TOOL_ROUNDS, config.request_type
                )

                # ── API-Call ─────────────────────────────────────────
                response = self.client.messages.create(
                    model=model,
                    max_tokens=config.max_tokens,
                    temperature=config.temperature,
                    system=config.system_prompt,
                    tools=config.tools,
                    messages=messages
                )

                # ── Usage akkumulieren ───────────────────────────────
                if hasattr(response, 'usage') and response.usage:
                    total_input_tokens += getattr(response.usage, 'input_tokens', 0) or 0
                    total_output_tokens += getattr(response.usage, 'output_tokens', 0) or 0

                # ── Abbruch bei end_turn oder max_tokens ─────────────
                if response.stop_reason != "tool_use":
                    # Finaler Text extrahieren
                    final_text = self._extract_text_from_content(response.content)
                    log.info(
                        "Tool-Request abgeschlossen nach %d Rounds (stop_reason=%s)",
                        round_num, response.stop_reason
                    )
                    return ApiResponse(
                        success=True,
                        content=final_text,
                        usage={
                            'input_tokens': total_input_tokens,
                            'output_tokens': total_output_tokens
                        },
                        raw_response=response,
                        stop_reason=response.stop_reason,
                        tool_results=all_tool_results if all_tool_results else None
                    )

                # ── Tool-Calls verarbeiten ───────────────────────────
                # Assistant-Antwort (mit ToolUseBlocks) an Messages anhängen
                messages.append({
                    "role": "assistant",
                    "content": response.content
                })

                # Alle ToolUseBlocks extrahieren und ausführen
                tool_result_contents = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue

                    tool_name = block.name
                    tool_input = block.input
                    tool_use_id = block.id

                    log.info(
                        "Tool-Call: %s(input=%s) [id=%s]",
                        tool_name, tool_input, tool_use_id
                    )

                    # Tool ausführen via Executor-Callback
                    try:
                        success, result_text = executor(tool_name, tool_input)
                    except Exception as exec_err:
                        log.error("Tool-Executor Fehler bei %s: %s", tool_name, exec_err)
                        success = False
                        result_text = f"Fehler bei Tool-Ausführung: {exec_err}"

                    # Ergebnis protokollieren
                    tool_record = {
                        'round': round_num,
                        'tool_name': tool_name,
                        'tool_input': tool_input,
                        'tool_use_id': tool_use_id,
                        'success': success,
                        'result': result_text
                    }
                    all_tool_results.append(tool_record)

                    # tool_result für API-Antwort aufbauen
                    tool_result_contents.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": result_text,
                        **({"is_error": True} if not success else {})
                    })

                    log.info(
                        "Tool-Result: %s → success=%s, result=%s",
                        tool_name, success,
                        result_text[:100] + '...' if len(result_text) > 100 else result_text
                    )

                # Tool-Results als user-Message anhängen
                messages.append({
                    "role": "user",
                    "content": tool_result_contents
                })

            # ── MAX_TOOL_ROUNDS erreicht ─────────────────────────────
            log.warning(
                "Tool-Request für %s nach %d Rounds abgebrochen (Sicherheitslimit)",
                config.request_type, MAX_TOOL_ROUNDS
            )
            return ApiResponse(
                success=True,
                content=self._extract_text_from_content(response.content),
                usage={
                    'input_tokens': total_input_tokens,
                    'output_tokens': total_output_tokens
                },
                raw_response=response,
                stop_reason='max_tool_rounds',
                tool_results=all_tool_results if all_tool_results else None
            )

        except anthropic.APIError as e:
            error_str = str(e)
            log.error("API-Fehler bei tool_request %s: %s", config.request_type, e)
            if 'credit balance' in error_str.lower():
                return ApiResponse(success=False, error='credit_balance_exhausted')
            return ApiResponse(success=False, error=error_str)

        except Exception as e:
            log.error("Unerwarteter Fehler bei tool_request %s: %s", config.request_type, e)
            return ApiResponse(success=False, error=str(e))

    @staticmethod
    def _extract_text_from_content(content) -> str:
        """
        Extrahiert Text aus dem content-Array einer Anthropic Response.
        Ignoriert ToolUseBlock-Objekte, sammelt nur TextBlock.text.

        Args:
            content: Liste von ContentBlock-Objekten (TextBlock, ToolUseBlock, ...)

        Returns:
            Zusammengefügter Text aller TextBlocks
        """
        if not content:
            return ''

        text_parts = []
        for block in content:
            if hasattr(block, 'text'):
                text_parts.append(block.text)

        return '\n'.join(text_parts).strip()
```

---

## 5. Keine Änderung an `request()` und `stream()`

Die bestehenden Methoden bleiben **vollständig unverändert**:

| Methode | Verwendung | Änderung |
|---------|-----------|----------|
| `request()` | Afterthought-Decision, Memory-Summary, Spec-Autofill, Session-Title, Tests | ❌ Keine |
| `stream()` | Chat, Afterthought-Followup | ❌ Keine |
| `tool_request()` | **NEU** — Cortex-Updates | ✅ Neu hinzugefügt |

**Begründung:** Tool-Use ist ein komplett separater Codepfad. Der Chat-Stream darf nicht mit Tool-Use-Logik verkompliziert werden. Cortex-Updates laufen als eigenständige Non-Streaming-Requests ab.

---

## 6. Export-Aktualisierung

### `src/utils/api_request/__init__.py`

```python
"""
API Request Package – Einheitlicher Anthropic API-Zugang.

Exportiert:
- ApiClient: Zentraler API-Client (einziger Anthropic-Zugang)
- RequestConfig: Konfiguration für einen API-Request
- ApiResponse: Einheitliche Response-Struktur für Non-Stream Requests
- StreamEvent: Event innerhalb eines Streams
- clean_api_response: Response-Bereinigung
- ToolExecutor: Typ-Alias für Tool-Execution Callbacks
"""

from .client import ApiClient, ToolExecutor
from .types import RequestConfig, ApiResponse, StreamEvent
from .response_cleaner import clean_api_response

__all__ = [
    'ApiClient',
    'ToolExecutor',
    'RequestConfig',
    'ApiResponse',
    'StreamEvent',
    'clean_api_response',
]
```

---

## 7. Fehlerbehandlung

### 7.1 Fehlerfälle und Verhalten

| Fehlerfall | Handling | Ergebnis |
|------------|----------|----------|
| **Kein API-Key** | Sofortiger Abbruch vor Loop | `ApiResponse(success=False, error='...')` |
| **Keine Tools in Config** | Sofortiger Abbruch | `ApiResponse(success=False, error='...')` |
| **API-Fehler (Rate Limit, 500, etc.)** | Exception-Catch im Try-Block | `ApiResponse(success=False, error=str(e))` |
| **Credit Balance erschöpft** | Spezial-Erkennung | `ApiResponse(success=False, error='credit_balance_exhausted')` |
| **Tool-Executor wirft Exception** | Try-Catch im Tool-Loop | `is_error=True` im tool_result, Loop geht weiter |
| **Tool-Executor gibt `(False, msg)` zurück** | Normaler Pfad | `is_error=True` im tool_result, API entscheidet ob Retry |
| **MAX_TOOL_ROUNDS erreicht** | Loop-Abbruch nach Limit | `ApiResponse(success=True, stop_reason='max_tool_rounds')` |
| **Unbekanntes Tool (vom Executor)** | Executor gibt Fehler zurück | `is_error=True`, API kann korrigieren |

### 7.2 `is_error` Flag

Wenn ein Tool fehlschlägt, wird `is_error: True` im `tool_result` gesetzt. Anthropic's API teilt dem Modell dann mit, dass der Tool-Call gescheitert ist — Claude kann daraufhin:
- Einen korrigierten Tool-Call machen
- Oder mit `end_turn` aufhören

```python
# Fehlerfall: Tool-Ausführung gescheitert
{
    "type": "tool_result",
    "tool_use_id": "toolu_abc123",
    "content": "Fehler: Datei 'notes.md' ist kein gültiger Cortex-Dateiname.",
    "is_error": True
}
```

### 7.3 Sicherheitslimit: `MAX_TOOL_ROUNDS`

- Default: **10 Rounds**
- In der Praxis werden Cortex-Updates 1-3 Rounds benötigen (lesen + schreiben)
- Das Limit verhindert Endlosschleifen bei unerwartetem API-Verhalten
- Bei Überschreitung: Erfolgreiche Response mit `stop_reason='max_tool_rounds'`

---

## 8. Datenfluss — Vollständiges Beispiel

```
Caller (Cortex-Trigger, Schritt 6):
│
│  config = RequestConfig(
│      system_prompt="Du bist die Persona ...",
│      messages=[{chat history}],
│      tools=[read_file, write_file],
│      max_tokens=4096,
│      temperature=0.5,
│      request_type='cortex_update'
│  )
│
│  result = api_client.tool_request(config, cortex_tool_executor)
│
▼
ApiClient.tool_request():
│
│  ─── Round 1 ──────────────────────────────────────
│  │ API-Call: messages + tools
│  │ Response: stop_reason="tool_use"
│  │   content = [
│  │     TextBlock("Ich lese zunächst die aktuelle Memory-Datei..."),
│  │     ToolUseBlock(name="read_file", input={"filename": "memory.md"})
│  │   ]
│  │
│  │ Executor: read_file("memory.md") → (True, "# Erinnerungen\n...")
│  │
│  │ Messages += assistant(content) + user(tool_result)
│  │
│  ─── Round 2 ──────────────────────────────────────
│  │ API-Call: updated messages + tools
│  │ Response: stop_reason="tool_use"
│  │   content = [
│  │     TextBlock("Ich aktualisiere jetzt die Datei..."),
│  │     ToolUseBlock(name="write_file", input={
│  │       "filename": "memory.md",
│  │       "content": "# Erinnerungen\n\n## Neuer Eintrag\n..."
│  │     })
│  │   ]
│  │
│  │ Executor: write_file("memory.md", content) → (True, "Datei erfolgreich geschrieben.")
│  │
│  │ Messages += assistant(content) + user(tool_result)
│  │
│  ─── Round 3 ──────────────────────────────────────
│  │ API-Call: updated messages + tools
│  │ Response: stop_reason="end_turn"
│  │   content = [
│  │     TextBlock("Memory-Datei wurde aktualisiert.")
│  │   ]
│  │
│  │ → Loop beendet
│
▼
ApiResponse:
    success=True
    content="Memory-Datei wurde aktualisiert."
    stop_reason="end_turn"
    tool_results=[
        {round: 1, tool_name: "read_file", success: True, ...},
        {round: 2, tool_name: "write_file", success: True, ...}
    ]
    usage={'input_tokens': 3500, 'output_tokens': 800}
```

---

## 9. Betroffene Dateien — Zusammenfassung

| Datei | Änderung |
|-------|----------|
| `src/utils/api_request/types.py` | `RequestConfig.tools` Feld hinzufügen, `ApiResponse.tool_results` Feld hinzufügen |
| `src/utils/api_request/client.py` | `tool_request()` Methode + `_extract_text_from_content()` Helper + `ToolExecutor` Typ-Alias + `MAX_TOOL_ROUNDS` Konstante |
| `src/utils/api_request/__init__.py` | `ToolExecutor` zum Export hinzufügen |

### Nicht betroffene Dateien

| Datei | Grund |
|-------|-------|
| `src/utils/api_request/response_cleaner.py` | Tool-Responses brauchen kein HTML-Cleaning |
| `src/utils/api_request/client.py` → `request()` | Unverändert — kein Tool-Use im Sync-Request |
| `src/utils/api_request/client.py` → `stream()` | Unverändert — kein Tool-Use im Chat-Stream |

---

## 10. Abhängigkeiten und Voraussetzungen

### Benötigt von diesem Schritt

- `anthropic` Python SDK (bereits installiert, unterstützt `tool_use` nativ)
- Keine neuen Dependencies

### Benötigt für spätere Schritte

| Späterer Schritt | Benötigt von 3A |
|------------------|-----------------|
| **3B: Aktivierungsstufen** | Schwellen-Logik triggert `tool_request()` |
| **4: Cortex Prompts** | System-Prompt für Cortex-Update wird in `RequestConfig.system_prompt` gesetzt |
| **6: API Integration** | `tool_request()` + `ToolExecutor` werden im Chat-Flow aufgerufen |

### SDK-Kompatibilität

Die Anthropic Python SDK (`anthropic>=0.25.0`) unterstützt Tool-Use nativ:
- `client.messages.create(tools=[...])` — Tool-Definitionen übergeben
- `response.content` enthält `ToolUseBlock`-Objekte mit `.type`, `.id`, `.name`, `.input`
- `tool_result` Messages werden als `content`-Array in einer User-Message gesendet
- Kein zusätzliches Setup oder Feature-Flag nötig

---

## 11. Test-Strategie

### Unit-Tests für `tool_request()`

```python
# tests/test_services/test_tool_request.py

def test_tool_request_single_round():
    """Tool-Call mit einem Round: read_file → end_turn"""

def test_tool_request_multi_round():
    """Tool-Call mit mehreren Rounds: read_file → write_file → end_turn"""

def test_tool_request_no_tools_error():
    """Fehler wenn config.tools leer ist"""

def test_tool_request_executor_exception():
    """Executor wirft Exception → is_error=True, Loop geht weiter"""

def test_tool_request_executor_failure():
    """Executor gibt (False, msg) zurück → is_error=True"""

def test_tool_request_max_rounds():
    """Sicherheitslimit: Abbruch nach MAX_TOOL_ROUNDS"""

def test_tool_request_api_error():
    """API-Fehler werden korrekt als ApiResponse(success=False) zurückgegeben"""

def test_tool_request_credit_exhausted():
    """Credit-Balance-Fehler wird erkannt"""

def test_tool_request_usage_accumulation():
    """Token-Usage wird über alle Rounds korrekt akkumuliert"""

def test_extract_text_from_content():
    """Nur TextBlocks werden extrahiert, ToolUseBlocks ignoriert"""
```

Die Tests verwenden Mock-Responses und einen Mock-Executor — keine echten API-Calls nötig.
