# Schritt 4A: Computed Placeholders für Cortex

## Übersicht

Die drei Cortex-Dateien (`memory.md`, `soul.md`, `relationship.md`) müssen zur Laufzeit in den System-Prompt injiziert werden. Dafür werden drei neue Placeholders registriert:

| Placeholder | Datei | Beschreibung |
|---|---|---|
| `{{cortex_memory}}` | `memory.md` | Faktenwissen, Vorlieben, wichtige Details |
| `{{cortex_soul}}` | `soul.md` | Persönlichkeitsentwicklung, innere Haltung |
| `{{cortex_relationship}}` | `relationship.md` | Beziehungsdynamik, gemeinsame Geschichte |

Diese Placeholders werden in den Prompt-Templates (Schritt 4B) verwendet, z.B.:

```
{{cortex_memory}}
{{cortex_soul}}
{{cortex_relationship}}
```

---

## 1. Analyse: Architektur-Optionen

### Das Problem

Der `PlaceholderResolver` kennt aktuell zwei Datenquellen für **static** Placeholders:

- `persona_config` → liest aus `persona_config.json`
- `user_profile` → liest aus `user_profile.json`

Und registrierte **compute functions** für **computed** Placeholders:

- `build_character_description`, `build_char_core_traits`, etc.
- `get_time_context.current_date`, etc.

Der Resolver hat **keinen Zugriff** auf den `CortexService` (aus Step 2B). Die Cortex-Daten müssen aber zur Resolution-Zeit verfügbar sein.

### Option A: Runtime-Vars aus ChatService (EMPFOHLEN)

**Prinzip:** ChatService liest Cortex-Dateien vor dem Prompt-Build und übergibt die Inhalte als `runtime_vars` an die PromptEngine.

```
ChatService
  ├── CortexService.get_cortex_for_prompt(persona_id)
  │     → { cortex_memory: "...", cortex_soul: "...", cortex_relationship: "..." }
  │
  └── engine.build_system_prompt(variant, runtime_vars={
        'language': 'de',
        'cortex_memory': '...',     ← NEU
        'cortex_soul': '...',       ← NEU
        'cortex_relationship': '...'← NEU
      })
```

| Pro | Contra |
|-----|--------|
| Kein Umbau am PlaceholderResolver nötig | ChatService muss Cortex-Daten explizit laden |
| Nutzt bestehendes Phase-3-Pattern (`runtime_vars`) | Daten werden bei jedem Request gelesen (kein Caching) |
| Klare Datenfluss-Richtung: Service → Engine | 3 zusätzliche Keys in `runtime_vars` |
| Testbar: Cortex-Daten leicht mockbar | — |
| CortexService.get_cortex_for_prompt() existiert bereits (2B) | — |

### Option B: CortexService-Referenz im PlaceholderResolver

**Prinzip:** Der PlaceholderResolver erhält eine Referenz auf den CortexService und ruft `read_file()` in einer compute function auf.

```python
# PlaceholderResolver.__init__():
self._cortex_service = cortex_service  # Neue Dependency

# Neue compute function:
def _compute_cortex_memory(self):
    persona_id = get_active_persona_id()
    return self._cortex_service.read_file(persona_id, 'memory.md')
```

| Pro | Contra |
|-----|--------|
| Echte "computed" Placeholder (Phase 2) | PlaceholderResolver bekommt Service-Dependency |
| Automatisch bei jedem resolve_text() verfügbar | Zirkuläre Abhängigkeit: Engine → Resolver → Service → Engine? |
| Kein Aufwand im ChatService nötig | Init-Reihenfolge wird komplexer |
| — | PlaceholderResolver wird weniger rein (side effects) |
| — | Schwerer testbar (Service muss gemockt werden) |

### Option C: Direkte Datei-Reads im PlaceholderResolver

**Prinzip:** Der PlaceholderResolver liest Cortex-Dateien direkt vom Dateisystem, ohne CortexService.

```python
def _compute_cortex_memory(self):
    persona_id = get_active_persona_id()
    path = os.path.join(CORTEX_DIR, persona_id, 'memory.md')
    return open(path).read() if os.path.exists(path) else ''
```

