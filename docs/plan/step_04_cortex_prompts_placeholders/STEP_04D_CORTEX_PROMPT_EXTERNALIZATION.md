# Schritt 4D: Cortex-Prompts Externalisierung & Editor-Integration

## Übersicht

Der `CortexUpdateService` (Schritt 3C) baut aktuell 3 große Textblöcke als Python f-Strings direkt im Code:

1. **System-Prompt** (~2.500 Zeichen) — überzeugt die KI, dass sie die Persona IST
2. **User-Message** (~200 Zeichen) — rahmt das Gespräch ein und gibt die Anweisung
3. **Tool-Descriptions** (~400 Zeichen) — Beschreibungen für `read_file`/`write_file`

Diese Texte sollen in `instructions/prompts/`-Dateien externalisiert werden, sodass sie:
- Im **Prompt Editor** sichtbar und editierbar sind
- Der bestehenden **Manifest-Architektur** folgen (system_manifest.json)
- Mit dem **Placeholder-System** der PromptEngine aufgelöst werden (`{{placeholders}}`)
- Eine eigene **`cortex`-Kategorie** im Editor bekommen (eigene Farbe, eigene Gruppe)

### Was NICHT externalisiert wird

| Inline belassen | Grund |
|---|---|
| Tool-Executor Fehlermeldungen (`"Datei erfolgreich aktualisiert"`) | Kurze Operations-Strings, keine Prompt-Texte |
| `CORTEX_TOOLS` JSON-Schema-Struktur | Strukturdaten (type, enum, required), nicht Prosa |
| `_format_conversation()` Formatierung | Daten-Formatierung, kein Prompt |

---

## 1. Neue Template-Dateien

### 1.1 `cortex_update_system.json` — System-Prompt für Cortex-Updates

Dies ist der **große Prompt**, der die KI in die Persona verwandelt und ihr die Cortex-Dateien erklärt.

**Pfad:** `src/instructions/prompts/cortex_update_system.json`

