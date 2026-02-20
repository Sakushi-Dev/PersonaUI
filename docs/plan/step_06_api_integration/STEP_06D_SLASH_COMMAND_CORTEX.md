# Schritt 6D: Slash Command `/cortex` — Sofortiger Trigger

## Übersicht

Der Slash Command `/cortex` ermöglicht es dem User, jederzeit **manuell** ein Cortex-Update auszulösen — unabhängig vom automatischen Frequenz-Trigger. Nach Ausführung wird der `cycle_base` auf `0` zurückgesetzt, sodass der nächste automatische Trigger wieder ab der aktuellen Nachrichtenanzahl zählt.

### Verhalten

```
1. User tippt /cortex im Chat-Input
2. Frontend ruft POST /api/commands/cortex-update
3. Backend:
   a) Prüft ob Cortex aktiviert ist
   b) Startet sofort CortexUpdateService im Background-Thread
   c) Setzt cycle_base = aktuelle message_count (Reset)
   d) Gibt Erfolg + Progress-Daten zurück
4. Frontend zeigt kurze Bestätigung ("🧠 Cortex-Update gestartet")
```

### Unterschied zum automatischen Trigger

| Aspekt | Automatischer Trigger | `/cortex` Command |
|--------|----------------------|-------------------|
| **Auslöser** | Schwelle erreicht (`messages_since_reset >= threshold`) | Manuelle User-Eingabe |
| **Prüfung** | Nachrichtenanzahl vs. Schwelle | Keine — sofortige Ausführung |
| **Voraussetzung** | Cortex enabled + genug Nachrichten | Cortex enabled + min. 1 Nachricht in Session |
| **Reset** | `cycle_base = message_count` | `cycle_base = message_count` (identisch) |
| **Persistenz** | Persistent in `cycle_state.json` | Persistent in `cycle_state.json` (identisch) |
| **Frequenz** | Bestimmt durch Setting (Häufig/Mittel/Selten) | Irrelevant — wird einfach ausgeführt |

---

## 1. Backend: Neuer Endpoint in `commands.py`

### 1.1 Route: `POST /api/commands/cortex-update`

```python
# ═══════════════════════════════════════════════════════════════
#  NEUER ENDPOINT in: src/routes/commands.py
# ═══════════════════════════════════════════════════════════════

import json

from utils.logger import log
from utils.database import get_message_count
from utils.cortex.tier_tracker import set_cycle_base, get_progress
from utils.cortex.tier_checker import (
    _load_cortex_config,
    _get_context_limit,
    _calculate_threshold,
    _start_background_cortex_update,
    FREQUENCIES,
    DEFAULT_FREQUENCY,
)
from utils.session_context import get_active_persona_id, get_active_session_id


@commands_bp.route('/api/commands/cortex-update', methods=['POST'])
@handle_route_error('cortex_update')
def cortex_update():
    """
    Slash Command: /cortex — Sofortiger Cortex-Update + Zähler-Reset.

    Prüft:
    - Cortex aktiviert?
    - Session hat Nachrichten?

    Startet Background-Update und gibt Progress-Daten zurück.
    """
    # 1. Cortex aktiviert?
    config = _load_cortex_config()
    if not config.get("enabled", False):
        return error_response("Cortex ist deaktiviert", 400)

    # 2. Aktive Session/Persona ermitteln
    persona_id = get_active_persona_id()
    session_id = get_active_session_id()

    if not persona_id or not session_id:
        return error_response("Keine aktive Session", 400)

    # 3. Session hat Nachrichten?
    message_count = get_message_count(session_id=session_id, persona_id=persona_id)
    if message_count == 0:
        return error_response("Keine Nachrichten in der Session", 400)

    # 4. Zähler-Reset: cycle_base = aktuelle message_count
    set_cycle_base(persona_id, session_id, message_count)

    # 5. Background-Update starten
    _start_background_cortex_update(persona_id, session_id)

    log.info(
        "[/cortex] Manueller Cortex-Update gestartet — Persona: %s, Session: %s, "
        "Messages: %d",
        persona_id, session_id, message_count
    )

    # 6. Progress-Daten für Frontend (nach Reset = 0%)
    frequency = config.get("frequency", DEFAULT_FREQUENCY)
    context_limit = _get_context_limit()
    threshold = _calculate_threshold(context_limit, frequency)
    progress = get_progress(persona_id, session_id, message_count, threshold)

    return success_response(
        message="Cortex-Update gestartet",
        cortex={
            "triggered": True,
            "progress": progress,
            "frequency": frequency
        }
    )
```

