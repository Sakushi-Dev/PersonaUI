# 06 — Prompt Engine

> JSON-based prompt template system with dual manifests, placeholder resolution, and domain organization.

---

## Overview

The PromptEngine is the central system for managing all AI prompt text. Instead of hardcoding prompt strings in Python code, all prompts are stored as **JSON template files** with `{{placeholder}}` variables that are resolved at runtime.

**File:** `src/utils/prompt_engine/engine.py` (~1482 lines)

```
src/utils/prompt_engine/
├── engine.py              Main PromptEngine class
├── loader.py              JSON file loading
├── placeholder_resolver.py Three-phase placeholder resolution
├── validator.py           Prompt validation
├── manifest_migrator.py   Manifest migration between versions
└── __init__.py            Package exports
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     PromptEngine                        │
│                                                         │
│  ┌─────────────┐   ┌───────────────┐   ┌─────────────┐  │
│  │   Loader    │   │   Resolver    │   │  Validator  │  │
│  │  (JSON I/O) │   │ (Placeholders)│   │  (Schema)   │  │
│  └──────┬──────┘   └──────┬────────┘   └──────┬──────┘  │
│         │                 │                    │        │
│  ┌──────▼─────────────────▼────────────────────▼─────┐  │
│  │              Internal Data Stores                 │  │
│  │  _system_manifest  _user_manifest  _domains       │  │
│  │  _system_registry  _user_registry  _resolver      │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## Dual Manifest System

The engine uses **two manifests** to separate system defaults from user customizations:

### System Manifest — `_meta/prompt_manifest.json`

Defines all available prompts, their metadata, and default text:

```json
{
    "version": "2.0",
    "prompts": {
        "system_rule": {
            "domain": "system_rule",
            "label": "System Rules",
            "description": "Core behavior rules for the persona",
            "category": "core",
            "order": 100,
            "variants": {
                "default": { "enabled": true },
                "experimental": { "enabled": true }
            }
        },
        "persona_description": { ... },
        "output_format": { ... }
    }
}
```

### User Manifest — `_meta/user_manifest.json`

Contains only user overrides. Missing entries fall back to the system manifest:

```json
{
    "version": "2.0",
    "prompts": {
        "system_rule": {
            "variants": {
                "default": { "enabled": false }
            }
        }
    }
}
```

This dual system means users can customize prompts without affecting the original defaults. Factory reset simply deletes the user manifest.

---

## Domain Files — Prompt Templates

Each prompt is stored in a **domain JSON file** in `src/instructions/prompts/`:

```json
// src/instructions/prompts/system_rule.json
{
    "id": "system_rule",
    "label": "System Rules",
    "description": "Core behavior rules",
    "variants": {
        "default": {
            "text": "You are {{char_name}}, a {{persona_type}}. You must always stay in character...",
            "enabled": true
        },
        "experimental": {
            "text": "You are {{char_name}}, a {{persona_type}}. Extended rules for experimental mode...",
            "enabled": true
        }
    }
}
```

### Domain File Catalog (32 files)

| Category | Domains |
|----------|---------|
| **Core** | `system_rule`, `persona_description`, `output_format`, `impersonation` |
| **Memory** | `conversation_history`, `cortex_context`, `remember` |
| **Behavior** | `emotional_state`, `conversation_dynamics`, `topic_boundaries`, `topic_transition_guard` |
| **Style** | `response_style_control`, `expression_style_detail` |
| **Continuity** | `relationship_tracking`, `continuity_guard`, `persona_integrity_shield`, `world_consistency` |
| **Afterthought** | `afterthought_followup`, `afterthought_inner_dialogue`, `afterthought_system_note` |
| **Cortex** | `cortex_update_system`, `cortex_update_tools`, `cortex_update_user_message` |
| **Autofill** | `background_autofill`, `spec_autofill_traits`, `spec_autofill_knowledge`, `spec_autofill_expression`, `spec_autofill_scenarios`, `spec_autofill_type` |
| **Utility** | `time_sense`, `title_generation`, `user_info` |

Each domain file also has a copy in `_defaults/` for factory reset recovery.

---

## Placeholder Resolution

**File:** `src/utils/prompt_engine/placeholder_resolver.py` (~404 lines)

Placeholders use the `{{key}}` syntax and are resolved in **three phases**:

### Phase 1: Static (Cached)

Loaded once from persona config and user profile:

| Placeholder | Source | Example |
|-------------|--------|---------|
| `{{char_name}}` | persona config | "Luna" |
| `{{persona_type}}` | persona config | "Companion" |
| `{{char_age}}` | persona config | "25" |
| `{{char_gender}}` | persona config | "female" |
| `{{char_background}}` | persona config | "A curious AI..." |
| `{{user_name}}` | user profile | "Alex" |
| `{{language}}` | user profile | "english" |

### Phase 2: Computed (Dynamic)

Calculated at resolve time via registered functions:

| Placeholder | Compute Function | Description |
|-------------|-----------------|-------------|
| `{{char_description}}` | `build_character_description()` | Full character description |
| `{{persona_type_description}}` | `build_persona_type_description()` | Persona type explanation |
| `{{char_core_traits}}` | `build_char_core_traits()` | Formatted trait list |
| `{{char_knowledge}}` | `build_char_knowledge()` | Knowledge areas |
| `{{char_expression}}` | `build_char_expression()` | Expression styles |
| `{{char_scenarios}}` | `build_char_scenarios()` | Scenario descriptions |
| `{{current_date}}` | `get_time_context()` | "23. Februar 2026" |
| `{{current_time}}` | `get_time_context()` | "14:30" |
| `{{current_weekday}}` | `get_time_context()` | "Montag" |
| `{{cortex_persona_context}}` | `build_cortex_persona_context()` | Cortex memory summary |

### Phase 3: Runtime (Caller-Provided)

Passed directly by the calling code:

| Placeholder | Provider | Used In |
|-------------|----------|---------|
| `{{elapsed_time}}` | `afterthought()` route | Afterthought prompts |
| `{{inner_dialogue}}` | `afterthought()` route | Followup prompts |
| `{{conversation_context}}` | `chat_stream()` route | History summary |

Unknown placeholders remain as `{{key}}` (no error raised).

---

## Dual Placeholder Registry

Similar to manifests, placeholders have system and user registries:

- **`_meta/placeholder_registry.json`** — System-defined placeholders with types, sources, descriptions
- **`_meta/user_placeholder_registry.json`** — User-added placeholders

```json
{
    "placeholders": {
        "char_name": {
            "type": "static",
            "source": "persona_config",
            "key": "char_name",
            "description": "Character name"
        },
        "current_date": {
            "type": "computed",
            "function": "get_time_context.current_date",
            "description": "Current date"
        }
    }
}
```

---

## Key Engine Methods

```python
engine = get_prompt_engine()

