# Schritt 3B: Aktivierungsstufen-Logik

> **⚠️ KORREKTUR v3:** Tier-Modell grundlegend geändert. Die 3 Stufen sind **keine sequentiellen Trigger**, sondern **3 auswählbare Frequenz-Optionen**. Der User wählt EINE Frequenz. Nach jedem Trigger wird der Zähler auf 0 zurückgesetzt.

## Übersicht

Das Cortex-System aktualisiert seine Dateien (`memory.md`, `soul.md`, `relationship.md`) nicht bei jeder Nachricht, sondern an einem definierten **Schwellenwert** innerhalb der Konversation. Dieser Schwellenwert wird als Prozentsatz des `contextLimit` berechnet — der vom User eingestellten maximalen Kontext-Länge (Nachrichten).

**Alle 3 Cortex-Dateien sind IMMER im System-Prompt** (via Computed Placeholders). Die Frequenz-Einstellung bestimmt nur **WIE OFT die KI die Dateien aktualisiert** — nicht welche Dateien geladen werden.

### Die 3 Frequenz-Optionen

Der User wählt im CortexOverlay **eine** von 3 Frequenzen:

| Option | Frontend-Label | Schwelle | Bedeutung |
|:------:|:--------------:|:--------:|-----------|
| 🔥 | **Häufig** | 50% | Update bei jeder Hälfte des Kontexts |
| ⚡ | **Mittel** | 75% | Update bei 3/4 des Kontexts (Default) |
| 🌙 | **Selten** | 95% | Update erst kurz vor Kontext-Ende |

### Funktionsprinzip

```
1. User wählt Frequenz: "Mittel" (75%)
2. contextLimit = 65 → Schwelle = floor(65 × 0.75) = 48 Nachrichten
3. Konversation läuft...
4. Bei Nachricht 48: → TRIGGER → Cortex-Update → Zähler reset auf 0
5. Konversation läuft weiter...
6. Bei Nachricht 96 (48+48): → TRIGGER → Cortex-Update → Zähler reset auf 0
7. ...und so weiter, endlos zyklisch
```

```
Nachricht:  0        48        96        144       192
            ├────────┤─────────┤─────────┤─────────┤────
            │ Zyklus 1│ Zyklus 2│ Zyklus 3│ Zyklus 4│
            └──►UPD   └──►UPD   └──►UPD   └──►UPD
```

Die Trigger-Prüfung findet **server-seitig** in `chat.py` statt, **vor** dem `done`-Event (damit Progress-Info im SSE-Payload enthalten sein kann). Das Cortex-Update selbst läuft als **separater, nicht-blockierender Background-Request** via `tool_use` (dokumentiert in Schritt 3A).

---

## 1. Schwellenwert-Berechnung

### 1.1 Formel

```
threshold_messages = floor(contextLimit × (frequency_percent / 100))
```

Es gibt nur **einen** aktiven Schwellenwert — den der gewählten Frequenz.

### 1.2 Berechnungsbeispiele

**Beispiel 1: `contextLimit = 65` (Default)**

| Frequenz | % | Berechnung | Trigger alle # Nachrichten |
|:--------:|:---:|-----------|:--------------------------:|
| Häufig | 50% | `floor(65 × 0.50)` | alle **32** |
| Mittel | 75% | `floor(65 × 0.75)` | alle **48** |
| Selten | 95% | `floor(65 × 0.95)` | alle **61** |

**Beispiel 2: `contextLimit = 200`**

| Frequenz | % | Berechnung | Trigger alle # Nachrichten |
|:--------:|:---:|-----------|:--------------------------:|
| Häufig | 50% | `floor(200 × 0.50)` | alle **100** |
| Mittel | 75% | `floor(200 × 0.75)` | alle **150** |
| Selten | 95% | `floor(200 × 0.95)` | alle **190** |

**Beispiel 3: `contextLimit = 10` (Minimum)**

| Frequenz | % | Berechnung | Trigger alle # Nachrichten |
|:--------:|:---:|-----------|:--------------------------:|
| Häufig | 50% | `floor(10 × 0.50)` | alle **5** |
| Mittel | 75% | `floor(10 × 0.75)` | alle **7** |
| Selten | 95% | `floor(10 × 0.95)` | alle **9** |

### 1.3 `contextLimit` — User-Wert (ungeclampt)

