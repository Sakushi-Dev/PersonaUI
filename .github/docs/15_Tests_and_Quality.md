# 15 — Tests & Quality

> Test architecture, fixtures, coverage areas, and development tools.

---

## Overview

PersonaUI uses **pytest** with **356 tests** across **16 test files** (~4,700 lines of test code). Tests run without any real API calls or database connections — everything is mocked. The frontend uses **ESLint** with React-specific plugins.

```
src/tests/
├── conftest.py                              Shared fixtures (11)
├── test_api_client.py                       ApiClient & data types (23 tests)
├── test_provider.py                         Provider pattern (6 tests)
├── test_integration/
│   ├── test_afterthought_flow.py            E2E afterthought (2 tests)
│   ├── test_chat_flow.py                    E2E chat flow (12 tests)
│   └── test_step06_api_integration.py       Startup, migration, wiring (32 tests)
├── test_prompt_engine/
│   ├── test_prompt_engine.py                Core engine (59 tests)
│   ├── test_phase5.py                       Export/Import/Reset (19 tests)
│   └── test_step04_cortex_prompts.py        Cortex prompts & placeholders (47 tests)
└── test_services/
    ├── test_chat_service.py                 ChatService (9 tests)
    ├── test_cortex_service.py               CortexService core (28 tests)
    ├── test_cortex_service_robustness.py    Atomic writes, cache, hardening (16 tests)
    ├── test_cortex_tiers.py                 Tier tracker & checker (25 tests)
    ├── test_cortex_update_service.py        Cortex update API (21 tests)
    └── test_tool_request.py                 tool_use loop (18 tests)
```

### Configuration

**File:** `pytest.ini`

```ini
[pytest]
testpaths = src/tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
```

### Running Tests

```bash
# All tests
pytest

# Specific test file
pytest src/tests/test_api_client.py

# Specific test class
pytest src/tests/test_api_client.py::TestApiClientStream

# Specific test
pytest src/tests/test_api_client.py::TestApiClientStream::test_stream_yields_events

# With coverage (if pytest-cov installed)
pytest --cov=src

# Skip known failures
pytest -k "not test_externalized_template"
```

---

## Fixtures — `conftest.py`

**File:** `src/tests/conftest.py` (~160 lines)

Shared fixtures provide consistent test data and mocked dependencies:

### Test Data Fixtures

| Fixture | Provides |
|---------|----------|
| `test_character_data` | Standard persona dict ("TestPersona", companion, with traits/knowledge) |
| `minimal_character_data` | Minimal persona dict ("Mini", only empty/basic fields) |
| `sample_conversation` | 4-message user/assistant conversation |
| `empty_conversation` | Empty list `[]` |

### Mock Fixtures

| Fixture | Mocks |
|---------|-------|
| `mock_anthropic` | Patches `utils.api_request.client.anthropic`, returns mock response (100 input / 50 output tokens) |
| `mock_anthropic_stream` | Patches anthropic for streaming — yields 2 `content_block_delta` events + `message_stop` |
| `api_client` | Real `ApiClient` instance initialized with `mock_anthropic` |
| `api_client_stream` | Real `ApiClient` instance with stream mock |
| `mock_api_client` | Completely mocked `ApiClient` with `is_ready=True`, `.request()` returning `ApiResponse` |
| `mock_engine` | Mocked `PromptEngine` — stubs `build_system_prompt`, `build_prefill`, `get_dialog_injections`, `get_chat_message_sequence`, etc. |
| `chat_service` | `ChatService` with mocked api_client + engine (bypasses `__init__`) |

---

## Test Coverage Areas

### ApiClient Tests — `test_api_client.py` (23 tests, ~207 lines)

