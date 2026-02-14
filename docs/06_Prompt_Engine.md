# 06 — Prompt Engine

## Overview

The **PromptEngine** is the central prompt management system of PersonaUI. It is a pure Python library (no Flask/PyWebView dependencies) with **~1163 lines** in the core module. It manages JSON-based prompt templates with a three-phase placeholder resolution system.

---

## Architecture

```
src/utils/prompt_engine/
  ├── __init__.py              ← Re-exports PromptEngine
  ├── engine.py (~1163 lines)  ← Core orchestrator
  ├── loader.py (~191 lines)   ← JSON I/O layer
  ├── placeholder_resolver.py  ← {{var}} resolution
  ├── validator.py (232 lines) ← Schema validation
  ├── memory_context.py        ← Memory formatting
  ├── migrator.py              ← Legacy .txt → JSON migration
  └── manifest_migrator.py     ← Single → Dual manifest migration
```

---

## File Structures

### Domain Files (`instructions/prompts/*.json`)

Each JSON file contains a prompt entry:

```json
{
  "impersonation": {
    "variants": {
      "default": {
        "content": "Du bist {{char_name}}, {{char_description}}..."
      },
      "experimental": {
        "content": "Alternative Version..."
      }
    },
    "placeholders_used": ["char_name", "char_description"]
  }
}
```

**36 domain files** available, including:
- Chat: `impersonation`, `system_rule`, `persona_description`, `output_format`, ...
- Afterthought: `afterthought_inner_dialogue`, `afterthought_followup`, `afterthought_system_note`
- Summary: `summary_impersonation`, `summary_system_rule`, `summary_user_prompt`, ...
- Spec-Autofill: `spec_autofill_persona_type`, `_core_trait`, `_knowledge`, `_scenario`, `_expression_style`
- Utility: `title_generation`, `background_autofill`

### Manifest (`_meta/prompt_manifest.json`)

```json
{
  "version": "2.0",
  "prompts": {
    "impersonation": {
      "name": "Impersonation",
      "description": "Core identity instruction",
      "category": "system",
      "type": "text",
      "target": "system_prompt",
      "position": "system_prompt",
      "order": 100,
      "enabled": true,
      "domain_file": "impersonation.json",
      "tags": ["core"],
      "variant_condition": null
    }
  }
}
```

### Dual Manifest System

| Manifest | Description |
|----------|-------------|
| `prompt_manifest.json` | System manifest (Git-versioned) |
| `user_manifest.json` | User manifest (gitignored) |

On ID collision, the user manifest wins. Each entry receives an `_origin` field (`system`/`user`).

### Dual Registry System

| Registry | File | Description |
|----------|------|-------------|
| `placeholder_registry.json` | System registry (Git-tracked) | Contains all system placeholders |
| `user_placeholder_registry.json` | User registry (gitignored) | User-defined placeholders, absent on first start |

On key collision, the **user registry** wins (user customization takes priority). Each entry in the merged view receives an `_origin` field for provenance tracking.

#### Example: System Registry (`_meta/placeholder_registry.json`)

```json
{
  "version": "2.0",
  "placeholders": {
    "char_name": {
      "name": "Character Name",
      "source": "persona_config",
      "source_path": "persona_settings.name",
      "type": "string",
      "resolve_phase": "static",
      "category": "persona"
    },
    "char_description": {
      "name": "Character Description",
      "source": "computed",
      "compute_function": "build_character_description",
      "resolve_phase": "computed",
      "category": "persona"
    }
  }
}
```

#### User Registry (`_meta/user_placeholder_registry.json`)

```json
{
  "version": "2.0",
  "placeholders": {
    "custom_greeting": {
      "name": "Custom Greeting",
      "source": "static",
      "type": "string",
      "resolve_phase": "static",
      "category": "custom",
      "default": "Hallo!"
    }
  }
}
```

---

## Three-Phase Placeholder Resolution

### Phase 1: Static (Cached)

Reads from `persona_config.json` and `user_profile.json` via dot-path navigation:
- `persona_settings.name` → `"Mia"`
- `user_name` → `"Saiks"`

