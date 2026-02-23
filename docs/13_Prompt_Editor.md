# 13 — Prompt Editor

> Standalone PyWebView application for viewing, editing, and managing prompt templates.

---

## Overview

The Prompt Editor is a **separate tool** for power users who want to customize the AI prompt templates directly. It runs as its own PyWebView window, independent of the main app.

**Launch:** `bin/prompt_editor.bat` or `python src/prompt_editor/editor.py`

```
src/prompt_editor/
├── __init__.py
├── editor.py          Main editor application (~590 lines)
├── api.py             EditorApi class (26 methods)
├── static/            Inline JS/CSS assets
└── templates/         HTML templates
```

---

## Architecture

```
PyWebView Window
    │
    ├── HTML/JS Frontend (inline-bundled)
    │     ├── Prompt list sidebar
    │     ├── Editor panel (text + metadata)
    │     ├── Placeholder browser
    │     ├── Preview panel
    │     └── Export/Import controls
    │
    └── EditorApi (Python ↔ JS bridge via pywebview)
          └── PromptEngine (reads/writes JSON prompt files)
```

The editor communicates with Python via PyWebView's JS-Python bridge — JavaScript calls `pywebview.api.method_name()` which executes Python methods in the `EditorApi` class.

---

## EditorApi Methods

**File:** `src/prompt_editor/api.py` (~26 methods)

### Prompt CRUD

| Method | Description |
|--------|-------------|
| `get_all_prompts()` | List all prompts with metadata |
| `get_prompt(prompt_id)` | Get a single prompt's full data |
| `update_prompt(prompt_id, variant, text)` | Update prompt text |
| `reset_prompt(prompt_id)` | Reset to factory default |
| `create_prompt(data)` | Create a new custom prompt |
| `delete_prompt(prompt_id)` | Delete a user-created prompt |

### Placeholder Management

| Method | Description |
|--------|-------------|
| `get_placeholders()` | List all registered placeholders |
| `get_placeholder(key)` | Get placeholder details (type, source) |
| `create_placeholder(data)` | Register a new placeholder |
| `delete_placeholder(key)` | Remove a user placeholder |

### Preview & Validation

| Method | Description |
|--------|-------------|
| `preview_prompt(prompt_id, variant)` | Resolve and preview a prompt with current data |
| `validate_prompt(text)` | Check for syntax errors in prompt text |
| `get_available_variants()` | List available variants (default, experimental) |

### Export & Import

| Method | Description |
|--------|-------------|
| `export_prompts()` | Export all prompts as ZIP file |
| `import_prompts(path)` | Import prompts from ZIP file |
| `factory_reset()` | Reset all prompts to system defaults |

### Compositor

| Method | Description |
|--------|-------------|
| `get_prompt_sequence(variant)` | Get the ordered prompt sequence |
| `preview_full_system_prompt(variant)` | Preview the assembled system prompt |

---

## Editor Features

### Prompt List

The sidebar shows all prompt templates organized by category:
- **Core:** system_rule, persona_description, output_format
- **Behavior:** emotional_state, conversation_dynamics, topic_boundaries
- **Style:** response_style_control, expression_style_detail
- **Memory:** conversation_history, cortex_context, remember
- **Afterthought:** afterthought_followup, afterthought_inner_dialogue
- etc.

Each prompt shows its enabled/disabled status per variant.

### Text Editor

The main editing area with:
- Raw text editing with `{{placeholder}}` syntax highlighting
- Variant tabs (default / experimental)
- Enable/disable toggle per variant
- Metadata display (category, order, description)

### Placeholder Browser

Lists all available `{{placeholder}}` variables with:
- Name and type (static / computed / runtime)
- Source (persona_config, user_profile, computed function)
- Current resolved value (live preview)
- Click-to-insert into the editor

### Full System Prompt Preview

The compositor view shows the **complete assembled system prompt** — all enabled prompts resolved and concatenated in order. This is exactly what gets sent to the API.

---

## Relationship to PromptEngine

The editor is a **UI layer over the PromptEngine**. All changes go through the engine's API:

```
Editor UI → EditorApi → PromptEngine
                          ├── Read/write JSON domain files
                          ├── Update manifests
                          └── Resolve placeholders
```

Changes made in the editor take effect immediately in chat (no restart needed) since the PromptEngine is shared.

---

## HTML Inlining

The editor uses **inline-bundled HTML** — all CSS and JavaScript are embedded directly in the HTML template. This is a requirement for PyWebView, which works best with self-contained HTML documents.

---

## Related Documentation

- [06 — Prompt Engine](06_Prompt_Engine.md) — The underlying engine the editor wraps
- [09 — Persona & Instructions](09_Persona_and_Instructions.md) — Persona data that fills placeholders
- [14 — Onboarding, Splash & Reset](14_Onboarding_Splash_and_Reset.md) — Other PyWebView standalone tools
