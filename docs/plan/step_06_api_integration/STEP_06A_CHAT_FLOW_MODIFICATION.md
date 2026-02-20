# Schritt 6A: Chat-Flow Modifikation

> **⚠️ KORREKTUR v3:** Tier-Modell vereinfacht. `check_and_trigger_cortex_update()` nimmt kein `context_limit` mehr, gibt kein `triggered_tier` int zurück sondern ein Dict mit `triggered`, `progress` und `frequency`. Das Done-Event enthält jetzt `cortex` statt `cortex_update`.

## Übersicht

Dieser Schritt beschreibt die Integration des Cortex-Systems in den bestehenden Chat-Stream. Drei zentrale Änderungen werden durchgeführt:

1. **System-Prompt bekommt Cortex-Daten** — `ChatService.chat_stream()` lädt Cortex-Dateien, übergibt sie als `runtime_vars`, die PromptEngine löst `{{cortex_*}}` Placeholders auf → Cortex-Inhalt erscheint als letzter Block im System-Prompt
2. **Tier-Check nach Response** — In `routes/chat.py` wird nach dem `done`-Event die Nachrichtenanzahl geprüft und bei Erreichen eines Schwellenwerts ein Background-Cortex-Update gestartet
3. **Message-Sequenz bleibt unverändert** — Cortex-Daten stehen ausschließlich im System-Prompt. Die bestehende Reihenfolge `first_assistant → history → prefill` wird nicht angetastet

### Unterschied zum alten Memory-System

| Aspekt | Altes Memory-System | Neues Cortex-System |
|--------|---------------------|---------------------|
| **Datenort** | SQL-Tabelle `memories` | Markdown-Dateien (`memory.md`, `soul.md`, `relationship.md`) |
| **Position im Prompt** | `first_assistant` Message (vor History) | Letzter Block im **System-Prompt** (Order 2000) |
| **Laden** | `_load_memory_context()` → formatierter String | `_load_cortex_context()` → Dict für `runtime_vars` |
| **Stats-Tracking** | `memory_est` als eigener Wert | Kein separater Wert — Cortex ist Teil von `system_prompt_est` |
| **Update-Trigger** | Manuell / API-basiert | Automatisch via Tier-Schwellen nach Chat-Response |
| **Update-Mechanismus** | Direkte DB-Operationen | `tool_use` API-Call im Background-Thread |

---

## 1. Aktueller Chat-Flow (IST-Zustand)

### 1.1 Ablauf: Request bis Response

```
Client                      routes/chat.py              ChatService                ApiClient
  │                              │                           │                         │
  │── POST /chat_stream ────────►│                           │                         │
  │   { message, session_id,     │                           │                         │
  │     context_limit, ... }     │                           │                         │
  │                              │                           │                         │
  │                              │── validate request ──────►│                         │
  │                              │── load_character() ──────►│                         │
  │                              │── get_conversation_context()                        │
  │                              │                           │                         │
  │                              │── generate() ─────────────│                         │
  │                              │   │                       │                         │
  │                              │   │── chat_stream() ─────►│                         │
  │                              │   │                       │                         │
  │                              │   │                       │── 1. build_system_prompt()
  │                              │   │                       │      runtime_vars: {language, ip_address}
  │                              │   │                       │                         │
  │                              │   │                       │── 2. _load_memory_context()
  │                              │   │                       │      → SQL memories → formatierter String
  │                              │   │                       │                         │
  │                              │   │                       │── 3. _build_chat_messages()
  │                              │   │                       │      Sequenz: first_assistant(memory+prefill_imp)
  │                              │   │                       │               → history
  │                              │   │                       │               → user_message
  │                              │   │                       │               → prefill
  │                              │   │                       │                         │
  │                              │   │                       │── 4. api_client.stream()──►│
  │                              │   │                       │                         │── Anthropic API
  │◄── SSE: chunk ──────────────│◄──│◄── chunk ─────────────│◄── chunk ───────────────│
  │◄── SSE: chunk ──────────────│◄──│◄── chunk ─────────────│◄── chunk ───────────────│
  │                              │   │                       │                         │
  │                              │   │── save_message(user) ─│                         │
  │                              │   │   (beim 1. chunk)     │                         │
  │                              │   │                       │                         │
  │◄── SSE: done ───────────────│◄──│◄── done ──────────────│◄── done ────────────────│
  │   { response, stats,        │   │                       │                         │
  │     character_name }        │   │── save_message(bot) ──│                         │
  │                              │   │                       │                         │
  │   (Response geschlossen)    │   │                       │                         │
```

### 1.2 Aktuelle Stats im `done`-Event

```json
{
  "type": "done",
  "response": "...",
  "stats": {
    "api_input_tokens": 1234,
    "output_tokens": 256,
    "system_prompt_est": 3200,
    "memory_est": 850,
    "history_est": 4100,
    "user_msg_est": 120,
    "prefill_est": 45,
    "total_est": 8315
  },
  "character_name": "Luna"
}
```

### 1.3 Aktuelle Dateien und Zuständigkeiten

| Datei | Rolle |
|-------|-------|
| [src/routes/chat.py](../../../src/routes/chat.py) | HTTP-Endpoint, SSE-Streaming, Message-Speicherung |
| [src/utils/services/chat_service.py](../../../src/utils/services/chat_service.py) | Orchestrierung: Prompt → Messages → API → Stats |
| [src/utils/api_request/client.py](../../../src/utils/api_request/client.py) | Anthropic API-Zugang, Stream-Handling |
| [src/utils/prompt_engine/engine.py](../../../src/utils/prompt_engine/engine.py) | System-Prompt aus Templates bauen |
| [src/utils/prompt_engine/placeholder_resolver.py](../../../src/utils/prompt_engine/placeholder_resolver.py) | `{{placeholder}}` → Werte auflösen |

