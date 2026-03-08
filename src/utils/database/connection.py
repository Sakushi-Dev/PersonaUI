"""
Database Connection & Path Management

Handles:
- Data directory setup
- Persona directory paths
- Persona ID discovery
"""

import os
from typing import List

# Data directory setup
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'data'))
os.makedirs(DATA_DIR, exist_ok=True)


def get_persona_dir(persona_id: str = "default") -> str:
    """Gibt Pfad zum Persona-Verzeichnis zurück. Erstellt es NICHT."""
    return os.path.join(DATA_DIR, persona_id)



def get_all_persona_ids() -> List[str]:
    """
    Returns all persona IDs for which directories with JSONL files exist.
    
    Returns:
        List of persona IDs (including 'default')
    """
    ids = []
    
    try:
        for entry in os.listdir(DATA_DIR):
            entry_path = os.path.join(DATA_DIR, entry)
            if not os.path.isdir(entry_path):
                continue
                
            # Check if directory contains sessions/sessions.jsonl or messages/messages_*.jsonl
            has_valid_files = False
            
            # Check for sessions/sessions.jsonl
            if os.path.exists(os.path.join(entry_path, 'sessions', 'sessions.jsonl')):
                has_valid_files = True
            else:
                # Check for messages/messages_*.jsonl files
                messages_dir = os.path.join(entry_path, 'messages')
                if os.path.isdir(messages_dir):
                    for file in os.listdir(messages_dir):
                        if file.startswith('messages_') and file.endswith('.jsonl'):
                            has_valid_files = True
                            break
            
            if has_valid_files:
                ids.append(entry)
                
    except OSError:
        # If DATA_DIR doesn't exist or can't be read, return empty list
        pass
    
    return ids
