# 11 — Services Layer

> ApiClient, ChatService, CortexService, and the Provider singleton pattern.

---

## Overview

PersonaUI's service layer consists of three main services managed by the Provider:

```
Provider (singleton locator)
├── ApiClient      Anthropic SDK wrapper (sync + streaming)
├── ChatService    Chat orchestration (message assembly → API → response)
└── CortexService  Long-term memory orchestration (tool_use)
```

All services are initialized once during startup and accessed via `provider.py`.

---

## Provider — Service Locator

**File:** `src/utils/provider.py`

```python
from utils.provider import (
    get_api_client,       # → ApiClient
    get_chat_service,     # → ChatService
    get_cortex_service,   # → CortexService
    get_prompt_engine,    # → PromptEngine (lazy init)
)
```

### How It Works

```python
class Provider:
    _api_client = None
    _chat_service = None
    _cortex_service = None
    _prompt_engine = None

    @classmethod
    def set_api_client(cls, client): cls._api_client = client
    
    @classmethod
    def get_api_client(cls): return cls._api_client

    @classmethod
    def get_prompt_engine(cls):
        if cls._prompt_engine is None:
            cls._prompt_engine = PromptEngine()  # Lazy init
        return cls._prompt_engine
```

Services are set during `app.py:init_services()`. The `PromptEngine` is lazily initialized on first call to `get_prompt_engine()`.

---

## ApiClient — Anthropic SDK Wrapper

**File:** `src/utils/api_request/client.py` (~418 lines)

```
src/utils/api_request/
├── client.py           ApiClient class
├── response_cleaner.py Response post-processing
├── types.py            RequestConfig, ApiResponse, StreamEvent
└── __init__.py         Package exports
```

### Initialization

```python
client = ApiClient(api_key='sk-ant-...')
# or
client = ApiClient()  # Reads from ANTHROPIC_API_KEY env var
```

Creates an `anthropic.Anthropic` SDK instance. The `is_ready` property checks if the client was initialized successfully.

### Request Types

| Type | Purpose |
|------|---------|
| `RequestConfig` | Input: system prompt, messages, model, temperature, max_tokens, prefill |
| `ApiResponse` | Output: success, content, usage, raw_response, stop_reason |
| `StreamEvent` | Streaming output: type (`chunk`/`done`/`error`) + content |

### Synchronous Requests

```python
response = client.request(RequestConfig(
    system_prompt="You are a helpful assistant.",
    messages=[{"role": "user", "content": "Hello"}],
    model="claude-sonnet-4-20250514",
    temperature=0.7,
    max_tokens=4096,
))
# response.success, response.content, response.usage
```

Used for: afterthought decisions, cortex updates, spec autofill, session title generation, tests.

### Streaming Requests

```python
for event in client.stream(config):
    if event.type == 'chunk':
        print(event.content, end='')  # Token fragment
    elif event.type == 'done':
        print(f'\n[Done: {event.usage}]')
    elif event.type == 'error':
        print(f'Error: {event.content}')
```

Used for: chat responses, afterthought followups.

### API Key Update

```python
client.update_api_key('sk-ant-new-key')  # Hot-swap without restart
```

### Model Resolution

```python
client._resolve_model(model=None)
# Returns configured default from settings if model is None
```

### Response Cleaning

**File:** `src/utils/api_request/response_cleaner.py`

Post-processes API responses:
- Strips prefill text from the beginning of responses
- Cleans up formatting artifacts
- Handles edge cases in Claude's output

### Error Handling

The client catches `anthropic.APIError` and returns structured errors:
- **Credit balance exhausted** → `error: "credit_balance_exhausted"` (special handling in UI)
- **Other API errors** → Error string passed through
- **Connection errors** → Generic error message

---

## ChatService — Chat Orchestration

**File:** `src/utils/services/chat_service.py` (~559 lines)

The ChatService is the central orchestator. It connects the PromptEngine, conversation history, Cortex memory, and the ApiClient.

### Initialization