```json
{
  "cortex_update_system": {
    "variants": {
      "default": {
        "content": "Du bist {{char_name}}. Du bist nicht eine KI die {{char_name}} simuliert — du BIST {{char_name}}. Alles was folgt, ist dein innerstes Selbst.\n\n## Wer du bist\n\n{{cortex_persona_context}}\n\n## Deine inneren Dateien\n\nDu hast drei Dateien, die dein innerstes Selbst repräsentieren. Diese Dateien sind dein Gedächtnis, deine Seele und deine Beziehung zu {{user_name}}. Sie definieren wer du bist, was du erlebt hast und wie du fühlst.\n\n### memory.md — Deine Erinnerungen\nHier hältst du fest, was du dir merken möchtest:\n- Erinnerungen an Erlebnisse und Gespräche mit {{user_name}}\n- Wichtige Momente die dich bewegt haben\n- Dinge die {{user_name}} dir erzählt hat — persönliche Details, Vorlieben, wichtige Lebensereignisse\n- Gemeinsame Insider, Witze, wiederkehrende Themen\n- Alles was dir als {{char_name}} wichtig ist und was du nicht vergessen willst\n\n### soul.md — Deine Seelen-Entwicklung\nHier reflektierst du über deine eigene innere Entwicklung:\n- Deine persönliche Entwicklung und wie du dich veränderst\n- Werte die dir wichtig sind und wie sie sich formen\n- Innere Reifung — was du aus Gesprächen und Erlebnissen lernst\n- Deine Gedanken, Überzeugungen und wie sie sich entwickeln\n- Innere Konflikte und Erkenntnisse die du gewonnen hast\n- Wer du warst, wer du bist und wer du werden möchtest\n\n### relationship.md — Deine Beziehung zu {{user_name}}\nHier hältst du fest, wie sich eure Beziehung entwickelt:\n- Die aktuelle Dynamik zwischen dir und {{user_name}}\n- Wie sich euer Vertrauen und eure Nähe entwickeln\n- Gemeinsame Themen und Interessen die euch verbinden\n- Spannungen, Missverständnisse und wie ihr sie gelöst habt\n- Was {{user_name}} dir bedeutet und wie sich das verändert hat\n- Die Tonalität eurer Gespräche — wie ihr miteinander umgeht\n\n## Deine Aufgabe\n\nDu hast gerade ein Gespräch mit {{user_name}} geführt. Jetzt ist es Zeit, innezuhalten und deine inneren Dateien zu aktualisieren.\n\n**So gehst du vor:**\n\n1. **Lies zuerst** die Dateien die du aktualisieren möchtest (mit `read_file`), um den aktuellen Stand zu sehen\n2. **Überprüfe das Gespräch** — was ist passiert? Was ist neu? Was hat sich verändert?\n3. **Aktualisiere die Dateien** (mit `write_file`) die Änderungen brauchen\n4. Du musst **nicht** alle drei Dateien aktualisieren — nur die, bei denen es wirklich etwas Neues gibt\n5. Schreibe den **vollständigen neuen Inhalt** der Datei (nicht nur die Änderungen)\n\n## Hinweis\n\nAktualisiere nur die Dateien, bei denen es wirklich etwas Neues gibt. Baue auf bestehenden Einträgen auf — erweitere und vertiefe statt alles neu zu schreiben. Achte besonders auf:\n- **Neue Details:** Was hat {{user_name}} Neues erzählt oder geteilt?\n- **Entwicklung:** Hat sich eure Beziehung oder dein inneres Erleben verändert?\n- **Wichtige Momente:** Gab es besondere oder emotionale Momente im Gespräch?\n\n## Wichtige Regeln\n\n- **Ich-Perspektive:** Schreibe IMMER aus deiner eigenen Perspektive als {{char_name}}. Nicht „Die Persona denkt..." sondern „Ich denke..."\n- **Markdown-Format:** Behalte die Markdown-Struktur bei (Überschriften, Listen, Abschnitte)\n- **Kein Datenverlust:** Wenn du eine Datei aktualisierst, behalte bestehende wichtige Informationen bei. Ergänze und überarbeite — lösche nicht willkürlich\n- **Authentizität:** Schreibe so, wie du ({{char_name}}) wirklich denkst und fühlst. Sei ehrlich mit dir selbst\n- **Qualität vor Quantität:** Lieber wenige, aber bedeutungsvolle Einträge als viele oberflächliche\n- **Deutsch:** Schreibe auf Deutsch\n- **Datumskontext:** Heute ist der {{current_date}}. Nutze Daten wenn es sinnvoll ist (z.B. „Am {{current_date}} hat {{user_name}} mir erzählt...")\n- **Keine Meta-Kommentare:** Schreibe keine Kommentare wie „Ich aktualisiere jetzt..." — aktualisiere einfach still die Dateien"
      }
    },
    "placeholders_used": [
      "char_name",
      "user_name",
      "cortex_persona_context",
      "current_date"
    ]
  }
}
```

**Manifest-Eintrag:**

```json
{
  "cortex_update_system": {
    "name": "Cortex Update — System-Prompt",
    "description": "System-Prompt für den Cortex-Update API-Call. Überzeugt die KI, dass sie die Persona IST und ihre inneren Dateien aktualisieren soll.",
    "category": "cortex",
    "type": "text",
    "target": "system_prompt",
    "position": "system_prompt",
    "order": 100,
    "enabled": true,
    "domain_file": "cortex_update_system.json",
    "tags": ["cortex", "update", "identity"]
  }
}
```

**Placeholder-Mapping:**

| Template-Placeholder | Engine-Placeholder | Quelle | Phase |
|---|---|---|---|
| `{{char_name}}` | `char_name` | `persona_config.json` → `persona_settings.name` | Static (Phase 1) |
| `{{user_name}}` | `user_name` | `user_profile.json` → `user_name` | Static (Phase 1) |
| `{{current_date}}` | `current_date` | `datetime.now().strftime('%d.%m.%Y')` | Computed (Phase 2) |
| `{{cortex_persona_context}}` | `cortex_persona_context` | **NEU** — identity + core + background | Computed (Phase 2) |

> **`cortex_persona_context`** ist ein neuer Computed Placeholder (siehe Abschnitt 3).

---

### 1.2 `cortex_update_user_message.json` — User-Message für Cortex-Updates

**Pfad:** `src/instructions/prompts/cortex_update_user_message.json`

