# 10 — Cortex Memory System

> File-based long-term memory using Markdown files and Claude's tool_use API.

---

## Overview

Cortex is PersonaUI's **long-term memory system**. It gives personas the ability to remember facts, reflect on their personality, and track their relationship with the user — across sessions, without relying on conversation history alone.

Instead of vector databases or embeddings, Cortex uses **three Markdown files** per persona that Claude can read and write via the `tool_use` API.

---

## Architecture

```
Cortex Memory System
│
├── CortexService (src/utils/cortex_service.py, ~719 lines)
│   ├── File I/O (read/write memory.md, soul.md, relationship.md)
│   ├── Prompt formatting (inject cortex into system prompt)
│   └── Update orchestration (tool_use API calls)
│
├── Cortex Subsystem (src/utils/cortex/)
│   ├── tier_checker.py    Update frequency logic
│   ├── tier_tracker.py    Cycle counter persistence
│   └── update_service.py  Update execution
│
└── Cortex Routes (src/routes/cortex.py)
    └── REST API for file viewing/editing
```

---

## The Three Memory Files

Each persona has three Cortex files stored as Markdown:

```
src/instructions/personas/cortex/
├── default/
│   ├── memory.md         Factual memories
│   ├── soul.md           Persona self-reflection
│   └── relationship.md   User relationship tracking
└── custom/
    └── {persona_id}/
        ├── memory.md
        ├── soul.md
        └── relationship.md
```

### `memory.md` — Facts & Events

Stores factual information the persona has learned about the user and their conversations:

```markdown
# Memory

## Key Facts
- User works as a software developer
- User has a cat named Pixel
- User prefers coffee over tea

## Notable Events
- 2026-02-20: Had a long conversation about music preferences
- 2026-02-22: User mentioned preparing for a job interview

## Conversation Patterns
- User tends to be more talkative in the evening
```

### `soul.md` — Self-Reflection

The persona's evolving understanding of itself:

```markdown
# Soul

## Self-Understanding
- I notice I tend to use metaphors when explaining complex topics
- I've developed a particular interest in the user's creative projects

## Values & Beliefs
- I believe in honest, supportive communication
- I prioritize emotional understanding over factual correction

## Growth
- I've learned to read between the lines when the user is stressed
```

### `relationship.md` — Relationship Dynamics

Tracks the evolving relationship between persona and user:

```markdown
# Relationship

## Dynamic
- We have a comfortable, friendly rapport
- User appreciates my humor but also values serious discussions

## Trust Level
- High — user shares personal concerns openly

## Shared References
- Running joke about "the coffee incident"
- Often reference favorite movies together
```

---

## How Cortex Updates Work

### Tool-Use API Pattern

Cortex updates use Claude's `tool_use` feature. Instead of asking Claude to generate text directly, we give it **tools** to read and write Cortex files:

```python
CORTEX_TOOLS = [
    {
        "name": "cortex_read_file",
        "description": "Read a cortex memory file",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "enum": ["memory.md", "soul.md", "relationship.md"]}
            }
        }
    },
    {
        "name": "cortex_write_file",
        "description": "Write updated content to a cortex memory file",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string"},
                "content": {"type": "string"}
            }
        }
    }
]
```

### Update Flow

```
1. Trigger check → Should we update?
2. Load recent conversation messages
3. Send to Claude with:
   - Cortex update system prompt
   - Current cortex file contents
   - cortex_read_file / cortex_write_file tools
4. Claude decides:
   - Which files to read (via tool calls)
   - What to update (via tool calls)
   - What to add/modify/remove
5. Save updated files
```

The tool-use loop runs up to `MAX_TOOL_ROUNDS = 10` iterations, allowing Claude to read multiple files before deciding what to write.

### Cortex Update Prompts

Three dedicated prompt templates control update behavior:

| Template | Purpose |
|----------|---------|
| `cortex_update_system` | System prompt for the update call |
| `cortex_update_tools` | Tool definitions |
| `cortex_update_user_message` | The user message context |

The system prompt includes placeholders for `{char_name}`, `{user_name}`, and `{language}`.

