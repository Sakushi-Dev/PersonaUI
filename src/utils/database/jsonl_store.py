"""
JSONL Storage Engine für PersonaUI.

Low-Level Storage Engine für JSONL-Dateien mit Thread-Safety,
Atomic Writes und effizienter Pagination.

Diese Engine ist das Fundament für den SQLite→JSONL Umbau.
Alle Operationen sind thread-safe und unterstützen gleichzeitige Zugriffe.

Verwendung:
    from utils.database.jsonl_store import append, read_all, next_id
    
    # Record hinzufügen
    record = {'id': next_id('sessions.jsonl'), 'name': 'test'}
    append('sessions.jsonl', record)
    
    # Alle Records lesen
    sessions = read_all('sessions.jsonl')
"""

import json
import os
import fcntl
import threading
from typing import List, Dict, Any, Callable, Optional, Tuple

from ..logger import log

# ---------------------------------------------------------------------------
# Globaler Lock-State für Thread-Safety
# ---------------------------------------------------------------------------
_file_locks: Dict[str, threading.Lock] = {}
_lock_registry_mutex = threading.Lock()

# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _get_file_lock(filepath: str) -> threading.Lock:
    """
    Gibt ein Thread-Lock für den gegebenen Dateipfad zurück.
    Erstellt ein neues Lock falls noch keins existiert.
    Thread-safe über globalen Registry-Mutex.
    """
    normalized_path = os.path.realpath(filepath)
    
    with _lock_registry_mutex:
        if normalized_path not in _file_locks:
            _file_locks[normalized_path] = threading.Lock()
        return _file_locks[normalized_path]


def _read_lines_raw(f) -> Tuple[int, str]:
    """
    Generator für das zeilenweise Lesen einer Datei.
    Überspringt leere Zeilen und gibt (line_num, stripped_line) zurück.
    """
    for line_num, line in enumerate(f, 1):
        stripped = line.strip()
        if not stripped:
            continue
        yield line_num, stripped