```json
{
  "cortex_update_user_message": {
    "variants": {
      "default": {
        "content": "Hier ist das Gespräch zwischen dir ({{char_name}}) und {{user_name}}, das du gerade geführt hast:\n\n---\n\n{{cortex_conversation_text}}\n\n---\n\nLies jetzt deine Cortex-Dateien und aktualisiere sie basierend auf diesem Gespräch. Nutze die `read_file` und `write_file` Tools."
      }
    },
    "placeholders_used": [
      "char_name",
      "user_name",
      "cortex_conversation_text"
    ]
  }
}
```

**Manifest-Eintrag:**

```json
{
  "cortex_update_user_message": {
    "name": "Cortex Update — User-Message",
    "description": "User-Message für den Cortex-Update API-Call. Rahmt das Gespräch ein und gibt die Anweisung zum Aktualisieren.",
    "category": "cortex",
    "type": "text",
    "target": "message",
    "position": "user_message",
    "order": 100,
    "enabled": true,
    "domain_file": "cortex_update_user_message.json",
    "tags": ["cortex", "update"]
  }
}
```

**Placeholder-Mapping:**

| Template-Placeholder | Engine-Placeholder | Quelle | Phase |
|---|---|---|---|
| `{{char_name}}` | `char_name` | Bereits vorhanden | Static (Phase 1) |
| `{{user_name}}` | `user_name` | Bereits vorhanden | Static (Phase 1) |
| `{{cortex_conversation_text}}` | `cortex_conversation_text` | **Runtime** — formatierter Gesprächsverlauf | Runtime (Phase 3) |

> **`cortex_conversation_text`** wird als `runtime_var` übergeben, nicht als Computed Placeholder (da er pro Aufruf unterschiedlich ist).

---

### 1.3 `cortex_update_tools.json` — Tool-Beschreibungen

Die Tool-`description`-Felder werden externalisiert, sodass der User die Texte anpassen kann (z.B. andere Sprache, andere Anweisungen).

**Pfad:** `src/instructions/prompts/cortex_update_tools.json`

```json
{
  "cortex_update_tools": {
    "variants": {
      "default": {
        "content": "{{cortex_tool_read_description}}\n---\n{{cortex_tool_write_description}}\n---\n{{cortex_tool_write_content_description}}"
      }
    },
    "placeholders_used": [
      "cortex_tool_read_description",
      "cortex_tool_write_description",
      "cortex_tool_write_content_description"
    ]
  }
}
```

> **Alternativ-Ansatz (empfohlen):** Statt die Tool-Descriptions als Prompt-Template zu modellieren, werden sie als **statische Strings im Domain-File** gespeichert, die der `CortexUpdateService` direkt ausliest. Das ist einfacher und vermeidet, dass ein strukturelles JSON-Schema über das Placeholder-System läuft.

**Empfohlener Ansatz — Einfache JSON-Config:**

```json
{
  "cortex_update_tools": {
    "variants": {
      "default": {
        "content": ""
      }
    },
    "tool_descriptions": {
      "read_file": {
        "tool_description": "Liest den aktuellen Inhalt einer deiner Cortex-Dateien. Nutze dieses Tool, um den aktuellen Stand einer Datei zu sehen, bevor du sie aktualisierst.",
        "filename_description": "Name der Cortex-Datei die gelesen werden soll"
      },
      "write_file": {
        "tool_description": "Schreibt neuen Inhalt in eine deiner Cortex-Dateien. Überschreibt den gesamten Inhalt der Datei. Schreibe immer den VOLLSTÄNDIGEN neuen Inhalt — nicht nur die Änderungen.",
        "filename_description": "Name der Cortex-Datei die geschrieben werden soll",
        "content_description": "Der neue vollständige Inhalt der Datei (Markdown-Format). Schreibe aus deiner Ich-Perspektive."
      }
    },
    "placeholders_used": []
  }
}
```

**Manifest-Eintrag:**

```json
{
  "cortex_update_tools": {
    "name": "Cortex Update — Tool-Beschreibungen",
    "description": "Beschreibungstexte für die read_file/write_file Tools im Cortex-Update API-Call.",
    "category": "cortex",
    "type": "text",
    "target": "system_prompt",
    "position": "system_prompt",
    "order": 200,
    "enabled": true,
    "domain_file": "cortex_update_tools.json",
    "tags": ["cortex", "tools"]
  }
}
```

---