### 1.2 Benötigte Imports in `commands.py`

Zusätzlich zu den bestehenden Imports:

```python
# NEUE Imports (ergänzen)
from utils.cortex.tier_tracker import set_cycle_base, get_progress
from utils.cortex.tier_checker import (
    _load_cortex_config,
    _get_context_limit,
    _calculate_threshold,
    _start_background_cortex_update,
    FREQUENCIES,
    DEFAULT_FREQUENCY,
)
from utils.session_context import get_active_persona_id, get_active_session_id
```

### 1.3 Hinweis: `session_context`

Der Endpoint braucht `persona_id` und `session_id`. Diese kommen **nicht** aus dem Request-Body (Slash Commands senden keine Argumente), sondern aus dem Server-seitigen Session-Context.

> **TODO:** Falls `get_active_persona_id()` / `get_active_session_id()` noch nicht existieren, müssen Hilfsfunktionen erstellt werden, die den aktuellen State aus `Flask.g`, Session-Cookie oder dem globalen App-State auslesen. Alternativ: Request-Body mit `persona_id` + `session_id` vom Frontend mitsenden (wie bei `/chat_stream`).

**Alternative: Frontend sendet IDs im Body:**

```python
@commands_bp.route('/api/commands/cortex-update', methods=['POST'])
@handle_route_error('cortex_update')
def cortex_update():
    data = request.get_json(silent=True) or {}
    persona_id = data.get('persona_id') or get_active_persona_id()
    session_id = data.get('session_id') or get_active_session_id()
    # ...Rest wie oben...
```

```javascript
// Frontend sendet IDs mit:
const res = await fetch('/api/commands/cortex-update', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ persona_id, session_id })
});
```

---

## 2. Frontend: Slash Command Registration

### 2.1 Neuer Command in `builtinCommands.js`

```javascript
// ═══════════════════════════════════════════════════════════════
//  NEUER COMMAND in: frontend/src/features/chat/slashCommands/builtinCommands.js
// ═══════════════════════════════════════════════════════════════

// /cortex – Sofort Cortex-Update auslösen und Zähler auf 0 zurücksetzen
register({
  name: 'cortex',
  description: 'Cortex-Update sofort auslösen (Zähler wird zurückgesetzt)',
  async execute() {
    console.log('[SlashCommand] /cortex – starte manuellen Cortex-Update …');

    try {
      const res = await fetch('/api/commands/cortex-update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          // Optional: persona_id und session_id mitsenden
          // Falls der Server sie nicht aus dem Session-Context holen kann
        })
      });

      const data = await res.json().catch(() => ({}));

      if (!res.ok || !data.success) {
        const msg = data.error || 'Unbekannter Fehler';
        console.error('[SlashCommand] /cortex fehlgeschlagen:', msg);
        // Keine alert() — dezente Benachrichtigung über Event
        window.dispatchEvent(new CustomEvent('cortex-command-error', {
          detail: { error: msg }
        }));
        return;
      }

      console.log('[SlashCommand] /cortex – Update gestartet.');

      // Progress-Bar auf 0% zurücksetzen + Trigger-Notification anzeigen
      if (data.cortex) {
        window.dispatchEvent(new CustomEvent('cortex-progress', {
          detail: {
            ...data.cortex,
            manual: true  // Kennzeichnung: manueller Trigger via /cortex
          }
        }));
      }
    } catch (err) {
      console.error('[SlashCommand] /cortex Netzwerk-Fehler:', err);
      window.dispatchEvent(new CustomEvent('cortex-command-error', {
        detail: { error: err.message }
      }));
    }
  },
});
```

### 2.2 Event-Behandlung im Frontend

Der `/cortex` Command dispatcht dasselbe `cortex-progress` Event wie der automatische Trigger im `done`-Event. Dadurch reagiert die Progress Bar identisch — mit einem zusätzlichen `manual: true` Flag für optionale UI-Unterscheidung.