---

## 2. Neuer Chat-Flow (SOLL-Zustand)

### 2.1 Vollständiges Sequenzdiagramm

```
Client                routes/chat.py       ChatService          CortexService     PromptEngine      ApiClient       TierChecker
  │                        │                    │                     │                │                │                │
  │── POST /chat_stream ──►│                    │                     │                │                │                │
  │   { message,           │                    │                     │                │                │                │
  │     session_id,        │                    │                     │                │                │                │
  │     context_limit }    │                    │                     │                │                │                │
  │                        │                    │                     │                │                │                │
  │                        │── validate ────────│                     │                │                │                │
  │                        │── load_character() │                     │                │                │                │
  │                        │── get_conv_ctx()   │                     │                │                │                │
  │                        │                    │                     │                │                │                │
  │                        │── generate() ──────│                     │                │                │                │
  │                        │   │                │                     │                │                │                │
  │                        │   │── chat_stream() ──────────────────────────────────────────────────────│                │
  │                        │   │                │                     │                │                │                │
  │                        │   │                │── 1. _load_cortex_context(persona_id)                │                │
  │                        │   │                │         │                                            │                │
  │                        │   │                │         ├──► get_cortex_for_prompt() ──►│             │                │
  │                        │   │                │         │    liest memory.md,           │             │                │
  │                        │   │                │         │    soul.md, relationship.md   │             │                │
  │                        │   │                │         │◄── { cortex_memory: "...",    │             │                │
  │                        │   │                │         │      cortex_soul: "...",      │             │                │
  │                        │   │                │         │      cortex_relationship: "..."} │          │                │
  │                        │   │                │         │                                            │                │
  │                        │   │                │── 2. runtime_vars.update(cortex_data)                │                │
  │                        │   │                │                                                      │                │
  │                        │   │                │── 3. build_system_prompt(variant, runtime_vars) ─────►│                │
  │                        │   │                │         Cortex-Block am Ende (Order 2000)             │                │
  │                        │   │                │◄────── aufgelöster System-Prompt ─────────────────────│                │
  │                        │   │                │                                                      │                │
  │                        │   │                │── 4. _build_chat_messages()                          │                │
  │                        │   │                │      (UNVERÄNDERT: first_assistant → history → prefill)               │
  │                        │   │                │      ⚠️ KEIN memory_context mehr in first_assistant   │                │
  │                        │   │                │                                                      │                │
  │                        │   │                │── 5. api_client.stream(config) ──────────────────────►│                │
  │                        │   │                │                                                      │── Anthropic API│
  │◄── SSE: chunk ────────│◄──│◄── chunk ──────│◄──────────────────── chunk ──────────────────────────│                │
  │◄── SSE: chunk ────────│◄──│◄── chunk ──────│◄──────────────────── chunk ──────────────────────────│                │
  │                        │   │                │                                                      │                │
  │                        │   │── save_message(user) ─ (beim 1. chunk)                                │                │
  │                        │   │                │                                                      │                │
  │                        │   │◄── done ───────│◄──────────────────── done ───────────────────────────│                │
  │                        │   │                │                                                      │                │
  │                        │   │── save_message(bot) ──                                                │                │
  │                        │   │                │                                                      │                │
  │                        │   │── ═══ TIER-CHECK ═══──────────────────────────────────────────────────────────────────►│
  │                        │   │    check_and_trigger(persona_id, session_id, context_limit)                            │
  │                        │   │                │                                                                       │
  │                        │   │                │                                           ┌── get_message_count()     │
  │                        │   │                │                                           ├── get_cycle_base()        │
  │                        │   │                │                                           ├── calculate_threshold()   │
  │                        │   │                │                                           │                           │
  │                        │   │                │                                           ├── [Schwelle erreicht?]    │
  │                        │   │                │                                           │   JA → set_cycle_base()   │
  │                        │   │                │                                           │        → Background-Thread│
  │                        │   │◄── return info ────────────────────────────────────────────│                           │
  │                        │   │                │                                                                       │
  │◄── SSE: done ────────│◄──│ { response, stats, cortex }                                                            │
  │                        │   │                │                                                                       │
  │   (Response closed)   │                                                                                            │
  │                        │                     Background: CortexUpdateService.execute_update()                       │
  │                        │                     → tool_use API-Call → read/write cortex files                          │
```

### 2.2 Modifizierter `chat_stream()` Flow — Schritt für Schritt

1. **Request empfangen** — user_message, session_id, context_limit, persona_id, etc.
2. **Validierung** — Leere Nachricht? API-Key? Character laden?
3. **`generate()` startet den SSE-Stream:**
   - a) `ChatService.chat_stream()` aufrufen
   - b) **NEU:** ChatService lädt Cortex via `_load_cortex_context(persona_id)` → Dict
   - c) **NEU:** `runtime_vars.update(cortex_data)` — Cortex-Placeholders werden auflösbar
   - d) `engine.build_system_prompt(variant, runtime_vars)` — Cortex-Block erscheint am Ende
   - e) **ENTFÄLLT:** `_load_memory_context()` — wird durch Cortex ersetzt
   - f) `_build_chat_messages()` — **UNVERÄNDERT** (aber ohne `memory_context` Parameter)
   - g) `api_client.stream(config)` — Stream startet
   - h) Chunks → Client (SSE)
   - i) Beim 1. Chunk: `save_message(user)` in Persona-DB
   - j) Done: `save_message(bot)` in Persona-DB
   - k) **NEU:** Cortex-Check via `check_and_trigger_cortex_update()`
   - l) **NEU:** `cortex` Info (Progress + Trigger-Status) im Done-Event an Client senden

