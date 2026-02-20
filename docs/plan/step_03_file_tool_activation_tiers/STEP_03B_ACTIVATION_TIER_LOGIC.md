# Schritt 3B: Aktivierungsstufen-Logik

## Übersicht

Das Cortex-System aktualisiert seine Dateien (`memory.md`, `soul.md`, `relationship.md`) nicht bei jeder Nachricht, sondern an definierten **Schwellenwerten** innerhalb einer Konversation. Diese Schwellen werden als Prozentsätze des `contextLimit` berechnet — der maximalen Anzahl von Nachrichten, die im Konversationskontext gehalten werden.

Drei Aktivierungsstufen (Tiers) bestimmen, wann ein Cortex-Update ausgelöst wird:

| Stufe | Default-Schwelle | Bedeutung |
|-------|:----------------:|-----------|
| Tier 1 | 50% von `contextLimit` | Frühes Update — erste Eindrücke, initiale Details |
| Tier 2 | 75% von `contextLimit` | Mittleres Update — Vertiefung, Beziehungsentwicklung |
| Tier 3 | 95% von `contextLimit` | Spätes Update — letzte Chance vor Kontext-Rotation |

Jeder Tier löst **genau einmal** pro Konversation aus. Die Trigger-Prüfung findet **server-seitig** in `chat.py` statt, **nachdem** der Chat-Response vollständig gestreamt und gespeichert wurde. Das Cortex-Update selbst läuft als **separater, nicht-blockierender Background-Request** via `tool_use` (dokumentiert in Schritt 3A).

---

## 1. Schwellenwert-Berechnung

### 1.1 Formel

```
threshold_messages = floor(contextLimit × (tier_threshold_percent / 100))
```

### 1.2 Berechnungsbeispiele

**Beispiel 1: `contextLimit = 65` (Default)**

| Tier | Schwelle (%) | Berechnung | Trigger bei Nachricht # |
|------|:------------:|-----------|:-----------------------:|
| 1 | 50% | `floor(65 × 0.50)` | **32** |
| 2 | 75% | `floor(65 × 0.75)` | **48** |
| 3 | 95% | `floor(65 × 0.95)` | **61** |

**Beispiel 2: `contextLimit = 200` (User-konfiguriert)**

| Tier | Schwelle (%) | Berechnung | Trigger bei Nachricht # |
|------|:------------:|-----------|:-----------------------:|
| 1 | 50% | `floor(200 × 0.50)` | **100** |
| 2 | 75% | `floor(200 × 0.75)` | **150** |
| 3 | 95% | `floor(200 × 0.95)` | **190** |

**Beispiel 3: `contextLimit = 10` (Minimum)**

| Tier | Schwelle (%) | Berechnung | Trigger bei Nachricht # |
|------|:------------:|-----------|:-----------------------:|
| 1 | 50% | `floor(10 × 0.50)` | **5** |
| 2 | 75% | `floor(10 × 0.75)` | **7** |
| 3 | 95% | `floor(10 × 0.95)` | **9** |

### 1.3 Hinweis zu `contextLimit`

Der `contextLimit` wird vom Frontend als Einstellung gesendet und definiert die maximale Anzahl von Nachrichten im Konversationskontext. Er wird in `chat_stream` aus dem Request gelesen:

```python
# Bestehend in src/routes/chat.py (Zeile 79-84):
context_limit = data.get('context_limit', 25)
try:
    context_limit = int(context_limit)
except (TypeError, ValueError):
    context_limit = 25
context_limit = max(10, min(100, context_limit))
```

> **Hinweis:** Der aktuelle Code clampt `contextLimit` auf `max(10, min(100, ...))`. Die `user_settings.json` kann jedoch Werte wie `200` enthalten. Ob der Clamp erweitert wird, ist eine separate Diskussion — die Tier-Berechnung nutzt den **effektiven** (geclampten) Wert.

---

## 2. Session-State: Tracking der gefeuerten Tiers

### 2.1 Problem

Jeder Tier soll nur **einmal** pro Konversation (Session) feuern. Dafür muss der Server sich merken, welche Tiers in der aktuellen Session bereits ausgelöst wurden. Da Flask keine persistente In-Process-Session-State hat und die App neustarten kann, muss der State robust gespeichert werden.

### 2.2 Lösung: Server-seitiges In-Memory-Dictionary mit DB-Fallback