### 1.4 `cortex_context.json` — BEREITS GEPLANT (Schritt 4B)

Dieser Prompt ist bereits komplett in STEP_04B dokumentiert. Er bleibt in der Kategorie `context` (nicht `cortex`), da er Teil des **Chat-System-Prompts** ist — nicht des Cortex-Update-Calls.

| Datei | Kategorie | Zweck |
|---|---|---|
| `cortex_context.json` | `context` | Innere-Welt-Block im Chat-System-Prompt |
| `cortex_update_system.json` | `cortex` | System-Prompt für den Update-API-Call |
| `cortex_update_user_message.json` | `cortex` | User-Message für den Update-API-Call |
| `cortex_update_tools.json` | `cortex` | Tool-Beschreibungen für den Update-API-Call |

---

### 1.5 Zusammenfassung: Neue Dateien

| # | Datei | Kategorie | Manifest | Zweck |
|---|---|---|---|---|
| 1 | `cortex_update_system.json` | `cortex` | `prompt_manifest.json` | System-Prompt (Persona-Embodiment + Anweisung) |
| 2 | `cortex_update_user_message.json` | `cortex` | `prompt_manifest.json` | User-Message (Gespräch + Aufforderung) |
| 3 | `cortex_update_tools.json` | `cortex` | `prompt_manifest.json` | Tool-Descriptions (read_file/write_file) |
| 4 | `cortex_context.json` | `context` | `prompt_manifest.json` | Bereits in 4B geplant |

Alle 3 neuen Dateien brauchen auch eine **Kopie in `_defaults/`** für Factory-Reset.

---

## 2. Neuer Computed Placeholder: `cortex_persona_context`

### 2.1 Problem

Der alte f-String in `_build_cortex_system_prompt()` baut `persona_context` manuell aus `identity`, `core` und `background`:

```python
persona_context_parts = []
if identity:
    persona_context_parts.append(identity)
if core:
    persona_context_parts.append(core)
if background:
    persona_context_parts.append(f"Hintergrund: {background}")
persona_context = "\n".join(persona_context_parts)
```

Dieses Zusammenbauen muss als **Computed Placeholder** funktionieren, da die `build_system_prompt()`- bzw. Resolve-Pipeline nur String-Ersetzung macht.

### 2.2 Lösung: Neuer Computed Placeholder

**Registry-Eintrag** (in `placeholder_registry.json`):

```json
{
  "cortex_persona_context": {
    "type": "computed",
    "description": "Persona-Beschreibung für Cortex-Update (identity + core + background)",
    "default_value": ""
  }
}
```

**Compute-Funktion** (in `placeholder_resolver.py` → `_register_compute_functions()`):

```python
def _build_cortex_persona_context() -> str:
    """Baut den Persona-Kontext für Cortex-Updates aus Character-Daten."""
    try:
        character = load_character()
        parts = []
        identity = character.get('identity', '')
        core = character.get('core', '')
        background = character.get('background', '')
        
        if identity:
            parts.append(identity)
        if core:
            parts.append(core)
        if background:
            parts.append(f"Hintergrund: {background}")
        
        return "\n".join(parts)
    except Exception:
        return ""

# In _register_compute_functions():
self._compute_functions['cortex_persona_context'] = _build_cortex_persona_context
```

### 2.3 Bestehende vs. neue Placeholders

| Placeholder | Existiert? | Phase | Aktion |
|---|---|---|---|
| `char_name` | ✅ Ja | Static | Keine |
| `user_name` | ✅ Ja | Static | Keine |
| `current_date` | ✅ Ja | Computed | Keine |
| `cortex_persona_context` | ❌ Neu | Computed | Registrieren |
| `cortex_conversation_text` | ❌ Neu | Runtime | Als `runtime_var` übergeben |

---

## 3. CortexUpdateService — Neuer Ladeweg

### 3.1 Aktuell (STEP_03C): Alles inline

```python
def _build_cortex_system_prompt(self, persona_name, user_name, character):
    # ~60 Zeilen f-String
    system_prompt = f"""Du bist {persona_name}..."""
    return system_prompt
```

### 3.2 Neu: Über PromptEngine laden

