"""
Cortex Trigger Checker — Prüft ob ein Cortex-Update ausgelöst werden soll.

Der User wählt eine Frequenz (Häufig=50%, Mittel=75%, Selten=95%).
Bei Erreichen der Schwelle: Update → Zähler reset → zyklisch wiederholen.
"""

import threading
import math
import json
import os
from typing import Dict, Optional

from utils.logger import log
from utils.database import get_message_count
from utils.cortex.tier_tracker import (
    get_cycle_base, set_cycle_base, rebuild_cycle_base, get_progress
)


# ─── Konstanten ──────────────────────────────────────────────────────────────

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Frequenz-Mapping
FREQUENCIES = {
    "frequent": {"label": "Häufig",  "percent": 50},
    "medium":   {"label": "Mittel",  "percent": 75},
    "rare":     {"label": "Selten",  "percent": 95},
}
DEFAULT_FREQUENCY = "medium"


# ─── Hilfsfunktionen ────────────────────────────────────────────────────────

def _load_cortex_config() -> dict:
    """
    Lädt die Cortex-Konfiguration aus cortex_settings.json.

    Returns:
        {"enabled": True, "frequency": "medium"}
    """
    settings_path = os.path.join(_BASE_DIR, 'settings', 'cortex_settings.json')
    defaults = {"enabled": True, "frequency": DEFAULT_FREQUENCY}

    try:
        if os.path.exists(settings_path):
            with open(settings_path, 'r', encoding='utf-8') as f:
                saved = json.load(f)
            return {**defaults, **saved}
    except Exception:
        pass
    return defaults


def _get_context_limit() -> int:
    """
    Liest den User-contextLimit (ungeclampt) aus user_settings.json.

    Verwendet den User-Wert für Cortex-Berechnung, nicht den
    geclampten Server-Wert. Nur Minimum 10, kein Maximum-Clamp.
    """
    settings_path = os.path.join(_BASE_DIR, 'settings', 'user_settings.json')
    defaults_path = os.path.join(_BASE_DIR, 'settings', 'defaults.json')

    # Zuerst User-Settings versuchen
    raw = None
    try:
        if os.path.exists(settings_path):
            with open(settings_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            raw = data.get('contextLimit')
    except Exception:
        pass

    # Fallback auf Defaults
    if raw is None:
        try:
            if os.path.exists(defaults_path):
                with open(defaults_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                raw = data.get('contextLimit', '100')
        except Exception:
            raw = '100'

    try:
        return max(10, int(raw))
    except (TypeError, ValueError):
        return 100


def _calculate_threshold(context_limit: int, frequency: str) -> int:
    """
    Berechnet die Nachrichtenanzahl-Schwelle.

    Args:
        context_limit: User-contextLimit (z.B. 65)
        frequency: "frequent" | "medium" | "rare"

    Returns:
        Schwelle in Nachrichten (z.B. 48)
    """
    freq_data = FREQUENCIES.get(frequency, FREQUENCIES[DEFAULT_FREQUENCY])
    return math.floor(context_limit * (freq_data["percent"] / 100))


# ─── Hauptfunktion ──────────────────────────────────────────────────────────

def check_and_trigger_cortex_update(
    persona_id: str,
    session_id: int
) -> Optional[dict]:
    """
    Prüft ob ein Cortex-Update getriggert werden soll.
    Gibt Progress-Daten zurück für das done-Event.

    Wird nach jedem erfolgreichen Chat-Response aufgerufen (vor done-yield).

    Args:
        persona_id: Aktive Persona-ID
        session_id: Aktuelle Session-ID

    Returns:
        {
            "triggered": bool,
            "progress": {
                "messages_since_reset": 25,
                "threshold": 48,
                "progress_percent": 52.1,
                "cycle_number": 3
            },
            "frequency": "medium"
        }
        Oder None wenn Cortex deaktiviert.
    """
    # 1. Cortex aktiviert?
    config = _load_cortex_config()
    if not config["enabled"]:
        return None

    frequency = config.get("frequency", DEFAULT_FREQUENCY)
    context_limit = _get_context_limit()
    threshold = _calculate_threshold(context_limit, frequency)

    if threshold <= 0:
        return None

    # 2. Nachrichtenanzahl holen
    message_count = get_message_count(session_id=session_id, persona_id=persona_id)
    if message_count == 0:
        return None

    # 3. cycle_base laden (oder rebuilden nach Restart)
    cycle_base = get_cycle_base(persona_id, session_id)

    # Rebuild wenn cycle_base noch nicht initialisiert (= 0)
    # und die Session schon Nachrichten hat
    if cycle_base == 0 and message_count > threshold:
        cycle_base = rebuild_cycle_base(persona_id, session_id, message_count, threshold)

    # 4. Prüfen ob Schwelle erreicht
    messages_since_reset = message_count - cycle_base
    triggered = messages_since_reset >= threshold

    if triggered:
        # Reset: neuer Zyklus beginnt
        set_cycle_base(persona_id, session_id, message_count)

        log.info(
            "Cortex-Update getriggert: %d Nachrichten seit Reset (Schwelle: %d, "
            "Frequenz: %s, contextLimit: %d) — Persona: %s, Session: %s",
            messages_since_reset, threshold, frequency, context_limit,
            persona_id, session_id
        )

        # Background-Update starten
        _start_background_cortex_update(persona_id, session_id)

    # 5. Progress-Daten berechnen (nach eventuellem Reset!)
    progress = get_progress(persona_id, session_id, message_count, threshold)

    return {
        "triggered": triggered,
        "progress": progress,
        "frequency": frequency
    }


# ─── Background-Update ──────────────────────────────────────────────────────

_active_updates: Dict[str, threading.Thread] = {}
_active_lock = threading.Lock()


def _start_background_cortex_update(persona_id: str, session_id: int) -> None:
    """
    Startet das Cortex-Update in einem Background-Thread.
    Nur ein Update pro Persona gleichzeitig (via _active_updates Dict).
    """
    with _active_lock:
        existing = _active_updates.get(persona_id)
        if existing and existing.is_alive():
            log.info("Cortex-Update übersprungen: läuft bereits — Persona: %s", persona_id)
            return

        def _run_update():
            try:
                from utils.cortex.update_service import CortexUpdateService
                service = CortexUpdateService()
                result = service.execute_update(
                    persona_id=persona_id,
                    session_id=session_id
                )
                if result.get('success'):
                    log.info("Cortex-Update abgeschlossen: %d Tool-Calls — Persona: %s",
                             result.get('tool_calls_count', 0), persona_id)
                else:
                    log.warning("Cortex-Update fehlgeschlagen: %s — Persona: %s",
                                result.get('error', '?'), persona_id)
            except Exception as e:
                log.error("Cortex-Update Exception: %s", e)
            finally:
                # Thread aus Tracking entfernen
                with _active_lock:
                    _active_updates.pop(persona_id, None)

        thread_name = f"cortex-update-{persona_id}"
        thread = threading.Thread(target=_run_update, name=thread_name, daemon=True)
        _active_updates[persona_id] = thread
        thread.start()
