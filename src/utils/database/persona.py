"""
Persona Database Management & Migration
Re-exports aus schema.py + Legacy-Migration.
"""

import sqlite3
import os
import glob
from typing import Optional
from ..logger import log
from .connection import get_db_path, get_db_connection, get_all_persona_ids, DATA_DIR
from .schema import init_persona_db
from .migrate_to_jsonl import _convert_timestamp
from . import jsonl_store


def migrate_from_legacy_db():
    """
    Migrates data from old chat.db directly to JSONL format.
    After successful migration, chat.db is renamed to chat.db.backup.
    
    Updated to migrate directly to JSONL, skipping the per-persona SQLite intermediate step.
    """
    legacy_db = os.path.join(DATA_DIR, 'chat.db')
    if not os.path.exists(legacy_db):
        return
    
    try:
        log.info("Migrating legacy chat.db directly to JSONL format...")
        
        old_conn = sqlite3.connect(legacy_db)
        old_cursor = old_conn.cursor()
        
        # Check which personas exist in the old DB
        old_cursor.execute(
            'SELECT DISTINCT COALESCE(persona_id, "default") FROM chat_sessions'
        )
        persona_ids_in_sessions = set(row[0] for row in old_cursor.fetchall())
        
        if not persona_ids_in_sessions:
            persona_ids_in_sessions = {'default'}
        
        log.info("Found personas in chat.db: %s", persona_ids_in_sessions)
        
        for pid in persona_ids_in_sessions:
            # Ensure persona directory exists
            jsonl_store.ensure_dir(os.path.join(DATA_DIR, pid))
            
            # Migrate sessions
            old_cursor.execute('''
                SELECT id, title, persona_id, created_at, updated_at
                FROM chat_sessions
                WHERE COALESCE(persona_id, 'default') = ?
            ''', (pid,))
            sessions = old_cursor.fetchall()
            
            sessions_path = os.path.join(DATA_DIR, pid, "sessions", "sessions.jsonl")
            sessions_migrated = 0
            messages_migrated = 0
            
            for session in sessions:
                session_id, title, db_persona_id, created_at, updated_at = session
                
                # Build session record
                session_record = {
                    "id": session_id,
                    "title": title or "Neue Konversation",
                    "persona_id": pid,
                    "created_at": _convert_timestamp(created_at),
                    "updated_at": _convert_timestamp(updated_at)
                }
                
                # Append session to sessions.jsonl
                jsonl_store.append(sessions_path, session_record)
                sessions_migrated += 1
                
                # Migrate messages for this session
                old_cursor.execute('''
                    SELECT id, session_id, message, is_user, timestamp, character_name
                    FROM chat_messages
                    WHERE session_id = ?
                ''', (session_id,))
                messages = old_cursor.fetchall()
                
                if messages:
                    messages_path = os.path.join(DATA_DIR, pid, "messages", f"messages_{session_id}.jsonl")
                    
                    for msg in messages:
                        msg_id, sess_id, message, is_user, timestamp, character_name = msg
                        
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
            
            log.info("Persona '%s': %d sessions, %d messages migrated to JSONL", 
                     pid, sessions_migrated, messages_migrated)
        
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
        log.info("Legacy migration completed successfully!")
        
    except Exception as e:
        log.error("Legacy migration failed: %s", e, exc_info=True)