---

## 3. Änderungen: `src/routes/chat.py`

### 3.1 Neue Imports

```python
# ─── NEU: Cortex Tier-Check ─────────────────────────────
from utils.cortex.tier_checker import check_and_trigger_cortex_update
```

### 3.2 `chat_stream()` — Modifizierte `generate()` Funktion

**Vorher:**

```python
def generate():
    chat_service = get_chat_service()
    user_msg_saved = False
    try:
        for event_type, event_data in chat_service.chat_stream(
            user_message=user_message,
            conversation_history=conversation_history,
            character_data=character,
            language='Deutsch',
            user_name=user_name,
            api_model=api_model,
            api_temperature=api_temperature,
            ip_address=user_ip,
            experimental_mode=experimental_mode,
            persona_id=persona_id
        ):
            if event_type == 'chunk':
                if not user_msg_saved:
                    save_message(user_message, True, character_name, session_id, persona_id=persona_id)
                    user_msg_saved = True
                yield f"data: {json.dumps({'type': 'chunk', 'text': event_data})}\n\n"
            elif event_type == 'done':
                save_message(event_data['response'], False, character_name, session_id, persona_id=persona_id)
                yield f"data: {json.dumps({'type': 'done', 'response': event_data['response'], 'stats': event_data['stats'], 'character_name': character_name})}\n\n"
            elif event_type == 'error':
                error_payload = {'type': 'error', 'error': event_data}
                if event_data == 'credit_balance_exhausted':
                    error_payload['error_type'] = 'credit_balance_exhausted'
                yield f"data: {json.dumps(error_payload)}\n\n"
    except Exception as e:
        log.error("Stream-Fehler: %s", e)
        yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
```

**Nachher:**

```python
def generate():
    chat_service = get_chat_service()
    user_msg_saved = False
    stream_success = False
    done_data = None

    try:
        for event_type, event_data in chat_service.chat_stream(
            user_message=user_message,
            conversation_history=conversation_history,
            character_data=character,
            language='Deutsch',
            user_name=user_name,
            api_model=api_model,
            api_temperature=api_temperature,
            ip_address=user_ip,
            experimental_mode=experimental_mode,
            persona_id=persona_id
        ):
            if event_type == 'chunk':
                if not user_msg_saved:
                    save_message(user_message, True, character_name, session_id, persona_id=persona_id)
                    user_msg_saved = True
                yield f"data: {json.dumps({'type': 'chunk', 'text': event_data})}\n\n"
            elif event_type == 'done':
                save_message(event_data['response'], False, character_name, session_id, persona_id=persona_id)
                stream_success = True
                done_data = event_data

                # ── NEU: Cortex Trigger-Check VOR done-yield ─────
                cortex_info = None
                try:
                    cortex_info = check_and_trigger_cortex_update(
                        persona_id=persona_id,
                        session_id=session_id
                    )
                except Exception as cortex_err:
                    log.warning("Cortex check failed (non-fatal): %s", cortex_err)
                # ─────────────────────────────────────────────────

                # Done-Event mit optionalem cortex Progress
                done_payload = {
                    'type': 'done',
                    'response': event_data['response'],
                    'stats': event_data['stats'],
                    'character_name': character_name
                }
                if cortex_info:
                    done_payload['cortex'] = cortex_info

                yield f"data: {json.dumps(done_payload)}\n\n"

            elif event_type == 'error':
                error_payload = {'type': 'error', 'error': event_data}
                if event_data == 'credit_balance_exhausted':
                    error_payload['error_type'] = 'credit_balance_exhausted'
                yield f"data: {json.dumps(error_payload)}\n\n"
    except Exception as e:
        log.error("Stream-Fehler: %s", e)
        yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
```

### 3.3 Warum Tier-Check VOR dem Done-Yield?

In der Schritt-3B-Spezifikation stand der Tier-Check **nach** dem letzten Yield. Das hatte den Vorteil, dass der Client das Done-Event sofort bekommt. Nachteil: Der Client weiß nicht, dass ein Cortex-Update gestartet wurde.

**Neue Architektur-Entscheidung:** Der Tier-Check wird **vor** dem Done-Yield ausgeführt, damit das Ergebnis in das Done-Event eingebaut werden kann. Der Tier-Check selbst ist schnell (~5ms: eine DB-Query + Vergleich), sodass die Verzögerung vernachlässigbar ist.

```
Alt (Step 3B):   ... → yield done → tier-check → (client weiß nichts)
Neu (Step 6A):   ... → save_message → cortex-check → yield done{cortex} → (client informiert)
```

> **Hinweis:** Das eigentliche Cortex-Update (tool_use API-Call, 3–10s) läuft weiterhin im Background-Thread. Nur die **Entscheidung** ob ein Update nötig ist, wird synchron gemacht.

### 3.4 `api_regenerate()` — Gleiche Änderung

Die `generate()` Funktion in `api_regenerate()` erhält dieselbe Tier-Check-Logik. Da Regenerate eine neue Bot-Antwort erzeugt, kann es ebenfalls einen Tier auslösen.

**Vorher:**

```python
elif event_type == 'done':
    save_message(event_data['response'], False, character_name, session_id, persona_id=persona_id)
    yield f"data: {json.dumps({'type': 'done', 'response': event_data['response'], 'stats': event_data['stats'], 'character_name': character_name})}\n\n"
```

**Nachher:**