```javascript
// In CortexUpdateIndicator oder ChatPage:
useEffect(() => {
  const handleProgress = (e) => {
    const cortexData = e.detail;
    setProgress(cortexData.progress);

    if (cortexData.triggered) {
      // Kurze Notification anzeigen
      const label = cortexData.manual
        ? '🧠 Manueller Cortex-Update gestartet'
        : '🧠 Cortex aktualisiert sich…';
      showNotification(label, 3000);
    }
  };

  const handleError = (e) => {
    showNotification(`⚠️ ${e.detail.error}`, 5000);
  };

  window.addEventListener('cortex-progress', handleProgress);
  window.addEventListener('cortex-command-error', handleError);
  return () => {
    window.removeEventListener('cortex-progress', handleProgress);
    window.removeEventListener('cortex-command-error', handleError);
  };
}, []);
```

---

## 3. Zähler-Reset-Logik

### 3.1 Was passiert beim Reset

```
Vor /cortex:
  contextLimit = 65, Frequenz = Mittel (75%), Schwelle = 48
  cycle_base = 48, message_count = 70
  messages_since_reset = 22
  Progress: 22/48 = 45.8%

User tippt /cortex:
  → Backend: set_cycle_base(persona_id, session_id, 70)
  → cycle_base wird 70
  → messages_since_reset = 70 - 70 = 0
  → Progress: 0%
  → Nächster automatischer Trigger bei message_count = 70 + 48 = 118

Nach /cortex:
  cycle_base = 70, message_count = 70
  Progress: 0%
  Nächster Trigger bei 118 Nachrichten

Nach Server-Neustart:
  → cycle_state.json enthält {"default:5": 70}
  → cycle_base = 70 (exakt wiederhergestellt)
  → Progress und nächster Trigger bleiben identisch
```

### 3.2 Visualisierung

```
Msg:  0      48      70      96      118     166
      ├──────┤───────┤───────┤───────┤───────┤──
      │  Zyklus 1   │ /cortex│  Zyklus (neu) │  Zyklus 3
      └──►AUTO-UPD  └──►MAN  └───────────────└──►AUTO-UPD
                     Reset=70                 Reset=118

      Progress Bar:
      [████████████████████] 100% → AUTO-UPDATE
      [████████░░░░░░░░░░░]  46%
      [░░░░░░░░░░░░░░░░░░░]   0% → /cortex → MANUELL
      [████████████████████] 100% → AUTO-UPDATE
```

### 3.3 Edge Case: Sofort nach Auto-Trigger

Wenn der automatische Trigger bei Nachricht 48 fired und der User direkt `/cortex` tippt:

```
message_count = 49 (die nächste Nachricht nach Auto-Trigger)
cycle_base (nach Auto) = 48
→ /cortex: cycle_base = 49, neuer Background-Update
→ Nächster Auto-Trigger bei 49 + 48 = 97
```

Das ist korrekt — der User hat explizit ein Update angefordert. Doppel-Updates sind unproblematisch, da sie in derselben Conversation-History operieren.

### 3.4 Edge Case: Laufendes Update

```python
# In _start_background_cortex_update():
for t in threading.enumerate():
    if t.name == thread_name and t.is_alive():
        log.info("Cortex-Update übersprungen: läuft bereits — Persona: %s", persona_id)
        return
```

Wenn bereits ein Background-Update läuft (z.B. Auto-Trigger gerade erst ausgelöst), wird der `/cortex`-Trigger trotzdem den `cycle_base` zurücksetzen, aber **kein zweites Update** starten. Das ist gewollt:
- Der cycle_base-Reset ist sofort wirksam
- Das laufende Update wird nicht unterbrochen
- Der Response enthält `"triggered": true` (cycle_base wurde resettet), Backend loggt den Skip

### 3.5 Edge Case: Server-Neustart nach `/cortex`

Der manuelle Reset ist **persistent** — `set_cycle_base()` schreibt sofort in `cycle_state.json` (atomarer Write via `os.replace`). Nach Neustart wird der exakte `cycle_base`-Wert aus der Datei geladen. Kein Datenverlust, keine Approximation.

---

## 4. API Response Format

### 4.1 Erfolg

```json
{
    "success": true,
    "message": "Cortex-Update gestartet",
    "cortex": {
        "triggered": true,
        "progress": {
            "messages_since_reset": 0,
            "threshold": 48,
            "progress_percent": 0.0,
            "cycle_number": 3
        },
        "frequency": "medium"
    }
}
```

### 4.2 Fehler: Cortex deaktiviert

```json
{
    "success": false,
    "error": "Cortex ist deaktiviert"
}
```

### 4.3 Fehler: Keine Nachrichten