Die Tier-Berechnung nutzt den **User-Wert** aus `user_settings.json`, NICHT den geclampten Server-Wert.

```python
# NEU: Für Cortex-Berechnung den User-Wert direkt lesen
from utils.settings_helper import get_user_setting

def _get_context_limit_for_cortex() -> int:
    """Liest den User-contextLimit für Cortex-Berechnung (ungeclampt)."""
    raw = get_user_setting('contextLimit', '65')
    try:
        return max(10, int(raw))  # Nur Minimum 10, kein Maximum-Clamp
    except (TypeError, ValueError):
        return 65
```

**Grund:** Wenn der User `contextLimit=200` hat und "Häufig" wählt, soll bei Nachricht 100 getriggert werden — nicht bei 50 (geclampt=100).

> **TODO:** Der Clamp in `chat.py` (`max(10, min(100, ...))`) sollte ggf. auch angepasst werden. Das ist aber ein separater Schritt.

---

## 2. Session-State: Zyklisches Tracking

### 2.1 Konzept

Pro Session tracken wir nur **einen Wert**: `cycle_base` — die Nachrichtenanzahl bei der der aktuelle Zyklus begann.

```
Zähler = message_count - cycle_base
Schwelle = floor(contextLimit × frequency_percent / 100)

Wenn Zähler >= Schwelle → TRIGGER → cycle_base = message_count → Zähler zurück auf 0
```

### 2.2 Lösung: File-Persistent Cycle State

```python
# src/utils/cortex/tier_tracker.py (NEU)

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
import math
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
```

### 2.3 Visualisierung

```
Frequenz: Mittel (75%), contextLimit = 65 → Schwelle = 48

Msg:  0    10    20    30    40    48    58    68    78    88    96   ...
      ├─────┼─────┼─────┼─────┼────┤─────┼─────┼─────┼─────┼────┤───
                                    │                              │
      ├───── Zyklus 1 ─────────────►UPD   ├───── Zyklus 2 ───────►UPD
      cycle_base=0                 reset   cycle_base=48          reset
                                   =48                             =96
      
      Progress Bar:
      [████████████████████████████] 100% → TRIGGER!
      [                            ] 0%   → Neustart
      [█████████████               ] 50%  → auf halbem Weg
```

### 2.4 Persistenz-Strategie: File-backed Cache

| Schicht | Zweck |
|---------|-------|
| **In-Memory Dict** | Cache für schnellen Zugriff (kein Disk-Read pro Check) |
| **`cycle_state.json`** | Persistenter State, überlebt Server-Neustarts |
| **`rebuild_cycle_base()`** | Fallback wenn Datei fehlt oder korrupt |

**Warum JSON-Datei statt DB?**
- Kein Schema/Migration nötig
- Atomarer Write via `os.replace` — crash-safe
- Nur geschrieben bei State-Änderung (Trigger oder Reset), nicht bei jedem Chat
- Typisch < 1KB (wenige aktive Sessions gleichzeitig)
- Liegt in `src/settings/` neben `cortex_settings.json`

**Dateiformat:**
```json
{
  "default:5": 48,
  "a1b2c3d4:12": 150,
  "default:8": 96
}
```
Key = `"{persona_id}:{session_id}"`, Value = `cycle_base` (message_count beim letzten Reset).

Manuelle `/cortex`-Resets werden genauso persistent wie automatische Trigger — kein Datenverlust bei Neustart.

---

## 3. Server-seitige Trigger-Logik

### 3.1 Ablauf-Diagramm