```python
# src/utils/cortex/tier_tracker.py (NEU)

"""
Cortex Tier Tracker — Verfolgt welche Aktivierungsstufen pro Session bereits gefeuert haben.

Nutzt ein In-Memory-Dictionary als primären Speicher. Bei Neustart wird der State
aus der Nachrichtenanzahl der Session re-kalkuliert (kein Datenverlust).
"""

import threading
from typing import Dict, Set

# Thread-safe In-Memory State
_lock = threading.Lock()
_fired_tiers: Dict[str, Set[int]] = {}
# Key: "{persona_id}:{session_id}" → Value: set of fired tier numbers (1, 2, 3)


def _session_key(persona_id: str, session_id: int) -> str:
    """Erzeugt einen eindeutigen Key für die Session."""
    return f"{persona_id}:{session_id}"


def get_fired_tiers(persona_id: str, session_id: int) -> Set[int]:
    """Gibt die bereits gefeuerten Tiers für eine Session zurück."""
    key = _session_key(persona_id, session_id)
    with _lock:
        return _fired_tiers.get(key, set()).copy()


def mark_tier_fired(persona_id: str, session_id: int, tier: int) -> None:
    """Markiert einen Tier als gefeuert für eine Session."""
    key = _session_key(persona_id, session_id)
    with _lock:
        if key not in _fired_tiers:
            _fired_tiers[key] = set()
        _fired_tiers[key].add(tier)


def reset_session(persona_id: str, session_id: int) -> None:
    """Setzt den Tier-State für eine Session zurück (z.B. bei clear_chat)."""
    key = _session_key(persona_id, session_id)
    with _lock:
        _fired_tiers.pop(key, None)


def reset_all() -> None:
    """Setzt den gesamten Tier-State zurück (z.B. bei App-Restart)."""
    with _lock:
        _fired_tiers.clear()


def rebuild_from_message_count(
    persona_id: str,
    session_id: int,
    message_count: int,
    context_limit: int,
    tier_thresholds: Dict[int, int]
) -> Set[int]:
    """
    Re-kalkuliert welche Tiers basierend auf der aktuellen Nachrichtenanzahl
    bereits gefeuert haben müssten. Wird nach App-Neustart verwendet.

    Args:
        persona_id: Persona-ID
        session_id: Session-ID
        message_count: Aktuelle Anzahl Nachrichten in der Session
        context_limit: Aktuelles Context-Limit
        tier_thresholds: Dict {1: 50, 2: 75, 3: 95} (Prozentwerte)

    Returns:
        Set der Tiers die als gefeuert markiert wurden
    """
    key = _session_key(persona_id, session_id)
    fired = set()

    for tier_num, threshold_percent in tier_thresholds.items():
        threshold_messages = int(context_limit * (threshold_percent / 100))
        if message_count >= threshold_messages:
            fired.add(tier_num)

    with _lock:
        _fired_tiers[key] = fired

    return fired
```

### 2.3 Warum In-Memory statt DB?

| Ansatz | Vorteil | Nachteil |
|--------|---------|----------|
| **In-Memory Dict** ✅ | Schnell, einfach, kein DB-Schema | Verliert State bei Restart |
| DB-Tabelle | Persistent | Neues SQL-Schema, Migration, Overhead |
| File-basiert | Persistent, kein SQL | I/O bei jeder Nachricht |

**Gewählter Kompromiss:** In-Memory mit **automatischem Rebuild** bei Bedarf. Wenn der Server neustartet und eine Session fortgesetzt wird, wird der Tier-State aus der aktuellen Nachrichtenanzahl re-kalkuliert. Das ist konservativ: Tiers die bereits gefeuert hätten, werden als "gefeuert" markiert (aber nicht erneut ausgelöst). Es gehen keine Updates verloren — sie werden im schlimmsten Fall übersprungen, was harmlos ist.

### 2.4 Session-Key Struktur

```
Key: "{persona_id}:{session_id}"

Beispiele:
  "default:1"           → Default-Persona, Session 1
  "a1b2c3d4:5"          → Custom-Persona, Session 5
```

Die Kombination aus `persona_id` und `session_id` ist notwendig, da verschiedene Personas eigene Cortex-Dateien haben und unabhängig getrackt werden müssen.

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
│  4. SSE 'done' Event senden                                      │
│                                                                  │
│  ══════ Stream ist abgeschlossen ══════════════════════════════  │
│                                                                  │
│  5. Tier-Check ausführen:                                        │
│     a) Message-Count für Session holen (get_message_count)       │
│     b) Cortex-Settings laden (Tiers + enabled)                   │
│     c) Schwellenwerte berechnen                                  │
│     d) Prüfen ob ein neuer Tier erreicht wurde                   │
│     e) Falls ja: mark_tier_fired() + Background-Update starten   │
│                                                                  │
│  6. Cortex-Update (falls getriggert):                            │
│     → Separater Thread (non-blocking)                            │
│     → tool_use API-Call (Schritt 3A)                             │
│     → KI liest/schreibt Cortex-Dateien                           │
│     → Ergebnis wird geloggt                                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Integration in `chat.py` — Tier-Check nach Stream

Die Tier-Prüfung wird **nach** dem erfolgreichen Stream-Ende eingefügt. Da der SSE-Stream zu diesem Zeitpunkt bereits alles an den Client gesendet hat, ist der Cortex-Update ein reiner Hintergrundprozess.