Lists are joined with `join_separator`. **Cache is invalidated on persona switch.**

### Phase 2: Computed (Fresh on Every Call)

Calls registered Python functions:

| Compute Function | Result |
|------------------|--------|
| `build_character_description` | Complete persona description |
| `build_persona_type_description` | Persona type label |
| `build_char_core_traits` | Core traits with descriptions + behaviors |
| `build_char_knowledge` | Knowledge areas with descriptions |
| `build_char_expression` | Communication style details |
| `build_char_scenarios` | Scenario settings |
| `get_time_context.current_date` | Date (DD.MM.YYYY) |
| `get_time_context.current_time` | Time (HH:MM) |
| `get_time_context.current_weekday` | Weekday (German) |

### Phase 3: Runtime (Passed by Caller)

Injected by the calling code:
- `elapsed_time` — Elapsed time (afterthought)
- `inner_dialogue` — Inner dialogue (afterthought follow-up)
- `memory_entries` — Memory entries
- `input` — User input (spec-autofill)
- `chat_text` — Chat text (summary)
- `language` — Language
- `history` — Conversation history

**Unknown placeholders** remain as `{{key}}` — no crash, no removal.

---

## PromptEngine Class — Method Overview

### Loading and Cache Management

| Method | Description |
|--------|-------------|
| `_load_all()` | Master loading sequence: migration → manifests → system registry → user registry → merge → domains → resolver → validation |
| `reload()` | Invalidate cache + re-run `_load_all()` |
| `invalidate_cache()` | Clear only the PlaceholderResolver cache |

### Prompt Access

| Method | Description |
|--------|-------------|
| `get_all_prompts()` | All manifest entries (for editor sidebar) |
| `get_prompt(id)` | Single prompt: `{id, meta, content}` |
| `get_prompts_by_target(target)` | Enabled prompts for a target, sorted by `order` |
| `get_prompts_by_category(category)` | All prompts of a category |

### Prompt Building

| Method | Return | Description |
|--------|--------|-------------|
| `build_system_prompt(variant)` | `str` | All `target=system_prompt` prompts, excluding `system_prompt_append`, excluding summary/spec_autofill |
| `get_system_prompt_append(variant)` | `str` | Only `position=system_prompt_append` prompts |
| `build_prefill(variant, category_filter)` | `str` | All `target=prefill` prompts; excludes `summary`/`spec_autofill` categories by default; `category_filter` allows targeted access |
| `get_first_assistant_content(variant)` | `str` | All `position=first_assistant` prompts |
| `get_chat_message_sequence(variant)` | `List[Dict]` | Ordered sequence: `first_assistant` → `history` → `prefill` |
| `get_dialog_injections(variant)` | `List[Dict]` | Multi-turn dialog injections |
| `resolve_prompt(id, variant)` | `str` | Resolve a single prompt |

### Specialized Builders

| Method | Description |
|--------|-------------|
| `build_summary_prompt(variant)` | `{system_prompt, prefill}` for memory summaries |
| `build_afterthought_inner_dialogue(variant)` | Inner dialogue prompt |
| `build_afterthought_followup(variant)` | Follow-up prompt |
| `build_spec_autofill_prompt(type, input)` | Spec autofill with `{{input}}` |

### Mutation (for Editor)

| Method | Description |
|--------|-------------|
| `save_prompt(id, data)` | Content to domain file, metadata to the correct manifest |
| `create_prompt(data)` | Always created in the user manifest |
| `delete_prompt(id)` | Only user prompts can be deleted; system prompts can only be disabled |
| `reorder_prompts(order)` | Update order values |
| `toggle_prompt(id, enabled)` | Enable/disable a prompt |
| `create_placeholder(key, data)` | Create a new static placeholder in the **user registry** |
| `delete_placeholder(key)` | Delete a placeholder (only static/custom/user); automatically routes to the correct registry |

### Export/Import/Reset