```python
chat_service = ChatService(api_client)
# Tries to load PromptEngine via Provider
# Falls back gracefully if engine unavailable
```

### Main Method: `stream_chat()`

```python
for event in chat_service.stream_chat(
    user_message="How are you?",
    conversation_history=[...],
    char_name="Luna",
    user_name="Alex",
    persona_language="english",
    session_id=1,
    persona_id="default",
    api_model=None,
    api_temperature=None,
    experimental_mode=False,
    pending_afterthought=None,
):
    handle_event(event)
```

### Internal Flow

```
stream_chat()
    │
    ├── 1. Build system prompt
    │     └── PromptEngine.build_system_prompt(variant, runtime_vars)
    │         ├── Resolve all enabled prompt templates
    │         ├── Fill {{placeholders}} (3-phase resolution)
    │         └── Concatenate into single system prompt string
    │
    ├── 2. Load Cortex context (if enabled)
    │     └── CortexService.get_cortex_for_prompt(persona_id)
    │
    ├── 3. Build message sequence
    │     └── _build_chat_messages()
    │         ├── Get sequence from PromptEngine
    │         ├── Insert conversation history
    │         ├── Add dialog injections (experimental)
    │         └── Add prefill (if configured)
    │
    ├── 4. Create RequestConfig
    │     └── system_prompt + messages + model + temperature
    │
    └── 5. Stream request
          └── ApiClient.stream(config) → yield StreamEvents
```

### Settings Reading

The ChatService reads settings directly from JSON files (not via the Provider) to stay decoupled:

```python
def _read_setting(key, default=None):
    """Reads from user_settings.json, fallback to defaults.json."""
```

### Afterthought Support

The ChatService also handles afterthought decisions:

```python
result = chat_service.evaluate_afterthought(
    conversation_history, char_name, elapsed_time, persona_language
)
# {'decision': True, 'inner_dialogue': 'I should ask about...'}
```

---

## CortexService — Long-Term Memory

**File:** `src/utils/cortex_service.py` (~719 lines)

See [10 — Cortex Memory System](10_Cortex_Memory_System.md) for comprehensive documentation.

Key methods:

```python
cortex = get_cortex_service()

# Get formatted cortex content for system prompt
context = cortex.get_cortex_for_prompt(persona_id)

# File operations
content = cortex.read_cortex_file(persona_id, 'memory.md')
cortex.write_cortex_file(persona_id, 'memory.md', new_content)
cortex.reset_cortex_file(persona_id, 'memory.md')

# Update trigger
cortex.run_cortex_update(persona_id, session_id)
```

---

## Service Lifecycle

```
Startup (app.py)
│
├── ApiClient(api_key)          ← Created from .env
├── ChatService(api_client)     ← Receives ApiClient
├── CortexService(api_client)   ← Receives ApiClient
│
├── Provider.set_api_client()
├── Provider.set_chat_service()
├── Provider.set_cortex_service()
│
└── PromptEngine                ← Lazy-initialized on first use
```

### Hot-Swap API Key

When the user changes their API key through the UI:

```python
client = get_api_client()
client.update_api_key(new_key)
# All services that reference this client automatically use the new key
```

---

## Type Definitions

**File:** `src/utils/api_request/types.py`

```python
@dataclass
class RequestConfig:
    system_prompt: str
    messages: list
    model: str = None
    temperature: float = 0.7
    max_tokens: int = 4096
    prefill: str = None

@dataclass
class ApiResponse:
    success: bool
    content: str = ''
    error: str = None
    usage: dict = None
    raw_response: Any = None
    stop_reason: str = None

@dataclass
class StreamEvent:
    type: str        # 'chunk', 'done', 'error'
    content: str = ''
    usage: dict = None
```

---

## Related Documentation

- [01 — App Core & Startup](01_App_Core_and_Startup.md) — Service initialization
- [05 — Chat System](05_Chat_System.md) — How ChatService is used
- [06 — Prompt Engine](06_Prompt_Engine.md) — Prompt resolution
- [10 — Cortex Memory System](10_Cortex_Memory_System.md) — CortexService details