```python
elif event_type == 'done':
    save_message(event_data['response'], False, character_name, session_id, persona_id=persona_id)

    # Cortex Trigger-Check (identisch zu chat_stream)
    cortex_info = None
    try:
        cortex_info = check_and_trigger_cortex_update(
            persona_id=persona_id,
            session_id=session_id
        )
    except Exception as cortex_err:
        log.warning("Cortex check failed (non-fatal): %s", cortex_err)

    done_payload = {
        'type': 'done',
        'response': event_data['response'],
        'stats': event_data['stats'],
        'character_name': character_name
    }
    if cortex_info:
        done_payload['cortex'] = cortex_info

    yield f"data: {json.dumps(done_payload)}\n\n"
```

### 3.5 `afterthought()` — KEIN Tier-Check

Der Afterthought-Followup ist ein kurzer Nachtrag (max 200 Tokens), keine vollständige Chat-Nachricht. Er erhöht die Nachrichtenanzahl nur um 1 (die Ergänzung). Tier-Checks werden hier **nicht** ausgeführt, um unnötige Cortex-Updates bei Kurzantworten zu vermeiden.

---

## 4. Änderungen: `src/utils/services/chat_service.py`

### 4.1 Neue Methode: `_load_cortex_context()`

Ersetzt konzeptionell `_load_memory_context()` als primäre Kontextquelle. Wird **direkt nach** der Varianten-Bestimmung aufgerufen.

```python
def _load_cortex_context(self, persona_id: str = None) -> Dict[str, str]:
    """
    Lädt Cortex-Dateien für die Placeholder-Auflösung.

    Liest memory.md, soul.md und relationship.md über den CortexService
    und gibt sie als Dict zurück, das direkt in runtime_vars gemergt wird.

    Returns:
        Dict mit cortex_memory, cortex_soul, cortex_relationship.
        Bei Fehler: Alle Werte sind leere Strings (Graceful Degradation).
    """
    try:
        from ..provider import get_cortex_service
        cortex_service = get_cortex_service()

        if persona_id is None:
            from ..config import get_active_persona_id
            persona_id = get_active_persona_id()

        return cortex_service.get_cortex_for_prompt(persona_id)
    except Exception as e:
        log.warning("Cortex-Kontext konnte nicht geladen werden: %s", e)
        return {
            'cortex_memory': '',
            'cortex_soul': '',
            'cortex_relationship': '',
        }
```

### 4.2 `chat_stream()` — Cortex-Integration und Memory-Entfernung

**Vollständiger modifizierter Ablauf:**

```python
def chat_stream(self, user_message: str, conversation_history: list,
                character_data: dict, language: str = 'de',
                user_name: str = 'User', api_model: str = None,
                api_temperature: float = None,
                ip_address: str = None, experimental_mode: bool = False,
                persona_id: str = None, pending_afterthought: str = None) -> Generator:
    """
    Haupt-Chat-Stream.

    Änderungen gegenüber Vorgängerversion:
    - include_memories Parameter ENTFERNT (Memory-System existiert nicht mehr)
    - Cortex-Daten werden via runtime_vars in System-Prompt injiziert
    - memory_context entfällt aus _build_chat_messages()
    - Stats: memory_est entfernt (Cortex ist Teil von system_prompt_est)
    """
    temperature = api_temperature if api_temperature is not None else 0.7

    if character_data is None:
        character_data = load_character()

    char_name = character_data.get('char_name', 'Assistant')

    # 1. System-Prompt via PromptEngine bauen
    variant = 'experimental' if experimental_mode else 'default'
    system_prompt = ''
    if self._engine:
        runtime_vars = {'language': language}
        if ip_address:
            runtime_vars['ip_address'] = ip_address

        # ── NEU: Cortex-Daten laden und als runtime_vars übergeben ──
        cortex_data = self._load_cortex_context(persona_id)
        runtime_vars.update(cortex_data)
        # ────────────────────────────────────────────────────────────

        system_prompt = self._engine.build_system_prompt(
            variant=variant, runtime_vars=runtime_vars
        ) or ''
    else:
        log.error("ChatService: Kein System-Prompt — PromptEngine nicht verfügbar!")
    system_prompt_est = len(system_prompt)

    # ── ENTFERNT: Memory-Loading ──────────────────────────────────
    # memory_context = ''                    ← ENTFERNT
    # memory_tokens_est = 0                  ← ENTFERNT
    # if include_memories:                   ← ENTFERNT
    #     memory_context = self._load_memory_context(persona_id)  ← ENTFERNT
    #     if memory_context:                 ← ENTFERNT
    #         memory_tokens_est = len(memory_context)  ← ENTFERNT
    # ──────────────────────────────────────────────────────────────

    # 2. Messages zusammenbauen (OHNE memory_context)
    messages, msg_stats = self._build_chat_messages(
        user_message, conversation_history,
        char_name, user_name, experimental_mode,
        pending_afterthought=pending_afterthought
    )

    # Debug-Logging (unverändert)
    log.debug("API-Messages (%d total): %s",
              len(messages),
              ' → '.join(f"{m['role']}({len(m['content'])})" for m in messages))

    # 3. RequestConfig erstellen
    config = RequestConfig(
        system_prompt=system_prompt,
        messages=messages,
        model=api_model,
        max_tokens=500,
        temperature=temperature,
        stream=True,
        request_type='chat'
    )

    # 4. Stream über ApiClient
    for event in self.api_client.stream(config):
        if event.event_type == 'chunk':
            yield ('chunk', event.data)
        elif event.event_type == 'done':
            # Stats berechnen (OHNE memory_est)
            total_est = (system_prompt_est
                         + msg_stats['history_est']
                         + msg_stats['user_msg_est']
                         + msg_stats['prefill_est'])
            yield ('done', {
                'response': event.data['response'],
                'stats': {
                    'api_input_tokens': event.data.get('api_input_tokens', 0),
                    'output_tokens': event.data.get('output_tokens', 0),
                    'system_prompt_est': system_prompt_est,
                    # 'memory_est' ENTFERNT — Cortex ist Teil von system_prompt_est
                    'history_est': msg_stats['history_est'],
                    'user_msg_est': msg_stats['user_msg_est'],
                    'prefill_est': msg_stats['prefill_est'],
                    'total_est': total_est
                }
            })
        elif event.event_type == 'error':
            yield ('error', event.data)
```

