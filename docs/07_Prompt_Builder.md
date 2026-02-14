# 07 — Prompt Builder (Legacy Bridge)

## Overview

The **Prompt Builder** is the legacy bridge between the old `.txt`-based prompt system and the new JSON-based `PromptEngine`. It follows a dual-path pattern: first it attempts to delegate to the engine; on failure it falls back to legacy files.

---

## Architecture

```
Routes/Services
  └── ChatPromptBuilder (Facade)
        ├── Has Engine? → PromptEngine.build_system_prompt()
        └── No Engine? → _load_master_prompt() → .txt files
```

---

## `src/utils/prompt_builder/chat.py` — ChatPromptBuilder

**383 lines.** Inherits from `PromptBase` (base class).

### Methods

| Method | Description |
|--------|-------------|
| `set_engine(engine)` | Injects the PromptEngine instance |
| `build_system_prompt(character_data, ...)` | Main entry point: engine delegation or legacy assembly |
| `build_core_prompt(char_name, language, ...)` | Builds core components: impersonation, system_rule, user_info, time_sense, output_format |
| `build_persona_prompt(character_data, ...)` | Persona description from template (default vs experimental) |
| `build_prefill(char_name, ...)` | Prefill: engine or legacy `.txt` |
| `get_prefill_impersonation(char_name, ...)` | Engine → `resolve_prompt('prefill_impersonation')` or legacy |
| `get_consent_dialog()` | Loads `consent_dialog.json` |
| `get_dialog_injections(variant, ...)` | Engine → `get_dialog_injections()` or legacy consent dialog |
| `get_greeting(character_data)` | Greeting message or None |

### Dual-Path Pattern

```python
def build_system_prompt(self, character_data, ...):
    if self._engine:
        # New path: PromptEngine
        variant = 'experimental' if experimental_mode else 'default'
        runtime_vars = {'language': language, ...}
        return self._engine.build_system_prompt(variant, runtime_vars)
    else:
        # Legacy path: .txt files
        parts = self.build_core_prompt(...)
        parts += self.build_persona_prompt(...)
        return "\n\n".join(parts)
```

---

## Legacy Prompt System

In legacy mode, `.txt` files are loaded from `instructions/system/main/`:
- `_load_master_prompt(prompt_dir)` — Loads all `.txt` files from a directory
- Placeholder syntax: `{char_name}` (single brace, instead of `{{char_name}}`)
- `str.format()` for placeholder replacement

---

## Variant Mapping

```python
variant = 'experimental' if experimental_mode else 'default'
```

The `experimental_mode` boolean is set in the frontend and sent along with all chat/afterthought requests.

---

## Dependencies

```
ChatPromptBuilder
  ├── PromptBase (base class)
  ├── config.get_config_path
  ├── time_context.get_time_context
  ├── PromptEngine (optional, via set_engine())
  │
  │  Consumers:
  ├── ChatService (via provider.get_prompt_engine())
  └── MemoryService (via provider.get_prompt_engine())
```

---

## Design Decisions

1. **Graceful degradation**: Engine errors produce empty/safe return values, never crashes
2. **No direct engine imports**: Sub-builders receive the engine via `set_engine()`, not via import
3. **Facade via provider**: The facade imports the engine through the `provider` module
4. **Architecture separation**: `prompt_engine/` has NO Flask/PyWebView imports (pure library)
5. **Backward compatibility**: Legacy `.txt` system remains as a fallback