```
┌─────────────────────────────────────────────────────────────────┐
│                     /chat_stream Request                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. User-Nachricht empfangen                                     │
│  2. Chat-Stream generieren (yield chunks)                        │
│  3. Bot-Antwort speichern (save_message)                         │
│                                                                  │
│  ══════ TRIGGER-CHECK (vor done-Event) ════════════════════════  │
│                                                                  │
│  4. Cortex Trigger-Check:                                        │
│     a) Cortex enabled?                                           │
│     b) Message-Count für Session holen                           │
│     c) Frequenz laden (Häufig/Mittel/Selten)                    │
│     d) Schwelle berechnen: floor(contextLimit × frequency%)     │
│     e) Zähler = message_count - cycle_base                       │
│     f) Wenn Zähler >= Schwelle → TRIGGER!                        │
│        → cycle_base = message_count (Reset)                      │
│        → Background Cortex-Update starten                        │
│     g) Progress-Daten berechnen → in done-Event mitsenden        │
│                                                                  │
│  5. SSE 'done' Event senden (inkl. cortex_progress + trigger)   │
│                                                                  │
│  6. Cortex-Update (falls getriggert):                            │
│     → Separater Thread (non-blocking)                            │
│     → tool_use API-Call (Schritt 3A)                             │
│     → KI liest/schreibt Cortex-Dateien                           │
│     → Ergebnis wird geloggt                                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Integration in `chat.py` — Trigger-Check vor done-Event

Der Trigger-Check wird **vor** dem `done`-yield ausgeführt, damit Progress-Daten im SSE-Payload enthalten sind.

```python
# ═══════════════════════════════════════════════════════════════
#  MODIFIKATION: src/routes/chat.py — chat_stream() Funktion
# ═══════════════════════════════════════════════════════════════

from utils.cortex.tier_checker import check_and_trigger_cortex_update

@chat_bp.route('/chat_stream', methods=['POST'])
@handle_route_error('chat_stream')
def chat_stream():
    data = request.get_json()
    user_message = data.get('message', '').strip()
    session_id = data.get('session_id')
    # ... bestehender Code ...

    def generate():
        chat_service = get_chat_service()
        user_msg_saved = False

        try:
            for event_type, event_data in chat_service.chat_stream(...):
                if event_type == 'chunk':
                    if not user_msg_saved:
                        save_message(user_message, True, character_name, 
                                     session_id, persona_id=persona_id)
                        user_msg_saved = True
                    yield f"data: {json.dumps({'type': 'chunk', 'text': event_data})}\n\n"

                elif event_type == 'done':
                    save_message(event_data['response'], False, character_name, 
                                 session_id, persona_id=persona_id)

                    # ═══ NEU: Cortex Trigger-Check VOR done-yield ═══
                    cortex_info = None
                    try:
                        cortex_info = check_and_trigger_cortex_update(
                            persona_id=persona_id,
                            session_id=session_id
                        )
                    except Exception as e:
                        log.warning("Cortex check failed (non-fatal): %s", e)

                    # done-Payload zusammenbauen
                    done_payload = {
                        'type': 'done',
                        'response': event_data['response'],
                        'stats': event_data['stats'],
                        'character_name': character_name
                    }
                    
                    # Cortex-Info mitsenden (Progress + Trigger-Status)
                    if cortex_info:
                        done_payload['cortex'] = cortex_info

                    yield f"data: {json.dumps(done_payload)}\n\n"

                elif event_type == 'error':
                    yield f"data: {json.dumps({'type': 'error', 'error': event_data})}\n\n"

        except Exception as e:
            log.error("Stream-Fehler: %s", e)
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no', 'Connection': 'keep-alive'}
    )
```

### 3.3 Timing

```
Timeline:
──────────────────────────────────────────────────────────►
  │ chunks...  │ trigger-check │ done (inkl. progress) │
  │            │     ~5ms       │                        │
  │ ← Client sieht chunks ──────────── done mit cortex → │
                                                          │
                                    Background-Update ───►│ (3-10s, non-blocking)
```

---

## 4. Tier-Checker Modul

### 4.1 Datei: `src/utils/cortex/tier_checker.py`

```python
"""
Cortex Trigger Checker — Prüft ob ein Cortex-Update ausgelöst werden soll.

Der User wählt eine Frequenz (Häufig=50%, Mittel=75%, Selten=95%).
Bei Erreichen der Schwelle: Update → Zähler reset → zyklisch wiederholen.
"""

import threading
import math
import json
import os
from typing import Optional

from utils.logger import log
from utils.database import get_message_count
from utils.cortex.tier_tracker import (
    get_cycle_base, set_cycle_base, rebuild_cycle_base, get_progress
)


# Frequenz-Mapping
FREQUENCIES = {
    "frequent": {"label": "Häufig",  "percent": 50},
    "medium":   {"label": "Mittel",  "percent": 75},
    "rare":     {"label": "Selten",  "percent": 95},
}
DEFAULT_FREQUENCY = "medium"