def _parse_line(line: str, filepath: str, line_num: int) -> Optional[Dict[str, Any]]:
    """
    Parst eine JSON-Zeile und behandelt Fehler graceful.
    Gibt None zurück bei korrupter Zeile (mit Warning-Log).
    """
    try:
        return json.loads(line)
    except json.JSONDecodeError as e:
        log.warning("Korrupte Zeile %d in %s: %s", line_num, filepath, e)
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def append(filepath: str, record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Hängt ein JSON-Objekt als neue Zeile an eine JSONL-Datei an.
    Erstellt die Datei falls nicht vorhanden.
    
    Args:
        filepath: Pfad zur JSONL-Datei
        record: Dictionary das als JSON-Zeile geschrieben wird
    
    Returns:
        Das geschriebene Record (Kopie des Eingabe-Records)
    
    Thread-safe: Exclusive Write-Lock
    """
    file_lock = _get_file_lock(filepath)
    
    with file_lock:
        # Verzeichnis erstellen falls nötig
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        
        with open(filepath, 'a', encoding='utf-8') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                json_line = json.dumps(record, ensure_ascii=False, separators=(',', ':'))
                f.write(json_line + '\n')
                f.flush()
                os.fsync(f.fileno())  # Ensure data is written to disk
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    
    return record.copy()


def read_all(filepath: str) -> List[Dict[str, Any]]:
    """
    Liest alle Zeilen einer JSONL-Datei.
    Überspringt korrupte Zeilen mit Warning-Log.
    
    Args:
        filepath: Pfad zur JSONL-Datei
    
    Returns:
        Liste aller Records. Leere Liste wenn Datei nicht existiert.
    
    Thread-safe: Shared Read-Lock
    """
    if not os.path.exists(filepath):
        return []
    
    file_lock = _get_file_lock(filepath)
    records = []
    
    with file_lock:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    for line_num, line in _read_lines_raw(f):
                        record = _parse_line(line, filepath, line_num)
                        if record is not None:
                            records.append(record)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except IOError as e:
            log.warning("Fehler beim Lesen von %s: %s", filepath, e)
            return []
    
    return records


def read_filtered(filepath: str, filter_fn: Callable[[Dict[str, Any]], bool]) -> List[Dict[str, Any]]:
    """
    Liest alle Zeilen einer JSONL-Datei und gibt nur die zurück,
    wo filter_fn(record) True ist.
    
    Args:
        filepath: Pfad zur JSONL-Datei
        filter_fn: Funktion die für jeden Record aufgerufen wird
    
    Returns:
        Liste der Records die den Filter passieren
    
    Thread-safe: Shared Read-Lock
    """
    if not os.path.exists(filepath):
        return []
    
    file_lock = _get_file_lock(filepath)
    records = []
    
    with file_lock:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    for line_num, line in _read_lines_raw(f):
                        record = _parse_line(line, filepath, line_num)
                        if record is not None:
                            try:
                                if filter_fn(record):
                                    records.append(record)
                            except Exception as e:
                                log.warning("Filter-Fehler bei Record %d in %s: %s", line_num, filepath, e)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except IOError as e:
            log.warning("Fehler beim Lesen von %s: %s", filepath, e)
            return []
    
    return records


def read_last_n(filepath: str, n: int) -> List[Dict[str, Any]]:
    """
    Liest die letzten N Zeilen einer JSONL-Datei effizient.
    Verwendet chunk-basiertes Rückwärts-Lesen vom Dateiende.
    
    Args:
        filepath: Pfad zur JSONL-Datei
        n: Anzahl der letzten Zeilen
    
    Returns:
        Liste der letzten N Records in chronologischer Reihenfolge (älteste zuerst)
    
    Thread-safe: Shared Read-Lock
    """
    if not os.path.exists(filepath) or n <= 0:
        return []
    
    file_lock = _get_file_lock(filepath)
    
    with file_lock:
        try:
            with open(filepath, 'rb') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    # Dateigröße ermitteln
                    f.seek(0, 2)  # Seek to end
                    file_size = f.tell()
                    
                    if file_size == 0:
                        return []
                    
                    # Chunk-basiert rückwärts lesen
                    chunk_size = 8192  # 8KB chunks
                    lines = []
                    buffer = b''
                    pos = file_size
                    
                    while pos > 0 and len(lines) <= n:
                        # Nächsten Chunk bestimmen
                        read_size = min(chunk_size, pos)
                        pos -= read_size
                        
                        # Chunk lesen und zu Buffer hinzufügen
                        f.seek(pos)
                        chunk = f.read(read_size)
                        buffer = chunk + buffer
                        
                        # Lines aus Buffer extrahieren
                        while b'\n' in buffer and len(lines) <= n:
                            buffer, line = buffer.rsplit(b'\n', 1)
                            if line.strip():  # Skip empty lines
                                lines.append(line.decode('utf-8').strip())
                    
                    # Restlichen Buffer verarbeiten falls vorhanden
                    if buffer.strip() and len(lines) <= n:
                        lines.append(buffer.decode('utf-8').strip())
                    
                    # Nur die letzten n Zeilen nehmen und umkehren für chronologische Reihenfolge
                    lines = lines[:n]
                    lines.reverse()
                    
                    # JSON parsing
                    records = []
                    for i, line in enumerate(lines):
                        record = _parse_line(line, filepath, i + 1)  # Approximation der line_num
                        if record is not None:
                            records.append(record)
                    
                    return records
                
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        
        except IOError as e:
            log.warning("Fehler beim Lesen der letzten %d Zeilen von %s: %s", n, filepath, e)
            return []


def read_paginated(filepath: str, limit: int, offset: int, reverse: bool = False) -> List[Dict[str, Any]]:
    """
    Liest eine Seite von Records mit Pagination-Support.
    
    Args:
        filepath: Pfad zur JSONL-Datei
        limit: Maximale Anzahl Records pro Seite
        offset: Anzahl Records zu überspringen
        reverse: Wenn True, neueste zuerst (erfordert vollständiges Laden)
    
    Returns:
        Liste der Records für die angegebene Seite
    
    Thread-safe: Shared Read-Lock
    """
    if not os.path.exists(filepath) or limit <= 0:
        return []
    
    if reverse:
        # Für reverse pagination müssen wir alles laden
        all_records = read_all(filepath)
        all_records.reverse()
        return all_records[offset:offset + limit]
    
    # Forward pagination mit streaming
    file_lock = _get_file_lock(filepath)
    records = []
    skipped = 0
    collected = 0
    
    with file_lock:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    for line_num, line in _read_lines_raw(f):
                        record = _parse_line(line, filepath, line_num)
                        if record is not None:
                            if skipped < offset:
                                skipped += 1
                                continue
                            
                            if collected < limit:
                                records.append(record)
                                collected += 1
                            else:
                                break
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except IOError as e:
            log.warning("Fehler beim paginierten Lesen von %s: %s", filepath, e)
            return []
    
    return records


def count_lines(filepath: str) -> int:
    """
    Zählt alle nicht-leeren Zeilen einer JSONL-Datei effizient.
    Parst NICHT das JSON (Performance).
    
    Args:
        filepath: Pfad zur JSONL-Datei
    
    Returns:
        Anzahl der nicht-leeren Zeilen
    
    Thread-safe: Shared Read-Lock
    """
    if not os.path.exists(filepath):
        return 0
    
    file_lock = _get_file_lock(filepath)
    count = 0
    
    with file_lock:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    for line in f:
                        if line.strip():
                            count += 1
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except IOError as e:
            log.warning("Fehler beim Zählen der Zeilen von %s: %s", filepath, e)
            return 0
    
    return count


def count_filtered(filepath: str, filter_fn: Callable[[Dict[str, Any]], bool]) -> int:
    """
    Zählt Records die ein Filter-Kriterium erfüllen.
    
    Args:
        filepath: Pfad zur JSONL-Datei
        filter_fn: Funktion die für jeden Record aufgerufen wird
    
    Returns:
        Anzahl der Records die den Filter passieren
    
    Thread-safe: Shared Read-Lock
    """
    if not os.path.exists(filepath):
        return 0
    
    file_lock = _get_file_lock(filepath)
    count = 0
    
    with file_lock:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    for line_num, line in _read_lines_raw(f):
                        record = _parse_line(line, filepath, line_num)
                        if record is not None:
                            try:
                                if filter_fn(record):
                                    count += 1
                            except Exception as e:
                                log.warning("Filter-Fehler bei Record %d in %s: %s", line_num, filepath, e)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except IOError as e:
            log.warning("Fehler beim gefilterten Zählen von %s: %s", filepath, e)
            return 0
    
    return count


def rewrite(filepath: str, records: List[Dict[str, Any]]) -> None:
    """
    Überschreibt die gesamte Datei mit neuen Records.
    Verwendet atomic write pattern (temp-Datei + rename).
    
    Args:
        filepath: Pfad zur JSONL-Datei
        records: Liste der Records die geschrieben werden sollen
    
    Thread-safe: Exclusive Write-Lock
    """
    file_lock = _get_file_lock(filepath)
    
    with file_lock:
        # Verzeichnis erstellen falls nötig
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        
        # Temp-Datei im selben Verzeichnis (atomic rename nur im selben Filesystem)
        temp_path = filepath + ".tmp." + str(os.getpid()) + "." + str(threading.get_ident())
        
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    for record in records:
                        json_line = json.dumps(record, ensure_ascii=False, separators=(',', ':'))
                        f.write(json_line + '\n')
                    f.flush()
                    os.fsync(f.fileno())  # Ensure data is written to disk
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            
            # Atomic replace
            os.replace(temp_path, filepath)
            
        except Exception as e:
            # Cleanup temp file on any error
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            raise e


def delete_file(filepath: str) -> None:
    """
    Löscht eine JSONL-Datei.
    Kein Fehler wenn Datei nicht existiert.
    
    Args:
        filepath: Pfad zur JSONL-Datei
    
    Thread-safe: Exclusive Write-Lock
    """
    if not os.path.exists(filepath):
        return
    
    file_lock = _get_file_lock(filepath)
    
    with file_lock:
        try:
            os.remove(filepath)
        except OSError as e:
            log.warning("Fehler beim Löschen von %s: %s", filepath, e)


def ensure_dir(dirpath: str) -> None:
    """
    Erstellt ein Verzeichnis falls nicht vorhanden.
    Keine Locks nötig da os.makedirs thread-safe ist.
    
    Args:
        dirpath: Pfad des Verzeichnisses
    """
    try:
        os.makedirs(dirpath, exist_ok=True)
    except OSError as e:
        log.warning("Fehler beim Erstellen des Verzeichnisses %s: %s", dirpath, e)


def next_id(filepath: str, id_field: str = 'id') -> int:
    """
    Generiert die nächste ID für ein Record.
    Liest die letzte Zeile der Datei und gibt die höchste ID + 1 zurück.
    
    Args:
        filepath: Pfad zur JSONL-Datei
        id_field: Name des ID-Feldes (default: 'id')
    
    Returns:
        Nächste verfügbare ID (bei leerer/nicht-existierender Datei: 1)
    
    Thread-safe: Shared Read-Lock
    """
    if not os.path.exists(filepath):
        return 1
    
    # Versuche zuerst die letzte Zeile zu lesen (effizient)
    last_records = read_last_n(filepath, 1)
    
    if not last_records:
        return 1
    
    last_record = last_records[0]
    
    if id_field in last_record:
        try:
            last_id = int(last_record[id_field])
            return last_id + 1
        except (ValueError, TypeError):
            # Fallback: alle Records lesen und maximum finden
            log.warning("ID-Feld '%s' in letzter Zeile von %s ist nicht int-artig, verwende Fallback", 
                       id_field, filepath)
    
    # Fallback: alle Records durchsuchen
    all_records = read_all(filepath)
    max_id = 0
    
    for record in all_records:
        if id_field in record:
            try:
                record_id = int(record[id_field])
                max_id = max(max_id, record_id)
            except (ValueError, TypeError):
                continue
    
    return max_id + 1