| Pro | Contra |
|-----|--------|
| Einfache Implementierung | Dupliziert Pfad-Logik aus CortexService |
| Kein Service-Import nötig | Kein Lazy-Init (ensure_cortex_files) |
| — | Kein Logging/Error-Handling aus CortexService |
| — | Verstößt gegen Single-Responsibility |
| — | Zwei Code-Pfade für denselben Dateizugriff |

### Entscheidung: Option A — runtime_vars aus ChatService

**Begründung:**

1. **Kein Engine-Umbau nötig** — der `PlaceholderResolver` bleibt unverändert
2. **Bewährtes Pattern** — `memory_entries`, `elapsed_time`, `language` werden bereits so übergeben
3. **CortexService.get_cortex_for_prompt()** existiert bereits aus Step 2B — genau für diesen Zweck entworfen
4. **Klare Ownership** — ChatService orchestriert, Engine resolvet
5. **Testbarkeit** — runtime_vars können in Tests als einfache Dicts übergeben werden

---

## 2. Placeholder-Registry Einträge

Die drei neuen Placeholders werden in `placeholder_registry.json` registriert. Sie verwenden `resolve_phase: "runtime"` und `source: "runtime"`, weil die Daten vom ChatService als runtime_vars kommen.

### 2.1 Registry-Format

```json
{
  "cortex_memory": {
    "name": "Cortex Memory",
    "description": "Inhalt der memory.md — Faktenwissen, Vorlieben, wichtige Details über den User",
    "source": "runtime",
    "type": "string",
    "default": "",
    "category": "cortex",
    "resolve_phase": "runtime"
  },
  "cortex_soul": {
    "name": "Cortex Soul",
    "description": "Inhalt der soul.md — Persönlichkeitsentwicklung, innere Haltung, emotionale Muster",
    "source": "runtime",
    "type": "string",
    "default": "",
    "category": "cortex",
    "resolve_phase": "runtime"
  },
  "cortex_relationship": {
    "name": "Cortex Relationship",
    "description": "Inhalt der relationship.md — Beziehungsdynamik, gemeinsame Geschichte, Vertrauenslevel",
    "source": "runtime",
    "type": "string",
    "default": "",
    "category": "cortex",
    "resolve_phase": "runtime"
  }
}
```

### 2.2 Einordnung in bestehende Kategorien

| Kategorie | Bestehende Placeholder | Neu |
|---|---|---|
| `persona` | `char_name`, `char_age`, `char_description`, ... | — |
| `user` | `user_name`, `user_gender`, `user_info`, ... | — |
| `context` | `current_date`, `current_time`, `memory_entries`, `history` | — |
| `afterthought` | `elapsed_time`, `inner_dialogue` | — |
| **`cortex`** | — | **`cortex_memory`, `cortex_soul`, `cortex_relationship`** |

Die neue Kategorie `cortex` gruppiert alle Cortex-bezogenen Placeholders und ermöglicht spätere Erweiterungen (z.B. `cortex_summary`, `cortex_goals`).

---

## 3. Code-Flow: ChatService → Cortex → Engine → Prompt

### 3.1 Sequenzdiagramm

```
User Request
     │
     ▼
┌─────────────────────┐
│    ChatService       │
│    chat_stream()     │
│                      │
│  1. variant bestimmen│
│  2. runtime_vars = { │
│       'language': .. │
│     }                │
│                      │
│  3. Cortex laden:    │────► CortexService.get_cortex_for_prompt(persona_id)
│     cortex_data =    │◄──── { cortex_memory: "...", cortex_soul: "...",
│       {...}          │        cortex_relationship: "..." }
│                      │
│  4. runtime_vars     │
│     .update(cortex)  │
│                      │
│  5. engine.build_    │────► PromptEngine.build_system_prompt(variant, runtime_vars)
│     system_prompt()  │         │
│                      │         ▼
│                      │      PlaceholderResolver.resolve_text(text, variant, runtime_vars)
│                      │         │
│                      │         ├── Phase 1: static (char_name, user_name, ...)
│                      │         ├── Phase 2: computed (current_date, char_description, ...)
│                      │         └── Phase 3: runtime (language, cortex_memory, cortex_soul, ...)
│                      │                              ▲
│                      │◄──── aufgelöster System-Prompt
│                      │
│  6. Messages bauen   │
│  7. API aufrufen     │
└─────────────────────┘
```