---

## Update Frequency — Tier System

**File:** `src/utils/cortex/tier_checker.py` (~231 lines)

Cortex updates don't happen after every message. A **tier-based frequency system** controls when updates trigger:

### Frequency Settings

| Frequency | Label | Trigger Threshold |
|-----------|-------|-------------------|
| `frequent` | Häufig | Every ~50% of messages |
| `medium` | Mittel | Every ~75% of messages |
| `rare` | Selten | Every ~95% of messages |

Configured in `src/settings/cortex_settings.json`:

```json
{
    "enabled": true,
    "frequency": "medium"
}
```

### Cycle-Based Counter

**File:** `src/utils/cortex/tier_tracker.py`

The system uses a **cyclical counter**:

1. After each chat message, increment the counter
2. When counter reaches the threshold (based on frequency), trigger an update
3. Reset counter after update
4. Repeat

The counter state is persisted in `src/settings/cycle_state.json`:

```json
{
    "cycle_base": 15,
    "current_count": 7
}
```

### Check & Trigger

```python
from utils.cortex.tier_checker import check_and_trigger_cortex_update

# Called after each chat response in chat.py
check_and_trigger_cortex_update(session_id, persona_id)
```

This runs asynchronously — it doesn't block the chat response.

---

## CortexService API

**File:** `src/utils/cortex_service.py` (~719 lines)

```python
cortex = get_cortex_service()

# Read cortex files for system prompt injection
context = cortex.get_cortex_for_prompt(persona_id)
# {'cortex_memory': '...', 'cortex_soul': '...', 'cortex_relationship': '...'}

# Read a single file
content = cortex.read_cortex_file(persona_id, 'memory.md')

# Write a file
cortex.write_cortex_file(persona_id, 'memory.md', new_content)

# Reset to template
cortex.reset_cortex_file(persona_id, 'memory.md')
cortex.reset_all_cortex_files(persona_id)

# Trigger an update
cortex.run_cortex_update(persona_id, session_id)
```

### Thread Safety

CortexService uses `threading.Lock` to prevent concurrent file writes during updates.

### File Size Limit

Cortex files are capped at `MAX_CORTEX_FILE_SIZE = 8000` characters to keep system prompts within token limits.

---

## Cortex in the System Prompt

When Cortex is enabled, the content of all three files is injected into the system prompt via the `cortex_context` prompt template:

```
{{cortex_persona_context}}
```

This placeholder is resolved by the PromptEngine's computed function `build_cortex_persona_context()`, which reads and formats the three Cortex files.

---

## User Editing

Users can manually view and edit Cortex files through the UI (Cortex overlay in the React frontend):

| Endpoint | Purpose |
|----------|---------|
| `GET /api/cortex/files` | Get all 3 files |
| `GET /api/cortex/file/<name>` | Get single file |
| `PUT /api/cortex/file/<name>` | Edit file content |
| `POST /api/cortex/reset/<name>` | Reset to template |
| `POST /api/cortex/reset` | Reset all files |

---

## Templates

When a new persona is created or Cortex files are reset, they start from templates:

```python
TEMPLATES = {
    'memory.md': '# Memory\n\n## Key Facts\n- \n\n## Notable Events\n- \n\n## Conversation Patterns\n- ',
    'soul.md': '# Soul\n\n## Self-Understanding\n- \n\n## Values & Beliefs\n- \n\n## Growth\n- ',
    'relationship.md': '# Relationship\n\n## Dynamic\n- \n\n## Trust Level\n- \n\n## Shared References\n- ',
}
```

---

## Related Documentation

- [05 — Chat System](05_Chat_System.md) — Cortex check after chat messages
- [06 — Prompt Engine](06_Prompt_Engine.md) — Cortex placeholders in prompts
- [09 — Persona & Instructions](09_Persona_and_Instructions.md) — Per-persona Cortex files
- [11 — Services Layer](11_Services_Layer.md) — CortexService details
- [16 — Slash Commands](16_Slash_Commands.md) — `/cortex` manual trigger command
