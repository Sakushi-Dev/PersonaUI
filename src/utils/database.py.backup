"""
Datenbank-Operationen für die Chat-Anwendung

Per-Persona Datenbank-Architektur:
- data/main.db       → Standard-Persona ('default')
- data/persona_{id}.db → Erstellte Personas (z.B. persona_89c4558f.db)

Jede Persona hat ihre eigene SQLite-DB mit identischem Schema.
Beim Erstellen einer Persona wird die DB angelegt, beim Löschen entfernt.
"""

import sqlite3
import os
import glob
from typing import List, Dict, Any, Optional
from .logger import log
from .sql_loader import sql, load_schema

# Stelle sicher, dass data/ Verzeichnis existiert
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
os.makedirs(DATA_DIR, exist_ok=True)


# ===== DB-PFAD & VERBINDUNG =====

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


# ===== SCHEMA & INITIALISIERUNG =====

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
    cursor.execute(sql('memories.upsert_db_info'), ('persona_id', persona_id))
    
    # Migration: last_memory_message_id Spalte zu chat_sessions hinzufügen
    try:
        cursor.execute(sql('migrations.check_last_memory_message_id'))
    except sqlite3.OperationalError:
        cursor.execute(sql('migrations.add_last_memory_message_id'))
        log.info("Migration: last_memory_message_id zu chat_sessions hinzugefügt (persona=%s)", persona_id)
    
    # Migration: start_message_id und end_message_id Spalten zu memories hinzufügen
    try:
        cursor.execute(sql('migrations.check_memory_message_ranges'))
    except sqlite3.OperationalError:
        cursor.execute(sql('migrations.add_start_message_id'))
        cursor.execute(sql('migrations.add_end_message_id'))
        log.info("Migration: start_message_id/end_message_id zu memories hinzugefügt (persona=%s)", persona_id)
    
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
        # persona_abc123.db → abc123
        persona_id = filename.replace('persona_', '').replace('.db', '')
        if persona_id:
            ids.append(persona_id)
    
    return ids


def init_all_dbs():
    """
    Initialisiert alle vorhandenen Persona-Datenbanken.
    Wird beim Server-Start aufgerufen.
    """
    log.info("Initialisiere Per-Persona Datenbanken...")
    
    # Prüfe ob alte chat.db existiert und migriert werden muss
    legacy_db = os.path.join(DATA_DIR, 'chat.db')
    if os.path.exists(legacy_db):
        log.warning("Alte chat.db gefunden - starte Migration...")
        migrate_from_legacy_db()
    
    # Initialisiere main.db (Standard-Persona)
    init_persona_db('default')
    
    # Initialisiere alle vorhandenen Persona-DBs
    pattern = os.path.join(DATA_DIR, 'persona_*.db')
    for db_file in glob.glob(pattern):
        filename = os.path.basename(db_file)
        persona_id = filename.replace('persona_', '').replace('.db', '')
        if persona_id:
            init_persona_db(persona_id)
    
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


# ===== MIGRATION =====