### 3.2 ChatService: Cortex-Daten laden und übergeben

Die Änderung betrifft **drei Methoden** im ChatService, die `build_system_prompt()` aufrufen:

1. `chat_stream()` — Haupt-Chat
2. `afterthought_decision()` — Innerer Dialog
3. `afterthought_followup_stream()` — Followup-Nachricht

In jeder Methode wird **vor** dem `build_system_prompt()`-Aufruf der Cortex-Kontext geladen:

```python
# ─── ChatService.chat_stream() ────────────────────────────────────

def chat_stream(self, user_message, conversation_history, character_data,
                language='de', user_name='User', api_model=None,
                api_temperature=None, include_memories=True,
                ip_address=None, experimental_mode=False,
                persona_id=None, pending_afterthought=None):
    # ...bestehender Code...

    # 1. System-Prompt via PromptEngine bauen
    variant = 'experimental' if experimental_mode else 'default'
    system_prompt = ''
    if self._engine:
        runtime_vars = {'language': language}
        if ip_address:
            runtime_vars['ip_address'] = ip_address

        # ── NEU: Cortex-Daten laden ──────────────────────────────
        cortex_data = self._load_cortex_context(persona_id)
        runtime_vars.update(cortex_data)
        # ─────────────────────────────────────────────────────────

        system_prompt = self._engine.build_system_prompt(
            variant=variant, runtime_vars=runtime_vars
        ) or ''
```

### 3.3 Neue Hilfsmethode: `_load_cortex_context()`

Analog zur bestehenden `_load_memory_context()` wird eine neue Methode hinzugefügt:

```python
def _load_cortex_context(self, persona_id: str = None) -> Dict[str, str]:
    """
    Lädt Cortex-Dateien für die Placeholder-Auflösung.

    Liest memory.md, soul.md und relationship.md über den CortexService
    und gibt sie als Dict zurück, das direkt in runtime_vars gemergt wird.

    Returns:
        {
            'cortex_memory': '...',
            'cortex_soul': '...',
            'cortex_relationship': '...',
        }
        Bei Fehler: Alle Werte sind leere Strings.
    """
    try:
        from ..provider import get_cortex_service
        cortex_service = get_cortex_service()

        if persona_id is None:
            from ..config import get_active_persona_id
            persona_id = get_active_persona_id()

        return cortex_service.get_cortex_for_prompt(persona_id)
    except Exception as e:
        log.warning("Cortex-Kontext konnte nicht geladen werden: %s", e)
        return {
            'cortex_memory': '',
            'cortex_soul': '',
            'cortex_relationship': '',
        }
```

**Analogie zu bestehendem Pattern:**

| Bestehend | Neu |
|---|---|
| `_load_memory_context(persona_id)` → `str` | `_load_cortex_context(persona_id)` → `Dict[str, str]` |
| Lädt SQL-Memories, formatiert für Prompt | Lädt Cortex-Dateien, gibt Dict für runtime_vars |
| Ergebnis → `memory_context` Variable | Ergebnis → `runtime_vars.update(...)` |

---

## 4. Änderungen pro Methode im ChatService

### 4.1 `chat_stream()` (Zeile ~254–258)

**Vorher:**
```python
runtime_vars = {'language': language}
if ip_address:
    runtime_vars['ip_address'] = ip_address
system_prompt = self._engine.build_system_prompt(variant=variant, runtime_vars=runtime_vars) or ''
```

**Nachher:**
```python
runtime_vars = {'language': language}
if ip_address:
    runtime_vars['ip_address'] = ip_address

# Cortex-Kontext laden und als runtime_vars übergeben
cortex_data = self._load_cortex_context(persona_id)
runtime_vars.update(cortex_data)

system_prompt = self._engine.build_system_prompt(variant=variant, runtime_vars=runtime_vars) or ''
```

### 4.2 `afterthought_decision()` (Zeile ~347–355)

**Vorher:**
```python
runtime_vars = {
    'language': language,
    'elapsed_time': elapsed_time,
}
if ip_address:
    runtime_vars['ip_address'] = ip_address
# ...
system_prompt = self._engine.build_system_prompt(variant=variant, runtime_vars=runtime_vars) or ''
```