### 4.3 `_build_chat_messages()` — Signatur-Änderung

Der `memory_context` Parameter wird entfernt, da Cortex-Daten jetzt im System-Prompt stehen.

**Vorher:**
```python
def _build_chat_messages(self, user_message: str, conversation_history: list,
                          memory_context: str, char_name: str, user_name: str,
                          nsfw_mode: bool, pending_afterthought: str = None) -> tuple:
```

**Nachher:**
```python
def _build_chat_messages(self, user_message: str, conversation_history: list,
                          char_name: str, user_name: str,
                          nsfw_mode: bool, pending_afterthought: str = None) -> tuple:
```

### 4.4 `_build_chat_messages()` — `first_assistant` Position bereinigen

Im `first_assistant`-Block wird der `memory_context` nicht mehr verwendet. Die Logik vereinfacht sich erheblich:

**Vorher (first_assistant Block):**
```python
if position == 'first_assistant':
    # Memory + Prefill-Impersonation kombiniert
    first_parts = []
    if memory_context:
        first_parts.append(memory_context)
    if prefill_imp_text:
        first_parts.append(prefill_imp_text)

    if dialog_injections:
        if first_parts and dialog_injections[0].get('role') == 'assistant':
            combined = "\n\n".join(first_parts) + "\n\n" + dialog_injections[0].get('content', '')
            messages.append({'role': 'assistant', 'content': combined})
            # ... etc
```

**Nachher (first_assistant Block):**
```python
if position == 'first_assistant':
    # Prefill-Impersonation (experimental mode only)
    first_parts = []
    if prefill_imp_text:
        first_parts.append(prefill_imp_text)

    if dialog_injections:
        if first_parts and dialog_injections[0].get('role') == 'assistant':
            combined = "\n\n".join(first_parts) + "\n\n" + dialog_injections[0].get('content', '')
            messages.append({'role': 'assistant', 'content': combined})
            history_tokens_est += len(combined)
            for msg in dialog_injections[1:]:
                messages.append(msg)
                history_tokens_est += len(msg.get('content', ''))
        elif first_parts:
            first_assistant = "\n\n".join(first_parts)
            messages.append({'role': 'assistant', 'content': first_assistant})
            history_tokens_est += len(first_assistant)
            for msg in dialog_injections:
                messages.append(msg)
                history_tokens_est += len(msg.get('content', ''))
        else:
            for msg in dialog_injections:
                messages.append(msg)
                history_tokens_est += len(msg.get('content', ''))
        dialog_injections = []
    elif first_parts:
        first_assistant = "\n\n".join(first_parts)
        messages.append({'role': 'assistant', 'content': first_assistant})
        history_tokens_est += len(first_assistant)
```

> Die Struktur bleibt identisch — nur `memory_context` fällt aus `first_parts` raus.

### 4.5 `afterthought_decision()` — Cortex statt Memory

**Vorher:**
```python
system_prompt = self._engine.build_system_prompt(variant=variant, runtime_vars=runtime_vars) or ''
# ...
memory_context = self._load_memory_context(persona_id)
messages = []
if memory_context:
    messages.append({'role': 'assistant', 'content': memory_context})
```

**Nachher:**
```python
# Cortex-Daten laden und in runtime_vars mergen
cortex_data = self._load_cortex_context(persona_id)
runtime_vars.update(cortex_data)

system_prompt = self._engine.build_system_prompt(variant=variant, runtime_vars=runtime_vars) or ''
# ...
# KEIN memory_context mehr — Cortex ist im System-Prompt
messages = []
```

### 4.6 `afterthought_followup()` — Cortex statt Memory

Identisches Pattern wie bei `afterthought_decision()`:

**Vorher:**
```python
system_prompt = self._engine.build_system_prompt(variant=variant, runtime_vars=runtime_vars) or ''
# ...
memory_context = self._load_memory_context(persona_id)
messages = []
if memory_context:
    messages.append({'role': 'assistant', 'content': memory_context})
```

**Nachher:**
```python
cortex_data = self._load_cortex_context(persona_id)
runtime_vars.update(cortex_data)

system_prompt = self._engine.build_system_prompt(variant=variant, runtime_vars=runtime_vars) or ''
# ...
messages = []  # Kein Memory-Prepend mehr
```

### 4.7 Signatur-Änderung zusammengefasst

| Methode | Entfernter Parameter | Grund |
|---------|---------------------|-------|
| `chat_stream()` | `include_memories` | Memory-System existiert nicht mehr |
| `_build_chat_messages()` | `memory_context` | Cortex ist im System-Prompt, nicht in Messages |

---

## 5. Stats-Änderungen

### 5.1 Warum `memory_est` entfällt

Im alten System war Memory-Content ein separater Text-Block, der in die `first_assistant` Message injiziert wurde — **außerhalb** des System-Prompts. Deshalb brauchte es einen eigenen Stats-Wert `memory_est`, um den Token-Beitrag des Memories separat auszuweisen.

Im neuen System sind die Cortex-Daten via `{{cortex_*}}` Placeholders **Teil des System-Prompts**. Der `system_prompt_est` Wert enthält bereits den aufgelösten Cortex-Content. Ein separater `cortex_est` wäre redundant.

### 5.2 Stats vorher vs. nachher