```python
# ═══════════════════════════════════════════════════════════════
#  MODIFIKATION: src/routes/chat.py — chat_stream() Funktion
# ═══════════════════════════════════════════════════════════════

from utils.cortex.tier_tracker import get_fired_tiers, mark_tier_fired, rebuild_from_message_count
from utils.cortex.tier_checker import check_and_trigger_cortex_update
from utils.database import get_message_count

@chat_bp.route('/chat_stream', methods=['POST'])
@handle_route_error('chat_stream')
def chat_stream():
    """API-Endpoint für gestreamte Chat-Nachrichten via SSE"""
    data = request.get_json()
    user_message = data.get('message', '').strip()
    session_id = data.get('session_id')
    # ... bestehender Code ...

    context_limit = data.get('context_limit', 25)
    try:
        context_limit = int(context_limit)
    except (TypeError, ValueError):
        context_limit = 25
    context_limit = max(10, min(100, context_limit))

    # ... bestehender Code (conversation_history, etc.) ...

    def generate():
        chat_service = get_chat_service()
        user_msg_saved = False
        stream_success = False            # ← NEU: Tracking ob Stream erfolgreich war

        try:
            for event_type, event_data in chat_service.chat_stream(
                # ... bestehende Parameter ...
            ):
                if event_type == 'chunk':
                    if not user_msg_saved:
                        save_message(user_message, True, character_name, session_id, persona_id=persona_id)
                        user_msg_saved = True
                    yield f"data: {json.dumps({'type': 'chunk', 'text': event_data})}\n\n"

                elif event_type == 'done':
                    save_message(event_data['response'], False, character_name, session_id, persona_id=persona_id)
                    stream_success = True  # ← NEU
                    yield f"data: {json.dumps({'type': 'done', 'response': event_data['response'], 'stats': event_data['stats'], 'character_name': character_name})}\n\n"

                elif event_type == 'error':
                    # ... bestehender Error-Code ...
                    yield f"data: {json.dumps(error_payload)}\n\n"

        except Exception as e:
            log.error("Stream-Fehler: %s", e)
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

        # ══════════════════════════════════════════════════════════
        #  NEU: Tier-Check NACH Stream-Ende
        # ══════════════════════════════════════════════════════════
        if stream_success:
            try:
                check_and_trigger_cortex_update(
                    persona_id=persona_id,
                    session_id=session_id,
                    context_limit=context_limit
                )
            except Exception as e:
                # Tier-Check darf niemals den Chat-Flow brechen
                log.warning("Cortex Tier-Check Fehler (non-fatal): %s", e)

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )
```

### 3.3 Wichtig: Position des Tier-Checks

Der Tier-Check steht **innerhalb** der `generate()` Generator-Funktion, **nach** dem letzten `yield`. Das bedeutet:

1. Alle SSE-Events sind bereits an den Client gesendet
2. Der Client hat `done` empfangen und zeigt die Antwort an
3. Der Tier-Check läuft noch im Server-Kontext des Generators
4. Flask schließt den Response erst, wenn der Generator endet

```
Timeline:
───────────────────────────────────────────────────────────►
  │ chunks...  │ done │ tier-check │ background-update │
  │ ← Client sieht diese Events → │                    │
                                   │ ← Nicht sichtbar → │
```

> **Hinweis:** Der Tier-Check selbst ist schnell (DB-Query + Vergleich). Nur das eigentliche Cortex-Update wird in einen Background-Thread ausgelagert.

---

## 4. Tier-Checker Modul

### 4.1 Datei: `src/utils/cortex/tier_checker.py`

