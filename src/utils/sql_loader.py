"""
SQL Query Loader - Lädt und cached benannte SQL-Abfragen aus .sql Dateien.

Konvention: Queries werden in .sql Dateien durch '-- name: query_name' Kommentare getrennt.
Mehrzeilige Queries werden bis zum nächsten '-- name:' Block zusammengefasst.

Beispiel .sql Datei:
    -- name: get_user
    SELECT * FROM users WHERE id = ?;
    
    -- name: insert_user
    INSERT INTO users (name, email) VALUES (?, ?);

Verwendung:
    from .sql_loader import sql
    
    cursor.execute(sql('chat.get_chat_history'), (session_id, limit, offset))
    cursor.execute(sql('sessions.create_session'), (title, persona_id))
"""

import os
from typing import Dict

# Cache for loaded SQL queries
_query_cache: Dict[str, str] = {}
_files_loaded: set = set()

# Pfad zum sql/ Verzeichnis
SQL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'sql'))


def _load_sql_file(filename: str) -> Dict[str, str]:
    """
    Parsed eine .sql Datei und extrahiert benannte Queries.
    
    Args:
        filename: Name der .sql Datei (ohne Pfad, z.B. 'chat.sql')
        
    Returns:
        Dict von query_name → SQL string
    """
    filepath = os.path.join(SQL_DIR, filename)
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"SQL-Datei nicht gefunden: {filepath}")
    
    queries = {}
    current_name = None
    current_lines = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            stripped = line.strip()
            
            # Neuer Query-Block erkannt
            if stripped.startswith('-- name:'):
                # Vorherigen Query speichern
                if current_name and current_lines:
                    queries[current_name] = '\n'.join(current_lines).strip()
                
                current_name = stripped.replace('-- name:', '').strip()
                current_lines = []
            
            # Skip comment lines (but not '-- name:')
            elif stripped.startswith('--') or stripped.startswith('-- ='):
                continue
            
            # Leere Zeilen und SQL-Zeilen sammeln
            elif current_name is not None:
                if stripped:  # Leere Zeilen innerhalb eines Queries ignorieren
                    current_lines.append(stripped)
    
    # Letzten Query speichern
    if current_name and current_lines:
        queries[current_name] = '\n'.join(current_lines).strip()
    
    return queries


def _ensure_loaded(module: str):
    """Stellt sicher, dass eine SQL-Datei geladen wurde."""
    if module not in _files_loaded:
        filename = f"{module}.sql"
        queries = _load_sql_file(filename)
        for name, query in queries.items():
            _query_cache[f"{module}.{name}"] = query
        _files_loaded.add(module)


def sql(query_path: str) -> str:
    """
    Holt eine benannte SQL-Query.
    
    Args:
        query_path: Pfad im Format 'datei.query_name' 
                    z.B. 'chat.get_chat_history', 'sessions.create_session'
        
    Returns:
        SQL-Query als String
        
    Raises:
        KeyError: Wenn die Query nicht gefunden wurde
        FileNotFoundError: Wenn die SQL-Datei nicht existiert
    """
    if query_path in _query_cache:
        return _query_cache[query_path]
    
    # Module aus dem Pfad extrahieren und laden
    parts = query_path.split('.', 1)
    if len(parts) != 2:
        raise KeyError(f"Ungültiger Query-Pfad: '{query_path}'. Format: 'modul.query_name'")
    
    module, name = parts
    _ensure_loaded(module)
    
    if query_path not in _query_cache:
        raise KeyError(
            f"SQL-Query '{query_path}' nicht gefunden. "
            f"Verfügbare Queries in '{module}': "
            f"{[k.split('.', 1)[1] for k in _query_cache if k.startswith(module + '.')]}"
        )
    
    return _query_cache[query_path]


def load_schema() -> str:
    """
    Lädt das komplette Schema als einzelnen SQL-String.
    Wird für die DB-Initialisierung verwendet.
    
    Returns:
        Gesamtes Schema-SQL
    """
    filepath = os.path.join(SQL_DIR, 'schema.sql')
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def reload():
    """Cache leeren und alle SQL-Dateien neu laden (für Entwicklung/Tests)."""
    _query_cache.clear()
    _files_loaded.clear()


def preload_all():
    """Alle SQL-Dateien vorab laden (optional, für schnelleren Zugriff)."""
    for filename in os.listdir(SQL_DIR):
        if filename.endswith('.sql') and filename != 'schema.sql':
            module = filename.replace('.sql', '')
            _ensure_loaded(module)