def _load_cortex_config() -> dict:
    """
    Lädt die Cortex-Konfiguration.

    Returns:
        {
            "enabled": True,
            "frequency": "medium"   # "frequent" | "medium" | "rare"
        }
    """
    settings_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        'settings', 'cortex_settings.json'
    )

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
    """Liest den User-contextLimit (ungeclampt)."""
    from utils.settings_helper import get_user_setting
    raw = get_user_setting('contextLimit', '65')
    try:
        return max(10, int(raw))
    except (TypeError, ValueError):
        return 65


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


def _start_background_cortex_update(persona_id: str, session_id: int) -> None:
    """
    Startet das Cortex-Update in einem Background-Thread.
    Nur ein Update pro Persona gleichzeitig.
    """
    thread_name = f"cortex-update-{persona_id}"

    # Prüfe ob bereits ein Update läuft
    for t in threading.enumerate():
        if t.name == thread_name and t.is_alive():
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

    thread = threading.Thread(target=_run_update, name=thread_name, daemon=True)
    thread.start()
```

---

## 5. Vollständiger Flow

### 5.1 Sequenzdiagramm

```
Client                    Server (chat.py)              TierChecker              Background Thread
  │                            │                            │                         │
  │── POST /chat_stream ──────►│                            │                         │
  │                            │                            │                         │
  │◄── SSE: chunk ─────────────│                            │                         │
  │◄── SSE: chunk ─────────────│                            │                         │
  │                            │                            │                         │
  │                            │── save_message() ──────────│                         │
  │                            │                            │                         │
  │                            │── check_and_trigger() ────►│                         │
  │                            │                            │── get_message_count()   │
  │                            │                            │── get_cycle_base()      │
  │                            │                            │── messages_since >= 48? │
  │                            │                            │                         │
  │                            │                            │── [JA! Trigger!]        │
  │                            │                            │── set_cycle_base(96)    │
  │                            │                            │── start_background() ──►│
  │                            │                            │                         │
  │                            │◄─ {triggered: true,        │                         │
  │                            │    progress: {0%, cycle 3}}│                         │
  │                            │                            │                         │
  │◄── SSE: done ──────────────│                            │                         │
  │   (inkl. cortex.progress)  │                            │  ┌─ CortexUpdateService │
  │                            │                            │  │  tool_use API-Call    │
  │   Frontend zeigt:          │                            │  │  read + write .md     │
  │   Progress Bar: 0%         │                            │  └─ Log result           │
  │   "🧠 Cortex updated!"    │                            │                         │
```

### 5.2 Pseudocode

```python
def on_chat_response_complete(persona_id, session_id):
    """Wird vor dem done-yield aufgerufen."""

    config = load_cortex_settings()
    if not config.enabled:
        return None

    frequency = config.frequency     # z.B. "medium"
    context_limit = get_user_context_limit()  # z.B. 65
    threshold = floor(65 * 0.75)     # = 48

    message_count = get_message_count(session_id)  # z.B. 96
    cycle_base = get_cycle_base(session_id)         # z.B. 48 (letzter Reset)
    
    messages_since_reset = 96 - 48   # = 48
    
    if messages_since_reset >= threshold:  # 48 >= 48 → JA!
        set_cycle_base(session_id, 96)     # Reset: neuer Zyklus
        start_background_update()           # KI aktualisiert Cortex-Dateien
        return {"triggered": True, "progress": {"percent": 0, "cycle": 3}}
    else:
        return {"triggered": False, "progress": {"percent": 75, "cycle": 2}}