| Class | Tests | What's Tested |
|-------|-------|--------------|
| `TestRequestConfig` | 2 | `RequestConfig` dataclass defaults and custom values |
| `TestApiResponse` | 3 | `ApiResponse` success/error/defaults |
| `TestStreamEvent` | 3 | `StreamEvent` chunk/done/error types |
| `TestResponseCleaner` | 5 | `clean_api_response()` — passthrough, empty, None, code blocks, HTML |
| `TestApiClientInit` | 3 | Constructor with/without key, `update_api_key()` hot-swap |
| `TestApiClientRequest` | 3 | Sync request, prefill, message building |
| `TestApiClientStream` | 1 | Streaming event generation |
| `TestApiClientContract` | 2 | Return value contracts for ApiResponse and StreamEvent |
| `TestPackageExports` | 1 | Package `__init__.py` exports all public names |

### Provider Tests — `test_provider.py` (6 tests, ~47 lines)

| Class | Tests | What's Tested |
|-------|-------|--------------|
| `TestInitServices` | 2 | `init_services()` creates ApiClient + ChatService, handles missing key |
| `TestGetters` | 4 | Getter functions work after init, raise `RuntimeError` before init |

### ChatService Tests — `test_chat_service.py` (9 tests, ~146 lines)

| Class | Tests | What's Tested |
|-------|-------|--------------|
| `TestChatServiceInit` | 1 | Constructor stores api_client |
| `TestChatStream` | 2 | `chat_stream()` yields `(event_type, data)` tuples; done event has stats |
| `TestAfterthoughtDecision` | 3 | Parses `[afterthought_OK]` → True, `[i_can_wait]` → False |
| `TestAfterthoughtFollowup` | 1 | `afterthought_followup()` yields stream events |
| `TestGenerateSessionTitle` | 2 | Title generation with fallback "Neue Konversation" |

### CortexService Tests — `test_cortex_service.py` (28 tests, ~228 lines)

| Class | Tests | What's Tested |
|-------|-------|--------------|
| `TestGetCortexDir` | 4 | Path routing for default, empty, None, custom persona IDs |
| `TestEnsureCortexDir` | 4 | Directory creation with template files, no overwrite of existing |
| `TestCreateCortexDir` | 2 | `create_cortex_dir()` success and default |
| `TestDeleteCortexDir` | 3 | Custom deletion, default guard, nonexistent returns false |
| `TestCortexServicePathResolution` | 2 | Instance method path resolution |
| `TestCortexServiceReadFile` | 3 | File reading, invalid filename raises, `read_all()` returns 3 keys |
| `TestCortexServiceWriteFile` | 2 | Write + roundtrip, invalid filename raises |
| `TestCortexServicePromptIntegration` | 2 | `get_cortex_for_prompt()` keys and section headers |
| `TestCortexServiceFilenameValidation` | 2 | Whitelist enforcement (7 parametrized bad filenames) |
| `TestCortexServiceToolCallHandler` | 4 | `_handle_tool_call()` for read/write/invalid tool/invalid filename |
| `TestCortexServiceFormatHistory` | 1 | `_format_history_for_update()` |
| `TestCortexServiceExecuteUpdate` | 2 | Error paths: API not ready, no history |

### CortexService Robustness — `test_cortex_service_robustness.py` (16 tests, ~267 lines)

| Class | Tests | What's Tested |
|-------|-------|--------------|
| `TestAtomicWrites` | 4 | Atomic writes via `tempfile` + `os.replace`, no leftover tmp files |
| `TestFileSizeLimit` | 4 | `MAX_CORTEX_FILE_SIZE` = 8000 enforcement, truncation, exact boundary |
| `TestCortexCache` | 5 | In-memory cache: populate, hit, write-through, delete invalidation, lock |
| `TestThreadTracking` | 2 | Active-updates dict exists, no `threading.enumerate()` usage (source scan) |
| `TestPromptInjectionHardening` | 3 | Anti-injection rules in templates (reads JSON + Python source) |
| `TestSSEDoneEventMatching` | 2 | **Cross-stack**: reads `routes/chat.py` + `useMessages.js` to verify field consistency |

