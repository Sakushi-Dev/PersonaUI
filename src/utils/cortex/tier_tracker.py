"""
Cortex Cycle Tracker — Zyklisches Tracking für Cortex-Updates.

Modell:
- User wählt eine Frequenz (Häufig=50%, Mittel=75%, Selten=95%)
- Bei Erreichen der Schwelle: Update auslösen, Zähler reset
- Endlos zyklisch: 0 → Schwelle → Update → 0 → Schwelle → Update → ...
- Progress = messages_since_base / threshold (für Progress Bar)

Persistenz:
- cycle_base wird in src/settings/cycle_state.json gespeichert
- In-Memory Dict dient als Cache für schnellen Zugriff
- Jeder Write (set_cycle_base, reset_session) schreibt sofort auf Disk
- Atomarer Write via tempfile + os.replace (kein Datenverlust bei Crash)
"""

import json
import os
import tempfile
import threading
from typing import Dict

from utils.logger import log

_lock = threading.Lock()

# In-Memory Cache — wird beim ersten Zugriff von Disk geladen
_cycle_state: Dict[str, int] = {}
_loaded = False

# Pfad zur persistenten State-Datei
_STATE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'settings', 'cycle_state.json'
)


def _session_key(persona_id: str, session_id: int) -> str:
    return f"{persona_id}:{session_id}"


def _load_from_disk() -> None:
    """Lädt den cycle_state von Disk in den Cache (einmalig beim ersten Zugriff)."""
    global _cycle_state, _loaded
    if _loaded:
        return
    try:
        if os.path.exists(_STATE_FILE):
            with open(_STATE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict):
                _cycle_state = {k: int(v) for k, v in data.items()}
                log.debug("[tier_tracker] State von Disk geladen: %d Sessions", len(_cycle_state))
    except Exception as e:
        log.warning("[tier_tracker] cycle_state.json konnte nicht geladen werden: %s", e)
        _cycle_state = {}
    _loaded = True


def _save_to_disk() -> None:
    """Schreibt den aktuellen Cache atomar auf Disk."""
    try:
        os.makedirs(os.path.dirname(_STATE_FILE), exist_ok=True)
        # Atomarer Write: tempfile → os.replace
        fd, tmp_path = tempfile.mkstemp(
            dir=os.path.dirname(_STATE_FILE),
            suffix='.tmp'
        )
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(_cycle_state, f, indent=2)
            os.replace(tmp_path, _STATE_FILE)
        except Exception:
            # Tempfile aufräumen bei Fehler
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
    except Exception as e:
        log.warning("[tier_tracker] cycle_state.json konnte nicht gespeichert werden: %s", e)


def get_cycle_base(persona_id: str, session_id: int) -> int:
    """Gibt die cycle_base für die Session zurück (0 wenn nicht vorhanden)."""
    key = _session_key(persona_id, session_id)
    with _lock:
        _load_from_disk()
        return _cycle_state.get(key, 0)


def set_cycle_base(persona_id: str, session_id: int, base: int) -> None:
    """Setzt die cycle_base (nach einem Trigger-Reset). Schreibt sofort auf Disk."""
    key = _session_key(persona_id, session_id)
    with _lock:
        _load_from_disk()
        _cycle_state[key] = base
        _save_to_disk()


def reset_session(persona_id: str, session_id: int) -> None:
    """Setzt den State für eine Session zurück (z.B. bei clear_chat). Schreibt auf Disk."""
    key = _session_key(persona_id, session_id)
    with _lock:
        _load_from_disk()
        if _cycle_state.pop(key, None) is not None:
            _save_to_disk()


def reset_persona(persona_id: str) -> None:
    """Entfernt ALLE cycle_state-Einträge einer Persona (bei Persona-Löschung oder Chat-Reset)."""
    prefix = f"{persona_id}:"
    with _lock:
        _load_from_disk()
        keys_to_remove = [k for k in _cycle_state if k.startswith(prefix)]
        if keys_to_remove:
            for k in keys_to_remove:
                del _cycle_state[k]
            _save_to_disk()
            log.debug("[tier_tracker] %d Einträge für Persona '%s' entfernt", len(keys_to_remove), persona_id)


def reset_all() -> None:
    """Setzt den gesamten State zurück (z.B. bei App-Reset). Löscht die Datei."""
    global _loaded
    with _lock:
        _cycle_state.clear()
        _loaded = True
        try:
            if os.path.exists(_STATE_FILE):
                os.remove(_STATE_FILE)
        except Exception as e:
            log.warning("[tier_tracker] cycle_state.json konnte nicht gelöscht werden: %s", e)


def rebuild_cycle_base(
    persona_id: str,
    session_id: int,
    message_count: int,
    threshold: int
) -> int:
    """
    Fallback: Rekonstruiert die cycle_base wenn die Datei fehlt/korrupt ist.

    Wird nur aufgerufen wenn get_cycle_base() == 0 und message_count > threshold,
    d.h. die Session hat mehr Nachrichten als die Schwelle aber keinen gespeicherten State.

    Args:
        persona_id: Persona-ID
        session_id: Session-ID
        message_count: Aktuelle Gesamtanzahl Nachrichten
        threshold: Aktuelle Schwelle in Nachrichten (z.B. 48)

    Returns:
        Rekonstruierte cycle_base
    """
    if threshold <= 0:
        threshold = 1

    # Wie viele volle Zyklen sind vergangen?
    completed_cycles = message_count // threshold
    cycle_base = completed_cycles * threshold

    # Speichern (In-Memory + Disk)
    set_cycle_base(persona_id, session_id, cycle_base)

    return cycle_base


def get_progress(
    persona_id: str,
    session_id: int,
    message_count: int,
    threshold: int
) -> dict:
    """
    Berechnet den Fortschritt zum nächsten Trigger für die Progress Bar.

    Args:
        persona_id: Persona-ID
        session_id: Session-ID
        message_count: Aktuelle Nachrichtenanzahl
        threshold: Schwelle in Nachrichten (z.B. 48)

    Returns:
        {
            "messages_since_reset": 25,
            "threshold": 48,
            "progress_percent": 52.1,
            "cycle_number": 3
        }
    """
    cycle_base = get_cycle_base(persona_id, session_id)
    messages_since_reset = message_count - cycle_base

    progress = (messages_since_reset / threshold * 100) if threshold > 0 else 0
    progress = min(progress, 100.0)

    cycle_number = (cycle_base // threshold + 1) if threshold > 0 else 1

    return {
        "messages_since_reset": messages_since_reset,
        "threshold": threshold,
        "progress_percent": round(progress, 1),
        "cycle_number": cycle_number
    }
