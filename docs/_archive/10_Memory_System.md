# 10 — Memory System

## Overview

The memory system enables AI personas to **remember information about the user** across sessions. An automated pipeline detects memorable content in conversations, extracts relevant details, and persists them per-category for later retrieval in prompts.

---

## Architecture

```
Memory Pipeline:
  Chat Message → Afterthought Analysis → Memory Marker Detection
    → Category Classification → Extraction & Persistence → Prompt Integration

Components:
  MemoryService (Python)          ← Backend logic & API calls
  MemoryManager.js (Frontend)     ← UI management
  memories.sql                    ← SQL queries
  prompt templates                ← Analysis & extraction prompts
```

---

## Memory Pipeline (4 Phases)

### Phase 1: Afterthought Analysis

After each AI response, the **Afterthought System** analyzes the conversation:

```
User message + AI response
  → afterthought prompt (via PromptEngine)
  → API call (streaming, apiAfterModel)
  → JSON response with analysis
```

**Afterthought output includes:**
- `inner_thoughts`: AI's "inner monologue"
- `mood_summary`: Current mood assessment
- `memory_markers`: Array of detected memorable items

### Phase 2: Memory Marker Detection

Memory markers are structured hints from the afterthought analysis:

```json
{
  "memory_markers": [
    {
      "category": "hobbies",
      "detail": "User enjoys playing guitar",
      "importance": "medium"
    }
  ]
}
```

**Importance levels**: `low`, `medium`, `high`  
Only markers with importance ≥ `medium` are processed further (configurable).

### Phase 3: Category Classification

Available memory categories:

| Category | Description | Examples |
|----------|-------------|----------|
| name | User's name | "My name is Alex" |
| age | User's age | "I'm 25" |
| location | Residence / origin | "I live in Berlin" |
| job | Occupation / career | "I work as a developer" |
| hobbies | Hobbies & interests | "I love gaming" |
| relationships | Family & social circle | "My brother is called Tom" |
| preferences | Likes & dislikes | "I love pizza" |
| personality | Character traits | "I'm rather introverted" |
| daily | Daily routine & habits | "I always get up at 6" |
| goals | Plans & dreams | "I want to learn Japanese" |
| history | Past events | "I used to live in Munich" |

### Phase 4: Extraction & Persistence

```python
MemoryService.process_memory_markers(markers, session_id):
    for marker in markers:
        # 1. Check importance threshold
        # 2. Validate category
        # 3. Check for duplicates (semantic similarity)
        # 4. Save or update existing memory
        # 5. Build confirmation for AI response
```

---

## MemoryService (`src/utils/services/memory_service.py`)

### Key Methods

| Method | Description |
|--------|-------------|
| `process_memory_markers(markers, session_id)` | Process markers from afterthought |
| `get_memories_for_prompt()` | All memories formatted for prompt |
| `get_memories_by_category(category)` | Memories filtered by category |
| `get_all_memories()` | All memories with metadata |
| `update_memory(memory_id, content)` | Edit memory content |
| `delete_memory(memory_id)` | Delete single memory |
| `delete_memories_by_category(category)` | Delete all in category |
| `clear_all_memories()` | Delete all memories |
| `get_memory_stats()` | Statistics per category |

### Duplicate Detection

Before saving a new memory, existing memories in the same category are checked:

1. Load existing memories in the category
2. Compare via string similarity (fuzzy matching)
3. If similarity > threshold → **update** existing memory
4. If no match → **create** new memory

### Prompt Integration

`get_memories_for_prompt()` builds a structured text block:

```
[Memory – Name]
- The user's name is Alex

[Memory – Hobbies]
- User enjoys playing guitar
- User likes strategy games

[Memory – Job]
- Works as a software developer
```

This block is injected into the system prompt via the `{{memories}}` placeholder.

---

## Frontend: MemoryManager.js

### Features

- **Memory overview**: Categorized display of all memories
- **Inline editing**: Click to edit individual memories
- **Delete**: Single entries or entire categories
- **Clear all**: Delete all memories with confirmation
- **Statistics**: Count per category
- **Real-time updates**: Automatic refresh after changes

### UI Components

```
Memory Panel (Sidebar)
  ├── Category Headers (collapsible)
  │     ├── Memory Entry
  │     │     ├── Content text
  │     │     ├── Edit button
  │     │     └── Delete button
  │     └── Category delete button
  ├── Statistics bar
  └── "Clear All" button
```

---

## Routes (Memory API)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/memories` | All memories |
| `GET` | `/api/memories/stats` | Memory statistics |
| `GET` | `/api/memories/category/{cat}` | Memories by category |
| `PUT` | `/api/memories/{id}` | Update memory |
| `DELETE` | `/api/memories/{id}` | Delete memory |
| `DELETE` | `/api/memories/category/{cat}` | Delete category |
| `DELETE` | `/api/memories/all` | Clear all |

All routes use the `@require_persona` decorator for persona isolation.

---

## Database Schema

```sql
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    content TEXT NOT NULL,
    importance TEXT DEFAULT 'medium',
    source_session_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Each persona's memories are stored in their own database (`persona_{id}.db`).

---

## Design Decisions

1. **Passive extraction**: Memories are captured from natural conversation, not explicit user commands
2. **Category system**: Structured categories instead of free-text tags for consistency
3. **Importance filtering**: Only sufficiently important information is stored
4. **Duplicate avoidance**: Fuzzy matching prevents redundant entries
5. **Per-persona isolation**: Each persona maintains its own memory set
6. **User control**: Full CRUD access — users can edit, delete, or clear memories at any time
7. **Prompt integration**: Memories are injected as structured blocks, not raw data