**Vorher:**
```json
{
  "stats": {
    "api_input_tokens": 1234,
    "output_tokens": 256,
    "system_prompt_est": 3200,
    "memory_est": 850,
    "history_est": 4100,
    "user_msg_est": 120,
    "prefill_est": 45,
    "total_est": 8315
  }
}
```

**Nachher:**
```json
{
  "stats": {
    "api_input_tokens": 1234,
    "output_tokens": 256,
    "system_prompt_est": 4050,
    "history_est": 4100,
    "user_msg_est": 120,
    "prefill_est": 45,
    "total_est": 8315
  }
}
```

| Feld | Änderung | Begründung |
|------|----------|------------|
| `system_prompt_est` | Wert steigt | Enthält jetzt Cortex-Daten (vorher ~3200, nachher ~4050) |
| `memory_est` | **ENTFERNT** | Cortex-Daten sind Teil von `system_prompt_est` |
| `total_est` | Formel angepasst | `system_prompt_est + history_est + user_msg_est + prefill_est` |
| Alle anderen | Unverändert | — |

### 5.3 Frontend-Kompatibilität

Das Frontend muss den `memory_est` Wert aus der Stats-Anzeige entfernen. Falls es fehlt, sollte es nicht abstürzen (defensive Programmierung).

```javascript
// Frontend-seitig: memory_est nicht mehr erwarten
const memoryEst = stats.memory_est ?? 0;  // Fallback auf 0 wenn nicht vorhanden
```

> **Migration:** Da `memory_est` nur für die Anzeige im Stats-Panel verwendet wird, ist die Änderung unkritisch. Das Frontend zeigt einfach keinen Memory-Wert mehr an.

---

## 6. SSE Done-Event Änderungen

### 6.1 Neues Feld: `cortex_update`

Das Done-Event bekommt ein optionales `cortex_update` Feld, das den Client über ein gestartetes Cortex-Update informiert.

**Ohne Cortex-Update (kein Tier erreicht):**
```json
{
  "type": "done",
  "response": "...",
  "stats": { ... },
  "character_name": "Luna"
}
```

**Mit Cortex-Update (Tier erreicht):**
```json
{
  "type": "done",
  "response": "...",
  "stats": { ... },
  "character_name": "Luna",
  "cortex_update": {
    "tier": 2,
    "status": "started"
  }
}
```

### 6.2 Feld-Beschreibung

| Feld | Typ | Beschreibung |
|------|-----|-------------|
| `cortex_update` | `object \| null` | Nur vorhanden wenn ein Tier ausgelöst wurde |
| `cortex_update.tier` | `int` | Welcher Tier ausgelöst wurde (1, 2, oder 3) |
| `cortex_update.status` | `string` | Immer `"started"` — das Update läuft im Hintergrund |

### 6.3 Frontend-Nutzung

Das Frontend kann das `cortex_update` Feld nutzen, um dem User eine dezente Notification zu zeigen:

```javascript
// Frontend: SSE done handler
if (data.cortex_update) {
    // Optionale UI-Indication, z.B. kleines Cortex-Animation-Icon
    showCortexUpdateIndicator(data.cortex_update.tier);
}
```

Wenn das Frontend das Feld ignoriert, passiert nichts — es ist rein informativ.

---

## 7. Was bleibt unverändert

### 7.1 Unveränderte Komponenten

| Komponente | Warum unverändert |
|------------|------------------|
| **`src/utils/api_request/client.py`** | Der ApiClient sendet System-Prompt + Messages an die API. Ob der System-Prompt Cortex-Daten enthält, ist ihm egal. |
| **`src/utils/prompt_engine/engine.py`** | `build_system_prompt()` leitet `runtime_vars` bereits durch — kein Umbau nötig. Cortex-Block kommt über Order 2000 automatisch ans Ende. |
| **`src/utils/prompt_engine/placeholder_resolver.py`** | Runtime-Vars (Phase 3) werden nativ unterstützt. `cortex_memory`, `cortex_soul`, `cortex_relationship` sind einfach neue Keys. |
| **Message-Sequenz** | `first_assistant → history → user_message → prefill` — diese Reihenfolge ändert sich nicht. Cortex-Daten sind im System-Prompt, nicht in den Messages. |
| **`save_message()` / DB-Schema** | Nachrichten werden identisch gespeichert. Cortex hat keine Auswirkung auf das Chat-DB-Schema. |
| **`get_conversation_context()`** | Der Konversationskontext wird identisch geladen. |

### 7.2 Entfernte Komponenten

| Komponente | Was passiert |
|------------|-------------|
| `_load_memory_context()` | Wird entfernt oder als Legacy-Stub belassen (returns `''`) |
| `format_memories_for_prompt()` | Wird entfernt (war in `memory_context.py`) |
| `include_memories` Parameter | Wird aus `chat_stream()` Signatur entfernt |
| `memory_context` Parameter | Wird aus `_build_chat_messages()` Signatur entfernt |
| `memory_est` Stats-Feld | Wird aus Stats-Dict entfernt |

---

## 8. Error Handling: Graceful Degradation

### 8.1 Prinzip

Das Cortex-System darf **niemals** den normalen Chat-Flow brechen. Wenn der CortexService oder der Tier-Check fehlschlägt, funktioniert der Chat weiterhin — nur ohne Cortex-Daten im System-Prompt.

### 8.2 Fehlerszenarien

