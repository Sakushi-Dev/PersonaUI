# 15 — Tests & Quality Assurance

## Overview

PersonaUI has a comprehensive test suite with **~162 tests** across 10 test files. The tests use `pytest` and `unittest.mock`, focusing on unit tests and integration tests. No real API calls are made.

---

## Configuration

### `pytest.ini`

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short --ignore=src
```

Verbose output, short tracebacks, `src/` directory is ignored.

---

## Test Infrastructure (`conftest.py`)

### Path Setup

```python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
os.chdir(os.path.join(os.path.dirname(__file__), '..', 'src'))
```

### Fixtures (15 Total)

| Category | Fixture | Description |
|----------|---------|-------------|
| **Persona** | `test_character_data` | Full persona: TestPersona, 25, female |
| | `minimal_character_data` | Minimal persona (Mini): only required fields |
| **Memory** | `sample_memories` | 2 active memories |
| | `empty_memories` | Empty list |
| | `many_memories` | 35 memories (exceeds 30-item limit) |
| **Conversation** | `sample_conversation` | 4 messages (2 user/assistant pairs) |
| | `empty_conversation` | Empty list |
| **API** | `mock_anthropic` | Mocked Anthropic module with default response |
| | `mock_anthropic_stream` | Streaming mock (ContentBlockDelta events) |
| | `api_client` | Initialized `ApiClient` with mock |
| | `api_client_stream` | Initialized `ApiClient` with stream mock |
| **Service** | `mock_api_client` | Fully mocked `ApiClient` with `ApiResponse` |
| | `mock_engine` | Mocked `PromptEngine` with all builder methods |
| | `chat_service` | `ChatService` with mocked dependencies |
| | `memory_service` | `MemoryService` with mocked dependencies |

**ChatService construction:** Via `__new__` + manual attribute assignment to avoid `__init__` side effects.

---

## Test Suite Overview

| Area | File | Tests | Coverage |
|------|------|-------|----------|
| API Client | `test_api_client.py` | ~20 | Dataclasses, response cleaner, client init/request/stream |
| Provider | `test_provider.py` | 8 | Service locator lifecycle |
| Chat Flow | `test_integration/test_chat_flow.py` | 13 | E2E chat: PromptEngine → message assembly → API → response |
| Afterthought | `test_integration/test_afterthought_flow.py` | 2 | Decision → followup flow |
| Memory Flow | `test_integration/test_memory_flow.py` | 3 | Preview → save, custom memory |
| Engine Integration | `test_prompt_builder/test_engine_integration.py` | ~17 | Engine parity, service integration, architecture rules |
| Prompt Engine | `test_prompt_engine/test_prompt_engine.py` | ~48 | Core engine, placeholder, loader, validator |
| Phase 5 | `test_prompt_engine/test_phase5.py` | 19 | Export, import, factory reset, integrity |
| Chat Service | `test_services/test_chat_service.py` | 8 | Streaming, afterthought, greeting |
| Memory Service | `test_services/test_memory_service.py` | 8 | Formatting, preview, save |
| **Total** | **10 files** | **~162** | |

---

## Detailed Test Descriptions

### API Client Tests (`test_api_client.py`)

| Test Class | Tests | Coverage |
|------------|-------|----------|
| `TestRequestConfig` | 2 | Default and custom values for RequestConfig dataclass |
| `TestApiResponse` | 3 | Success/error/default states |
| `TestStreamEvent` | 3 | Chunk/done/error types |
| `TestResponseCleaner` | 5 | Plain text, empty, None, code blocks, HTML tags |
| `TestApiClientInit` | 3 | Init with/without key, `update_api_key` |
| `TestApiClientRequest` | 3 | Simple request, prefill injection, message structure |
| `TestApiClientStream` | 1 | Stream yields events |
| `TestApiClientContract` | 2 | Response/event field contracts |
| `TestPackageExports` | 1 | Package exports present |

### Provider Tests (`test_provider.py`)

| Test Class | Tests | Coverage |
|------------|-------|----------|
| `TestInitServices` | 2 | `init_services` with/without key |
| `TestGetters` | 6 | Getter before/after init (RuntimeError vs. correct instance) |

### Integration Tests

#### Chat Flow (`test_chat_flow.py` — Most Comprehensive Integration Test)

| Test Class | Tests | Coverage |
|------------|-------|----------|
| `TestChatFlowE2E` | 3 | Full chat stream, with history, error handling (`credit_balance_exhausted`) |
| `TestPromptReachesApi` | 7 | System prompt correctly sent, user message in API, memory in messages, history complete, prefill as last assistant message, RequestConfig, complete pipeline |
| `TestGreetingInHistory` | 3 | Greeting not merged with memory, greeting visible on 2nd turn, no consecutive same roles |

**Key Assertions:**
- System prompt comes exactly from `engine.build_system_prompt()` (no hardcoded appends)
- No consecutive same roles (alternating user/assistant enforced)
- Memory text appears in message content
- Prefill is the last message with `role=assistant`
- `RequestConfig.stream=True`, `request_type='chat'`

#### Afterthought Flow (`test_afterthought_flow.py`)

- `test_decision_then_followup` — "Yes" → Decision True → Followup streams
- `test_decision_no_skips_followup` — "No" → Decision False, no followup

#### Memory Flow (`test_memory_flow.py`)

- `test_preview_then_save` — Preview + save with "Memory from..." prefix
- `test_custom_memory_save` — Custom memory without API call
- `test_save_with_no_messages_fails` — Empty message list → error

### Prompt Engine Tests

#### Core Engine (`test_prompt_engine.py` — ~939 Lines, Largest Test File)

| Test Class | Tests | Coverage |
|------------|-------|----------|
| `TestPlaceholderResolver` | 8 | Simple resolution, unknown stays `{{key}}`, cache, invalidation, runtime overrides |
| `TestPromptLoader` | 8 | Load manifest, load domain file, missing → error, atomic writes |
| `TestPromptValidator` | 7 | Valid manifest, missing fields, invalid category, cross-reference |
| `TestPromptEngine` | 16 | System prompt (default/experimental), variant condition, order, prefill, consent dialog, reload, resolve, get/delete/save |
| `TestMigrator` | 6 | Placeholder conversion, dry run, skip existing |
| `TestArchitecture` | 3 | No Flask/PyWebView imports (AST-level check) |

**Fixture:** `temp_instructions_dir` creates a complete JSON prompt system in `tmp_path`:
- Manifest with 7 prompts
- System placeholder registry with 5 placeholders
- User placeholder registry (optional, for user/system separation)
- Domain files: `chat.json`, `prefill.json`, `consent_dialog.json`, `afterthought.json`

#### Phase 5 Tests (`test_phase5.py`)

| Test Class | Tests | Coverage |
|------------|-------|----------|
| `TestExportPromptSet` | 4 | ZIP creation, content, metadata, `_defaults/` excluded |
| `TestImportPromptSet` | 8 | Replace/merge/overwrite/invalid mode, missing/invalid ZIP, roundtrip |
| `TestFactoryReset` | 3 | Restore files from `_defaults/`, manifest |
| `TestValidateIntegrity` | 4 | All valid, corrupt file recovery, missing file recovery |

### Engine Integration (`test_engine_integration.py`)

| Test Class | Tests | Coverage |
|------------|-------|----------|
| `TestPromptEngineParity` | 14 | Structural validity: system prompt, prefill, afterthought, summary, spec autofill |
| `TestServiceEngineIntegration` | 1 | ChatService engine handoff |
| `TestArchitecturePhase2` | 2 | No Flask/PyWebView imports in prompt_engine/ |

### Service Tests

#### ChatService (`test_chat_service.py`)

| Test Class | Tests |
|------------|-------|
| `TestChatServiceInit` | 1 |
| `TestChatStream` | 2 |
| `TestAfterthoughtDecision` | 3 |
| `TestAfterthoughtFollowup` | 1 |
| `TestGetGreeting` | 1 |

#### MemoryService (`test_memory_service.py`)

| Test Class | Tests |
|------------|-------|
| `TestMemoryServiceInit` | 1 |
| `TestGetFormattedMemories` | 2 |
| `TestCreateSummaryPreview` | 2 |
| `TestSaveSessionMemory` | 2 |
| `TestSaveCustomMemory` | 1 |

---

## Test Patterns

### Mocking Strategy

- **No real API calls**: Anthropic SDK fully mocked
- **No real DB access** in unit tests: DB functions mocked
- **Temporary filesystem** for engine tests: `tmp_path` fixture

### Architecture Enforcement

Tests verify architecture rules via AST analysis and grep:
- `prompt_engine/` has NO Flask or PyWebView imports
- Sub-builders don't import the engine directly
- Facade uses provider module

### Contract Assertions

- Field existence checks (all expected fields present)
- Type checks (correct types for response fields)
- Structural validity (prompt output contains expected markers)

---

## Dev Tools

### `src/dev/prompts/merge_to_defaults.py`

Developer tool for syncing current prompt files to `_defaults/` (factory reset baseline):

```bash
# Preview (dry run)
python -m dev.prompts.merge_to_defaults

# Apply
python -m dev.prompts.merge_to_defaults --apply
```

- Detects NEW, UPDATED, and REMOVED files
- Copies with `shutil.copy2` (preserves metadata)
- Cleans up orphaned files in `_defaults/`

### Batch Files (`bin/`)

| File | Description |
|------|-------------|
| `start.bat` | Start the app |
| `start_prompt_editor.bat` | Start the Prompt Editor |
| `update.bat` | Git pull + update dependencies |
| `reset.bat` | Run factory reset |
| `install_py12.bat` | Python 3.12 installer |
| `prompt_editor.bat` | Start Prompt Editor (alternative) |

---

## Dependencies

```
Test Suite
  ├── pytest (test framework)
  ├── pytest-mock (mocking)
  ├── unittest.mock (MagicMock, patch, PropertyMock)
  ├── conftest.py (15 fixtures)
  │
  │  Tested modules:
  ├── utils/api_request/* (ApiClient, Types, Cleaner)
  ├── utils/provider (Service Locator)
  ├── utils/services/* (ChatService, MemoryService)
  ├── utils/prompt_engine/* (Engine, Loader, Resolver, Validator)
  └── utils/prompt_builder/* (Facade, Sub-Builder)
```