**Nachher:**
```python
runtime_vars = {
    'language': language,
    'elapsed_time': elapsed_time,
}
if ip_address:
    runtime_vars['ip_address'] = ip_address

# Cortex-Kontext laden
cortex_data = self._load_cortex_context(persona_id)
runtime_vars.update(cortex_data)

system_prompt = self._engine.build_system_prompt(variant=variant, runtime_vars=runtime_vars) or ''
```

### 4.3 `afterthought_followup_stream()` (Zeile ~443–454)

**Vorher:**
```python
runtime_vars = {
    'language': language,
    'elapsed_time': elapsed_time,
    'inner_dialogue': inner_dialogue,
}
if ip_address:
    runtime_vars['ip_address'] = ip_address
# ...
system_prompt = self._engine.build_system_prompt(variant=variant, runtime_vars=runtime_vars) or ''
```

**Nachher:**
```python
runtime_vars = {
    'language': language,
    'elapsed_time': elapsed_time,
    'inner_dialogue': inner_dialogue,
}
if ip_address:
    runtime_vars['ip_address'] = ip_address

# Cortex-Kontext laden
cortex_data = self._load_cortex_context(persona_id)
runtime_vars.update(cortex_data)

system_prompt = self._engine.build_system_prompt(variant=variant, runtime_vars=runtime_vars) or ''
```

---

## 5. CortexService.get_cortex_for_prompt() — Bereits definiert (Step 2B)

Diese Methode existiert bereits aus der Step-2B-Spezifikation:

```python
# CortexService (aus STEP_02B_CORTEX_SERVICE.md)

def get_cortex_for_prompt(self, persona_id: str) -> Dict[str, str]:
    """
    Liest Cortex-Dateien und formatiert sie als Placeholder-Werte.

    Returns:
        {
            'cortex_memory': '...',       # Inhalt von memory.md (stripped)
            'cortex_soul': '...',         # Inhalt von soul.md (stripped)
            'cortex_relationship': '...', # Inhalt von relationship.md (stripped)
        }
    """
    files = self.read_all(persona_id)
    return {
        'cortex_memory': files['memory'].strip(),
        'cortex_soul': files['soul'].strip(),
        'cortex_relationship': files['relationship'].strip(),
    }
```

Die Keys matchen exakt die Placeholder-Namen in der Registry. Kein Mapping nötig.

---

## 6. Resolution-Ablauf im Detail

### Phase 1: Static (gecached)
```
char_name       ← persona_config.json → "Luna"
char_age        ← persona_config.json → "24"
user_name       ← user_profile.json   → "Max"
...
```

### Phase 2: Computed (frisch berechnet)
```
current_date    ← get_time_context()   → "20.02.2026"
char_description← build_char_desc()    → "Luna ist eine 24-jährige..."
char_core_traits← build_char_traits()  → "Einfühlsam: ..."
...
```

### Phase 3: Runtime (vom Aufrufer)
```
language        ← ChatService          → "de"
cortex_memory   ← ChatService          → "# Erinnerungen\n\n- Max liebt Katzen..."
cortex_soul     ← ChatService          → "# Identität\n\nIch bin Luna..."
cortex_relationship ← ChatService      → "# Beziehungsstatus\n\nMax und ich..."
```

### Priorität bei Namenskollision

`runtime_vars` (Phase 3) überschreiben `computed` (Phase 2), die `static` (Phase 1) überschreiben:

```python
# PlaceholderResolver._build_variables():
variables = {}
variables.update(self._resolve_static())    # Phase 1
variables.update(self._resolve_computed())   # Phase 2 überschreibt Phase 1
if runtime_vars:
    variables.update(runtime_vars)           # Phase 3 überschreibt Phase 2
return variables
```

Die Cortex-Placeholder (`cortex_memory`, `cortex_soul`, `cortex_relationship`) sind unique — keine Kollisionsgefahr mit bestehenden Placeholder-Namen.

---

## 7. Betroffene Dateien

### Geänderte Dateien