| Szenario | Auswirkung | Handling |
|----------|------------|----------|
| **CortexService nicht verfügbar** | `_load_cortex_context()` gibt leere Strings zurück | `{{cortex_*}}` Placeholders bleiben leer → Cortex-Block wird durch Conditional Rendering übersprungen (Step 4B/4C) |
| **Cortex-Dateien nicht vorhanden** | `get_cortex_for_prompt()` gibt leere Strings zurück | Identisch zu oben — Template ist so gestaltet, dass leere Sektionen nicht angezeigt werden |
| **Cortex-Datei defekt (I/O Error)** | `_load_cortex_context()` fängt Exception, returnt leere Strings | Chat funktioniert ohne Cortex, Warning geloggt |
| **Tier-Check schlägt fehl** | `check_and_trigger_cortex_update()` wirft Exception | Exception wird in `chat.py` gefangen, Warning geloggt, Done-Event ohne `cortex_update` gesendet |
| **Background-Update schlägt fehl** | CortexUpdateService loggt Error | Kein Effekt auf aktuellen Chat. Nächster Tier-Check kann erneut triggern. |
| **PromptEngine nicht geladen** | `_engine is None` | Bestehender Fallback: `system_prompt = ''` — Chat funktioniert ohne System-Prompt |

### 8.3 Error-Chain im Code

```python
# 1. Cortex-Loading: Graceful Degradation
def _load_cortex_context(self, persona_id):
    try:
        cortex_service = get_cortex_service()
        return cortex_service.get_cortex_for_prompt(persona_id)
    except Exception as e:
        log.warning("Cortex-Kontext konnte nicht geladen werden: %s", e)
        return {'cortex_memory': '', 'cortex_soul': '', 'cortex_relationship': ''}
        # ↑ Chat funktioniert weiter, Placeholders bleiben leer

# 2. Tier-Check: Non-Fatal
try:
    triggered_tier = check_and_trigger_cortex_update(...)
except Exception as tier_err:
    log.warning("Cortex Tier-Check Fehler (non-fatal): %s", tier_err)
    # ↑ Done-Event wird trotzdem gesendet, nur ohne cortex_update

# 3. Background-Update: Isolierter Thread
def _run_update():
    try:
        service.execute_update(...)
    except Exception as e:
        log.error("Cortex-Update Exception: %s", e)
        # ↑ Thread stirbt leise, nächster Tier-Check kann retry machen
```

### 8.4 Logging-Stufen

| Stufe | Wann |
|-------|------|
| `log.warning` | Cortex nicht ladbar, Tier-Check Fehler (recoverable) |
| `log.error` | Background-Update fehlgeschlagen (sollte untersucht werden) |
| `log.info` | Tier ausgelöst, Update gestartet/abgeschlossen (normal) |
| `log.debug` | Cortex-Daten geladen, Placeholder aufgelöst (Entwicklung) |

---

## 9. Alle modifizierten Dateien

### 9.1 Geänderte Dateien

| # | Datei | Änderung |
|---|-------|----------|
| 1 | `src/routes/chat.py` | Import `check_and_trigger_cortex_update`, Tier-Check in `generate()` bei `chat_stream` und `api_regenerate`, Done-Event um `cortex_update` erweitert |
| 2 | `src/utils/services/chat_service.py` | +`_load_cortex_context()` Methode, `chat_stream()`: Cortex statt Memory laden, `_build_chat_messages()`: `memory_context` Parameter entfernt, `afterthought_decision()`: Cortex statt Memory, `afterthought_followup()`: Cortex statt Memory, Stats: `memory_est` entfernt |

### 9.2 Detaillierte Änderungen pro Datei

#### `src/routes/chat.py`

| Zeile (ca.) | Änderung | Beschreibung |
|-------------|----------|-------------|
| ~5 (Imports) | **NEU** | `from utils.cortex.tier_checker import check_and_trigger_cortex_update` |
| ~93–123 (generate in chat_stream) | **MODIFIZIERT** | `done`-Block: Tier-Check vor Yield, `cortex_update` in Done-Payload |
| ~240–265 (generate in api_regenerate) | **MODIFIZIERT** | Identische Tier-Check-Logik wie in `chat_stream` |

#### `src/utils/services/chat_service.py`

| Zeile (ca.) | Änderung | Beschreibung |
|-------------|----------|-------------|
| ~1 (Docstring) | **MODIFIZIERT** | Docstring aktualisieren: "Memory-Loading" → "Cortex-Loading" |
| ~14 (Import) | **ENTFERNT** | `from ..prompt_engine.memory_context import format_memories_for_prompt` |
| ~43–57 (`_load_memory_context`) | **ENTFERNT** | Gesamte Methode löschen |
| ~43–57 (`_load_cortex_context`) | **NEU** | Neue Methode: Cortex-Dateien laden → Dict |
| ~58 (`_build_chat_messages` Signatur) | **MODIFIZIERT** | `memory_context: str` Parameter entfernen |
| ~107–120 (first_assistant Block) | **MODIFIZIERT** | `memory_context` aus `first_parts` entfernen |
| ~254–258 (`chat_stream` runtime_vars) | **NEU** | `cortex_data = self._load_cortex_context()`, `runtime_vars.update()` |
| ~264–268 (Memory-Loading) | **ENTFERNT** | Gesamter `if include_memories:` Block |
| ~272 (`_build_chat_messages` Aufruf) | **MODIFIZIERT** | `memory_context` Argument entfernen |
| ~304 (total_est Berechnung) | **MODIFIZIERT** | `memory_tokens_est` entfernen |
| ~311 (Stats Dict) | **MODIFIZIERT** | `'memory_est'` Zeile entfernen |
| ~232 (`chat_stream` Signatur) | **MODIFIZIERT** | `include_memories` Parameter entfernen |
| ~347–355 (`afterthought_decision`) | **MODIFIZIERT** | Cortex laden vor `build_system_prompt()`, Memory-Block entfernen |
| ~443–454 (`afterthought_followup`) | **MODIFIZIERT** | Cortex laden vor `build_system_prompt()`, Memory-Block entfernen |
| ~497 (afterthought Stats) | **MODIFIZIERT** | `'memory_est': 0` → entfernen |