def migrate_from_legacy_db():
    """
    Migriert Daten aus der alten chat.db in per-Persona Datenbanken.
    Nach erfolgreicher Migration wird chat.db zu chat.db.backup umbenannt.
    """
    legacy_db = os.path.join(DATA_DIR, 'chat.db')
    if not os.path.exists(legacy_db):
        return
    
    try:
        old_conn = sqlite3.connect(legacy_db)
        old_cursor = old_conn.cursor()
        
        # Prüfe welche Personas in der alten DB existieren
        old_cursor.execute(
            'SELECT DISTINCT COALESCE(persona_id, "default") FROM chat_sessions'
        )
        persona_ids_in_sessions = set(row[0] for row in old_cursor.fetchall())
        
        # Auch Persona-IDs aus Memories holen
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
        
        log.info("Gefundene Personas in chat.db: %s", all_persona_ids)
        
        for pid in all_persona_ids:
            db_path = get_db_path(pid)
            new_conn = sqlite3.connect(db_path)
            _init_db_schema(new_conn, pid)
            new_cursor = new_conn.cursor()
            
            # Migriere Sessions
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
                
                # Migriere Nachrichten für diese Session
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
            
            # Migriere Memories
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
                pass  # Keine memories Tabelle in alter DB
            
            new_conn.commit()
            new_conn.close()
            log.info("Persona '%s': %d Sessions migriert", pid, len(sessions))
        
        old_conn.close()
        
        # Alte DB umbenennen
        backup_path = legacy_db + '.backup'
        # Falls backup schon existiert, mit Nummer versehen
        if os.path.exists(backup_path):
            i = 1
            while os.path.exists(f"{legacy_db}.backup.{i}"):
                i += 1
            backup_path = f"{legacy_db}.backup.{i}"
        
        os.rename(legacy_db, backup_path)
        log.info("Alte chat.db umbenannt zu %s", os.path.basename(backup_path))
        log.info("Migration erfolgreich abgeschlossen!")
        
    except Exception as e:
        log.error("Migration fehlgeschlagen: %s", e, exc_info=True)


# ===== CHAT HISTORY =====

def get_chat_history(limit: int = 30, session_id: int = None, offset: int = 0,
                     persona_id: str = 'default') -> List[Dict[str, Any]]:
    """
    Holt die Chat-Historie aus der Datenbank
    
    Args:
        limit: Maximale Anzahl der zurückzugebenden Nachrichten (Standard: 30)
        session_id: ID der Session (wenn None, wird die neueste Session verwendet)
        offset: Anzahl der zu überspringenden Nachrichten (für Pagination)
        persona_id: ID der Persona (bestimmt welche DB verwendet wird)
        
    Returns:
        Liste von Nachricht-Dictionaries (neueste zuerst, dann umgekehrt)
    """
    conn = get_db_connection(persona_id)
    cursor = conn.cursor()
    
    # Wenn keine session_id angegeben, hole die neueste Session
    if session_id is None:
        cursor.execute(sql('chat.get_latest_session_id'))
        result = cursor.fetchone()
        if result:
            session_id = result[0]
        else:
            conn.close()
            return []
    
    # Hole Memory-Ranges für diese Session (nur AKTIVE Memories mit Ranges)
    cursor.execute(sql('chat.get_memory_ranges'), (session_id,))
    memory_ranges = cursor.fetchall()
    
    # Fallback: Wenn keine Ranges vorhanden, nutze den alten Marker
    cursor.execute(sql('chat.get_session_memory_marker'), (session_id,))
    marker_row = cursor.fetchone()
    last_memory_message_id = marker_row[0] if marker_row and marker_row[0] else None
    
    # Hilfsfunktion: Prüfe ob eine Message-ID in einem der Memory-Ranges liegt
    def is_memorized(msg_id):
        if memory_ranges:
            for start_id, end_id in memory_ranges:
                if start_id <= msg_id <= end_id:
                    return True
            return False
        # Fallback für alte Memories ohne Ranges
        return last_memory_message_id is not None and msg_id <= last_memory_message_id
    
    cursor.execute(sql('chat.get_chat_history'), (session_id, limit, offset))
    
    # Umkehren, damit die älteste der geladenen Nachrichten zuerst kommt
    messages = []
    for row in reversed(cursor.fetchall()):
        msg = {
            'id': row[0],
            'message': row[1],
            'is_user': bool(row[2]),
            'timestamp': row[3],
            'character_name': row[4],
            'memorized': is_memorized(row[0])
        }
        messages.append(msg)
    
    conn.close()
    return messages


