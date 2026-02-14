# 05 — Chat System

## Overview

The chat system is the **core feature** of PersonaUI. It enables real-time communication with AI personas via Server-Sent Events (SSE), including a unique "Afterthought" system for autonomous persona messages.

---

## Architecture

```
Frontend (MessageManager.js)
  │
  ├── POST /chat_stream ──→ chat.py ──→ ChatService.chat_stream()
  │                                         │
  │                                    PromptEngine.build_system_prompt()
  │                                    PromptEngine.build_prefill()
  │                                    PromptEngine.get_chat_message_sequence()
  │                                         │
  │                                    ApiClient.stream(RequestConfig)
  │                                         │
  │                                    Anthropic Claude API
  │
  ├── POST /afterthought ──→ chat.py ──→ ChatService.afterthought_decision()
  │   (decision phase)                     ChatService.afterthought_followup()
  │
  └── SSE Events ← chunk | done | error
```

---

## Chat Flow (Main Message)

### 1. Frontend Sends Message

```javascript
// MessageManager.js → sendMessage()
POST /chat_stream {
  message: "Hallo!",
  session_id: 1,
  api_model: "claude-sonnet-4-5-20250929",
  api_temperature: 0.7,
  experimental_mode: false,
  context_limit: 25
}
```

### 2. Backend Processing

1. **Validation**: Message not empty, API key present
2. **Context limit**: Clamped to [10, 100]
3. **Character data** loaded (active persona)
4. **Conversation context** fetched from persona-specific DB
5. **SSE stream** started

### 3. ChatService Message Assembly

`_build_chat_messages()` follows the PromptEngine sequence:

| Position | Content | Role |
|----------|---------|------|
| `first_assistant` | Memory context (memories) | `assistant` |
| `history` | Conversation history | alternating `user`/`assistant` |
| `prefill` | Control prefix for the response | `assistant` |

**Edge Case Handling:**
- Consecutive identical roles are separated by "bridge messages" (Claude API requires alternating roles)
- Dialog injections are inserted as separate messages

### 4. SSE Stream Processing

```
Server → SSE Events:
  data: {"type":"chunk", "text":"Hallo"}
  data: {"type":"chunk", "text":" zurück!"}
  data: {"type":"done", "response":"Hallo zurück!", "stats":{...}, "character_name":"Mia"}
```

The frontend uses the `ReadableStream` API to process SSE events:
- **`chunk`**: Text is continuously inserted into the chat bubble (with cursor animation)
- **`done`**: Final response + statistics, user and bot messages are saved to the DB
- **`error`**: Special handling for `credit_balance_exhausted`

### 5. Save Message to DB

After the complete stream:
- User message saved on the **first chunk**
- Bot response saved on the **done** event
- Both stored in the persona-specific SQLite DB

---

## Afterthought System

A unique feature: The persona can **unsolicited** send a follow-up message.

### Timer Escalation (Frontend)

```
10 seconds → 1 minute → 5 minutes → 15 minutes → 1 hour
```

After each timer expires, the decision phase is triggered.

### Phase 1: Decision (Inner Dialogue)

```
POST /afterthought {
  phase: "decision",
  session_id: 1,
  elapsed_time: "10 Sekunden"
}
```

1. PromptEngine resolves `afterthought_inner_dialogue` prompt
2. Persona system prompt includes `afterthought_system_note` (position: `system_prompt_append`)
3. Persona performs an inner monologue and ends with **"Ja"** (Yes) or **"Nein"** (No)
4. Response is parsed (last word)

**Response:**
```json
{
  "decision": true,
  "inner_dialogue": "Hmm, ich möchte noch etwas hinzufügen... Ja"
}
```

### Phase 2: Followup (Streamed)

Only if `decision = true`:

```
POST /afterthought {
  phase: "followup",
  session_id: 1,
  inner_dialogue: "...",
  elapsed_time: "10 Sekunden"
}
```

- Returned as SSE stream (like `/chat_stream`)
- Follow-up message is saved to the DB
- Afterthought timers are reset

---

## Variant System

| Variant | Description |
|---------|-------------|
| `default` | Standard mode, SFW content |
| `experimental` | Extended features, fewer restrictions |

The variant affects:
- Which prompts are loaded (`variant_condition`)
- Prompt content (each domain file can have different variants)
- System prompt assembly

---

## System Prompt Assembly

The system prompt is composed of **15+ individual prompt building blocks** (sorted by `order`):

| Order | Prompt | Description |
|-------|--------|-------------|
| 100 | `impersonation` | Core identity instruction |
| 200 | `persona_integrity_shield` | Persona integrity protection |
| 300 | `system_rule` | General system rules |
| 400 | `conversation_dynamics` | Conversation dynamics |
| 500 | `topic_transition_guard` | Topic transition guard |
| 600 | `persona_description` | Persona description |
| 600 | `world_consistency` | World consistency |
| 700 | `expression_style_detail` | Expression style details |
| 900 | `emotional_state` | Emotional state |
| 1000 | `user_info` | User information |
| 1100 | `relationship_tracking` | Relationship tracking |
| 1200 | `time_sense` | Time awareness |
| 1300 | `response_style_control` | Response style control |
| 1400 | `output_format` | Output format |
| 1500 | `topic_boundaries` | Topic boundaries |
| 1600 | `continuity_guard` | Continuity guard |

---

## Notification Sound

Generated via Web Audio API (no audio file import):
- **Two-tone signal**: D5 (587 Hz) + G5 (784 Hz)
- Duration: 80ms per tone
- Gain envelope for a soft sound

---

## Dependencies

```
MessageManager.js (Frontend)
  ├── /chat_stream (SSE) → chat.py
  │     ├── ChatService.chat_stream()
  │     │     ├── PromptEngine (system prompt, prefill, sequence)
  │     │     ├── ApiClient.stream() → Anthropic API
  │     │     └── database (conversation context)
  │     └── database (save messages)
  │
  └── /afterthought (SSE/JSON) → chat.py
        ├── ChatService.afterthought_decision()
        └── ChatService.afterthought_followup()
```

---

## Design Decisions

1. **SSE instead of WebSockets**: Server-Sent Events for simplicity and HTTP compatibility
2. **Per-chunk streaming**: Response is streamed character by character for a natural typing feel
3. **Afterthought timer escalation**: Escalating intervals prevent too-frequent API calls
4. **Bridge messages**: Automatic insertion when consecutive identical roles occur
5. **User message saved only on first chunk**: Prevents saving on API errors
6. **Credit balance detection**: Special error handling for exhausted API credits