```python
"""
Cortex Tier Checker — Prüft ob ein Cortex-Update ausgelöst werden soll.

Wird nach jedem erfolgreichen Chat-Response aufgerufen.
Vergleicht die aktuelle Nachrichtenanzahl mit den konfigurierten Schwellenwerten
und startet bei Bedarf ein Background-Cortex-Update.
"""

import threading
import math
from typing import Optional

from utils.logger import log
from utils.database import get_message_count
from utils.cortex.tier_tracker import get_fired_tiers, mark_tier_fired, rebuild_from_message_count


def _load_tier_config() -> dict:
    """
    Lädt die Cortex-Tier-Konfiguration.

    Returns:
        {
            "enabled": True,
            "tiers": {
                1: {"threshold": 50, "enabled": True},
                2: {"threshold": 75, "enabled": True},
                3: {"threshold": 95, "enabled": True}
            }
        }
    """
    import json
    import os

    settings_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        'settings', 'cortex_settings.json'
    )

    defaults = {
        "enabled": True,
        "tiers": {
            "tier1": {"threshold": 50, "enabled": True},
            "tier2": {"threshold": 75, "enabled": True},
            "tier3": {"threshold": 95, "enabled": True}
        }
    }

    try:
        if os.path.exists(settings_path):
            with open(settings_path, 'r', encoding='utf-8') as f:
                saved = json.load(f)
            merged = {**defaults, **saved}
            merged['tiers'] = {**defaults['tiers'], **saved.get('tiers', {})}
        else:
            merged = defaults
    except Exception:
        merged = defaults

    # Konvertiere "tier1" → 1 für internen Gebrauch
    config = {
        "enabled": merged.get("enabled", True),
        "tiers": {}
    }
    for key, value in merged.get("tiers", {}).items():
        tier_num = int(key.replace("tier", ""))
        config["tiers"][tier_num] = {
            "threshold": value.get("threshold", 50),
            "enabled": value.get("enabled", True)
        }

    return config


def _calculate_thresholds(context_limit: int, tier_config: dict) -> dict:
    """
    Berechnet die absoluten Nachrichtenanzahl-Schwellenwerte.

    Args:
        context_limit: Maximale Nachrichten im Kontext (z.B. 65)
        tier_config: Tier-Konfiguration aus _load_tier_config()

    Returns:
        {1: 32, 2: 48, 3: 61}  → Tier → Nachrichtenanzahl
    """
    thresholds = {}
    for tier_num, tier_data in tier_config["tiers"].items():
        if tier_data["enabled"]:
            thresholds[tier_num] = math.floor(
                context_limit * (tier_data["threshold"] / 100)
            )
    return thresholds


def check_and_trigger_cortex_update(
    persona_id: str,
    session_id: int,
    context_limit: int
) -> Optional[int]:
    """
    Prüft ob ein Cortex-Update getriggert werden soll und startet es ggf.

    Wird nach jedem erfolgreichen Chat-Response aufgerufen.

    Args:
        persona_id: Aktive Persona-ID
        session_id: Aktuelle Session-ID
        context_limit: Aktuelles Context-Limit (geclampt)

    Returns:
        Tier-Nummer die getriggert wurde, oder None
    """
    # 1. Cortex global deaktiviert?
    config = _load_tier_config()
    if not config["enabled"]:
        return None

    # 2. Keine aktiven Tiers?
    thresholds = _calculate_thresholds(context_limit, config)
    if not thresholds:
        return None

    # 3. Aktuelle Nachrichtenanzahl holen
    message_count = get_message_count(session_id=session_id, persona_id=persona_id)
    if message_count == 0:
        return None

    # 4. Bereits gefeuerte Tiers laden
    fired = get_fired_tiers(persona_id, session_id)

    # 5. Falls noch kein State existiert (z.B. nach Restart), rebuilden
    if not fired and message_count > 0:
        threshold_percents = {
            tier_num: tier_data["threshold"]
            for tier_num, tier_data in config["tiers"].items()
            if tier_data["enabled"]
        }
        # Rebuild markiert Tiers die VOR der jetzigen Nachricht erreicht wurden
        # Wir nutzen (message_count - 1) damit der aktuelle neue Tier trotzdem feuert
        fired = rebuild_from_message_count(
            persona_id, session_id,
            message_count - 1,  # -1: Nur Tiers die VOR dieser Nachricht gefeuert hätten
            context_limit, threshold_percents
        )

    # 6. Prüfen ob ein neuer Tier erreicht wurde
    triggered_tier = None
    for tier_num in sorted(thresholds.keys()):
        threshold = thresholds[tier_num]
        if message_count >= threshold and tier_num not in fired:
            triggered_tier = tier_num
            break  # Nur den niedrigsten neuen Tier auslösen

    if triggered_tier is None:
        return None

    # 7. Tier als gefeuert markieren
    mark_tier_fired(persona_id, session_id, triggered_tier)

    log.info(
        "Cortex Tier %d ausgelöst: %d/%d Nachrichten (Schwelle: %d, contextLimit: %d) — Persona: %s, Session: %s",
        triggered_tier, message_count, context_limit,
        thresholds[triggered_tier], context_limit,
        persona_id, session_id
    )

    # 8. Background Cortex-Update starten
    _start_background_cortex_update(
        persona_id=persona_id,
        session_id=session_id,
        context_limit=context_limit,
        triggered_tier=triggered_tier
    )

    return triggered_tier


def _start_background_cortex_update(
    persona_id: str,
    session_id: int,
    context_limit: int,
    triggered_tier: int
) -> None:
    """
    Startet das Cortex-Update in einem Background-Thread.

    Der Thread führt den tool_use API-Call aus (Schritt 3A: CortexUpdateService).
    Da dies ein separater API-Request ist, blockiert er weder den Chat-Stream
    noch den Response an den Client.

    Args:
        persona_id: Persona-ID
        session_id: Session-ID
        context_limit: Context-Limit für den Konversationskontext
        triggered_tier: Welcher Tier das Update ausgelöst hat (für Logging)
    """
    def _run_update():
        try:
            from utils.cortex.update_service import CortexUpdateService

            service = CortexUpdateService()
            result = service.execute_update(
                persona_id=persona_id,
                session_id=session_id,
                context_limit=context_limit,
                triggered_tier=triggered_tier
            )

            if result.get('success'):
                log.info(
                    "Cortex-Update abgeschlossen (Tier %d): %d Tool-Calls ausgeführt — Persona: %s",
                    triggered_tier,
                    result.get('tool_calls_count', 0),
                    persona_id
                )
            else:
                log.warning(
                    "Cortex-Update fehlgeschlagen (Tier %d): %s — Persona: %s",
                    triggered_tier,
                    result.get('error', 'Unbekannter Fehler'),
                    persona_id
                )
        except Exception as e:
            log.error("Cortex-Update Exception (Tier %d): %s", triggered_tier, e)

    thread = threading.Thread(
        target=_run_update,
        name=f"cortex-update-{persona_id}-t{triggered_tier}",
        daemon=True  # Thread stirbt mit dem Hauptprozess
    )
    thread.start()
```

### 4.2 Warum `break` beim ersten neuen Tier?

```python
for tier_num in sorted(thresholds.keys()):
    if message_count >= threshold and tier_num not in fired:
        triggered_tier = tier_num
        break  # ← Nur EINEN Tier pro Nachricht
```

Es wird bewusst nur **ein** Tier pro Nachricht ausgelöst:

1. **Vermeidet parallele Tool-Use Calls:** Zwei gleichzeitige Cortex-Updates könnten sich gegenseitig überschreiben
2. **Progressive Vertiefung:** Tier 1 schreibt erste Eindrücke, Tier 2 baut darauf auf
3. **Edge Case:** Falls der User mehrere Tiers gleichzeitig überspringt (z.B. bei Rebuild nach Restart), wird nur der niedrigste neue Tier ausgelöst. Die höheren Tiers feuern bei der nächsten Nachricht.

---

## 5. Vollständiger Flow: Chat → Tier-Check → Cortex-Update

### 5.1 Sequenzdiagramm

```
Client                    Server (chat.py)              TierChecker              Background Thread
  │                            │                            │                         │
  │── POST /chat_stream ──────►│                            │                         │
  │                            │                            │                         │
  │◄── SSE: chunk ─────────────│                            │                         │
  │◄── SSE: chunk ─────────────│                            │                         │
  │◄── SSE: chunk ─────────────│                            │                         │
  │                            │                            │                         │
  │                            │── save_message() ─────────►│                         │
  │◄── SSE: done ──────────────│                            │                         │
  │                            │                            │                         │
  │    (Client zeigt Antwort)  │── check_and_trigger() ────►│                         │
  │                            │                            │── get_message_count()   │
  │                            │                            │── get_fired_tiers()     │
  │                            │                            │── calculate_thresholds()│
  │                            │                            │                         │
  │                            │                            │── [Tier 2 erreicht!]    │
  │                            │                            │── mark_tier_fired(2)    │
  │                            │                            │                         │
  │                            │                            │── start_background() ──►│
  │                            │◄─ return tier=2 ───────────│                         │
  │                            │                            │                         │
  │    (Response closed)       │                            │  ┌─ CortexUpdateService │
  │                            │                            │  │  tool_use API-Call    │
  │                            │                            │  │  read memory.md       │
  │                            │                            │  │  write memory.md      │
  │                            │                            │  │  write soul.md        │
  │                            │                            │  └─ Log result           │
  │                            │                            │                         │
```

### 5.2 Timing

| Phase | Dauer | Blockiert Client? |
|-------|-------|:-----------------:|
| Chat-Stream (Chunks) | 2–15s | Nein (Streaming) |
| Tier-Check | ~5ms | Nein (nach `done`) |
| Background Cortex-Update | 3–10s | **Nein** (eigener Thread) |

### 5.3 Was passiert bei jedem Chat-Response

```python
# Pseudocode — vereinfachter Ablauf

def on_chat_response_complete(persona_id, session_id, context_limit):
    """Wird nach jedem erfolgreichen Chat-Response aufgerufen."""

    # 1. Cortex aktiviert?
    config = load_cortex_settings()
    if not config.enabled:
        return

    # 2. Nachrichten zählen
    msg_count = get_message_count(session_id, persona_id)

    # 3. Schwellenwerte berechnen
    #    contextLimit=65, tier1=50% → threshold=32
    thresholds = {
        1: floor(context_limit * 0.50),  # 32
        2: floor(context_limit * 0.75),  # 48
        3: floor(context_limit * 0.95),  # 61
    }

    # 4. Welche Tiers sind schon gefeuert?
    fired = get_fired_tiers(persona_id, session_id)
    # z.B. {1} → Tier 1 hat bereits gefeuert

    # 5. Neuer Tier erreicht?
    for tier in [1, 2, 3]:
        if tier not in fired and msg_count >= thresholds[tier]:
            # Tier 2 bei 48 Nachrichten → JA!
            mark_tier_fired(persona_id, session_id, tier)
            start_background_cortex_update(persona_id, session_id, tier)
            break  # Nur einen Tier pro Nachricht
```

---

## 6. Settings-Struktur für Tier-Konfiguration

### 6.1 Datei: `src/settings/cortex_settings.json`

Diese Datei wurde bereits in Schritt 2C definiert. Die Tier-relevanten Felder:

```json
{
    "enabled": true,
    "tiers": {
        "tier1": {
            "threshold": 50,
            "enabled": true
        },
        "tier2": {
            "threshold": 75,
            "enabled": true
        },
        "tier3": {
            "threshold": 95,
            "enabled": true
        }
    }
}
```

### 6.2 Felder-Referenz

| Feld | Typ | Default | Beschreibung |
|------|-----|---------|-------------|
| `enabled` | `bool` | `true` | Cortex-System global ein/aus |
| `tiers.tier1.threshold` | `int` | `50` | Schwellenwert in % des `contextLimit` — Stufe 1 |
| `tiers.tier1.enabled` | `bool` | `true` | Ob Stufe 1 aktiv ist |
| `tiers.tier2.threshold` | `int` | `75` | Schwellenwert in % des `contextLimit` — Stufe 2 |
| `tiers.tier2.enabled` | `bool` | `true` | Ob Stufe 2 aktiv ist |
| `tiers.tier3.threshold` | `int` | `95` | Schwellenwert in % des `contextLimit` — Stufe 3 |
| `tiers.tier3.enabled` | `bool` | `true` | Ob Stufe 3 aktiv ist |

### 6.3 Validierungsregeln

