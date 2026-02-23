# 05 — Chat System

> SSE streaming, message assembly, afterthought system, and the complete chat request lifecycle.

---

## Overview

The chat system is the core feature of PersonaUI. A user message flows through several layers before reaching the Anthropic API and streaming back:

```
User types message (React)
    │
    ├── POST /chat_stream (Flask)
    │     ├── Load persona config
    │     ├── Load conversation history (SQLite)
    │     ├── Load Cortex memory (if enabled)
    │     ├── ChatService.stream_chat()
    │     │     ├── PromptEngine → system prompt
    │     │     ├── Build message sequence
    │     │     └── ApiClient.stream() → Anthropic API
    │     ├── SSE stream → React frontend
    │     ├── Save messages to DB
    │     └── Check Cortex update trigger
    │
    └── (optional) POST /afterthought
          ├── Phase 1: Decision (should persona follow up?)
          └── Phase 2: Followup (SSE streamed response)
```

---

## SSE Streaming — `/chat_stream`

### Request

```json
POST /chat_stream
{
    "message": "Hello!",
    "session_id": 1,
    "api_model": "claude-sonnet-4-20250514",
    "api_temperature": 0.7,
    "context_limit": 25,
    "experimental_mode": false,
    "pending_afterthought": null
}
```

### Response (Server-Sent Events)

```
data: {"type": "chunk", "content": "Hello"}
data: {"type": "chunk", "content": " there!"}
data: {"type": "chunk", "content": " How are"}
data: {"type": "chunk", "content": " you?"}
data: {"type": "done", "content": "Hello there! How are you?", "usage": {"input_tokens": 1200, "output_tokens": 15}, "afterthought": true}
```

Event types:
- **`chunk`** — Partial token from the streaming response
- **`done`** — Stream complete. Includes full text, token usage, and afterthought flag
- **`error`** — An error occurred. Includes error message and optional `error_type`

### Processing Flow

1. **Validate input** — Check for empty message, API key readiness
2. **Load context** — Persona config, user profile, conversation history
3. **Build messages** via `ChatService._build_chat_messages()`:
   - Get message sequence from PromptEngine
   - Insert conversation history at correct position
   - Apply dialog injections (experimental mode)
   - Add prefill if configured
4. **Build system prompt** via PromptEngine — resolves all placeholders
5. **Stream to API** via `ApiClient.stream()` — yields `StreamEvent` objects
6. **Save to DB** — User message saved on first chunk, bot message on done
7. **Cortex check** — `check_and_trigger_cortex_update()` if enabled

---

## System Prompt Assembly

The system prompt is built from multiple prompt templates, each resolved via the PromptEngine:

```
┌─────────────────────────────────────┐
│          System Prompt              │
├─────────────────────────────────────┤
│ 1. system_rule                      │  ← Core behavior rules
│ 2. persona_description              │  ← Character description
│ 3. output_format                    │  ← Response formatting rules
│ 4. response_style_control           │  ← Style enforcement
│ 5. expression_style_detail          │  ← Writing style details
│ 6. emotional_state                  │  ← Current emotional context
│ 7. conversation_dynamics            │  ← Conversation flow rules
│ 8. topic_boundaries                 │  ← Topic restrictions
│ 9. topic_transition_guard           │  ← Smooth topic changes
│ 10. relationship_tracking           │  ← User relationship context
│ 11. continuity_guard                │  ← Memory continuity
│ 12. persona_integrity_shield        │  ← Stay in character
│ 13. world_consistency               │  ← Fictional world rules
│ 14. time_sense                      │  ← Current date/time
│ 15. user_info                       │  ← User name/preferences
│ 16. cortex_context                  │  ← Long-term memory (if enabled)
│ 17. conversation_history_context    │  ← Recent history summary
│ 18. remember                        │  ← Key facts to remember
└─────────────────────────────────────┘
```

