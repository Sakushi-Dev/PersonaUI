# 09 — Persona & Instructions System

## Overview

The persona system enables the creation and management of **AI personas** with configurable personality traits, knowledge areas, expression styles, and scenarios. Each persona gets its own SQLite database for complete isolation.

---

## Architecture

```
instructions/
  ├── personas/
  │     ├── spec/
  │     │     ├── persona_spec.json         ← Master specification (all options)
  │     │     └── custom_spec/
  │     │           └── custom_spec.json    ← User extensions
  │     ├── default/
  │     │     └── default_persona.json      ← Factory default "Mia"
  │     └── active/
  │           └── persona_config.json       ← Currently active persona
  ├── created_personas/
  │     └── {uuid}.json                    ← User-created personas
  └── prompts/
        └── (36 domain files)              ← Prompt templates
```

---

## Persona Specification (`persona_spec.json`)

Master schema with all available options for persona creation:

### Persona Types (6)

| Type | Description |
|------|-------------|
| Transcendent | Born as human, consciousness transferred to AI |
| Human | Human from Earth |
| Elf | Elven being |
| Robot | Robot/android |
| Alien | Extraterrestrial being |
| Demon | Demonic/dark beings |

### Core Traits (12)

| Trait | Description | Behaviors |
|-------|-------------|-----------|
| friendly | Warm-hearted and helpful | 3 behaviors |
| shy | Reserved and introverted | 3 behaviors |
| suspicious | Cautious and skeptical | 3 behaviors |
| intelligent | Analytical and inquisitive | 3 behaviors |
| playful | Light-hearted and humorous | 3 behaviors |
| confident | Assured and determined | 3 behaviors |
| curious | Inquisitive and explorative | 3 behaviors |
| creative | Imaginative and innovative | 3 behaviors |
| empathetic | Compassionate and understanding | 3 behaviors |
| loyal | Faithful and dependable | 3 behaviors |
| protective | Caring and watchful | 3 behaviors |
| spontaneous | Impulsive and lively | 3 behaviors |

Each trait has: `description` + `behaviors[]` (exactly 3 entries)

### Knowledge Areas (14)

Cooking, Movies, Sports, Music, Art, Technology, Science, Gaming, Literature, Travel, Fashion, General Knowledge, History, Conversations

### Expression Styles (3)

| Style | Description | Example |
|-------|-------------|---------|
| normal | Standard communication | Regular text |
| nonverbal | Asterisk actions | `*smiles* Hello!` |
| messenger | Emojis and messenger style | `Hey! 😊` |

Each style has: `name`, `description`, `example`, `characteristics[]`

### Scenarios (6)

| Scenario | Description | Setting |
|----------|-------------|---------|
| Fantasy | Fantasy world | 4 setting elements |
| Adventure | Adventure setting | 4 setting elements |
| Medieval | Medieval world | 4 setting elements |
| Long-distance | Long-distance relationship | 4 setting elements |
| Sci-Fi | Science fiction | 4 setting elements |
| Everyday | Everyday situations | 4 setting elements |

Scenarios are **only available for non-AI personas** (e.g. not for Transcendent without scenario context).

---

## Custom Specs (`custom_spec.json`)

User-created extensions in the same structure:

```json
{
  "persona_spec": {
    "persona_type": { "custom_key": "Description" },
    "core_traits_details": { "custom_trait": { "description": "...", "behaviors": [...] } },
    "knowledge_areas": { "custom_area": "Description" },
    "expression_styles": { "custom_style": { "name": "...", "description": "...", ... } },
    "scenarios": { "custom_scenario": { "name": "...", "description": "...", "setting": [...] } }
  }
}
```

Custom specs are highlighted in the UI with a blue badge.

### Custom Spec CRUD (Routes)

| Endpoint | Description |
|----------|-------------|
| `GET /api/custom-specs` | All custom specs |
| `POST /api/custom-specs/{category}` | Add new entry |
| `DELETE /api/custom-specs/{category}/{key}` | Delete entry |
| `POST /api/custom-specs/autofill` | AI-generated fields |

AI autofill uses the PromptEngine (`build_spec_autofill_prompt`) with the cost-efficient `apiAutofillModel`.

---

## Persona Configuration

### Default Persona (`default_persona.json`)

