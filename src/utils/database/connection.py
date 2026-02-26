"""
Database Connection & Schema Management

Handles:
- Database paths and connections
- Schema initialization
- Migration logic
"""

import sqlite3
import os
from typing import List
from ..sql_loader import sql, load_schema

# Data directory setup
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'data'))
os.makedirs(DATA_DIR, exist_ok=True)


def get_db_path(persona_id: str = 'default') -> str:
    """
    Returns the database file path for a specific persona.
    
    Args:
        persona_id: Persona ID ('default' or a UUID)
        
    Returns:
        Path to SQLite file
    """
    if persona_id == 'default' or not persona_id:
        return os.path.join(DATA_DIR, 'main.db')
    return os.path.join(DATA_DIR, f'persona_{persona_id}.db')


def get_db_connection(persona_id: str = 'default') -> sqlite3.Connection:
    """
    Creates a database connection with foreign keys enabled.
    
    Args:
        persona_id: Persona ID
        
    Returns:
        sqlite3.Connection object
    """
    db_path = get_db_path(persona_id)
    conn = sqlite3.connect(db_path)
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def init_db_schema(conn: sqlite3.Connection, persona_id: str = 'default'):
    """
    Initializes the database schema in a connection.
    Creates all necessary tables and indexes.
    """
    cursor = conn.cursor()
    cursor.execute('PRAGMA foreign_keys = ON')
    
    # Load and execute schema from SQL file
    cursor.executescript(load_schema())
    
    # Set persona_id in db_info
    cursor.execute(sql('chat.upsert_db_info'), ('persona_id', persona_id))
    
    conn.commit()
    
    conn.commit()


def init_persona_db(persona_id: str = 'default'):
    """Initializes the database for a specific persona."""
    db_path = get_db_path(persona_id)
    conn = sqlite3.connect(db_path)
    init_db_schema(conn, persona_id)
    conn.close()


def get_all_persona_ids() -> List[str]:
    """
    Returns all persona IDs for which databases exist.
    
    Returns:
        List of persona IDs (including 'default')
    """
    import glob
    
    ids = []
    
    # main.db → default
    if os.path.exists(os.path.join(DATA_DIR, 'main.db')):
        ids.append('default')
    
    # persona_*.db → custom personas
    pattern = os.path.join(DATA_DIR, 'persona_*.db')
    for db_file in glob.glob(pattern):
        filename = os.path.basename(db_file)
        # persona_abc123.db → abc123
        persona_id = filename.replace('persona_', '').replace('.db', '')
        if persona_id:
            ids.append(persona_id)
    
    return ids