### 9.3 Unveränderte Dateien

| Datei | Warum unverändert |
|-------|------------------|
| `src/utils/api_request/client.py` | Empfängt System-Prompt + Messages — keine Cortex-Kenntnis nötig |
| `src/utils/prompt_engine/engine.py` | `build_system_prompt()` und `runtime_vars` funktionieren bereits |
| `src/utils/prompt_engine/placeholder_resolver.py` | Phase-3 Runtime-Vars werden nativ unterstützt |
| `src/utils/cortex/tier_checker.py` | Wird **importiert** aber nicht **geändert** (aus Step 3B) |
| `src/utils/cortex/tier_tracker.py` | Wird von tier_checker intern verwendet (aus Step 3B) |
| `src/utils/cortex/update_service.py` | Wird im Background-Thread aufgerufen (aus Step 3C) |

### 9.4 Entfernte Dateien/Module

| Datei | Was passiert |
|-------|-------------|
| `src/utils/prompt_engine/memory_context.py` | Wird in Step 1 (Altes Memory entfernen) gelöscht — hier nicht mehr importiert |

---

## 10. Gesamtbild: System-Prompt-Aufbau mit Cortex

```
┌──────────────────────────────────────────────────────┐
│                    SYSTEM PROMPT                      │
│                                                      │
│  ┌─────────────────────────────────────────────┐     │
│  │ Block 1 (Order 100): core_identity          │     │
│  │ "Du bist {{char_name}}, {{char_age}}..."    │     │
│  └─────────────────────────────────────────────┘     │
│                                                      │
│  ┌─────────────────────────────────────────────┐     │
│  │ Block 2 (Order 200): personality            │     │
│  │ "{{char_core_traits}}"                      │     │
│  └─────────────────────────────────────────────┘     │
│                                                      │
│  ┌─────────────────────────────────────────────┐     │
│  │ Block 3 (Order 300): behavior_rules         │     │
│  │ "Antworte immer auf {{language}}..."        │     │
│  └─────────────────────────────────────────────┘     │
│                                                      │
│  ┌─────────────────────────────────────────────┐     │
│  │ ...weitere Blöcke (400-1900)...             │     │
│  └─────────────────────────────────────────────┘     │
│                                                      │
│  ┌─────────────────────────────────────────────┐     │
│  │ Block N (Order 2000): cortex_context  ← NEU │     │
│  │                                             │     │
│  │ **INNERE WELT — SELBSTWISSEN**              │     │
│  │                                             │     │
│  │ Die folgenden Abschnitte beschreiben dein   │     │
│  │ tiefstes Wissen über dich selbst...         │     │
│  │                                             │     │
│  │ {{cortex_memory}}                           │     │
│  │ → "# Erinnerungen\n- Max liebt Katzen..."  │     │
│  │                                             │     │
│  │ {{cortex_soul}}                             │     │
│  │ → "# Identität\nIch bin neugierig..."       │     │
│  │                                             │     │
│  │ {{cortex_relationship}}                     │     │
│  │ → "# Beziehung\nEnge Freundschaft..."       │     │
│  │                                             │     │
│  │ **ENDE INNERE WELT**                        │     │
│  └─────────────────────────────────────────────┘     │
│                                                      │
└──────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────┐
│                    MESSAGES                           │
│                                                      │
│  ┌─────────────────────────────────────────────┐     │
│  │ first_assistant (optional)                  │     │
│  │ Prefill-Impersonation (experimental only)   │     │
│  │ ⚠️ KEIN Memory-Content mehr hier!           │     │
│  └─────────────────────────────────────────────┘     │
│                                                      │
│  ┌─────────────────────────────────────────────┐     │
│  │ history                                     │     │
│  │ Greeting → User → Bot → User → Bot → ...   │     │
│  └─────────────────────────────────────────────┘     │
│                                                      │
│  ┌─────────────────────────────────────────────┐     │
│  │ user_message                                │     │
│  │ "Hey Luna, erinnerst du dich an gestern?"   │     │
│  └─────────────────────────────────────────────┘     │
│                                                      │
│  ┌─────────────────────────────────────────────┐     │
│  │ prefill (optional)                          │     │
│  │ Remember-Block als letzte Assistant-Message  │     │
│  └─────────────────────────────────────────────┘     │
│                                                      │
└──────────────────────────────────────────────────────┘
```

---

## 11. Zusammenfassung

| Aspekt | Detail |
|--------|--------|
| **Kern-Änderung** | Cortex-Daten fließen via `runtime_vars` in den System-Prompt ein |
| **Position im Prompt** | Letzter Block (Order 2000, Template `cortex_context.json`) |
| **Message-Sequenz** | Unverändert: `first_assistant → history → user_message → prefill` |
| **Memory-Entfernung** | `_load_memory_context()`, `memory_context` Parameter, `memory_est` Stats-Feld |
| **Tier-Check** | Synchron im `done`-Handler, Ergebnis im SSE-Done-Event |
| **Background-Update** | Asynchroner Thread via `CortexUpdateService` (Step 3C) |
| **Error Handling** | Dreistufig: Cortex-Load → Tier-Check → Background-Update, jeweils non-fatal |
| **Stats-Änderung** | `memory_est` entfällt, Cortex ist Teil von `system_prompt_est` |
| **SSE-Änderung** | Optionales `cortex_update` Feld im Done-Event |
| **Geänderte Dateien** | 2 (`chat.py`, `chat_service.py`) |
| **Abhängigkeiten** | Step 2B (CortexService), Step 3B (tier_checker), Step 4A/4B (Placeholders + Template) |