| Regel | Beschreibung |
|-------|-------------|
| `threshold` ∈ [5, 99] | Muss zwischen 5% und 99% liegen |
| `tier1 < tier2 < tier3` | Schwellen müssen aufsteigend sein |
| Mindest-Abstand: 10% | Zwischen Tiers müssen mindestens 10 Prozentpunkte liegen |
| Deaktivierte Tiers | Werden bei der Threshold-Berechnung übersprungen |

Die Validierung wird in der Route `PUT /api/cortex/settings` (Schritt 2C) durchgeführt:

```python
def _validate_tier_thresholds(tiers: dict) -> tuple[bool, str]:
    """Validiert die Tier-Schwellenwerte."""
    active_tiers = []
    for key in ['tier1', 'tier2', 'tier3']:
        tier = tiers.get(key, {})
        if tier.get('enabled', True):
            threshold = tier.get('threshold')
            if threshold is not None:
                if not (5 <= threshold <= 99):
                    return False, f"{key}.threshold muss zwischen 5 und 99 liegen"
                active_tiers.append((key, threshold))

    # Aufsteigende Reihenfolge prüfen
    for i in range(1, len(active_tiers)):
        prev_key, prev_val = active_tiers[i - 1]
        curr_key, curr_val = active_tiers[i]
        if curr_val <= prev_val:
            return False, f"{curr_key}.threshold ({curr_val}) muss größer als {prev_key}.threshold ({prev_val}) sein"
        if curr_val - prev_val < 10:
            return False, f"Mindestabstand zwischen {prev_key} und {curr_key}: 10 Prozentpunkte"

    return True, ""
```

---

## 7. Edge Cases

### 7.1 `contextLimit` ändert sich mid-conversation

**Szenario:** User startet Chat mit `contextLimit=65`, wechselt nach 30 Nachrichten zu `contextLimit=200`.

**Verhalten:**
- Die Schwellenwerte werden bei **jedem** Tier-Check neu berechnet
- Der `context_limit` kommt aus dem aktuellen Request (`data.get('context_limit')`)
- Bereits gefeuerte Tiers bleiben gefeuert (In-Memory State)
- Neue Tier-Schwellen werden gegen die neue Grenze berechnet

```
Vorher (contextLimit=65):
  Tier 1 bei 32 → bereits gefeuert bei Nachricht 32 ✓
  Tier 2 bei 48 → noch nicht erreicht

User ändert contextLimit auf 200:
  Tier 2 bei 150 → weit entfernt (aktuell 30 Nachrichten)
  Tier 3 bei 190 → weit entfernt
```

**Ergebnis:** Die höheren Tiers verschieben sich nach hinten. Das ist erwartetes Verhalten — ein größerer Kontext bedeutet mehr Nachrichten bevor ein Update nötig ist.

### 7.2 `contextLimit` wird verkleinert

**Szenario:** User hat `contextLimit=200`, wechselt nach 120 Nachrichten zu `contextLimit=65`.

```
Vorher (contextLimit=200):
  Tier 1 bei 100 → gefeuert bei Nachricht 100 ✓
  Tier 2 bei 150 → noch nicht erreicht

User ändert contextLimit auf 65:
  Tier 2 bei 48 → msg_count=120 ≥ 48 → NICHT gefeuert (Rebuild markiert als "already fired")
  Tier 3 bei 61 → msg_count=120 ≥ 61 → NICHT gefeuert (Rebuild markiert als "already fired")
```

**Verhalten:** Der Rebuild (Abschnitt 2.2, `rebuild_from_message_count`) erkennt, dass bei der neuen Berechnung Tier 2 und 3 schon überschritten wären, und markiert sie als "gefeuert" — ohne das Update tatsächlich auszuführen. Das ist konservativ korrekt: Lieber ein Update überspringen als den gleichen Kontext doppelt zu verarbeiten.

### 7.3 Session-Wechsel

**Szenario:** User wechselt von Session 5 zu Session 8.

**Verhalten:**
- Der Tier-State ist pro Session (`"{persona_id}:{session_id}"`)
- Session 5 behält ihren Tier-State
- Session 8 hat einen eigenen (möglicherweise leeren) State
- Beim ersten Chat in Session 8 wird der State ggf. rebuilt

### 7.4 Persona-Wechsel

**Szenario:** User wechselt von Default-Persona zu Custom-Persona.

**Verhalten:**
- Der Tier-State ist pro Persona+Session Kombination
- Verschiedene Personas haben eigene Cortex-Dateien → eigene Update-Zyklen
- `"default:5"` und `"custom123:5"` sind unabhängige Tier-States

### 7.5 `clear_chat` — Chat-Historie wird gelöscht

**Szenario:** User löscht den gesamten Chat.

**Verhalten:**
```python
# In src/routes/chat.py — clear_chat()
@chat_bp.route('/clear_chat', methods=['POST'])
def clear_chat():
    clear_chat_history()
    # NEU: Tier-State für die Session zurücksetzen
    reset_session(persona_id, session_id)
    return success_response()
```

Der Tier-State wird zurückgesetzt, damit bei neuen Nachrichten die Tiers erneut feuern können.

### 7.6 Server-Neustart

**Szenario:** App wird neu gestartet, User chattet in bestehender Session weiter.

