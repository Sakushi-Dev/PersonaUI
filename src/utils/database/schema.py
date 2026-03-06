"""
Schema-Initialisierung und Persona-DB Verwaltung

Erstellt/löscht Persona-Verzeichnisse und verwaltet JSONL-Lifecycle.
"""

import os
import shutil
from typing import Optional

from ..logger import log
from .connection import DATA_DIR, get_all_persona_ids
from . import jsonl_store


def init_persona_db(persona_id: str = 'default'):
    """
    Initialisiert das Verzeichnis für eine bestimmte Persona.
    Erstellt Persona-Verzeichnis via jsonl_store.ensure_dir().
    """
    persona_dir = os.path.join(DATA_DIR, persona_id)
    jsonl_store.ensure_dir(persona_dir)


def create_persona_db(persona_id: str) -> bool:
    """
    Erstellt ein neues Verzeichnis für eine Persona.
    
    Args:
        persona_id: ID der neuen Persona
        
    Returns:
        True bei Erfolg
    """
    try:
        init_persona_db(persona_id)
        log.info("Persona-Verzeichnis erstellt: %s", persona_id)
        return True
    except Exception as e:
        log.error("Fehler beim Erstellen des Persona-Verzeichnisses für %s: %s", persona_id, e)
        return False


def delete_persona_db(persona_id: str) -> bool:
    """
    Löscht das Verzeichnis einer Persona.
    
    Args:
        persona_id: ID der Persona (nicht 'default'!)
        
    Returns:
        True bei Erfolg
    """
    if persona_id == 'default':
        log.warning("Standard-Verzeichnis kann nicht gelöscht werden!")
        return False
    
    persona_dir = os.path.join(DATA_DIR, persona_id)
    try:
        if os.path.isdir(persona_dir):
            shutil.rmtree(persona_dir)
            log.info("Persona-Verzeichnis gelöscht: %s", persona_dir)
            return True
        return False
    except Exception as e:
        log.error("Fehler beim Löschen des Persona-Verzeichnisses %s: %s", persona_id, e)
        return False


def init_all_dbs():
    """
    Initialisiert alle vorhandenen Persona-Verzeichnisse.
    Wird beim Server-Start aufgerufen.
    """
    # SQLite→JSONL Migration (läuft nur wenn .db Dateien existieren)
    from .migrate_to_jsonl import migrate_sqlite_to_jsonl
    migrate_sqlite_to_jsonl()
    
    log.info("Initialisiere Per-Persona Verzeichnisse...")
    
    # Initialisiere default Verzeichnis
    default_dir = os.path.join(DATA_DIR, "default")
    jsonl_store.ensure_dir(default_dir)
    
    persona_ids = get_all_persona_ids()
    log.info("%d Persona(s) gefunden: %s", len(persona_ids), persona_ids)


def find_session_persona(session_id: int) -> Optional[str]:
    """
    Sucht in allen Persona-Verzeichnissen nach einer Session-ID.
    Wird für Rückwärtskompatibilität bei URLs ohne persona-Parameter verwendet.
    
    Args:
        session_id: ID der Session
        
    Returns:
        persona_id als String oder None
    """
    for pid in get_all_persona_ids():
        sessions_path = os.path.join(DATA_DIR, pid, "sessions", "sessions.jsonl")
        matches = jsonl_store.read_filtered(sessions_path, lambda s: s.get('id') == session_id)
        if matches:
            return pid
    return None