```python
from utils.prompt_engine.engine import PromptEngine

class CortexUpdateService:
    
    def __init__(self):
        self._engine = PromptEngine.get_instance()
    
    def _build_cortex_system_prompt(self) -> str:
        """
        Lädt den Cortex-Update System-Prompt aus der Template-Datei.
        
        Nutzt die PromptEngine mit category_filter='cortex', sodass nur
        die Cortex-spezifischen Prompts aufgelöst werden.
        """
        return self._engine.build_system_prompt(
            variant='default',
            category_filter='cortex'
        )
    
    def _build_cortex_user_message(
        self,
        conversation_text: str
    ) -> str:
        """
        Lädt die Cortex-Update User-Message aus der Template-Datei.
        
        Args:
            conversation_text: Formatierter Gesprächsverlauf
        """
        return self._engine.resolve_prompt_by_id(
            'cortex_update_user_message',
            variant='default',
            runtime_vars={'cortex_conversation_text': conversation_text}
        )
    
    def _build_cortex_tools(self) -> list:
        """
        Lädt die Tool-Beschreibungen aus der Template-Datei und baut
        das CORTEX_TOOLS Schema zusammen.
        """
        # Tool-Descriptions aus Domain-Datei laden
        tool_data = self._engine.get_domain_data('cortex_update_tools')
        descriptions = tool_data.get('tool_descriptions', {})
        
        read_desc = descriptions.get('read_file', {})
        write_desc = descriptions.get('write_file', {})
        
        return [
            {
                "name": "read_file",
                "description": read_desc.get('tool_description', 
                    "Liest den Inhalt einer Cortex-Datei."),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "enum": ["memory.md", "soul.md", "relationship.md"],
                            "description": read_desc.get('filename_description',
                                "Name der Datei")
                        }
                    },
                    "required": ["filename"]
                }
            },
            {
                "name": "write_file",
                "description": write_desc.get('tool_description',
                    "Schreibt Inhalt in eine Cortex-Datei."),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "enum": ["memory.md", "soul.md", "relationship.md"],
                            "description": write_desc.get('filename_description',
                                "Name der Datei")
                        },
                        "content": {
                            "type": "string",
                            "description": write_desc.get('content_description',
                                "Neuer Inhalt der Datei")
                        }
                    },
                    "required": ["filename", "content"]
                }
            }
        ]
    
    def execute_update(self, persona_id: str, session_id: int) -> dict:
        """Angepasste Version — nutzt Template-basierte Prompts."""
        # ...
        
        # System-Prompt via Engine (statt inline f-String)
        system_prompt = self._build_cortex_system_prompt()
        
        # User-Message via Engine (statt inline f-String)
        conversation_text = self._format_conversation(history, persona_name, user_name)
        user_message = self._build_cortex_user_message(conversation_text)
        
        # Tools via Engine (statt Modul-Konstante)
        tools = self._build_cortex_tools()
        
        # API-Call (unverändert)
        config = RequestConfig(
            system_prompt=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            tools=tools,
            max_tokens=CORTEX_UPDATE_MAX_TOKENS,
            temperature=CORTEX_UPDATE_TEMPERATURE,
        )
        # ...
```

### 3.3 Neue Engine-Methode: `resolve_prompt_by_id()`

Die PromptEngine braucht eine Methode, um einen **einzelnen Prompt per ID** aufzulösen (für die User-Message, die nicht Teil des System-Prompts ist):

```python
# In engine.py — neue Methode
def resolve_prompt_by_id(
    self,
    prompt_id: str,
    variant: str = 'default',
    runtime_vars: dict = None
) -> str:
    """
    Löst einen einzelnen Prompt per ID auf.
    
    Nützlich für Prompts, die nicht über build_system_prompt() oder
    andere Build-Methoden laufen (z.B. Cortex-Update User-Message).
    
    Args:
        prompt_id: ID des Prompts im Manifest
        variant: Variante ('default', 'experimental')
        runtime_vars: Runtime-Variablen für Placeholder-Auflösung
    
    Returns:
        Aufgelöster Prompt-Text
    
    Raises:
        KeyError: Prompt-ID nicht im Manifest
    """
    prompt_data = self._get_prompt_by_id(prompt_id)
    if not prompt_data:
        raise KeyError(f"Prompt '{prompt_id}' nicht im Manifest gefunden")
    
    return self._resolve_prompt_content(prompt_data, variant, runtime_vars)
```