**Verhalten:**
1. In-Memory State ist leer (`_fired_tiers = {}`)
2. Beim ersten Tier-Check wird `rebuild_from_message_count()` aufgerufen
3. Basierend auf der aktuellen Nachrichtenanzahl werden vergangene Tiers als "gefeuert" markiert
4. Nur der **nächste** noch nicht gefeuerte Tier kann auslösen

```
Beispiel: Session hat 50 Nachrichten, contextLimit=65
  → Rebuild: Tier 1 (32) → gefeuert, Tier 2 (48) → gefeuert
  → Nächster Trigger: Tier 3 bei 61
```

### 7.7 Gleichzeitige Updates vermeiden

**Szenario:** User sendet schnell hintereinander Nachrichten, ein Tier wird getriggert, aber der Background-Update läuft noch.

**Lösung:** Thread-Name als einfache Sperre:

```python
def _start_background_cortex_update(persona_id, session_id, context_limit, triggered_tier):
    """Startet Update nur wenn kein anderer für diese Persona läuft."""

    thread_name = f"cortex-update-{persona_id}"

    # Prüfe ob bereits ein Update-Thread für diese Persona läuft
    for thread in threading.enumerate():
        if thread.name == thread_name and thread.is_alive():
            log.info(
                "Cortex-Update übersprungen (Tier %d): Vorheriges Update läuft noch — Persona: %s",
                triggered_tier, persona_id
            )
            return

    thread = threading.Thread(
        target=_run_update,
        name=thread_name,
        daemon=True
    )
    thread.start()
```

> **Hinweis:** `mark_tier_fired()` wird trotzdem aufgerufen — der Tier gilt als gefeuert, auch wenn das Update übersprungen wurde, weil ein anderes noch läuft. Das nächste reguläre Update (nächster Tier) wird die Änderungen aufholen.

### 7.8 Kein API-Key konfiguriert

**Szenario:** Cortex ist aktiviert, aber kein API-Key ist vorhanden.

**Verhalten:** Der Tier-Check selbst läuft immer (ist nur ein Zahlenvergleich). Das Background-Update in `CortexUpdateService.execute_update()` prüft den API-Key und schlägt fehl → Log-Warnung. Der Tier wird als gefeuert markiert (kein Retry).

---

## 8. Frontend-Benachrichtigung (optionaler Indikator)

### 8.1 Überblick

Das Frontend kann optional anzeigen, dass ein Cortex-Update im Hintergrund läuft. Dies ist **kein** blockierendes UI-Element, sondern ein dezenter Indikator.

### 8.2 Ansatz: SSE-Event im done-Payload

Die einfachste Integration ist ein zusätzliches Feld im `done`-Event des Chat-Streams:

```python
# In chat.py — generate(), beim 'done' Event:
elif event_type == 'done':
    save_message(event_data['response'], False, character_name, session_id, persona_id=persona_id)
    stream_success = True

    # Tier-Check vorziehen für Frontend-Info
    triggered_tier = None
    try:
        triggered_tier = check_and_trigger_cortex_update(
            persona_id=persona_id,
            session_id=session_id,
            context_limit=context_limit
        )
    except Exception:
        pass

    done_payload = {
        'type': 'done',
        'response': event_data['response'],
        'stats': event_data['stats'],
        'character_name': character_name
    }

    # Optional: Cortex-Update-Info mitsenden
    if triggered_tier is not None:
        done_payload['cortex_update'] = {
            'triggered': True,
            'tier': triggered_tier
        }

    yield f"data: {json.dumps(done_payload)}\n\n"
```

> **Alternative zum Ansatz in Abschnitt 3.2:** Statt den Tier-Check **nach** dem letzten yield auszuführen, wird er **vor** dem done-yield ausgeführt, damit das `done`-Event die Cortex-Info enthalten kann. Der Background-Thread wird trotzdem erst nach dem yield gestartet (innerhalb von `check_and_trigger_cortex_update`).

### 8.3 Frontend-Handling in `useMessages.js`

```javascript
// In frontend/src/features/chat/hooks/useMessages.js
// Im onDone-Callback:

onDone: (data) => {
    setIsStreaming(false);
    setIsLoading(false);
    setStreamingStats(data.stats || null);

    // Finalize message
    updateLastMessage({
        message: data.response,
        _streaming: false,
        character_name: data.character_name,
        timestamp: new Date().toISOString(),
        stats: data.stats,
    });

    // NEU: Cortex-Update Benachrichtigung
    if (data.cortex_update?.triggered) {
        // Optional: Event emittieren für UI-Indikator
        window.dispatchEvent(new CustomEvent('cortex-update', {
            detail: { tier: data.cortex_update.tier }
        }));
    }

    if (get('notificationSound', false)) {
        playNotificationSound();
    }
},
```

### 8.4 UI-Indikator Konzept

```
┌─────────────────────────────────────────────┐
│              Chat-Interface                  │
│                                              │
│  [User] Hey, erzähl mir von deinem Tag      │
│                                              │
│  [Persona] Ach, heute war wirklich...        │
│                                              │
│  ┌──────────────────────────────────┐        │
│  │ 🧠 Cortex aktualisiert sich...  │        │  ← Dezenter Indikator
│  └──────────────────────────────────┘        │     (verschwindet nach ~3s)
│                                              │
│  [Nachricht eingeben...]                     │
└─────────────────────────────────────────────┘
```