def get_message_count(session_id: int = None, persona_id: str = 'default') -> int:
    """
    Holt die Gesamtanzahl der Nachrichten für eine Session
    
    Args:
        session_id: ID der Session (wenn None, wird die neueste Session verwendet)
        persona_id: ID der Persona
        
    Returns:
        Anzahl der Nachrichten
    """
    conn = get_db_connection(persona_id)
    cursor = conn.cursor()
    
    if session_id is None:
        cursor.execute(sql('chat.get_latest_session_id'))
        result = cursor.fetchone()
        if result:
            session_id = result[0]
        else:
            conn.close()
            return 0
    
    cursor.execute(sql('chat.get_message_count'), (session_id,))
    
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_conversation_context(limit: int = 10, session_id: int = None,
                             persona_id: str = 'default') -> list:
    """
    Holt die letzten N Nachrichten für den Kontext der Claude API
    
    Args:
        limit: Anzahl der letzten Nachrichten
        session_id: ID der Session (wenn None, wird die neueste Session verwendet)
        persona_id: ID der Persona
        
    Returns:
        Liste von Nachrichten im Claude API Format
    """
    conn = get_db_connection(persona_id)
    cursor = conn.cursor()
    
    if session_id is None:
        cursor.execute(sql('chat.get_latest_session_id'))
        result = cursor.fetchone()
        if result:
            session_id = result[0]
        else:
            conn.close()
            return []
    
    cursor.execute(sql('chat.get_conversation_context'), (session_id, limit))
    
    raw_rows = list(reversed(cursor.fetchall()))
    raw_count = len(raw_rows)
    
    log.debug("Context-History: session=%s, persona=%s, limit=%d, raw_count=%d",
             session_id, persona_id, limit, raw_count)
    
    messages = []
    merged_count = 0
    for row in raw_rows:
        role = "user" if row[1] else "assistant"
        # Aufeinanderfolgende gleiche Rollen zusammenführen (z.B. durch Afterthought)
        # Claude API erfordert alternierende user/assistant Rollen
        if messages and messages[-1]['role'] == role:
            messages[-1]['content'] += "\n\n" + row[0]
            merged_count += 1
        else:
            messages.append({
                'role': role,
                'content': row[0]
            })
    
    # Leading assistant messages (z.B. Greeting) werden NICHT entfernt,
    # damit die KI weiß, dass sie bereits begrüßt hat.
    # Die Claude API akzeptiert Messages die mit assistant beginnen,
    # wenn der system-Parameter separat übergeben wird.

    if merged_count > 0:
        log.info("Context-History: %d Nachrichten zusammengeführt. Final: %d msgs",
                 merged_count, len(messages))
    else:
        log.debug("Context-History: Final %d msgs", len(messages))
    
    conn.close()
    return messages


def save_message(message: str, is_user: bool, character_name: str = 'Assistant',
                 session_id: int = None, persona_id: str = 'default') -> int:
    """
    Speichert eine Nachricht in der Datenbank
    
    Args:
        message: Der Nachrichtentext
        is_user: True wenn Nachricht vom User, False wenn vom Bot
        character_name: Name des Charakters
        session_id: ID der Session (wenn None, wird die neueste Session verwendet)
        persona_id: ID der Persona
        
    Returns:
        ID der eingefügten Nachricht
    """
    conn = get_db_connection(persona_id)
    cursor = conn.cursor()
    
    if session_id is None:
        cursor.execute(sql('chat.get_latest_session_id'))
        result = cursor.fetchone()
        if result:
            session_id = result[0]
        else:
            conn.close()
            session_id = create_session(persona_id=persona_id)
            conn = get_db_connection(persona_id)
            cursor = conn.cursor()
    
    cursor.execute(sql('chat.insert_message'), (session_id, message, is_user, character_name))
    
    # Update session's updated_at timestamp
    cursor.execute(sql('chat.update_session_timestamp'), (session_id,))
    
    message_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return message_id


def clear_chat_history(persona_id: str = 'default'):
    """Löscht die gesamte Chat-Historie einer Persona"""
    conn = get_db_connection(persona_id)
    cursor = conn.cursor()
    cursor.execute(sql('chat.delete_all_messages'))
    cursor.execute(sql('chat.delete_all_sessions'))
    conn.commit()
    conn.close()


