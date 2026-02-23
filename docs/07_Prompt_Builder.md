# 07 — Prompt Builder

> Legacy prompt builder with PromptEngine delegation — a bridge for backward compatibility.

---

## Overview

The Prompt Builder is the **original** prompt construction system. It has been largely superseded by the PromptEngine (see [06 — Prompt Engine](06_Prompt_Engine.md)) but remains as a fallback bridge.

**File:** `src/utils/prompt_builder/chat.py` (~368 lines)

```
src/utils/prompt_builder/
└── chat.py    ChatPromptBuilder class
```

---

## Dual-Path Pattern

The builder implements a **delegation pattern**: it tries the PromptEngine first, falls back to legacy `.txt` files if the engine is unavailable.

```
ChatPromptBuilder
    │
    ├── Has engine? → PromptEngine.resolve_prompt(...)
    │                  PromptEngine.build_system_prompt(...)
    │
    └── No engine? → Load .txt files from instructions/system/main/
                     Manual placeholder replacement
```

### Engine Injection

```python
builder = ChatPromptBuilder()
builder.set_engine(prompt_engine)  # Enables PromptEngine delegation
```

Once `set_engine()` is called, all prompt resolution goes through the engine. The legacy `.txt` fallback is only used if the engine is `None` or fails.

---

## Legacy File Structure

The builder originally loaded prompts from plain text files:

```
src/instructions/system/main/
├── impersonation.txt
├── system_rule.txt
├── char_description.txt
├── sub_system_reminder.txt
├── prefill_impersonation.txt
└── prefill_system_rules.txt
```

These files are no longer the primary source — the JSON domain files in `src/instructions/prompts/` have replaced them. The builder's fallback hardcodes minimal defaults if even the `.txt` files are missing:

```python
def _get_master_prompt_fallback(self):
    return {
        'impersonation': '',
        'system_rule': 'You are {char_name}. Respond in {language}.',
        'char_description': '{char_description}',
        'sub_system_reminder': '',
        'prefill_impersonation': '',
        'prefill_system_rules': 'I respond as {char_name}:'
    }
```

---

## Key Methods

### `build_system_prompt(character, user_name, persona_language, ...)`

Builds the complete system prompt string:

1. **Engine path:** Delegates to `engine.build_system_prompt()` with variant and runtime vars
2. **Legacy path:** Concatenates `.txt` file contents with manual `{placeholder}` replacement

### `build_core_prompt(character)`

Builds just the persona description section. Used when only the character context is needed (e.g., title generation).

### `_load_consent_dialog()`

Loads experimental-mode consent dialog injections. These are user/assistant message pairs injected into the conversation to prime the AI for extended behavior.

---

## Relationship to ChatService

The `ChatService` primarily uses the PromptEngine directly. The Prompt Builder is available as an alternative path:

```
ChatService
    ├── self._engine (PromptEngine)     ← Primary path
    └── ChatPromptBuilder                ← Available but rarely used
```

In practice, the PromptEngine handles all prompt resolution for active features. The builder remains for:
- **Backward compatibility** — Code that references the builder doesn't break
- **Graceful degradation** — If the PromptEngine fails to load, basic prompts still work
- **Testing** — Some tests use the builder's simpler interface

---

## Related Documentation

- [06 — Prompt Engine](06_Prompt_Engine.md) — The primary prompt system
- [05 — Chat System](05_Chat_System.md) — How prompts are used in chat
- [11 — Services Layer](11_Services_Layer.md) — ChatService that consumes prompts
