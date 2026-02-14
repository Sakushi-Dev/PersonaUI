# 13 — Prompt Editor

## Overview

The Prompt Editor is a **standalone PyWebView application** for visually editing all prompt templates. It offers CRUD operations, live preview, placeholder management, validation, and a compositor view.

---

## Architecture

```
bin/start_prompt_editor.bat
  └── src/prompt_editor/editor.py (PyWebView launcher)
        └── EditorApi (Python ↔ JS bridge)
              └── PromptEngine (pure Python library)

JS modules (9 files, inline-bundled):
  utils.js → prompt-list.js → prompt-editor.js → highlight.js
  → placeholder-manager.js → autocomplete.js → preview.js
  → compositor.js → app.js
```

---

## Startup (`editor.py`)

```python
def start_editor():
    sys.path → src/
    os.chdir → src/
    api = EditorApi()
    html = load_editor_html()  # CSS + 9 JS inline-bundled
    webview.create_window("Prompt Editor", html=html, 
                          width=1300, height=850, 
                          min_size=(900, 600),
                          js_api=api)
    webview.start()
```

**PyWebView Bridge:** JavaScript calls Python methods via `window.pywebview.api.*`.

---

## EditorApi (`api.py` — 590 Lines)

### Prompt CRUD (9 Methods)

| Method | Description |
|--------|-------------|
| `get_all_prompts()` | All prompts for sidebar |
| `get_prompt(prompt_id)` | Single prompt with meta + content |
| `save_prompt(prompt_id, data_json)` | Save content + metadata |
| `create_prompt(data_json)` | New prompt (always in user manifest) |
| `duplicate_prompt(prompt_id)` | Duplicate prompt with "_copy" suffix |
| `delete_prompt(prompt_id)` | Only user prompts deletable |
| `toggle_prompt(prompt_id, enabled)` | Enable/disable prompt |
| `reorder_prompts(order_json)` | Update order values |
| `search_prompts(query)` | Search by name, description, category |

### Placeholder Management (6 Methods)

| Method | Description |
|--------|-------------|
| `get_all_placeholders()` | Registry data |
| `get_placeholder_values(variant)` | Resolved values |
| `get_placeholder_usages(placeholder_key)` | Where is this placeholder used? |
| `update_placeholders_used(prompt_id, placeholders)` | Update placeholder list |
| `create_placeholder(key, data)` | Create new placeholder in **user registry** |
| `delete_placeholder(key)` | Only static/custom/user placeholders deletable; routes to correct registry |

### Preview (5 Methods)

| Method | Description |
|--------|-------------|
| `preview_prompt(prompt_id, variant)` | Single prompt with resolved placeholders + token estimate |
| `preview_full_system(variant)` | Complete system prompt + prefill + first assistant + append |
| `preview_category(category, variant)` | All prompts in a category |
| `preview_chat(variant)` | Chat preview: system prompt + message sequence + dialog injections |
| `get_compositor_data(variant)` | Grouping by API request type |

### Compositor

Groups all prompts by API request type:

| Category → Request Type |
|--------------------------|
| system, persona, context, prefill, dialog_injection → `chat` |
| afterthought → `afterthought` |
| summary → `summary` |
| spec_autofill → `spec_autofill` |
| utility → `utility` |

### Utilities (6 Methods)

| Method | Description |
|--------|-------------|
| `validate_all()` | Full validation: errors + warnings |
| `reload()` | Reload engine |
| `get_engine_info()` | Engine status and statistics |
| `get_categories()` | Available categories |
| `get_domain_files()` | All domain files |
| `reset_prompt_to_default(prompt_id)` | Per-prompt factory reset |

---

## Editor UI Structure

### Sidebar

- **Search field**: Filter by name/description/category
- **Prompt list**: Scrollable, color-coded by category
- **Action buttons**: New prompt, validate, full preview, compositor, placeholder manager, reload

### Editor Area

**Metadata Panel:**
| Field | Description |
|-------|-------------|
| ID | Unique prompt identifier |
| Name | Human-readable name |
| Category | system, persona, context, prefill, dialog_injection, afterthought, summary, spec_autofill, utility, custom |
| Description | Short description |
| Target | system_prompt, message, prefill |
| Position | system_prompt, system_prompt_append, first_assistant, consent_dialog, user_message, prefill, history |
| Order | Sort order (numeric) |
| Domain File | JSON file |
| Enabled | On/off toggle |

**Variant Tabs:** Default and Experimental with separate content

**Content Editor:**
- `<textarea>` for text prompts
- Multi-turn editor for dialog injections (role + content)

**Placeholder Panel:** Available placeholders with insert button

**Live Preview:** Resolved prompt with token estimate

### Action Buttons

| Button | Description |
|--------|-------------|
| Restore Default | Reset to factory default |
| Duplicate | Duplicate prompt |
| Delete | Delete (user prompts only) |
| Discard | Discard changes |
| Save | Save |

---

## Keyboard Shortcuts

Documented on the welcome screen:
- Standard editor shortcuts for navigation and editing

---

## HTML Bundling

The editor uses the same inlining pattern as the splash screen:

```python
def load_editor_html():
    html = read('editor.html')
    css = read('editor.css')
    js = [read(f) for f in js_files]  # 9 files in dependency order
    html = html.replace('{{EDITOR_CSS}}', css)
    html = html.replace('{{EDITOR_JS}}', '\n'.join(js))
    return html
```

Everything is embedded into a single HTML string for PyWebView (avoids `file://` issues).

---

## Token Estimation

```python
estimated_tokens = len(text) // 4
```

Rough character-to-token estimate, displayed in the preview.

---

## Dependencies

```
Prompt Editor
  ├── PyWebView (desktop window)
  ├── EditorApi (bridge layer)
  │     └── PromptEngine (full access)
  │           ├── PromptLoader (JSON I/O)
  │           ├── PlaceholderResolver
  │           └── PromptValidator
  │
  ├── editor.css (styling)
  └── 9 JS modules (UI logic)

Independent from:
  ├── Flask (no web server needed)
  ├── Anthropic API (no API calls)
  └── Database (no DB access)
```

---

## Design Decisions

1. **Standalone app**: Separate window, independent from main chat
2. **No Flask**: Direct PyWebView access to PromptEngine
3. **System vs user**: System prompts can only be disabled, not deleted
4. **Atomic writes**: Temp file + `os.replace()` for safe write operations
5. **Inline bundling**: All assets embedded in HTML for PyWebView compatibility
6. **Compositor view**: Shows how prompts combine in different API requests