def get_total_message_count(persona_id: str = 'default') -> int:
    """Gibt die Gesamtanzahl aller Nachrichten zurück (über alle Sessions einer Persona)"""
    conn = get_db_connection(persona_id)
    cursor = conn.cursor()
    cursor.execute(sql('chat.get_total_message_count'))
    count = cursor.fetchone()[0]
    conn.close()
    return count


# ===== SESSION MANAGEMENT =====

def create_session(title: str = "Neue Konversation", persona_id: str = "default") -> int:
    """
    Erstellt eine neue Chat-Session
    
    Args:
        title: Titel der Session
        persona_id: ID der Persona für diese Session
        
    Returns:
        ID der neuen Session
    """
    conn = get_db_connection(persona_id)
    cursor = conn.cursor()
    
    cursor.execute(sql('sessions.create_session'), (title, persona_id))
    
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return session_id


def get_all_sessions(persona_id: str = None) -> List[Dict[str, Any]]:
    """
    Holt alle Chat-Sessions, optional gefiltert nach Persona.
    Wenn persona_id=None, werden Sessions aus ALLEN Persona-DBs aggregiert.
    
    Args:
        persona_id: Wenn angegeben, nur Sessions dieser Persona
        
    Returns:
        Liste von Session-Dictionaries, sortiert nach updated_at (neueste zuerst)
    """
    if persona_id is not None:
        # Einzelne Persona-DB abfragen
        return _get_sessions_from_db(persona_id)
    
    # Alle Persona-DBs aggregieren
    all_sessions = []
    for pid in get_all_persona_ids():
        sessions = _get_sessions_from_db(pid)
        all_sessions.extend(sessions)
    
    # Nach updated_at sortieren (neueste zuerst)
    all_sessions.sort(key=lambda s: s.get('updated_at', ''), reverse=True)
    return all_sessions


def _get_sessions_from_db(persona_id: str) -> List[Dict[str, Any]]:
    """Holt alle Sessions aus einer bestimmten Persona-DB"""
    try:
        conn = get_db_connection(persona_id)
        cursor = conn.cursor()
        
        cursor.execute(sql('sessions.get_all_sessions'))
        
        sessions = []
        for row in cursor.fetchall():
            sessions.append({
                'id': row[0],
                'title': row[1],
                'created_at': row[2],
                'updated_at': row[3],
                'persona_id': row[4] if row[4] else persona_id
            })
        
        conn.close()
        return sessions
    except Exception as e:
        log.error("Fehler beim Laden der Sessions für Persona %s: %s", persona_id, e)
        return []


def get_persona_session_summary() -> List[Dict[str, Any]]:
    """
    Gibt eine Zusammenfassung der Sessions pro Persona zurück
    (aggregiert über alle Persona-DBs)
    
    Returns:
        Liste von Dictionaries mit persona_id, session_count, last_updated
    """
    summary = []
    
    for pid in get_all_persona_ids():
        try:
            conn = get_db_connection(pid)
            cursor = conn.cursor()
            
            cursor.execute(sql('sessions.get_session_count_summary'))
            
            row = cursor.fetchone()
            conn.close()
            
            if row and row[0] > 0:
                summary.append({
                    'persona_id': pid,
                    'session_count': row[0],
                    'last_updated': row[1]
                })
        except Exception:
            continue
    
    # Nach last_updated sortieren
    summary.sort(key=lambda s: s.get('last_updated', '') or '', reverse=True)
    return summary


def get_session_persona_id(session_id: int, persona_id: str = 'default') -> str:
    """
    Gibt die persona_id einer Session zurück.
    
    Args:
        session_id: ID der Session
        persona_id: ID der Persona (bestimmt welche DB abgefragt wird)
        
    Returns:
        persona_id als String oder 'default'
    """
    conn = get_db_connection(persona_id)
    cursor = conn.cursor()
    
    cursor.execute(sql('sessions.get_session_persona_id'), (session_id,))
    row = cursor.fetchone()
    conn.close()
    
    return row[0] if row and row[0] else persona_id


