"""
Schema-Initialisierung und Persona-DB Verwaltung

Erstellt/löscht Persona-Datenbanken und verwaltet DB-Lifecycle.
"""

import sqlite3
import os
import glob
from typing import List, Optional

from ..logger import log
from ..sql_loader import sql, load_schema
from .connection import DATA_DIR, get_db_path, get_db_connection


def _init_db_schema(conn: sqlite3.Connection, persona_id: str = 'default'):
    """
    Initialisiert das Datenbank-Schema in einer Verbindung.
    Erstellt alle nötigen Tabellen und Indizes.
    """
    cursor = conn.cursor()
    cursor.execute('PRAGMA foreign_keys = ON')
    
    # Schema aus SQL-Datei laden und ausführen
    cursor.executescript(load_schema())
    
    # Persona-ID in DB-Info setzen
    cursor.execute(sql('chat.upsert_db_info'), ('persona_id', persona_id))
    
    conn.commit()


def init_persona_db(persona_id: str = 'default'):
    """Initialisiert die Datenbank für eine bestimmte Persona"""
    db_path = get_db_path(persona_id)
    conn = sqlite3.connect(db_path)
    _init_db_schema(conn, persona_id)
    conn.close()


def create_persona_db(persona_id: str) -> bool:
    """
    Erstellt eine neue Datenbank für eine Persona.
    
    Args:
        persona_id: ID der neuen Persona
        
    Returns:
        True bei Erfolg
    """
    try:
        init_persona_db(persona_id)
        # Migrationen für die neue DB ausführen
        from .migration import run_pending_migrations
        run_pending_migrations(persona_id)
        log.info("Persona-DB erstellt: %s", get_db_path(persona_id))
        return True
    except Exception as e:
        log.error("Fehler beim Erstellen der Persona-DB für %s: %s", persona_id, e)
        return False


def delete_persona_db(persona_id: str) -> bool:
    """
    Löscht die Datenbank einer Persona.
    
    Args:
        persona_id: ID der Persona (nicht 'default'!)
        
    Returns:
        True bei Erfolg
    """
    if persona_id == 'default':
        log.warning("Standard-DB kann nicht gelöscht werden!")
        return False
    
    db_path = get_db_path(persona_id)
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
            log.info("Persona-DB gelöscht: %s", db_path)
            return True
        return False
    except Exception as e:
        log.error("Fehler beim Löschen der Persona-DB %s: %s", persona_id, e)
        return False


def get_all_persona_ids() -> List[str]:
    """
    Gibt alle Persona-IDs zurück, für die Datenbanken existieren.
    
    Returns:
        Liste von Persona-IDs (inkl. 'default')
    """
    ids = []
    
    # main.db → default
    if os.path.exists(os.path.join(DATA_DIR, 'main.db')):
        ids.append('default')
    
    # persona_*.db → custom personas
    pattern = os.path.join(DATA_DIR, 'persona_*.db')
    for db_file in glob.glob(pattern):
        filename = os.path.basename(db_file)
        persona_id = filename.replace('persona_', '').replace('.db', '')
        if persona_id:
            ids.append(persona_id)
    
    return ids


def init_all_dbs():
    """
    Initialisiert alle vorhandenen Persona-Datenbanken.
    Wird beim Server-Start aufgerufen.
    """
    from .migration import run_pending_migrations
    
    log.info("Initialisiere Per-Persona Datenbanken...")
    
    # Initialisiere main.db (Standard-Persona)
    init_persona_db('default')
    
    # Initialisiere alle vorhandenen Persona-DBs
    pattern = os.path.join(DATA_DIR, 'persona_*.db')
    for db_file in glob.glob(pattern):
        filename = os.path.basename(db_file)
        persona_id = filename.replace('persona_', '').replace('.db', '')
        if persona_id:
            init_persona_db(persona_id)
    
    # Ausstehende Migrationen ausführen
    run_pending_migrations()
    
    persona_ids = get_all_persona_ids()
    log.info("%d Persona-DB(s) bereit: %s", len(persona_ids), persona_ids)


def find_session_persona(session_id: int) -> Optional[str]:
    """
    Sucht in allen Persona-DBs nach einer Session-ID.
    Wird für Rückwärtskompatibilität bei URLs ohne persona-Parameter verwendet.
    
    Args:
        session_id: ID der Session
        
    Returns:
        persona_id als String oder None
    """
    for pid in get_all_persona_ids():
        try:
            conn = get_db_connection(pid)
            cursor = conn.cursor()
            cursor.execute(sql('sessions.check_session_exists'), (session_id,))
            if cursor.fetchone():
                conn.close()
                return pid
            conn.close()
        except Exception:
            continue
    return None
