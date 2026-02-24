# 09 — Persona & Instructions

> Persona specification, configuration, CRUD lifecycle, custom specs, and AI-powered autofill.

---

## Overview

A "persona" in PersonaUI is a fully configurable AI character. Each persona has a name, personality type, traits, knowledge areas, expression styles, scenarios, and a background story. The persona system is what makes PersonaUI different from a basic chatbot — characters feel distinct and consistent.

---

## Persona Specification Schema

The persona spec defines what attributes a persona can have. Stored in `src/instructions/personas/spec/persona_spec.json`:

### Persona Types (6 built-in)

The core personality archetype:

| Type | Description |
|------|-------------|
| Companion | Friendly, supportive companion |
| Mentor | Wise advisor and teacher |
| Entertainer | Playful and humorous |
| Professional | Focused and task-oriented |
| Creative | Artistic and imaginative |
| Mysterious | Enigmatic and intriguing |

### Core Traits (12 built-in)

Personality characteristics (multiple selectable):

Empathetic, Analytical, Humorous, Serious, Adventurous, Cautious, Creative, Practical, Introverted, Extroverted, Optimistic, Philosophical

### Knowledge Areas (14 built-in)

What the persona knows about:

Science, Technology, History, Art, Music, Literature, Gaming, Sports, Cooking, Travel, Psychology, Philosophy, Nature, Pop Culture

### Expression Styles (3 built-in)

How the persona communicates:

| Style | Description |
|-------|-------------|
| Casual | Relaxed, conversational tone |
| Formal | Professional, structured responses |
| Poetic | Lyrical, metaphorical language |

### Scenarios (6 built-in)

Situations the persona is good at handling. These inform how the persona adapts its responses to different contexts.

---

## Persona Configuration

**File:** `src/utils/config.py` (~802 lines)

The config module is the backbone of persona management:

### Active Persona

```
src/instructions/personas/active/persona_config.json
```

This file always contains the currently active persona's configuration. When a user switches personas, this file is overwritten.

### Default Persona

```
src/instructions/personas/default/default_persona.json
```

Factory default that can be restored.

### Created Personas

```
src/instructions/created_personas/
├── my_friend_luna.json
├── wise_mentor_kai.json
└── ...
```

User-created personas are stored as individual JSON files.

### Configuration Structure

```json
{
    "char_name": "Luna",
    "char_age": "25",
    "char_gender": "female",
    "persona": "Companion",
    "char_background": "A curious and empathetic AI companion who loves exploring ideas...",
    "core_traits": ["Empathetic", "Creative", "Humorous"],
    "knowledge_areas": ["Psychology", "Art", "Music"],
    "expression_style": "Casual",
    "scenarios": ["Emotional Support", "Creative Brainstorming"],
    "avatar": "luna_avatar.jpg",
    "start_msg_enabled": true,
    "start_msg_text": "Hey! What's on your mind today?"
}
```

---

## Key Config Functions

```python
from utils.config import (
    load_character,          # Load active persona config
    save_character,          # Save persona config changes
    get_active_persona_id,   # Get current persona ID
    activate_persona,        # Switch active persona
    get_available_options,   # Get persona spec (types, traits, etc.)
    get_config_path,         # Resolve relative path to src/
)
```

### `load_character(persona_id=None)`

Returns the persona config as a dict. If `persona_id` is None, loads the active persona.

### `save_character(data, persona_id=None)`

Merges the provided data into the existing config and saves. Handles avatar changes and file management.

### `activate_persona(persona_id)`

1. Saves the current active persona back to its file
2. Loads the target persona from `created_personas/`
3. Writes it to `active/persona_config.json`
4. Initializes the persona's database if needed
5. Initializes Cortex memory files

---

## Persona CRUD Lifecycle

### Create

```
POST /api/personas
    → Validate name uniqueness
    → Generate persona ID from name
    → Save to created_personas/{id}.json
    → Create persona database
    → Initialize Cortex files
    → Return new persona
```

### Read

```
GET /api/personas          → List all personas
GET /api/personas/active   → Get active persona ID
GET /get_char_config       → Get active persona config
```

### Update

```
PUT /api/personas/<id>     → Update persona fields (name immutable)
POST /save_char_config     → Save active persona config
```

### Delete

```
DELETE /api/personas/<id>
    → Cannot delete "default" persona
    → If deleting active persona, switch to default first
    → Delete persona JSON file
    → Delete persona database
    → Delete Cortex files
```

### Activate

```
POST /api/personas/<id>/activate
    → Save current persona back
    → Load target persona
    → Write to active/persona_config.json
    → Init DB + Cortex for target
```

---

## Custom Specs

Users can extend the persona specification with custom entries:

**File:** `src/instructions/personas/spec/custom_spec/`

```
custom_spec/
├── persona_types.json     Custom persona types
├── core_traits.json       Custom traits
├── knowledge_areas.json   Custom knowledge areas
├── expression_styles.json Custom expression styles
└── scenarios.json         Custom scenarios
```

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/custom-specs` | Get all custom specs |
| POST | `/api/custom-specs/<category>` | Add new spec entry |
| DELETE | `/api/custom-specs/<category>/<key>` | Remove spec entry |
| POST | `/api/custom-specs/autofill` | AI-generate a spec value |

Custom specs are merged with built-in specs in the UI, giving users unlimited persona configuration options.

---

## AI-Powered Autofill

PersonaUI can use Claude to auto-generate persona content:

### Background Autofill

`POST /api/personas/background-autofill` generates a complete background story based on the persona's current settings (name, type, traits, etc.).

Uses the `background_autofill` prompt template:
```
Given this character: {{char_name}}, a {{persona_type}} with traits {{char_core_traits}}...
Generate a detailed background story.
```

### Spec Autofill

`POST /api/custom-specs/autofill` generates content for individual spec fields:

- `spec_autofill_traits` — Generate trait descriptions
- `spec_autofill_knowledge` — Generate knowledge area details
- `spec_autofill_expression` — Generate expression style descriptions
- `spec_autofill_scenarios` — Generate scenario descriptions
- `spec_autofill_type` — Generate persona type descriptions

Each uses a dedicated prompt template with the current persona context.

---

## File Structure Summary

```
src/instructions/
├── personas/
│   ├── active/
│   │   └── persona_config.json      Currently active persona
│   ├── default/
│   │   └── default_persona.json     Factory default
│   ├── spec/
│   │   ├── persona_spec.json        Built-in spec schema
│   │   └── custom_spec/             User-added spec entries
│   └── cortex/                      Cortex memory files (see doc 10)
│       ├── default/
│       └── custom/
├── created_personas/                 User-created persona files
└── prompts/                          Prompt templates (see doc 06)
```

---

## Related Documentation

- [02 — Configuration & Settings](02_Configuration_and_Settings.md) — Settings that affect personas
- [06 — Prompt Engine](06_Prompt_Engine.md) — Placeholders filled from persona config
- [08 — Database Layer](08_Database_Layer.md) — Per-persona databases
- [10 — Cortex Memory System](10_Cortex_Memory_System.md) — Per-persona long-term memory
- [12 — Frontend React SPA](12_Frontend_React_SPA.md) — Persona UI overlays