```

---

## 6. Settings-Struktur

### 6.1 Datei: `src/settings/cortex_settings.json`

```json
{
    "enabled": true,
    "frequency": "medium"
}
```

**Das ist alles.** Keine komplexe Tier-Struktur mehr.

### 6.2 Felder-Referenz

| Feld | Typ | Default | Mögliche Werte | Beschreibung |
|------|-----|---------|-----------------|--------------|
| `enabled` | `bool` | `true` | `true`/`false` | Cortex-System global ein/aus |
| `frequency` | `string` | `"medium"` | `"frequent"`, `"medium"`, `"rare"` | Gewählte Update-Frequenz |

### 6.3 Frontend-Mapping

| `frequency` Wert | Frontend-Label | Emoji | Schwelle |
|:-----------------:|:--------------:|:-----:|:--------:|
| `"frequent"` | Häufig | 🔥 | 50% |
| `"medium"` | Mittel | ⚡ | 75% |
| `"rare"` | Selten | 🌙 | 95% |

### 6.4 Keine Validierung nötig

Im Gegensatz zum alten 3-Slider-Modell braucht es keine Validierung:
- Nur 3 feste Werte möglich (Radio-Buttons, kein Freitext)
- Kein Sortierungs- oder Abstands-Check nötig
- Ungültige Werte → Fallback auf `"medium"`

---

## 7. Edge Cases

### 7.1 `contextLimit` ändert sich

Die Schwelle wird **jedes Mal** neu berechnet. Änderung wird beim nächsten Chat-Response wirksam.

```
Vorher: contextLimit=65, Mittel → Schwelle 48, cycle_base=0, msg=30
User ändert contextLimit auf 200 → Schwelle wird 150
Nächster Check: 30 - 0 = 30 < 150 → noch nicht
```

### 7.2 Frequenz ändert sich

Gleich wie contextLimit — sofortige Auswirkung auf die nächste Berechnung.

```
Vorher: Mittel=75%, contextLimit=65 → Schwelle 48, msg_since_reset=30
User wechselt zu Häufig=50% → Schwelle wird 32
Nächster Check: 30 < 32 → noch 2 Nachrichten
```

### 7.3 Session-Wechsel

`cycle_base` ist pro `{persona_id}:{session_id}` — Wechsel betrifft nur die neue Session.

### 7.4 Persona-Wechsel

Verschiedene Personas haben eigene `cycle_base` States und eigene Cortex-Dateien.

### 7.5 `clear_chat`

```python
# In chat.py — clear_chat():
reset_session(persona_id, session_id)  # cycle_base gelöscht → nächster Zyklus startet bei 0
```

### 7.6 Server-Neustart

State wird beim ersten Zugriff aus `cycle_state.json` geladen — exakter Wert, inkl. manueller `/cortex`-Resets. Nur wenn die Datei fehlt/korrupt ist, greift `rebuild_cycle_base()` als Fallback.

### 7.7 Gleichzeitige Updates

Thread-Name-Sperre verhindert parallele Updates pro Persona. Wenn ein Update noch läuft und der nächste Trigger kommt, wird der Trigger trotzdem verarbeitet (cycle_base reset), aber kein zweiter Background-Thread gestartet.

### 7.8 Kein API-Key

Trigger-Check läuft (ist nur Zahlenvergleich). Background-Update schlägt fehl → Log-Warnung. cycle_base wurde aber schon resettet → nächster Trigger nach weiteren `threshold` Nachrichten.

### 7.9 Regenerate

Kein Trigger bei Regenerate — Nachrichtenanzahl ändert sich nicht (altes gelöscht, neues gespeichert).

---

## 8. Frontend: Progress Bar + Frequenz-Auswahl

### 8.1 done-Event Payload

```json
{
    "type": "done",
    "response": "...",
    "stats": { ... },
    "character_name": "Mia",
    "cortex": {
        "triggered": false,
        "progress": {
            "messages_since_reset": 25,
            "threshold": 48,
            "progress_percent": 52.1,
            "cycle_number": 2
        },
        "frequency": "medium"
    }
}
```

### 8.2 Progress Bar im Chat

Das Frontend kann eine dezente Progress Bar im ChatInput/ContextBar-Bereich anzeigen:

```
┌───────────────────────────────────────────┐
│  [████████████░░░░░░░░░░░░] 52% ⚡ Mittel │  ← Cortex Progress
│                                            │
│  [Nachricht eingeben...]                   │
└───────────────────────────────────────────┘
```

Bei Trigger:
```
┌───────────────────────────────────────────┐
│  🧠 Cortex aktualisiert sich...           │  ← Kurze Notification (3s)
│  [░░░░░░░░░░░░░░░░░░░░░░░░] 0%   ⚡      │  ← Reset auf 0
│                                            │
│  [Nachricht eingeben...]                   │
└───────────────────────────────────────────┘
```

### 8.3 Frequenz-Auswahl im CortexOverlay

Statt 3 Slidern: **Radio-Button-Gruppe / Segmented Control**:

```
┌─────────────────────────────────────────┐
│  Cortex-Einstellungen                    │
│                                          │
│  Status: [Toggle: Ein/Aus]               │
│                                          │
│  Update-Frequenz:                        │
│  ┌─────────┬─────────┬─────────┐        │
│  │🔥 Häufig│⚡ Mittel │🌙 Selten│        │
│  │  (50%)  │  (75%)  │  (95%)  │        │
│  └─────────┴─────────┴─────────┘        │
│       ↑ aktuell ausgewählt               │
│                                          │
│  Cortex-Dateien:                         │
│  [Tab: Memory | Seele | Beziehung]       │
│  ...                                     │
└─────────────────────────────────────────┘
```

### 8.4 Frontend-Handling in `useMessages.js`

```javascript
onDone: (data) => {
    // ... bestehender Code ...

    // Cortex-Progress Event
    if (data.cortex) {
        window.dispatchEvent(new CustomEvent('cortex-progress', {
            detail: data.cortex
        }));
    }
},
```

---

## 9. Neue und geänderte Dateien

### 9.1 Neue Dateien

| Datei | Zweck |
|-------|-------|
| `src/utils/cortex/__init__.py` | Package-Init (Exports) |
| `src/utils/cortex/tier_tracker.py` | Zyklisches Tracking (cycle_base pro Session) |
| `src/utils/cortex/tier_checker.py` | Trigger-Logik + Progress-Berechnung |
| `src/settings/cycle_state.json` | Persistenter Cycle-State (auto-generiert) |

### 9.2 Geänderte Dateien

| Datei | Änderung |
|-------|----------|
| `src/routes/chat.py` | Trigger-Check vor done-yield, Progress in done-Payload |
| `src/settings/cortex_settings.json` | Vereinfacht: nur `enabled` + `frequency` |
| `src/settings/cycle_state.json` | Persistenter Cycle-State (auto-generiert bei erstem Trigger) |

### 9.3 Abhängig von

| Datei | Schritt | Zweck |
|-------|---------|-------|
| `src/utils/cortex/update_service.py` | 3C + 6 | CortexUpdateService — tool_use Call |
| `src/settings/cortex_settings.json` | 2C | Settings-Datei |

### 9.4 Package-Init

```python
# src/utils/cortex/__init__.py