```json
{
  "persona_settings": {
    "name": "Mia",
    "age": 24,
    "gender": "weiblich",
    "persona": "Transzendent",
    "core_traits": ["freundlich", "intelligent", "empathisch"],
    "knowledge": ["Allgemeinwissen", "Technologie", "Wissenschaft", "Literatur", "Gespräche"],
    "expression": "normal",
    "scenarios": [],
    "background": "...",
    "start_msg_enabled": true,
    "start_msg": "Hey! Na, was geht bei dir so?",
    "avatar": "59a993875c33.jpeg",
    "avatar_type": "standard"
  }
}
```

### Active Persona (`persona_config.json`)

Same structure as default, plus `active_persona_id` field. This file is read by the PromptEngine for `{{char_name}}` and other placeholders.

---

## Persona Management (`src/utils/config.py` — 766 Lines)

### CRUD Functions

| Function | Description |
|----------|-------------|
| `load_char_config()` | Load active persona settings |
| `save_char_config(data)` | Save persona settings, preserve `active_persona_id` |
| `get_active_persona_id()` | Get active persona ID |
| `set_active_persona_id(id)` | Set active persona ID |
| `ensure_active_persona_config()` | Auto-create `persona_config.json` from defaults |
| `load_default_persona()` | Load factory default |
| `list_created_personas()` | All personas (default + created), marks which is active |
| `save_created_persona(data)` | New persona JSON + SQLite DB, returns 8-char UUID |
| `update_created_persona(id, data)` | Update existing persona (name remains immutable) |
| `delete_created_persona(id)` | Delete persona JSON + DB file |
| `load_persona_by_id(id)` | Load specific persona |
| `activate_persona(id)` | Copy persona config to active, invalidate prompt cache |
| `restore_default_persona()` | Restore factory default |

### Character Description Builder

`build_character_description()` assembles a rich text description:

1. **Identity**: Name, age, gender, persona type + description
2. **Core**: Personality traits with descriptions and behaviors
3. **Knowledge**: Knowledge areas with descriptions
4. **Communication style**: Expression name, description, characteristics
5. **Scenarios**: Only for non-AI personas
6. **Background**: Free-text background story
7. **Greeting**: Optional start message

**Return dict:**
```python
{
    "char_name": str,
    "identity": str,
    "core": str,
    "behavior": str,
    "comms": str,
    "voice": str,
    "greeting": str|None,
    "start_msg_enabled": bool,
    "background": str,
    "desc": str  # Full description
}
```

---

## Persona Lifecycle

```
Creation:
  UI (Persona Creator) → POST /api/personas
    → save_created_persona(data)
      → Generate UUID (8 characters)
      → Save JSON file in created_personas/
      → create_persona_db(uuid) → Create SQLite DB
      → Return persona ID

Editing:
  UI (Persona Editor) → PUT /api/personas/{id}
    → update_created_persona(id, data)
      → Load and update JSON file
      → Name remains immutable
      → If active: reload config

Activation:
  UI → POST /api/personas/{id}/activate
    → activate_persona(id)
      → Copy persona config to active/persona_config.json
      → Set active_persona_id
      → Invalidate PromptEngine cache
      → All subsequent requests use new persona

Deletion:
  UI → DELETE /api/personas/{id}
    → delete_created_persona(id)
      → Delete JSON file
      → Delete SQLite DB (persona_{id}.db)
      → Activate default persona if active one was deleted
```

---

## AI-Generated Background Story

`POST /api/personas/background-autofill`:

1. Build reference text from persona fields
2. PromptEngine: use `resolve_prompt('background_autofill', ...)`
3. Fallback: Hardcoded German prompt
4. API call with `apiAutofillModel` (cost-efficient), max 400 tokens
5. Return generated background story

---

## Dependencies

```
config.py (Persona management)
  ├── database (create_persona_db, delete_persona_db)
  ├── logger
  ├── provider.get_prompt_engine (lazy import, avoid circular dep)
  ├── persona_spec.json (available options)
  ├── custom_spec.json (user extensions)
  │
  │  Consumers:
  ├── Routes: character, main, chat
  ├── PlaceholderResolver (reads persona_config.json)
  ├── ChatService (loads character data)
  └── MemoryService
```

---

## Design Decisions

1. **Per-persona DB isolation**: Each persona gets its own SQLite DB for clean separation
2. **8-char UUID**: Short enough for UI, long enough for uniqueness
3. **Spec-based system**: Structured options instead of free text for consistent persona creation
4. **Custom spec extensions**: Users can extend the spec system with their own options
5. **Prompt cache invalidation**: Persona switch explicitly invalidates the PromptEngine cache
6. **`_configs_match()` deep compare**: Prevents unnecessary reactivation when nothing changed