```json
{
    "success": false,
    "error": "Keine Nachrichten in der Session"
}
```

---

## 5. Autocomplete-Integration

Der Command `/cortex` erscheint wie alle anderen Commands in der `SlashCommandMenu`-Popup:

```
User tippt: /cor

┌─────────────────────────────────────────────┐
│  /cortex  Cortex-Update sofort auslösen … │ ← einziger Treffer
└─────────────────────────────────────────────┘
```

Kein spezielles Verhalten nötig — die bestehende Registry-Suche (`startsWith` + `includes`) findet den Command automatisch.

---

## 6. Betroffene Dateien

### 6.1 Geänderte Dateien

| Datei | Änderung |
|-------|----------|
| `src/routes/commands.py` | Neuer Endpoint `POST /api/commands/cortex-update` |
| `frontend/src/features/chat/slashCommands/builtinCommands.js` | Neuer Command `/cortex` registrieren |

### 6.2 Evtl. geänderte Dateien

| Datei | Änderung | Bedingung |
|-------|----------|-----------|
| `src/utils/cortex/tier_checker.py` | Hilfsfunktionen public machen (Underscore entfernen) | Falls private `_`-Prefix stört |
| `src/utils/session_context.py` (NEU) | Session/Persona-Ermittlung | Falls nicht aus Request-Body |

### 6.3 Abhängigkeiten

| Komponente | Schritt | Abhängigkeit |
|------------|---------|-------------|
| `tier_tracker.set_cycle_base()` | 3B | Zähler-Reset |
| `tier_tracker.get_progress()` | 3B | Progress-Daten für Response |
| `tier_checker._start_background_cortex_update()` | 3B | Background-Thread starten |
| `tier_checker._load_cortex_config()` | 3B | Settings lesen |
| `tier_checker._calculate_threshold()` | 3B | Schwelle berechnen |
| `CortexUpdateService` | 3C | Eigentliches Update via tool_use |
| `SlashCommandRegistry` | Bestehend | Command-Registrierung |

---

## 7. Design-Entscheidungen

| Entscheidung | Gewählt | Alternative | Begründung |
|-------------|---------|-------------|------------|
| API Endpoint statt Frontend-only | ✅ Server | Frontend-only | Update braucht Server-seitige Logik (Background-Thread, DB, tool_use) |
| Gleicher Reset wie Auto-Trigger | ✅ `set_cycle_base(msg_count)` | Separater Reset auf 0 | Konsistent — beide Wege nutzen denselben Mechanismus |
| `cortex-progress` Event wiederverwenden | ✅ Gleicher Event | Eigener `cortex-manual` Event | Weniger Code, Progress Bar reagiert identisch |
| `manual: true` Flag | ✅ Im Event-Detail | Separater Event-Name | Ermöglicht optionale UI-Unterscheidung ohne eigenen Listener |
| Kein Argument-Parsing | ✅ Keine Args | `/cortex force` etc. | KISS — es gibt nur eine Aktion |
| Skip bei laufendem Update | ✅ Skip Thread, Reset trotzdem | Queue / Cancel | Thread-Name-Sperre ist ausreichend, kein Race Condition |

---

## 8. Implementierungsreihenfolge

```
1. Backend: Cortex-Modul (Schritt 3B) muss existieren
          ↓
2. Backend: Endpoint in commands.py hinzufügen
          ↓
3. Frontend: Command in builtinCommands.js registrieren
          ↓
4. Frontend: cortex-command-error Event-Handling (optional)
          ↓
5. Test: /cortex im Chat-Input tippen → Update startet → Progress reset
```

Der Command kann als **letzter Integrationsschritt** nach Step 6A (Chat-Flow) implementiert werden, da er dieselbe Infrastruktur nutzt.

---

## 9. Zusammenfassung

```
/cortex — Manueller Sofort-Trigger
────────────────────────────────────

  User: /cortex
    ↓
  Frontend → POST /api/commands/cortex-update
    ↓
  Backend:
    ✓ Cortex enabled?
    ✓ Aktive Session + Nachrichten?
    → set_cycle_base(message_count)     ← Zähler-Reset
    → _start_background_cortex_update()  ← Update im Thread
    ← { success, cortex: { triggered, progress, frequency } }
    ↓
  Frontend:
    → dispatch 'cortex-progress' Event (manual: true)
    → Progress Bar: 0%
    → Notification: "🧠 Manueller Cortex-Update gestartet"
```
