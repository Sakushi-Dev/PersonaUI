# 15 — Tests & Quality

> Test architecture, fixtures, coverage areas, and development tools.

---

## Overview

PersonaUI uses **pytest** with ~162 tests across ~10 test files. Tests run without any real API calls or database connections — everything is mocked.

```
tests/
├── conftest.py                 Shared fixtures (15+)
├── test_api_client.py          ApiClient tests
├── test_provider.py            Provider pattern tests
├── test_integration/           Integration tests
├── test_prompt_builder/        Prompt builder tests
├── test_prompt_engine/         Prompt engine tests
└── test_services/              ChatService tests
```

### Configuration

**File:** `pytest.ini`

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short --ignore=src
```

### Running Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/test_api_client.py

# Specific test
pytest tests/test_api_client.py::TestApiClient::test_stream_request

# With coverage (if pytest-cov installed)
pytest --cov=src
```

---

## Fixtures — `conftest.py`

**File:** `tests/conftest.py` (~195 lines)

Shared fixtures provide consistent test data and mocked dependencies:

### Test Data Fixtures

| Fixture | Provides |
|---------|----------|
| `test_character_data` | Standard persona dict ("TestPersona", companion, with traits/knowledge) |
| `minimal_character_data` | Minimal persona dict ("Mini", basic fields only) |
| `sample_conversation` | 4-message user/assistant conversation |
| `empty_conversation` | Empty list `[]` |

### Mock Fixtures

| Fixture | Mocks |
|---------|-------|
| `mock_anthropic` | Patches `anthropic` module, returns `MagicMock` response |
| `mock_anthropic_stream` | Patches `anthropic` for streaming (yields test chunks) |
| `mock_prompt_engine` | Mocked `PromptEngine` with `resolve_prompt()`, `build_system_prompt()` |
| `mock_api_client` | Mocked `ApiClient` with `is_ready=True` |
| `mock_chat_service` | Mocked `ChatService` |

### Environment Fixtures

| Fixture | Purpose |
|---------|---------|
| `clean_env` | Ensures `ANTHROPIC_API_KEY` is unset between tests |
| `temp_dir` | Provides a temporary directory for file operations |

---

## Test Coverage Areas

### ApiClient Tests — `test_api_client.py`

| Test Area | What's Tested |
|-----------|--------------|
| Initialization | Constructor with/without API key, env var fallback |
| `is_ready` | True when client exists, false when not |
| `update_api_key()` | Hot-swap API key, invalid key handling |
| `request()` | Sync request success/failure, error types |
| `stream()` | Streaming request, chunk events, done event, error handling |
| Credit balance | Special handling for `credit_balance_exhausted` error |
| Model resolution | Default model fallback, explicit model override |

### Provider Tests — `test_provider.py`

| Test Area | What's Tested |
|-----------|--------------|
| Set/get services | ApiClient, ChatService, CortexService registration |
| Lazy init | PromptEngine created on first `get_prompt_engine()` call |
| Singleton behavior | Same instance returned on repeated calls |
| Module functions | `get_api_client()`, `get_chat_service()` delegates |

### ChatService Tests — `test_services/`

| Test Area | What's Tested |
|-----------|--------------|
| Message building | `_build_chat_messages()` with various inputs |
| System prompt | Prompt assembly via PromptEngine |
| Streaming | Event yielding, error propagation |
| Afterthought | Decision parsing (yes/no), inner dialogue extraction |
| Settings reading | `_read_setting()` with fallback chain |
| Cortex loading | `_load_cortex_context()` with enabled/disabled states |

### Prompt Engine Tests — `test_prompt_engine/`

| Test Area | What's Tested |
|-----------|--------------|
| Loading | Manifest loading, domain file parsing, error isolation |
| Resolution | Placeholder resolution (static, computed, runtime) |
| Variants | Default vs experimental variant text |
| CRUD | Create/update/delete prompts, manifest updates |
| Export/Import | ZIP export, import with validation |
| Factory reset | Reset to `_defaults/` |
| Thread safety | Concurrent access to shared engine |

### Prompt Builder Tests — `test_prompt_builder/`

| Test Area | What's Tested |
|-----------|--------------|
| Engine delegation | Builder with engine vs without |
| Fallback | `.txt` file loading, hardcoded fallback |
| System prompt | `build_system_prompt()` output |
| Placeholder replacement | `{char_name}`, `{language}` substitution |

### Integration Tests — `test_integration/`

| Test Area | What's Tested |
|-----------|--------------|
| Full chat flow | Message → system prompt → API request → response |
| Persona switching | Active persona change, DB routing |
| Settings cascade | Defaults → user overrides → env vars |

---

## Testing Principles

### No Real API Calls

All Anthropic API interactions are mocked. Tests verify that the correct parameters are passed to the SDK, not that the SDK works.

### No Real Database

Database tests use temporary SQLite databases or mock the database functions entirely.

### Architecture Enforcement

Some tests use AST (Abstract Syntax Tree) analysis to enforce architectural rules:
- Verify that services don't import each other directly
- Check that routes use the standard response format
- Ensure no hardcoded prompt strings in route files

### Isolated Fixtures

Each test gets fresh fixtures. No test depends on another test's state.

---

## Development Tools

### `src/dev/`

Development-only utilities:

| Tool | Purpose |
|------|---------|
| `dev/prompts/` | Prompt development/testing tools |
| `dev/frontend/` | Frontend development utilities |

### `merge_to_defaults.py`

A development script used when adding new settings:
1. Reads the current `user_settings.json`
2. Merges new keys into `defaults.json`
3. Ensures both files stay in sync

---

## Related Documentation

- [11 — Services Layer](11_Services_Layer.md) — Services being tested
- [06 — Prompt Engine](06_Prompt_Engine.md) — Engine tests
- [08 — Database Layer](08_Database_Layer.md) — Database mocking