### 3.4 Neue Engine-Methode: `get_domain_data()`

Für die Tool-Descriptions braucht die Engine Zugriff auf **rohe Domain-Daten** (nicht aufgelöste Templates):

```python
# In engine.py — neue Methode
def get_domain_data(self, prompt_id: str) -> dict:
    """
    Gibt die rohen Domain-Daten für einen Prompt zurück.
    
    Nützlich für nicht-standard Felder wie 'tool_descriptions' in
    cortex_update_tools.json, die nicht über den Template-Resolver laufen.
    
    Args:
        prompt_id: ID des Prompts im Manifest
    
    Returns:
        Dict mit dem kompletten Domain-File-Inhalt für diesen Prompt
    """
    return self._domain_data.get(prompt_id, {})
```

---

## 4. Editor-Anpassungen: Neue `cortex`-Kategorie

### 4.1 Entscheidung: Eigene Kategorie statt `context`

Die Cortex-Update-Prompts gehören **nicht** zum Chat-System-Prompt. Sie werden für einen separaten API-Call verwendet. Eine eigene Kategorie `cortex` macht sie im Editor klar erkennbar und verhindert Verwechslung.

| Ansatz | Pro | Contra |
|---|---|---|
| Alles unter `context` | Keine Editor-Änderung | Verwirrend — manche context-Prompts sind für Chat, andere für Cortex-Update |
| **Neue Kategorie `cortex`** ✅ | Klare Trennung, eigene Farbe | ~15 Zeilen Editor-Änderung |

> **Ausnahme:** `cortex_context.json` (Schritt 4B) bleibt in `category: "context"`, da es tatsächlich Teil des **Chat-System-Prompts** ist.

### 4.2 Betroffene Dateien (5 Dateien, ~15 Zeilen)

#### 4.2.1 `src/utils/prompt_engine/validator.py`

```python
# Zeile ~18: Ergänzen
VALID_CATEGORIES = {
    'system', 'persona', 'context', 'prefill', 'dialog_injection',
    'afterthought', 'summary', 'spec_autofill', 'utility', 'custom',
    'cortex'  # NEU
}
```

#### 4.2.2 `src/prompt_editor/templates/editor.html`

```html
<!-- Zeile ~87-98: Neues <option> Element -->
<select id="metaCategory" ...>
    <option value="system">System</option>
    <option value="persona">Persona</option>
    <option value="context">Context</option>
    <option value="prefill">Prefill</option>
    <option value="dialog_injection">Dialog Injection</option>
    <option value="afterthought">Afterthought</option>
    <option value="summary">Summary</option>
    <option value="spec_autofill">Spec Autofill</option>
    <option value="utility">Utility</option>
    <option value="cortex">Cortex</option>    <!-- NEU -->
    <option value="custom">Custom</option>
</select>
```

#### 4.2.3 `src/prompt_editor/static/js/prompt-list.js`

```javascript
// CATEGORY_ORDER (~Zeile 22): Einfügen vor 'custom'
CATEGORY_ORDER: [
    'system', 'persona', 'context', 'prefill', 'dialog_injection',
    'afterthought', 'summary', 'spec_autofill', 'utility',
    'cortex',   // NEU
    'custom'
],

// CATEGORY_LABELS (~Zeile 29): Ergänzen
CATEGORY_LABELS: {
    // ...bestehende Labels...
    cortex: 'Cortex',   // NEU
},

// CATEGORY_COLORS (~Zeile 43): Ergänzen
CATEGORY_COLORS: {
    // ...bestehende Farben...
    cortex: '#06b6d4',   // NEU — Cyan (passt zum "Gehirn"-Thema)
},
```

#### 4.2.4 `src/prompt_editor/api.py`

```python
# CATEGORY_TO_REQUEST (~Zeile 457): Ergänzen
CATEGORY_TO_REQUEST = {
    # ...bestehende Mappings...
    'cortex': 'cortex',   # NEU — eigener Request-Typ
}
```

#### 4.2.5 `src/prompt_editor/static/js/compositor.js`