### Cortex Tier System — `test_cortex_tiers.py` (25 tests, ~257 lines)

| Class | Tests | What's Tested |
|-------|-------|--------------|
| `TestCycleBase` | 6 | CRUD, isolation between sessions/personas, disk persistence + reload |
| `TestResetSession` | 3 | Session reset, noop for nonexistent, isolation |
| `TestResetAll` | 1 | Full state clear |
| `TestRebuildCycleBase` | 3 | Cycle base recalculation, exact multiples, threshold-zero fallback |
| `TestGetProgress` | 4 | Progress percentage: basic, after-reset, at-threshold, capped at 100% |
| `TestCalculateThreshold` | 6 | Threshold computation for frequent/medium/rare at different context limits |
| `TestCheckAndTrigger` | 7 | Full trigger integration: disabled, no messages, below/at threshold, second cycle, frequent |

Uses `autouse` fixture to reset module-level state and redirect state file to `tmp_path`.

### Cortex Update Service — `test_cortex_update_service.py` (21 tests, ~275 lines)

| Class | Tests | What's Tested |
|-------|-------|--------------|
| `TestToolDefinitions` | 3 | CORTEX_TOOLS structure (2 tools: read_file, write_file) |
| `TestRateLimit` | 3 | Rate limiting per persona (30s cooldown) |
| `TestToolExecutor` | 5 | `_execute_tool()`: read, write, unknown tool, ValueError, no duplicate tracking |
| `TestSystemPromptBuilder` | 6 | Fallback system prompt: persona name, user name, file descriptions, identity, date |
| `TestMessageBuilder` | 3 | Message formatting for cortex update calls |
| `TestExecuteUpdate` | 5 | Full flow: success, no API key, too few messages, rate limit, API failure |
| `TestConstants` | 3 | Config constants: max_tokens=8192, temperature=0.4, rate_limit=30s |

### Tool Request Tests — `test_tool_request.py` (18 tests, ~367 lines)

| Class | Tests | What's Tested |
|-------|-------|--------------|
| `TestToolRequestSingleRound` | 2 | end_turn without tools, single tool round |
| `TestToolRequestMultiRound` | 2 | Read→write multi-round, multiple tools in single round |
| `TestToolRequestErrors` | 7 | No API key, no tools, empty tools, executor exception/failure, API error, credit exhaustion |
| `TestToolRequestMaxRounds` | 1 | MAX_TOOL_ROUNDS safety limit |
| `TestToolRequestUsage` | 1 | Token usage accumulation across rounds |
| `TestExtractTextFromContent` | 4 | `_extract_text_from_content()`: empty, text-only, mixed, tool-blocks-only |
| `TestToolRequestMessageBuilding` | 1 | assistant + tool_result message structure |

### Prompt Engine Tests — `test_prompt_engine.py` (59 tests, ~937 lines)

**Largest test file.** Uses an elaborate `temp_instructions_dir` fixture (~180 lines) that creates a full in-memory prompt engine directory with manifest, registry, domain files, and persona config.

| Class | Tests | What's Tested |
|-------|-------|--------------|
| `TestPlaceholderResolver` | 8 | PlaceholderResolver: 3-phase resolution, caching, invalidation, runtime overrides |
| `TestPromptLoader` | 10 | Manifest loading, domain files, atomic writes, missing file errors |
| `TestPromptValidator` | 9 | Schema validation, cross-reference, domain validation, placeholder warnings |
| `TestPromptEngine` | 21 | Full engine API: system prompt, prefill, variants, consent dialog, reload, CRUD, cache |
| `TestMigrator` | 8 | Placeholder migration `{x}` → `{{x}}`, parity checks, dry run |
| `TestArchitecture` | 3 | **AST-based import checking** — verifies zero flask/webview imports in prompt_engine/ |

### Phase 5 — Export, Import, Reset — `test_phase5.py` (19 tests, ~365 lines)