Each block is a JSON prompt template with `{{placeholder}}` variables resolved by the engine. The sequence and inclusion of blocks depends on the active variant (`default` or `experimental`).

---

## Message Sequence

The `ChatService._build_chat_messages()` method constructs the messages array sent to the Anthropic API. The sequence is defined by the PromptEngine and typically follows this order:

```
Messages Array:
  1. [assistant] First assistant message (impersonation prefill)
  2. [user/assistant...] Conversation history
  3. [user/assistant...] Dialog injections (experimental mode)
  4. [user] Current user message
  5. [assistant] Response prefill (primes the response style)
```

The `conversation_history` is loaded from SQLite with a configurable `context_limit` (default: 25 messages, range: 10–100).

---

## Afterthought System

The afterthought system allows the persona to autonomously send follow-up messages after a period of silence. It works in two phases:

### Phase 1: Decision

The frontend calls `POST /afterthought` with `phase: "decision"` after a configurable delay:

```json
POST /afterthought
{
    "session_id": 1,
    "phase": "decision",
    "elapsed_time": "15 seconds"
}
```

The backend asks the AI: *"Should you say something more?"* — returns a yes/no decision with an inner dialogue explaining the reasoning.

```json
{
    "success": true,
    "data": {
        "decision": true,
        "inner_dialogue": "I want to ask about their day..."
    }
}
```

### Phase 2: Followup

If the decision was "yes", the frontend calls `POST /afterthought` with `phase: "followup"`:

```json
POST /afterthought
{
    "session_id": 1,
    "phase": "followup",
    "inner_dialogue": "I want to ask about their day..."
}
```

This returns an SSE stream just like `/chat_stream` with the persona's follow-up message.

### Timer Escalation

The afterthought delay escalates with consecutive follow-ups to prevent spam:

```
1st afterthought:  base delay (e.g., 15s)
2nd afterthought:  2× base delay
3rd afterthought:  increasing delay
...until user sends a message (resets the counter)
```

### Afterthought Prompts

Three dedicated prompt templates drive the system:
- `afterthought_system_note` — Injected into the system prompt during afterthought
- `afterthought_inner_dialogue` — The decision-phase prompt
- `afterthought_followup` — The followup-phase system context

---

## Variant System

The chat system supports two variants:

| Variant | Activated By | Effect |
|---------|-------------|--------|
| `default` | Normal mode | Standard prompts and behavior |
| `experimental` | `experimentalMode: true` | Extended prompts, dialog injections, prefill impersonation |

Variants are configured in the PromptEngine manifest. Each prompt can have different text for each variant.

---

## Message Persistence

Messages are saved to the per-persona SQLite database:

```
User sends "Hello"
    → save_message(session_id, "Hello", is_user=True, char_name="User")

AI responds "Hi there!"
    → save_message(session_id, "Hi there!", is_user=False, char_name="Luna")
```

Session timestamps are updated after each message.

---

## Additional Chat Endpoints

### Auto First Message — `POST /chat/auto_first_message`

When `start_msg_enabled` is true in settings, the persona automatically sends a greeting when entering an empty chat. Uses the SSE streaming format.

### Regenerate — `POST /chat/regenerate`

Deletes the last bot message and re-generates it. The user message remains, and a new response is streamed.

### Edit Last Message — `PUT /chat/last_message`

Updates the text of the last message in the database. Used for inline editing.

### Delete Last Message — `DELETE /chat/last_message`

Removes the last message from the session.

### Clear Chat — `POST /clear_chat`

Deletes all messages in a session.

---

## Related Documentation

- [04 — Routes & API](04_Routes_and_API.md) — Endpoint reference
- [06 — Prompt Engine](06_Prompt_Engine.md) — Template resolution
- [08 — Database Layer](08_Database_Layer.md) — Message persistence
- [10 — Cortex Memory System](10_Cortex_Memory_System.md) — Cortex update triggers
- [11 — Services Layer](11_Services_Layer.md) — ChatService and ApiClient