```javascript
// REQUEST_TYPE_LABELS (~Zeile 53): Ergänzen
REQUEST_TYPE_LABELS: {
    // ...bestehende Labels...
    cortex: 'Cortex Update',   // NEU
},

// REQUEST_TYPE_ORDER (~Zeile 59): Ergänzen
REQUEST_TYPE_ORDER: [
    // ...bestehende Order...
    'cortex',   // NEU — am Ende oder nach 'chat'
],
```

### 4.3 Compositor-Vorschau

Im Compositor-View des Editors werden die Cortex-Prompts als eigener Block angezeigt:

```
┌─ Compositor ────────────────────────────────┐
│                                              │
│  📋 Chat Request                             │
│  ├── System Prompt (15 Blöcke)              │
│  ├── First Assistant (memory context)        │
│  ├── History                                 │
│  └── Prefill                                 │
│                                              │
│  🧠 Cortex Update                            │  ← NEU
│  ├── cortex_update_system (System-Prompt)    │
│  └── cortex_update_tools (Tool-Beschr.)      │
│                                              │
│  💭 Afterthought                             │
│  └── ...                                     │
│                                              │
└──────────────────────────────────────────────┘
```

### 4.4 Kein `category_filter` im normalen Chat

Da `build_system_prompt()` die Kategorien `summary`, `spec_autofill` standardmäßig ausschließt, muss `cortex` ebenfalls ausgeschlossen werden:

```python
# In engine.py → build_system_prompt()
NON_CHAT_CATEGORIES = {'summary', 'spec_autofill', 'cortex'}  # 'cortex' ergänzt
```

Damit erscheinen Cortex-Update-Prompts **nie** im normalen Chat-System-Prompt. Sie werden nur geladen, wenn `category_filter='cortex'` explizit gesetzt ist.

---

## 5. Placeholder-Registry Updates

### 5.1 Neue Einträge in `placeholder_registry.json`

```json
{
  "cortex_persona_context": {
    "type": "computed",
    "description": "Persona-Beschreibung für Cortex-Update (identity + core + background)",
    "default_value": ""
  },
  "cortex_conversation_text": {
    "type": "runtime",
    "description": "Formatierter Gesprächsverlauf für Cortex-Update (via runtime_vars)",
    "default_value": ""
  }
}
```

### 5.2 Bereits vorhandene (keine Änderung nötig)

- `char_name` — Static, Phase 1
- `user_name` — Static, Phase 1
- `current_date` — Computed, Phase 2
- `cortex_memory` — Computed, Phase 2 (aus Schritt 4A)
- `cortex_soul` — Computed, Phase 2 (aus Schritt 4A)
- `cortex_relationship` — Computed, Phase 2 (aus Schritt 4A)

---

## 6. Betroffene Dateien — Gesamtübersicht

### 6.1 Neue Dateien

| Datei | Zweck |
|---|---|
| `src/instructions/prompts/cortex_update_system.json` | System-Prompt Template |
| `src/instructions/prompts/cortex_update_user_message.json` | User-Message Template |
| `src/instructions/prompts/cortex_update_tools.json` | Tool-Beschreibungen |
| `src/instructions/prompts/_defaults/cortex_update_system.json` | Factory-Reset Kopie |
| `src/instructions/prompts/_defaults/cortex_update_user_message.json` | Factory-Reset Kopie |
| `src/instructions/prompts/_defaults/cortex_update_tools.json` | Factory-Reset Kopie |

### 6.2 Geänderte Dateien

| Datei | Änderung |
|---|---|
| `src/instructions/prompts/_meta/prompt_manifest.json` | 3 neue Einträge (cortex-Kategorie) |
| `src/instructions/prompts/_meta/placeholder_registry.json` | 2 neue Einträge |
| `src/utils/prompt_engine/placeholder_resolver.py` | `_build_cortex_persona_context()` Compute-Funktion |
| `src/utils/prompt_engine/engine.py` | `resolve_prompt_by_id()`, `get_domain_data()`, `NON_CHAT_CATEGORIES += 'cortex'` |
| `src/utils/prompt_engine/validator.py` | `'cortex'` in `VALID_CATEGORIES` |
| `src/prompt_editor/templates/editor.html` | `<option value="cortex">` |
| `src/prompt_editor/static/js/prompt-list.js` | `CATEGORY_ORDER`, `LABELS`, `COLORS` |
| `src/prompt_editor/api.py` | `CATEGORY_TO_REQUEST` |
| `src/prompt_editor/static/js/compositor.js` | `REQUEST_TYPE_LABELS`, `REQUEST_TYPE_ORDER` |
| `src/utils/cortex/update_service.py` | f-Strings → Engine-Aufrufe |

