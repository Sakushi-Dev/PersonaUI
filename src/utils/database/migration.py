"""
Datenbank-Migrationen

Infrastruktur für Schema-Migrationen.
Neue Migrationen werden in der MIGRATIONS-Liste registriert und
beim Server-Start automatisch ausgeführt (sofern noch nicht angewendet).

Verwendung:
    Neue Migration hinzufügen:
    1. SQL in src/sql/migrations.sql als benannte Query anlegen
    2. Migration-Dict in MIGRATIONS-Liste eintragen
    3. run_pending_migrations() wird beim nächsten Start automatisch aufgerufen
"""

import sqlite3
from typing import List, Dict

from ..logger import log
from ..sql_loader import sql
from .connection import get_db_connection
from .schema import get_all_persona_ids


# ===== MIGRATION REGISTRY =====
# Jede Migration hat:
#   - id: Eindeutiger Name (wird in db_info gespeichert)
#   - description: Kurzbeschreibung
#   - check: SQL-Query-Name zum Prüfen ob schon angewendet (oder None)
#   - apply: Liste von SQL-Query-Namen die ausgeführt werden
#
# Reihenfolge ist wichtig! Neue Migrationen immer UNTEN anfügen.

MIGRATIONS: List[Dict] = [
    {
        'id': 'add_last_memory_message_id',
        'description': 'Memory-Marker Spalte zu Sessions hinzufügen',
        'check': 'migrations.check_last_memory_message_id',
        'apply': ['migrations.add_last_memory_message_id'],
    },
    {
        'id': 'add_memory_message_ranges',
        'description': 'Start/End Message-ID für Memory-Ranges',
        'check': 'migrations.check_memory_message_ranges',
        'apply': ['migrations.add_start_message_id', 'migrations.add_end_message_id'],
    },
    {
        'id': 'add_mood_tables',
        'description': 'Mood-State und History Tabellen hinzufügen',
        'check': 'migrations.check_mood_state',
        'apply': ['migrations.create_mood_state', 'migrations.create_mood_history'],
    },
]


def _is_migration_applied(cursor: sqlite3.Cursor, migration_id: str) -> bool:
    """Prüft ob eine Migration bereits angewendet wurde (via db_info Tabelle)."""
    try:
        cursor.execute('SELECT value FROM db_info WHERE key = ?', (f'migration_{migration_id}',))
        return cursor.fetchone() is not None
    except sqlite3.OperationalError:
        return False


def _mark_migration_applied(cursor: sqlite3.Cursor, migration_id: str):
    """Markiert eine Migration als angewendet."""
    cursor.execute(
        'INSERT OR REPLACE INTO db_info (key, value) VALUES (?, ?)',
        (f'migration_{migration_id}', '1')
    )


def _run_migration(conn: sqlite3.Connection, migration: Dict) -> bool:
    """
    Führt eine einzelne Migration auf einer DB-Verbindung aus.
    
    Returns:
        True wenn angewendet, False wenn übersprungen
    """
    cursor = conn.cursor()
    mid = migration['id']
    
    # Bereits angewendet?
    if _is_migration_applied(cursor, mid):
        return False
    
    # Check-Query: Prüfe ob die Änderung schon existiert (z.B. Spalte vorhanden)
    if migration.get('check'):
        try:
            cursor.execute(sql(migration['check']))
            # Query erfolgreich → Änderung existiert bereits, nur markieren
            _mark_migration_applied(cursor, mid)
            conn.commit()
            return False
        except sqlite3.OperationalError:
            pass  # Änderung fehlt noch → Migration ausführen
    
    # Apply-Queries ausführen
    for query_name in migration['apply']:
        cursor.execute(sql(query_name))
    
    _mark_migration_applied(cursor, mid)
    conn.commit()
    return True


def run_pending_migrations(persona_id: str = None):
    """
    Führt alle ausstehenden Migrationen aus.
    
    Args:
        persona_id: Wenn angegeben, nur für diese Persona.
                    Wenn None, für ALLE Persona-DBs.
    """
    if persona_id is not None:
        persona_ids = [persona_id]
    else:
        persona_ids = get_all_persona_ids()
    
    total_applied = 0
    
    for pid in persona_ids:
        try:
            conn = get_db_connection(pid)
            applied = 0
            
            for migration in MIGRATIONS:
                if _run_migration(conn, migration):
                    log.info("Migration '%s' angewendet (persona=%s): %s",
                             migration['id'], pid, migration['description'])
                    applied += 1
            
            conn.close()
            total_applied += applied
        except Exception as e:
            log.error("Migration fehlgeschlagen für Persona %s: %s", pid, e, exc_info=True)
    
    if total_applied > 0:
        log.info("%d Migration(en) insgesamt angewendet", total_applied)
