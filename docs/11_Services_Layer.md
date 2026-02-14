# 11 — Services Layer

## Overview

The services layer encapsulates the core business logic of PersonaUI in **three central services**: `ApiClient`, `ChatService`, and `MemoryService`. These services manage API communication, chat orchestration, and the memory system.

---

## Architecture

```
Services Layer:
  src/utils/services/
    ├── __init__.py
    ├── api_client.py      ← API communication with Anthropic
    ├── chat_service.py    ← Chat orchestration & SSE streaming
    └── memory_service.py  ← Memory management & extraction
```

All services are **lazily initialized** via the Provider pattern (see doc 03).

---

## ApiClient (`api_client.py`)

### Responsibility

Direct interface to the Anthropic Claude API. Handles authentication, request building, streaming, and error handling.

### Key Methods

| Method | Description |
|--------|-------------|
| `send_message(messages, system, model, max_tokens, stream)` | Send message to Claude API |
| `send_message_streaming(messages, system, model, max_tokens)` | SSE streaming response |
| `count_tokens(messages, system)` | Token counting via API |
| `get_available_models()` | List available models |

### Streaming Implementation

```python
def send_message_streaming(self, messages, system, model, max_tokens):
    with self.client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=messages
    ) as stream:
        for text in stream.text_stream:
            yield text
```

### Configuration

- **API Key**: Read from `user_settings.json` → `apiKey`
- **Models**: Configurable per function (chat, afterthought, autofill)
- **Max tokens**: Per-request configurable
- **Timeout**: Default 120 seconds
- **Retry logic**: Automatic retry on transient errors (429, 500, 529)

### Error Handling

| Error | Handling |
|-------|----------|
| `AuthenticationError` | Clear message to check API key |
| `RateLimitError` | Retry with exponential backoff |
| `APIConnectionError` | Retry, then clear error message |
| `APIStatusError` (overloaded) | Retry with backoff |
| General exceptions | Logged, wrapped in `ServiceError` |

---

## ChatService (`chat_service.py`)

### Responsibility

Orchestrates the complete chat flow: message preparation, prompt building, API call, response processing, persistence, and afterthought triggering.

### Chat Flow (Sequence)

```
User sends message
  → ChatService.process_message()
    1. Load conversation history from DB
    2. Build system prompt (via PromptEngine)
    3. Append user message to history
    4. Trim history if token limit exceeded
    5. API call (streaming via ApiClient)
    6. Collect & save AI response
    7. Trigger afterthought (async)
    8. Return full response
```

### Key Methods

| Method | Description |
|--------|-------------|
| `process_message(user_message, session_id)` | Main entry: process a chat message |
| `stream_response(user_message, session_id)` | SSE streaming chat response |
| `get_conversation_history(session_id)` | Load message history |
| `save_message(session_id, role, content)` | Persist a message |
| `trim_history(messages, max_tokens)` | Shorten history to fit token limit |
| `trigger_afterthought(session_id, user_msg, ai_msg)` | Start afterthought analysis |
| `regenerate_response(session_id)` | Regenerate last AI response |
| `edit_and_regenerate(session_id, message_id, new_content)` | Edit user message & regenerate |

### SSE Streaming

```python
def stream_response(self, user_message, session_id):
    # 1. Prepare (history, prompt, etc.)
    # 2. Start streaming
    for chunk in self.api_client.send_message_streaming(...):
        yield f"data: {json.dumps({'text': chunk})}\n\n"
    # 3. After complete: save, afterthought
    yield f"data: {json.dumps({'done': True, 'message_id': msg_id})}\n\n"
```

### History Management

- **Token limit**: Configurable via `contextLength` setting
- **Trimming strategy**: Oldest messages removed first, system prompt never trimmed
- **Persistence**: All messages stored in persona-specific SQLite DB
- **Context window**: Sliding window over conversation history

### Afterthought System

After each AI response, an **asynchronous afterthought analysis** is triggered:

1. Build afterthought prompt (separate from chat prompt)
2. Send last exchange (user + AI) for analysis
3. Parse JSON response for:
   - `inner_thoughts`: AI's internal monologue
   - `mood_summary`: Current mood
   - `memory_markers`: Memorable items (→ MemoryService)
4. Save afterthought result to DB
5. Send SSE event with afterthought data

Uses the cost-efficient `apiAfterModel` to keep costs low.

### Variant System

Supports **response variants** (regeneration):

```
Original response → Variant 1 → Variant 2 → ...
  ↑ User can navigate between variants
```

| Feature | Description |
|---------|-------------|
| Regenerate | Generate new response for same input |
| Edit & regenerate | Edit user message, then regenerate |
| Variant navigation | Switch between response variants |
| Variant deletion | Remove unwanted variants |

Variants are stored as separate messages with a `variant_group` field linking them.

---

## MemoryService (`memory_service.py`)

See dedicated [10_Memory_System.md](10_Memory_System.md) for full documentation.

### Summary of Integration

```
ChatService → afterthought → memory_markers
  → MemoryService.process_memory_markers()
    → Validate & deduplicate
    → Persist to DB
    → Available via {{memories}} placeholder in next prompt
```

---

## Service Initialization

### Provider Pattern

Services are initialized lazily via the Provider module:

```python
# src/utils/provider.py

_api_client = None
_chat_service = None
_memory_service = None

def get_api_client():
    global _api_client
    if _api_client is None:
        _api_client = ApiClient(api_key=get_api_key())
    return _api_client

def get_chat_service():
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService(
            api_client=get_api_client(),
            prompt_engine=get_prompt_engine()
        )
    return _chat_service
```

### Advantages

1. **No circular imports**: Services are created on-demand
2. **Testable**: Easy to inject mocks
3. **Memory efficient**: Only instantiated when needed
4. **Configurable**: API key changes trigger re-initialization

### Re-initialization

When settings change (e.g., API key), services are re-created:

```python
def reset_services():
    global _api_client, _chat_service, _memory_service
    _api_client = None
    _chat_service = None
    _memory_service = None
```

---

## Dependencies

```
ApiClient
  ├── anthropic SDK
  ├── user_settings.json (API key, models)
  └── logger

ChatService
  ├── ApiClient (API calls)
  ├── PromptEngine (prompt building)
  ├── Database (message persistence)
  ├── MemoryService (afterthought → memories)
  └── logger

MemoryService
  ├── Database (memory persistence)
  ├── ApiClient (for extraction, if needed)
  └── logger

Provider
  ├── ApiClient, ChatService, MemoryService
  ├── PromptEngine
  └── Settings (API key, model config)
```

---

## Design Decisions

1. **Service separation**: Each service has a clear, single responsibility
2. **Lazy initialization**: Services are only created when first accessed
3. **Provider pattern**: Centralized service creation avoids circular dependencies
4. **Streaming-first**: Chat uses SSE streaming for real-time response display
5. **Afterthought as side-effect**: Post-processing runs after response delivery, doesn't block the user
6. **Cost-aware model selection**: Different models for chat (powerful) vs. afterthought/autofill (cost-efficient)
7. **Variant system**: Users can regenerate and compare responses without losing history