"""Cortex Package — Update-Frequenz und zyklische Trigger-Logik."""

from utils.cortex.tier_tracker import (
    get_cycle_base, set_cycle_base, reset_session, reset_all,
    rebuild_cycle_base, get_progress
)
from utils.cortex.tier_checker import check_and_trigger_cortex_update

__all__ = [
    'get_cycle_base', 'set_cycle_base', 'reset_session', 'reset_all',
    'rebuild_cycle_base', 'get_progress', 'check_and_trigger_cortex_update',
]
```

---

## 10. Zusammenfassung

```
┌──────────────────────────────────────────────────┐
│          Cortex Aktivierungslogik (v3)             │
├──────────────────────────────────────────────────┤
│                                                    │
│  User wählt EINE Frequenz:                         │
│                                                    │
│   🔥 Häufig  = alle 50% von contextLimit           │
│   ⚡ Mittel  = alle 75% von contextLimit (Default) │
│   🌙 Selten  = alle 95% von contextLimit           │
│                                                    │
│  Beispiel: contextLimit=65, Mittel (75%)           │
│  → Schwelle = 48 Nachrichten                       │
│                                                    │
│  Msg 0 ──────────────────── 48 → UPDATE → Reset    │
│  Msg 0 ──────────────────── 48 → UPDATE → Reset    │
│  Msg 0 ──────────────────── 48 → UPDATE → Reset    │
│  ... (endlos zyklisch)                             │
│                                                    │
│  Progress Bar: [████████████░░░░] 52% ⚡            │
│                                                    │
└──────────────────────────────────────────────────┘
```

---

## 11. Abhängigkeiten

| Abhängigkeit | Richtung | Details |
|-------------|----------|---------|
| **Schritt 2C** | ← | `cortex_settings.json` Lesen/Schreiben |
| **Schritt 3A** | ← | `ApiClient.tool_request()` für Background-Update |
| **Schritt 3C** | ← | `CortexUpdateService` für den Update-Call |
| **Schritt 5** | → | CortexOverlay: Frequenz-Selector + Progress Bar |
| **Schritt 6** | → | Chat-Flow Integration |
