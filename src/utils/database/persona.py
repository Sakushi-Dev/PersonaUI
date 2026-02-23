"""
Persona Database Management & Migration

Handles:
- Creating/deleting persona databases
- Legacy migration from chat.db
- Finding sessions across persona DBs
"""

import sqlite3
import os
import glob
from typing import Optional
from ..logger import log
from .connection import get_db_path, get_db_connection, init_persona_db, init_db_schema, get_all_persona_ids, DATA_DIR
from ..sql_loader import sql


def create_persona_db(persona_id: str) -> bool:
    """
    Creates a new database for a persona.
    
    Args:
        persona_id: New persona ID
        
    Returns:
        True on success
    """
    try:
        init_persona_db(persona_id)
        log.info("Persona DB created: %s", get_db_path(persona_id))
        return True
    except Exception as e:
        log.error("Error creating persona DB for %s: %s", persona_id, e)
        return False


def delete_persona_db(persona_id: str) -> bool:
    """
    Deletes a persona's database.
    
    Args:
        persona_id: Persona ID (not 'default'!)
        
    Returns:
        True on success
    """
    if persona_id == 'default':
        log.warning("Default DB cannot be deleted!")
        return False
    
    db_path = get_db_path(persona_id)
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
            log.info("Persona DB deleted: %s", db_path)
            return True
        return False
    except Exception as e:
        log.error("Error deleting persona DB %s: %s", persona_id, e)
        return False


def init_all_dbs():
    """
    Initializes all existing persona databases.
    Called on server startup.
    """
    log.info("Initializing per-persona databases...")
    
    # Check if old chat.db exists and needs migration
    legacy_db = os.path.join(DATA_DIR, 'chat.db')
    if os.path.exists(legacy_db):
        log.warning("Found old chat.db - starting migration...")
        migrate_from_legacy_db()
    
    # Initialize main.db (default persona)
    init_persona_db('default')
    
    # Initialize all existing persona DBs
    pattern = os.path.join(DATA_DIR, 'persona_*.db')
    for db_file in glob.glob(pattern):
        filename = os.path.basename(db_file)
        persona_id = filename.replace('persona_', '').replace('.db', '')
        if persona_id:
            init_persona_db(persona_id)
    
    persona_ids = get_all_persona_ids()
    log.info("%d persona DB(s) ready: %s", len(persona_ids), persona_ids)


def find_session_persona(session_id: int) -> Optional[str]:
    """
    Searches all persona DBs for a session ID.
    Used for backwards compatibility with URLs without persona parameter.
    
    Args:
        session_id: Session ID
        
    Returns:
        persona_id as string or None
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


def migrate_from_legacy_db():
    """
    Migrates data from old chat.db to per-persona databases.
    After successful migration, chat.db is renamed to chat.db.backup.
    """
    legacy_db = os.path.join(DATA_DIR, 'chat.db')
    if not os.path.exists(legacy_db):
        return
    
    try:
        old_conn = sqlite3.connect(legacy_db)
        old_cursor = old_conn.cursor()
        
        # Check which personas exist in the old DB
        old_cursor.execute(
            'SELECT DISTINCT COALESCE(persona_id, "default") FROM chat_sessions'
        )
        persona_ids_in_sessions = set(row[0] for row in old_cursor.fetchall())
        
        # Also get persona IDs from memories
        try:
            old_cursor.execute(
                'SELECT DISTINCT COALESCE(persona_id, "default") FROM memories'
            )
            persona_ids_in_memories = set(row[0] for row in old_cursor.fetchall())
        except sqlite3.OperationalError:
            persona_ids_in_memories = set()
        
        all_persona_ids = persona_ids_in_sessions | persona_ids_in_memories
        if not all_persona_ids:
            all_persona_ids = {'default'}
        
        log.info("Found personas in chat.db: %s", all_persona_ids)
        
        for pid in all_persona_ids:
            db_path = get_db_path(pid)
            new_conn = sqlite3.connect(db_path)
            init_db_schema(new_conn, pid)
            new_cursor = new_conn.cursor()
            
            # Migrate sessions
            old_cursor.execute('''
                SELECT id, title, persona_id, created_at, updated_at
                FROM chat_sessions
                WHERE COALESCE(persona_id, 'default') = ?
            ''', (pid,))
            sessions = old_cursor.fetchall()
            
            for session in sessions:
                new_cursor.execute('''
                    INSERT OR IGNORE INTO chat_sessions (id, title, persona_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', session)
                
                # Migrate messages for this session
                old_cursor.execute('''
                    SELECT id, session_id, message, is_user, timestamp, character_name
                    FROM chat_messages
                    WHERE session_id = ?
                ''', (session[0],))
                messages = old_cursor.fetchall()
                
                for msg in messages:
                    new_cursor.execute('''
                        INSERT OR IGNORE INTO chat_messages (id, session_id, message, is_user, timestamp, character_name)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', msg)
            
            # Migrate memories
            try:
                old_cursor.execute('''
                    SELECT id, session_id, persona_id, content, created_at, is_active
                    FROM memories
                    WHERE COALESCE(persona_id, 'default') = ?
                ''', (pid,))
                memories = old_cursor.fetchall()
                
                for mem in memories:
                    new_cursor.execute('''
                        INSERT OR IGNORE INTO memories (id, session_id, persona_id, content, created_at, is_active)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', mem)
            except sqlite3.OperationalError:
                pass  # No memories table in old DB
            
            new_conn.commit()
            new_conn.close()
            log.info("Persona '%s': %d sessions migrated", pid, len(sessions))
        
        old_conn.close()
        
        # Rename old DB
        backup_path = legacy_db + '.backup'
        # If backup already exists, add number
        if os.path.exists(backup_path):
            i = 1
            while os.path.exists(f"{legacy_db}.backup.{i}"):
                i += 1
            backup_path = f"{legacy_db}.backup.{i}"
        
        os.rename(legacy_db, backup_path)
        log.info("Old chat.db renamed to %s", os.path.basename(backup_path))
        log.info("Migration completed successfully!")
        
    except Exception as e:
        log.error("Migration failed: %s", e, exc_info=True)