| Datei | Änderung |
|---|---|
| `src/instructions/prompts/_meta/placeholder_registry.json` | +3 neue Einträge (`cortex_memory`, `cortex_soul`, `cortex_relationship`) |
| `src/utils/services/chat_service.py` | +1 neue Methode `_load_cortex_context()`, 3 Methoden erweitert um Cortex-Loading |

### Unveränderte Dateien

| Datei | Warum unverändert |
|---|---|
| `src/utils/prompt_engine/placeholder_resolver.py` | Runtime-Vars werden nativ unterstützt — kein Umbau nötig |
| `src/utils/prompt_engine/engine.py` | `build_system_prompt()` leitet `runtime_vars` bereits durch |
| `src/utils/services/cortex_service.py` | `get_cortex_for_prompt()` existiert bereits (Step 2B) |
| `src/utils/prompt_builder/chat.py` | Legacy-Pfad, wird nicht mehr aktiv für Engine-Prompts verwendet |

### Neue Dateien

Keine — alle Änderungen finden in bestehenden Dateien statt.

---

## 8. Validierung & Tests

### 8.1 Registry-Validierung

Der PlaceholderResolver lädt die Registry beim Start. Neue Einträge mit `resolve_phase: "runtime"` werden automatisch erkannt — sie werden nicht in Phase 1/2 verarbeitet, sondern warten auf runtime_vars.

**Prüfpunkte:**
- Registry-JSON ist valide (kein Syntax-Fehler)
- Keys sind unique (keine Duplikate)
- `category: "cortex"` ist konsistent

### 8.2 Testszenarien

```python
# test_placeholder_resolver.py

def test_cortex_placeholders_via_runtime_vars(self):
    """Cortex-Placeholders werden über runtime_vars aufgelöst."""
    text = "Memory: {{cortex_memory}} | Soul: {{cortex_soul}}"
    result = resolver.resolve_text(text, runtime_vars={
        'cortex_memory': 'Max liebt Katzen',
        'cortex_soul': 'Ich bin neugierig',
        'cortex_relationship': 'Enge Freundschaft',
    })
    assert result == "Memory: Max liebt Katzen | Soul: Ich bin neugierig"

def test_cortex_placeholders_empty_when_no_data(self):
    """Fehlende Cortex-Daten → leerer String (kein Crash)."""
    text = "Memory: {{cortex_memory}}"
    result = resolver.resolve_text(text, runtime_vars={
        'cortex_memory': '',
    })
    assert result == "Memory: "

def test_cortex_placeholders_unresolved_without_runtime(self):
    """Ohne runtime_vars bleiben Cortex-Placeholders stehen."""
    text = "{{cortex_memory}}"
    result = resolver.resolve_text(text)
    assert result == "{{cortex_memory}}"
```

```python
# test_chat_service.py

def test_load_cortex_context_returns_dict(self, mock_cortex_service):
    """_load_cortex_context() gibt Dict mit 3 Keys zurück."""
    mock_cortex_service.get_cortex_for_prompt.return_value = {
        'cortex_memory': 'test memory',
        'cortex_soul': 'test soul',
        'cortex_relationship': 'test rel',
    }
    result = chat_service._load_cortex_context('default')
    assert 'cortex_memory' in result
    assert result['cortex_memory'] == 'test memory'

def test_load_cortex_context_error_returns_empty(self):
    """Bei CortexService-Fehler → alle Werte leer."""
    result = chat_service._load_cortex_context('nonexistent')
    assert result == {
        'cortex_memory': '',
        'cortex_soul': '',
        'cortex_relationship': '',
    }
```

---

## 9. Zusammenfassung

| Aspekt | Detail |
|---|---|
| **Approach** | Option A — runtime_vars aus ChatService |
| **Neue Placeholder** | `{{cortex_memory}}`, `{{cortex_soul}}`, `{{cortex_relationship}}` |
| **Resolve-Phase** | Phase 3 (runtime) |
| **Datenquelle** | `CortexService.get_cortex_for_prompt(persona_id)` |
| **Orchestrierung** | `ChatService._load_cortex_context()` → `runtime_vars.update()` |
| **Geänderte Dateien** | 2 (Registry + ChatService) |
| **Engine-Änderungen** | Keine |
| **Abhängigkeiten** | Step 2B (CortexService muss existieren) |