def get_session(session_id: int, persona_id: str = 'default') -> Dict[str, Any]:
    """
    Holt eine spezifische Session
    
    Args:
        session_id: ID der Session
        persona_id: ID der Persona
        
    Returns:
        Session-Dictionary oder None
    """
    conn = get_db_connection(persona_id)
    cursor = conn.cursor()
    
    cursor.execute(sql('sessions.get_session_by_id'), (session_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            'id': row[0],
            'title': row[1],
            'created_at': row[2],
            'updated_at': row[3],
            'persona_id': row[4] if row[4] else persona_id
        }
    return None


def update_session_title(session_id: int, title: str, persona_id: str = 'default') -> bool:
    """
    Aktualisiert den Titel einer Session
    
    Args:
        session_id: ID der Session
        title: Neuer Titel
        persona_id: ID der Persona
        
    Returns:
        True bei Erfolg, False bei Fehler
    """
    try:
        conn = get_db_connection(persona_id)
        cursor = conn.cursor()
        
        cursor.execute(sql('sessions.update_session_title'), (title, session_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        log.error("Fehler beim Aktualisieren des Session-Titels: %s", e)
        return False


def delete_session(session_id: int, persona_id: str = 'default') -> bool:
    """
    Löscht eine Session und alle zugehörigen Nachrichten
    
    Args:
        session_id: ID der Session
        persona_id: ID der Persona
        
    Returns:
        True bei Erfolg, False bei Fehler
    """
    try:
        conn = get_db_connection(persona_id)
        cursor = conn.cursor()
        
        # Nachrichten werden automatisch gelöscht (CASCADE)
        cursor.execute(sql('sessions.delete_session'), (session_id,))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        log.error("Fehler beim Löschen der Session: %s", e)
        return False


def get_current_session_id(persona_id: str = 'default') -> int:
    """
    Holt die ID der aktuellen (neuesten) Session einer Persona
    
    Args:
        persona_id: ID der Persona
        
    Returns:
        Session-ID oder None wenn keine Session existiert
    """
    conn = get_db_connection(persona_id)
    cursor = conn.cursor()
    
    cursor.execute(sql('sessions.get_current_session_id'))
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result else None


# ===== MEMORY MANAGEMENT =====

def save_memory(session_id: int, content: str, persona_id: str = 'default',
                start_message_id: int = None, end_message_id: int = None) -> int:
    """
    Speichert eine Memory-Zusammenfassung
    
    Args:
        session_id: ID der Session (kann None sein)
        content: Inhalt der Zusammenfassung
        persona_id: ID der Persona (bestimmt welche DB verwendet wird)
        start_message_id: Erste Nachrichten-ID die diese Memory abdeckt
        end_message_id: Letzte Nachrichten-ID die diese Memory abdeckt
        
    Returns:
        ID der gespeicherten Memory
    """
    conn = get_db_connection(persona_id)
    cursor = conn.cursor()
    
    cursor.execute(sql('memories.insert_memory'),
                   (session_id, persona_id, content, start_message_id, end_message_id))
    
    memory_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return memory_id


def get_all_memories(active_only: bool = False, persona_id: str = None) -> List[Dict[str, Any]]:
    """
    Holt alle Memories einer Persona
    
    Args:
        active_only: Nur aktive Memories zurückgeben
        persona_id: Persona-ID (bestimmt welche DB abgefragt wird)
        
    Returns:
        Liste von Memory-Dictionaries, sortiert nach Datum (neueste zuerst)
    """
    if persona_id is None:
        persona_id = 'default'
    
    conn = get_db_connection(persona_id)
    cursor = conn.cursor()
    
    if active_only:
        cursor.execute(sql('memories.get_active_memories'))
    else:
        cursor.execute(sql('memories.get_all_memories'))
    
    memories = []
    for row in cursor.fetchall():
        memories.append({
            'id': row[0],
            'session_id': row[1],
            'persona_id': row[2],
            'content': row[3],
            'created_at': row[4],
            'is_active': bool(row[5])
        })
    
    conn.close()
    return memories


def get_active_memories(persona_id: str = None) -> List[Dict[str, Any]]:
    """
    Holt alle aktiven Memories für die Verwendung im Chat
    
    Args:
        persona_id: Persona-ID
        
    Returns:
        Liste von aktiven Memory-Dictionaries
    """
    return get_all_memories(active_only=True, persona_id=persona_id)


def update_memory(memory_id: int, content: str, persona_id: str = 'default') -> bool:
    """
    Aktualisiert den Inhalt einer Memory
    
    Args:
        memory_id: ID der Memory
        content: Neuer Inhalt
        persona_id: ID der Persona
        
    Returns:
        True bei Erfolg, False bei Fehler
    """
    try:
        conn = get_db_connection(persona_id)
        cursor = conn.cursor()
        
        cursor.execute(sql('memories.update_memory_content'), (content, memory_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        log.error("Fehler beim Aktualisieren der Memory: %s", e)
        return False


def delete_memory(memory_id: int, persona_id: str = 'default') -> bool:
    """
    Löscht eine Memory und aktualisiert den Memory-Marker der zugehörigen Session.
    
    Args:
        memory_id: ID der Memory
        persona_id: ID der Persona
        
    Returns:
        True bei Erfolg, False bei Fehler
    """
    try:
        conn = get_db_connection(persona_id)
        cursor = conn.cursor()
        
        # Hole session_id der Memory bevor wir löschen
        cursor.execute(sql('memories.get_memory_session_id'), (memory_id,))
        row = cursor.fetchone()
        session_id = row[0] if row else None
        
        # Memory löschen
        cursor.execute(sql('memories.delete_memory'), (memory_id,))
        
        # Memory-Marker der Session neu berechnen basierend auf verbleibenden Memories
        if session_id is not None:
            cursor.execute(sql('memories.get_max_end_message_id'), (session_id,))
            max_row = cursor.fetchone()
            new_marker = max_row[0] if max_row and max_row[0] else None
            
            cursor.execute(sql('memories.update_session_memory_marker'), (new_marker, session_id))
            log.info("Memory-Marker nach Löschen neu berechnet: session=%s, new_marker=%s", session_id, new_marker)
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        log.error("Fehler beim Löschen der Memory: %s", e)
        return False


def toggle_memory_status(memory_id: int, persona_id: str = 'default') -> bool:
    """
    Schaltet den Aktiv-Status einer Memory um
    
    Args:
        memory_id: ID der Memory
        persona_id: ID der Persona
        
    Returns:
        True bei Erfolg, False bei Fehler
    """
    try:
        conn = get_db_connection(persona_id)
        cursor = conn.cursor()
        
        cursor.execute(sql('memories.toggle_memory_status'), (memory_id,))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        log.error("Fehler beim Umschalten des Memory-Status: %s", e)
        return False


def get_session_message_count(session_id: int = None, persona_id: str = 'default') -> int:
    """
    Gibt die Anzahl der Nachrichten in einer Session zurück
    
    Args:
        session_id: ID der Session (wenn None, wird die neueste Session verwendet)
        persona_id: ID der Persona
        
    Returns:
        Anzahl der Nachrichten
    """
    return get_message_count(session_id=session_id, persona_id=persona_id)


def set_last_memory_message_id(session_id: int, message_id: int, persona_id: str = 'default') -> bool:
    """
    Setzt den Memory-Marker für eine Session (letzte Nachrichten-ID, bis zu der
    eine Erinnerung erstellt wurde).
    
    Args:
        session_id: ID der Session
        message_id: ID der letzten erfassten Nachricht
        persona_id: ID der Persona
        
    Returns:
        True bei Erfolg
    """
    try:
        conn = get_db_connection(persona_id)
        cursor = conn.cursor()
        cursor.execute(sql('memories.set_last_memory_message_id'), (message_id, session_id))
        conn.commit()
        conn.close()
        log.info("Memory-Marker gesetzt: session=%s, last_msg_id=%s", session_id, message_id)
        return True
    except Exception as e:
        log.error("Fehler beim Setzen des Memory-Markers: %s", e)
        return False


def get_last_memory_message_id(session_id: int, persona_id: str = 'default') -> Optional[int]:
    """
    Holt den Memory-Marker für eine Session.
    
    Args:
        session_id: ID der Session
        persona_id: ID der Persona
        
    Returns:
        Letzte erfasste Nachrichten-ID oder None
    """
    conn = get_db_connection(persona_id)
    cursor = conn.cursor()
    cursor.execute(sql('memories.get_last_memory_message_id'), (session_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row and row[0] else None


def get_max_message_id(session_id: int, persona_id: str = 'default') -> Optional[int]:
    """
    Holt die höchste Nachrichten-ID einer Session.
    
    Args:
        session_id: ID der Session
        persona_id: ID der Persona
        
    Returns:
        Höchste Message-ID oder None
    """
    conn = get_db_connection(persona_id)
    cursor = conn.cursor()
    cursor.execute(sql('chat.get_max_message_id'), (session_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row and row[0] else None


def get_user_message_count_since_marker(session_id: int, persona_id: str = 'default') -> int:
    """
    Zählt die User-Nachrichten seit dem letzten Memory-Marker.
    Wenn kein Marker gesetzt ist, werden alle User-Nachrichten gezählt.
    
    Args:
        session_id: ID der Session
        persona_id: ID der Persona
        
    Returns:
        Anzahl der User-Nachrichten seit Marker
    """
    conn = get_db_connection(persona_id)
    cursor = conn.cursor()
    
    # Hole Marker
    cursor.execute(sql('chat.get_session_memory_marker'), (session_id,))
    marker_row = cursor.fetchone()
    marker = marker_row[0] if marker_row and marker_row[0] else None
    
    if marker:
        cursor.execute(sql('chat.count_user_messages_since_marker'), (session_id, marker))
    else:
        cursor.execute(sql('chat.count_all_user_messages'), (session_id,))
    
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_messages_since_marker(session_id: int, persona_id: str = 'default', limit: int = 100) -> Dict[str, Any]:
    """
    Holt nur die Nachrichten NACH dem letzten Memory-Marker.
    Wenn kein Marker gesetzt ist, werden alle Nachrichten zurückgegeben.
    Begrenzt auf max `limit` Nachrichten (Standard: 100).
    
    Args:
        session_id: ID der Session
        persona_id: ID der Persona
        limit: Maximale Anzahl Nachrichten (Standard: 100)
        
    Returns:
        Dict mit 'messages' (Liste), 'total' (Gesamtzahl seit Marker), 'truncated' (bool)
    """
    conn = get_db_connection(persona_id)
    cursor = conn.cursor()
    
    # Hole Marker
    cursor.execute(sql('chat.get_session_memory_marker'), (session_id,))
    marker_row = cursor.fetchone()
    marker = marker_row[0] if marker_row and marker_row[0] else None
    
    # Zähle Gesamtzahl seit Marker
    if marker:
        cursor.execute(sql('chat.get_messages_since_marker_count'), (session_id, marker))
    else:
        cursor.execute(sql('chat.get_all_messages_count'), (session_id,))
    total = cursor.fetchone()[0]
    truncated = total > limit
    
    # Hole die letzten `limit` Nachrichten seit Marker (die neuesten, damit nichts Wichtiges fehlt)
    if marker:
        cursor.execute(sql('chat.get_messages_since_marker'), (session_id, marker, limit))
    else:
        cursor.execute(sql('chat.get_all_messages_limited'), (session_id, limit))
    
    # Umkehren für chronologische Reihenfolge
    messages = []
    for row in reversed(cursor.fetchall()):
        messages.append({
            'id': row[0],
            'message': row[1],
            'is_user': bool(row[2]),
            'timestamp': row[3],
            'character_name': row[4]
        })
    
    conn.close()
    return {'messages': messages, 'total': total, 'truncated': truncated}