Der Indikator:
- Erscheint nur wenn `cortex_update.triggered === true`
- Zeigt sich als kleine, nicht-blockierende Notification
- Verschwindet nach 3 Sekunden automatisch
- Wird in Schritt 5 (Cortex Settings UI) implementiert

---

## 9. Integration mit `chat/regenerate`

Der Tier-Check muss auch beim Regenerieren von Nachrichten greifen, da die Nachrichtenanzahl sich dabei nicht ändert (altes Bot-Msg gelöscht, neues generiert), aber es ist trotzdem ein vollständiger Chat-Cycle.

**Entscheidung:** Kein Tier-Check bei Regenerate. Die Nachrichtenanzahl bleibt gleich, also kann kein neuer Tier erreicht werden.

```python
# src/routes/chat.py — api_regenerate()
# KEIN Tier-Check nötig:
# - delete_last_message() entfernt die alte Bot-Nachricht
# - save_message() speichert die neue Bot-Nachricht
# - Netto-Änderung: 0 Nachrichten → kein neuer Tier möglich
```

---

## 10. Neue und geänderte Dateien

### 10.1 Neue Dateien

| Datei | Zweck |
|-------|-------|
| `src/utils/cortex/__init__.py` | Package-Init (Exports) |
| `src/utils/cortex/tier_tracker.py` | In-Memory Tracking der gefeuerten Tiers pro Session |
| `src/utils/cortex/tier_checker.py` | Tier-Prüfung und Background-Update Trigger |

### 10.2 Geänderte Dateien

| Datei | Änderung |
|-------|----------|
| `src/routes/chat.py` | Import `tier_checker`, Tier-Check nach Stream-Ende in `chat_stream()` und `clear_chat()` |

### 10.3 Abhängig von (noch nicht implementiert)

| Datei | Schritt | Zweck |
|-------|---------|-------|
| `src/utils/cortex/update_service.py` | 3A + 6 | `CortexUpdateService.execute_update()` — der eigentliche Tool-Use Call |
| `src/settings/cortex_settings.json` | 2C | Settings-Datei (wird von `_load_tier_config` gelesen) |

### 10.4 Package-Init

```python
# src/utils/cortex/__init__.py

"""
Cortex Utility Package — Aktivierungsstufen und Update-Logik.

Modules:
    tier_tracker — In-Memory State für gefeuerte Tiers pro Session
    tier_checker — Schwellenwert-Prüfung und Background-Update Trigger
    update_service — CortexUpdateService für Tool-Use API-Calls (Schritt 3A/6)
"""

from utils.cortex.tier_tracker import (
    get_fired_tiers,
    mark_tier_fired,
    reset_session,
    reset_all,
    rebuild_from_message_count
)
from utils.cortex.tier_checker import check_and_trigger_cortex_update

__all__ = [
    'get_fired_tiers',
    'mark_tier_fired',
    'reset_session',
    'reset_all',
    'rebuild_from_message_count',
    'check_and_trigger_cortex_update',
]
```

---

## 11. Zusammenfassung

```
                    ┌──────────────────────────────────────┐
                    │         Aktivierungsstufen-Logik       │
                    ├──────────────────────────────────────┤
                    │                                        │
                    │  contextLimit = 65 (User-Einstellung)  │
                    │                                        │
                    │  Tier 1: 50% = 32 Nachrichten          │
                    │  Tier 2: 75% = 48 Nachrichten          │
                    │  Tier 3: 95% = 61 Nachrichten          │
                    │                                        │
                    │  ──────────────────────────────────     │
                    │                                        │
                    │  Nachricht 31: ❌ Kein Tier             │
                    │  Nachricht 32: ✅ Tier 1 → Update      │
                    │  Nachricht 33: ❌ Tier 1 schon gefeuert│
                    │  ...                                    │
                    │  Nachricht 48: ✅ Tier 2 → Update      │
                    │  ...                                    │
                    │  Nachricht 61: ✅ Tier 3 → Update      │
                    │  Nachricht 62: ❌ Alle Tiers gefeuert  │
                    │                                        │
                    │  ──────────────────────────────────     │
                    │                                        │
                    │  Pro Tier: 1x feuern, Background-      │
                    │  Thread, non-blocking, tool_use Call    │
                    │                                        │
                    └──────────────────────────────────────┘
```

---

## 12. Abhängigkeiten zu anderen Schritten

| Abhängigkeit | Richtung | Details |
|-------------|----------|---------|
| **Schritt 2C** (Cortex API Routes) | ← Voraussetzung | `cortex_settings.json` Lesen/Schreiben, Settings-Endpoints |
| **Schritt 3A** (Tool-Use API Client) | ← Voraussetzung | `ApiClient.tool_request()` für den Background-Update |
| **Schritt 6** (API Integration) | → Nachfolger | `CortexUpdateService` implementiert den eigentlichen Update-Call |
| **Schritt 5** (Cortex Settings UI) | → Nachfolger | UI zum Konfigurieren der Tier-Schwellenwerte |
