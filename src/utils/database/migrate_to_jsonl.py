"""
SQLite to JSONL Migration

Automatically converts existing SQLite .db files to JSONL format.
Runs during app startup to migrate from old SQLite storage to new JSONL system.

Migration order:
1. chat.db (legacy) -> JSONL (handled by persona.py)
2. main.db + persona_*.db -> JSONL (handled here)

After successful migration, .db files are renamed to .db.pre_jsonl_backup.
"""

import sqlite3
import os
import glob
from datetime import datetime
from typing import Optional, List, Tuple

from ..logger import log
from .connection import DATA_DIR
from . import jsonl_store


def _convert_timestamp(ts: Optional[str]) -> str:
    """
    Converts SQLite timestamp to ISO format.
    
    SQLite format: "2026-03-03 21:50:00" (space between date and time)
    JSONL format: "2026-03-03T21:50:00" (ISO 8601)
    
    Args:
        ts: Timestamp string from SQLite or None
        
    Returns:
        ISO formatted timestamp string
    """
    if not ts or not ts.strip():
        return datetime.now().isoformat()
    return ts.strip().replace(" ", "T", 1)


def _get_persona_id_from_db_path(db_path: str) -> str:
    """
    Extracts persona_id from database file path.
    
    Args:
        db_path: Path to SQLite database file
        
    Returns:
        persona_id: "default" for main.db, extracted ID for persona_*.db
    """
    filename = os.path.basename(db_path)
    
    if filename == 'main.db':
        return 'default'
    
    if filename.startswith('persona_') and filename.endswith('.db'):
        # Extract ID from persona_abc123.db -> abc123
        return filename[8:-3]  # Remove "persona_" prefix and ".db" suffix
    
    # Fallback
    return 'default'


def _migrate_single_db(db_path: str, persona_id: str) -> bool:
    """
    Migrates a single SQLite database to JSONL format.
    
    Args:
        db_path: Path to the SQLite database file
        persona_id: Persona ID to use for JSONL storage
        
    Returns:
        True if migration was successful, False on error
    """
    try:
        log.info("Migrating %s -> JSONL (persona: %s)", db_path, persona_id)
        
        # Open SQLite connection
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if chat_sessions table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='chat_sessions'
        """)
        
        if not cursor.fetchone():
            log.info("No chat_sessions table in %s - nothing to migrate", db_path)
            conn.close()
            return True
        
        # Ensure persona directory exists
        jsonl_store.ensure_dir(os.path.join(DATA_DIR, persona_id))
        
        # Migrate sessions
        cursor.execute("""
            SELECT id, title, persona_id, created_at, updated_at
            FROM chat_sessions
        """)
        sessions = cursor.fetchall()
        
        sessions_migrated = 0
        messages_migrated = 0
        
        sessions_path = os.path.join(DATA_DIR, persona_id, "sessions", "sessions.jsonl")
        
        for session_row in sessions:
            session_id, title, db_persona_id, created_at, updated_at = session_row
            
            # Build session record
            session_record = {
                "id": session_id,
                "title": title or "Neue Konversation",
                "persona_id": persona_id,  # Use target persona_id, not DB value
                "created_at": _convert_timestamp(created_at),
                "updated_at": _convert_timestamp(updated_at)
            }
            
            # Append session to sessions.jsonl
            jsonl_store.append(sessions_path, session_record)
            sessions_migrated += 1
            
            # Migrate messages for this session
            cursor.execute("""
                SELECT id, session_id, message, is_user, timestamp, character_name
                FROM chat_messages
                WHERE session_id = ?
            """, (session_id,))
            messages = cursor.fetchall()
            
            if messages:
                messages_path = os.path.join(DATA_DIR, persona_id, "messages", f"messages_{session_id}.jsonl")
                
                for msg_row in messages:
                    msg_id, sess_id, message, is_user, timestamp, character_name = msg_row
                    
                    # Build message record
                    message_record = {
                        "id": msg_id,
                        "session_id": sess_id,
                        "message": message or "",
                        "is_user": bool(is_user),  # Convert 0/1 to false/true
                        "timestamp": _convert_timestamp(timestamp),
                        "character_name": character_name or "Assistant"
                    }
                    
                    # Append message to messages_{session_id}.jsonl
                    jsonl_store.append(messages_path, message_record)
                    messages_migrated += 1
        
        conn.close()
        
        # Rename original DB file
        backup_path = db_path + ".pre_jsonl_backup"
        os.rename(db_path, backup_path)
        
        log.info("Migration complete: %s -> JSONL (%d sessions, %d messages)", 
                 os.path.basename(db_path), sessions_migrated, messages_migrated)
        
        return True
        
    except Exception as e:
        log.error("Migration failed for %s: %s", db_path, e, exc_info=True)
        return False


def migrate_sqlite_to_jsonl() -> None:
    """
    Main migration function that converts existing SQLite databases to JSONL.
    
    Process:
    1. Scan DATA_DIR for .db files (main.db, persona_*.db)
    2. Skip if no .db files found
    3. Skip if JSONL data already exists (idempotent check)
    4. For each .db file: extract persona_id, migrate to JSONL, rename .db
    5. Log summary of migration results
    
    This function is called from init_all_dbs() during app startup.
    """
    log.info("Checking for SQLite databases to migrate...")
    
    # Find all .db files in DATA_DIR
    db_pattern = os.path.join(DATA_DIR, "*.db")
    db_files = glob.glob(db_pattern)
    
    # Filter to only main.db and persona_*.db files
    target_files = []
    for db_file in db_files:
        filename = os.path.basename(db_file)
        if filename == "main.db" or (filename.startswith("persona_") and filename.endswith(".db")):
            target_files.append(db_file)
    
    if not target_files:
        log.info("No SQLite databases found - skipping migration")
        return
    
    # Check if migration already happened (idempotent check)
    default_sessions_file = os.path.join(DATA_DIR, "default", "sessions", "sessions.jsonl")
    if os.path.exists(default_sessions_file):
        log.info("JSONL files already exist - skipping migration")
        return
    
    log.info("Found %d SQLite databases to migrate: %s", 
             len(target_files), [os.path.basename(f) for f in target_files])
    
    # Migration statistics
    successful_migrations = 0
    failed_migrations = 0
    
    # Migrate each database
    for db_path in target_files:
        persona_id = _get_persona_id_from_db_path(db_path)
        
        if _migrate_single_db(db_path, persona_id):
            successful_migrations += 1
        else:
            failed_migrations += 1
    
    # Log summary
    if successful_migrations > 0:
        log.info("Migration summary: %d successful, %d failed", 
                 successful_migrations, failed_migrations)
    else:
        log.warning("All migrations failed! Check logs for details.")