| Class | Tests | What's Tested |
|-------|-------|--------------|
| `TestExportPromptSet` | 4 | ZIP export: creation, contents, metadata, excludes defaults |
| `TestImportPromptSet` | 8 | 3 merge modes (replace/merge/overwrite), error paths, roundtrip |
| `TestFactoryReset` | 3 | Restore from `_defaults/`, manifest restore, missing defaults handling |
| `TestValidateIntegrity` | 4 | Corruption detection, auto-recovery from defaults, unrecoverable corruption |

### Cortex Prompts — `test_step04_cortex_prompts.py` (47 tests, ~528 lines)

| Class | Tests | What's Tested |
|-------|-------|--------------|
| `TestShouldIncludeBlock` | 7 | `_should_include_block()` — conditional inclusion based on `requires_any` |
| `TestCleanResolvedText` | 6 | `_clean_resolved_text()` — whitespace normalization |
| `TestNonChatCategories` | 2 | NON_CHAT_CATEGORIES filtering (cortex excluded from chat prompts) |
| `TestResolvePromptById` | 2 | `resolve_prompt_by_id()` valid + unknown |
| `TestGetDomainData` | 3 | Tool descriptions structure |
| `TestValidatorCortex` | 4 | Validator extensions for cortex category |
| `TestCortexServiceSectionHeaders` | 5 | Section header wrapping for memory/soul/relationship |
| `TestLoadCortexContext` | 3 | Setting gate: disabled returns empty, enabled loads data |
| `TestCortexUpdateServiceEngine` | 6 | PromptEngine integration with fallback for tools, messages, system prompt |
| `TestCortexPersonaContextCompute` | 3 | `_compute_cortex_persona_context()` building + empty fields |
| `TestRegistryAndManifestIntegrity` | 6 | **File-based integrity checks** on actual config JSON files |

### Integration Tests — `test_integration/`

#### Afterthought Flow — `test_afterthought_flow.py` (2 tests, ~69 lines)

| Class | Tests | What's Tested |
|-------|-------|--------------|
| `TestAfterthoughtFlowE2E` | 2 | Full decision → followup pipeline; skip on `[i_can_wait]` |

#### Chat Flow — `test_chat_flow.py` (12 tests, ~322 lines)

| Class | Tests | What's Tested |
|-------|-------|--------------|
| `TestChatFlowE2E` | 3 | Full streaming chat, history handling, error events |
| `TestPromptReachesApi` | 6 | System prompt, user message, history, prefill, config all arrive in RequestConfig |
| `TestAutoFirstMessageInHistory` | 3 | Auto-first-message as standalone assistant message, role sequence validation |

#### API Integration — `test_step06_api_integration.py` (32 tests, ~403 lines)

| Class | Tests | What's Tested |
|-------|-------|--------------|
| `TestEnsureCortexDirs` | 4 | Startup `ensure_cortex_dirs()`: default, custom, idempotent, missing dir |
| `TestSettingsMigration` | 6 | `memoriesEnabled` → `cortexEnabled` migration (6 edge cases) |
| `TestEnsureCortexSettings` | 4 | `cortex_settings.json` creation, preservation, additions, corruption |
| `TestMigrateSettings` | 1 | Combined migration flow |
| `TestCortexUpdateEndpoint` | 4 | Cortex update config check, disabled returns error, import verification |
| `TestChatRouteImports` | 3 | **Source code scanning** of `chat.py` for cortex imports |
| `TestStartupIntegration` | 5 | **Source/JSON reading** for startup wiring (app.py, defaults.json) |
| `TestFrontendCortexCommand` | 2 | **Cross-stack**: reads `builtinCommands.js` + `commands.py` for `/cortex` |
| `TestProviderAndRoutes` | 3 | **Source scanning** for correct imports, no legacy memory imports |

### Prompt Builder — `test_engine_integration.py` (15 tests, ~138 lines)