# Resolve a single prompt
text = engine.resolve_prompt('system_rule', variant='default')

# Build the complete system prompt (all enabled prompts in order)
system_prompt = engine.build_system_prompt(variant='default', runtime_vars={...})

# Get the chat message sequence
sequence = engine.get_chat_message_sequence(variant='default')

# Get dialog injections (experimental mode)
injections = engine.get_dialog_injections(variant='experimental')

# CRUD operations
engine.update_prompt('system_rule', variant='default', text='new text...')
engine.reset_prompt_to_default('system_rule')

# Export/Import
engine.export_prompts('/path/to/export.zip')
engine.import_prompts('/path/to/export.zip')

# Factory reset
engine.factory_reset()  # Restores all prompts from _defaults/
```

---

## Thread Safety

The PromptEngine uses a `threading.RLock` for all read/write operations. This is critical because:
- Multiple chat requests can resolve prompts simultaneously
- The Prompt Editor can modify prompts while chats are active
- Cortex updates may trigger prompt changes

---

## Manifest Migration

**File:** `src/utils/prompt_engine/manifest_migrator.py`

When the prompt system is updated (new prompts, schema changes), the migrator handles the transition:

1. Checks if `user_manifest.json` exists
2. If the system manifest version is newer, merges new prompts into the user manifest
3. Preserves all user customizations
4. Creates backup before migration

---

## Related Documentation

- [05 — Chat System](05_Chat_System.md) — How prompts are used in chat
- [07 — Prompt Builder](07_Prompt_Builder.md) — Legacy builder with engine delegation
- [09 — Persona & Instructions](09_Persona_and_Instructions.md) — Persona data that fills placeholders
- [13 — Prompt Editor](13_Prompt_Editor.md) — UI for editing prompts
