"""
Memory Context Formatierung – Formatiert Memory-Einträge für den Prompt-Kontext.

Reine Utility-Funktion: Kein DB-Zugriff – erhält nur bereits geladene Memory-Daten.
Delegiert an PromptEngine wenn verfügbar, sonst hardcoded Fallback.
"""

import re
from typing import List, Dict, Any, Optional
from ..logger import log


def format_memories_for_prompt(memories: List[Dict[str, Any]], max_memories: int = 30,
                                engine=None) -> str:
    """
    Formatiert Memory-Einträge als Prompt-Kontext.

    WICHTIG: Erhält nur bereits geladene Memory-Daten.
    Kein DB-Zugriff – die DB-Abfrage erfolgt im Aufrufer (Service oder Route).

    Args:
        memories: Liste von Memory-Dicts mit 'content' Key
        max_memories: Maximale Anzahl
        engine: Optionale PromptEngine für Template-basierte Formatierung

    Returns:
        Formatierter Memory-Kontext als String
    """
    if not memories:
        return ""

    # Begrenze auf max_memories
    if len(memories) > max_memories:
        memories = memories[:max_memories]

    # Collect memory entries
    memory_entries = []
    for memory in memories:
        content = memory.get('content', '').strip()
        if content:
            # Remove excessive blank lines within a memory
            content = re.sub(r'\n{2,}', '\n', content)
            memory_entries.append(content)

    if not memory_entries:
        return ""

    # Engine-Delegation: Verwende memory_context Template mit {{memory_entries}} Placeholder
    if engine:
        try:
            entries_text = "\n\n".join(memory_entries)
            runtime_vars = {'memory_entries': entries_text}
            result = engine.resolve_prompt('memory_context', variant='default', runtime_vars=runtime_vars)
            if result:
                return result
        except Exception as e:
            log.warning("Engine memory_context fehlgeschlagen, Fallback: %s", e)

    # Fallback: hardcoded Format
    memory_lines = []
    memory_lines.append("**MEMORY CONTEXT**\n\nHere is the conversation history so far:")
    memory_lines.append("")

    for entry in memory_entries:
        memory_lines.append(entry)
        memory_lines.append("")  # Leerzeile zwischen Memories

    memory_lines.append("\n\n**END OF MEMORY CONTEXT**")

    return "\n".join(memory_lines)