| Method | Description |
|--------|-------------|
| `export_prompt_set(path)` | ZIP with manifests + registries + domain files + metadata |
| `import_prompt_set(zip, mode)` | Import modes: `replace`, `merge`, `overwrite` |
| `factory_reset(scope)` | Restore from `_defaults/`: `system` (keeps user prompts) or `full` |
| `reset_prompt_to_default(id)` | Per-prompt factory reset |
| `validate_integrity()` | Startup check: validates JSON, recovers from `_defaults/` |

---

## Validation

The `PromptValidator` checks:

| Check | Level | Description |
|-------|-------|-------------|
| Manifest fields | Error | Required fields: name, type, target, position, order, enabled, domain_file |
| Enum values | Error | category, type, target, position from allowed sets |
| Order type | Error | Must be numeric |
| Cross-references | Error | Each `domain_file` in the manifest must exist as a loaded domain |
| Domain content | Error | Text prompts need `content`, multi-turn needs `messages` |
| Placeholder declaration | Warning | `{{key}}` in content should be listed in `placeholders_used` |
| Placeholder registry | Warning | `{{key}}` in content should exist in the registry |

### Valid Enum Values

| Field | Values |
|-------|--------|
| `category` | system, persona, context, prefill, dialog_injection, afterthought, summary, spec_autofill, utility, custom |
| `type` | text, multi_turn |
| `target` | system_prompt, message, prefill |
| `position` | system_prompt, first_assistant, consent_dialog, user_message, prefill, system_prompt_append, history |

---

## Memory Context Formatting

`format_memories_for_prompt(memories, max_memories=30, engine=None)`:

1. Truncate to `max_memories`
2. Clean content
3. If engine is available: `engine.resolve_prompt('memory_context', ...)` with `{{memory_entries}}`
4. Fallback: Hardcoded `**MEMORY CONTEXT** ... **END OF MEMORY CONTEXT**` format

---

## Migration System

### `PromptMigrator` — Legacy .txt → JSON

Converts old `.txt`-based prompts to JSON domain files:
- `{key}` → `{{key}}` for known placeholders
- Backup creation
- Parity check (whitespace-normalized comparison)

### `ManifestMigrator` — Single → Dual Manifest

One-time migration: Compares active manifest with factory default. IDs not found in the default are classified as user prompts and moved to `user_manifest.json`.

---

## Internal Registry Management

### Merge Strategy (`_merge_registries()`)

1. Load system placeholders as base
2. Overlay user placeholders on top
3. On key collision: **user wins** (with log warning)
4. `_user_placeholder_keys` set is rebuilt (for write routing)

### Write Routing

| Operation | Target |
|-----------|--------|
| `create_placeholder()` | Always → user registry |
| `delete_placeholder()` | Checks via `_is_user_placeholder(key)` → user or system registry |
| Reload after mutation | Merged view is recalculated |

### Internal State Attributes

| Attribute | Description |
|-----------|-------------|
| `_system_registry` | System registry (Git-tracked) |
| `_user_registry` | User registry (gitignored) |
| `_registry` | Merged view (system + user) |
| `_user_placeholder_keys` | Set of keys belonging to the user registry |

### PlaceholderResolver Integration

The `PlaceholderResolver` receives the **merged registry dict** directly upon creation (instead of a file path as before). The internal `_load_registry()` method in the resolver is marked as **DEPRECATED** (legacy support).

---

## Thread Safety

The entire `PromptEngine` is **thread-safe** via `threading.RLock`:
- All read and write operations are locked
- RLock allows re-entrance (important for nested calls)
- Atomic JSON write operations via temp file + `os.replace()`

---

## Dependencies

```
PromptEngine
  ├── PromptLoader         ← JSON I/O (atomic writes, system + user registry)
  ├── PlaceholderResolver  ← {{var}} resolution (receives merged registry dict)
  │     ├── config.build_character_description
  │     ├── config.load_char_config / load_char_profile
  │     └── time_context.get_time_context
  ├── PromptValidator      ← Schema validation
  ├── ManifestMigrator     ← One-time migration
  └── logger.log

Consumers:
  ├── ChatService          ← System prompt, prefill, sequence
  ├── MemoryService        ← Summary prompt
  ├── ChatPromptBuilder    ← Legacy bridge
  └── EditorApi            ← Prompt editor UI
```