| Class | Tests | What's Tested |
|-------|-------|--------------|
| `TestPromptEngineParity` | 12 | Structural parity: all engine outputs non-empty (system prompt, prefill, afterthought, spec types) |
| `TestServiceEngineIntegration` | 1 | ChatService uses engine directly |
| `TestArchitecturePhase2` | 2 | **Source scanning with glob** — zero flask/webview imports in prompt_engine/ |

---

## Test Distribution

| Category | Files | Tests |
|----------|-------|-------|
| API Client & Data Types | 1 | 23 |
| Provider | 1 | 6 |
| Chat Service | 1 | 9 |
| Cortex System | 5 | 111 |
| Tool Request | 1 | 18 |
| Prompt Engine | 3 | 125 |
| Prompt Builder | 1 | 15 |
| Integration (E2E) | 3 | 46 |
| **Total** | **16** | **356** |

---

## Testing Patterns

### No Real API Calls

All Anthropic API interactions are mocked. Tests verify that the correct parameters are passed to the SDK, not that the SDK works.

### No Real Database

Database functions are mocked entirely. Temp directories are used for file-based tests.

### AST-Based Architecture Enforcement

Tests use Python's `ast` module to parse source files and enforce architectural rules:
- Verify that `prompt_engine/` has zero Flask or PyWebView imports
- Ensure no hardcoded prompt strings leak into route files
- Check module existence against expected structure

### Cross-Stack Contract Verification

Some tests read both Python backend and JavaScript frontend source files to verify consistency:
- SSE event field names match between `routes/chat.py` and `useMessages.js`
- Slash command names match between `builtinCommands.js` and `commands.py`
- Cortex field names sent by backend match what frontend expects

### Source Code Scanning

Integration tests read `.py` source files to verify wiring:
- `chat.py` imports cortex tier checker
- `app.py` calls `ensure_cortex_dirs()` and `migrate_settings()`
- `defaults.json` contains required keys

### Module-Level State Reset

Tests that touch module-level globals (e.g. `tier_tracker.py`) use `autouse` fixtures to reset state between tests and redirect file paths to `tmp_path`.

### Isolated Fixtures

Each test gets fresh fixtures. No test depends on another test's state. The prompt engine tests use an elaborate ~180-line temp fixture that creates a full in-memory prompt directory.

---

## Frontend Quality — ESLint

**File:** `frontend/eslint.config.js`

The React frontend uses ESLint flat config with:
- `@eslint/js` recommended rules
- `eslint-plugin-react-hooks` — enforces React hooks rules
- `eslint-plugin-react-refresh` — Vite HMR compatibility
- Custom rule: `no-unused-vars` ignores uppercase/underscore-prefixed variables

```bash
cd frontend
npx eslint .
```

---

## Development Tools

### `src/dev/`

Development-only utilities not used in production:

| Tool | Purpose |
|------|---------|
| `dev/prompts/merge_to_defaults.py` | Copies current prompt files to `_defaults/` as new factory defaults |
| `dev/frontend/build_frontend.bat` | Standalone frontend build script (finds Node.js, runs npm build) |

### `merge_to_defaults.py`

Copies all current prompt files (including `_meta/`) from `src/instructions/prompts/` to `src/instructions/prompts/_defaults/`. This sets the current state as the new factory default for resets.

```bash
# Preview (dry-run)
python src/dev/prompts/merge_to_defaults.py

# Apply
python src/dev/prompts/merge_to_defaults.py --apply
```

### `build_frontend.bat`

A standalone Windows batch script that:
1. Locates the project root directory
2. Finds Node.js (project-local or system)
3. Runs `npm install` + `npm run build`

Useful for rebuilding the frontend outside the normal startup flow.

---

## Related Documentation

- [11 — Services Layer](11_Services_Layer.md) — Services being tested
- [06 — Prompt Engine](06_Prompt_Engine.md) — Engine tests
- [08 — Database Layer](08_Database_Layer.md) — Database mocking
- [10 — Cortex Memory System](10_Cortex_Memory_System.md) — Cortex tier system and update service