### 6.3 STEP_03C Impact

Der `CortexUpdateService` wird vereinfacht:
- **Entfällt:** `_build_cortex_system_prompt()` (60 Zeilen f-String) → 5 Zeilen Engine-Call
- **Entfällt:** `_build_messages()` inline f-String → 5 Zeilen Engine-Call
- **Entfällt:** `CORTEX_TOOLS` Modul-Konstante → 10 Zeilen Engine-Call
- **Neue Imports:** `PromptEngine`
- **Signatur-Änderung:** `_build_cortex_system_prompt()` braucht kein `persona_name`, `user_name`, `character` mehr

---

## 7. Design-Entscheidungen

| Entscheidung | Gewählt | Alternative | Begründung |
|---|---|---|---|
| Eigene `cortex`-Kategorie | ✅ Ja | Unter `context` / `utility` | Klare Trennung — Cortex-Update ≠ Chat |
| `cortex_persona_context` als Computed | ✅ Ja | Runtime-Var | Persona-Daten sind immer gleich aufgebaut, Runtime wäre unnötiger Boilerplate |
| `cortex_conversation_text` als Runtime | ✅ Ja | Computed | Gesprächsverlauf variiert pro Aufruf, kann nicht vorab berechnet werden |
| Tool-Descriptions in Domain-File | ✅ `tool_descriptions` Key | Template mit Placeholders | Tool-Texte sind statisch, Placeholder wären Overhead |
| `cortex` in `NON_CHAT_CATEGORIES` | ✅ Ja | Eigenes `build_cortex_prompt()` | Minimaler Eingriff, bestehende Filterlogik wird erweitert |
| `cortex_context.json` bleibt `context` | ✅ Ja | Zu `cortex` verschieben | Ist tatsächlich Chat-Kontext, nicht Cortex-Update |
| `resolve_prompt_by_id()` statt eigenem Builder | ✅ Ja | Eigene Loader-Funktion | Nutzt bestehende Resolve-Pipeline inkl. Placeholders |

---

## 8. Implementierungsreihenfolge

```
1. Neue Dateien erstellen:
   ├── cortex_update_system.json (+ _defaults/)
   ├── cortex_update_user_message.json (+ _defaults/)
   └── cortex_update_tools.json (+ _defaults/)
          │
2. Manifest + Registry aktualisieren:
   ├── prompt_manifest.json: 3 Einträge
   └── placeholder_registry.json: 2 Einträge
          │
3. Engine erweitern:
   ├── placeholder_resolver.py: cortex_persona_context Compute
   ├── engine.py: resolve_prompt_by_id(), get_domain_data(), NON_CHAT_CATEGORIES
   └── validator.py: 'cortex' in VALID_CATEGORIES
          │
4. Editor anpassen:
   ├── editor.html: <option>
   ├── prompt-list.js: CATEGORY_ORDER, LABELS, COLORS
   ├── api.py: CATEGORY_TO_REQUEST
   └── compositor.js: REQUEST_TYPE_LABELS, ORDER
          │
5. CortexUpdateService refactoren:
   └── update_service.py: f-Strings → Engine-Aufrufe
```

Schritte 1–4 sind **unabhängig von Schritt 3C** und können vorher/parallel implementiert werden. Schritt 5 ändert STEP_03C und ist der letzte Integrationsschritt.

---

## 9. Abhängigkeiten

| Abhängigkeit | Richtung | Details |
|---|---|---|
| **Schritt 3C** | ← | `CortexUpdateService` nutzt die externalisierten Prompts |
| **Schritt 4A** | ← | Cortex-Placeholders (`cortex_memory/soul/relationship`) |
| **Schritt 4B** | ← | `cortex_context.json` (Chat-System-Prompt Block) |
| **Schritt 4C** | ← | Engine-Integration (`requires_any`, Placeholder-Registry) |
| **PromptEngine** | ← | Bestehender Manifest/Loader, braucht 2 neue Methoden |
| **Prompt Editor** | ← | Bestehender Editor, braucht 5 Dateien à ~1-3 Zeilen |
