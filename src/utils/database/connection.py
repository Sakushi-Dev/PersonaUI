"""
Datenbank-Verbindung und Pfad-Management

Zentrale Stelle für DB-Pfade und Verbindungen.
Alle anderen Module importieren von hier.
"""

import sqlite3
import os

# Stelle sicher, dass data/ Verzeichnis existiert
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'data'))
os.makedirs(DATA_DIR, exist_ok=True)


def get_db_path(persona_id: str = 'default') -> str:
    """
    Gibt den Pfad zur Datenbank-Datei für eine bestimmte Persona zurück.
    
    Args:
        persona_id: ID der Persona ('default' oder eine UUID)
        
    Returns:
        Pfad zur SQLite-Datei
    """
    if persona_id == 'default' or not persona_id:
        return os.path.join(DATA_DIR, 'main.db')
    return os.path.join(DATA_DIR, f'persona_{persona_id}.db')


def get_db_connection(persona_id: str = 'default') -> sqlite3.Connection:
    """
    Erstellt eine Datenbankverbindung mit aktivierten Foreign Keys
    
    Args:
        persona_id: ID der Persona
        
    Returns:
        sqlite3.Connection Objekt
    """
    db_path = get_db_path(persona_id)
    conn = sqlite3.connect(db_path)
    conn.execute('PRAGMA foreign_keys = ON')
    return conn
