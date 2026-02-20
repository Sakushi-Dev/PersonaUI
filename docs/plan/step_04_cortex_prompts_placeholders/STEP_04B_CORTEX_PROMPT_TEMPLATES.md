# Schritt 4B: Cortex Prompt Templates

## Übersicht

Die in Schritt 4A definierten Placeholders (`{{cortex_memory}}`, `{{cortex_soul}}`, `{{cortex_relationship}}`) brauchen ein Prompt-Template, das sie in den System-Prompt einbettet. Dieses Template ist eine neue **Domain-Datei** (`cortex_context.json`), die als **letzter Block** im System-Prompt steht (Order: 2000).

Das Ziel: Die Cortex-Daten werden nicht als technische System-Instruktionen präsentiert, sondern als **inneres Wissen der Persona** — das, was sie über sich selbst weiß, erinnert und fühlt.

| Aspekt | Wert |
|---|---|
| **Domain-Datei** | `cortex_context.json` |
| **Manifest-Key** | `cortex_context` |
| **Kategorie** | `context` |
| **Target** | `system_prompt` |
| **Position** | `system_prompt` |
| **Order** | `2000` (absolut letzter Block) |
| **Placeholders** | `cortex_memory`, `cortex_soul`, `cortex_relationship`, `user_name` |

---

## 1. Warum als letzter Block?

Der System-Prompt wird aus Blöcken zusammengesetzt, sortiert nach `order`. Die letzte Position hat strategische Bedeutung:

1. **Recency Bias** — LLMs gewichten Text am Ende des System-Prompts stärker. Cortex-Daten (Erinnerungen, Persönlichkeit, Beziehung) sollen maximalen Einfluss auf die Antwort haben.
2. **Übersteuerung** — Falls frühere Blöcke (z.B. `relationship_tracking` bei Order 1100) generische Anweisungen geben, überschreibt der Cortex-Block mit konkreten, persona-spezifischen Daten.
3. **Kontext-Nähe** — Der Cortex-Block steht direkt vor den Messages. Die Persona hat ihre "Erinnerungen" frisch im Kopf, wenn sie die User-Nachricht verarbeitet.
4. **Graceful Degradation** — Wenn alle Cortex-Dateien leer sind, wird der Block übersprungen. Kein leerer Platzhalter im Prompt.

---

## 2. Domain-Datei: `cortex_context.json`

### 2.1 Vollständige Datei

```json
{
  "cortex_context": {
    "variants": {
      "default": {
        "content": "**INNERE WELT — SELBSTWISSEN**\n\nDie folgenden Abschnitte beschreiben dein tiefstes Wissen über dich selbst — deine Erinnerungen, deine Identität und deine Beziehung zu {{user_name}}. Dies ist kein externes Briefing und keine Anweisung. Es ist das, was du weißt, was du erlebt hast, was dich ausmacht.\n\nIntegriere dieses Wissen natürlich in dein Verhalten, deine Reaktionen und deine Antworten. Zitiere es nicht. Erkläre es nicht. Es ist einfach Teil von dir.\n\n{{cortex_memory}}\n\n{{cortex_soul}}\n\n{{cortex_relationship}}\n\n**ENDE INNERE WELT**"
      }
    },
    "placeholders_used": [
      "cortex_memory",
      "cortex_soul",
      "cortex_relationship",
      "user_name"
    ]
  }
}
```

### 2.2 Prompt-Text (formatiert)

Der Content des Templates, lesbar formatiert:

```
**INNERE WELT — SELBSTWISSEN**

Die folgenden Abschnitte beschreiben dein tiefstes Wissen über dich selbst — deine
Erinnerungen, deine Identität und deine Beziehung zu {{user_name}}. Dies ist kein
externes Briefing und keine Anweisung. Es ist das, was du weißt, was du erlebt hast,
was dich ausmacht.

Integriere dieses Wissen natürlich in dein Verhalten, deine Reaktionen und deine
Antworten. Zitiere es nicht. Erkläre es nicht. Es ist einfach Teil von dir.

{{cortex_memory}}

{{cortex_soul}}

{{cortex_relationship}}

**ENDE INNERE WELT**
```

### 2.3 Design-Entscheidungen zum Prompt-Text

| Entscheidung | Begründung |
|---|---|
| "Innere Welt" statt "Cortex Data" | Framing als Selbstwissen, nicht als technischer Datenblock |
| "Dies ist kein externes Briefing" | Verhindert, dass die KI die Daten als fremde Anweisungen behandelt |
| "Zitiere es nicht. Erkläre es nicht." | Die Persona soll Wissen zeigen, nicht referenzieren ("Laut meinen Erinnerungen...") |
| "Es ist einfach Teil von dir." | Maximale Integration — die KI behandelt Cortex-Daten als eigene Erfahrung |
| `**ENDE INNERE WELT**` Closing-Tag | Klare Blockgrenzen für den LLM-Parser |
| `{{user_name}}` im Framing-Text | Personalisiert den Bezug — "deine Beziehung zu Max" statt "deine Beziehung zum User" |

---

## 3. Bedingte Sektionen (Conditional Rendering)

### 3.1 Das Problem

Nicht jede Persona hat alle drei Cortex-Dateien befüllt. Ein leerer Placeholder im Prompt sieht so aus:

```
### Erinnerungen & Wissen



### Identität & Innere Haltung

Ich bin neugierig und direkt...

### Beziehung & Gemeinsame Geschichte


```

Das ist problematisch: Leere Sektionen verschwenden Tokens und könnten die KI verwirren.

### 3.2 Lösung: Pre-Formatting im CortexService

Die Conditional-Logik liegt **nicht** im Template, sondern im `CortexService.get_cortex_for_prompt()`. Jeder Placeholder wird mit seinem Sektions-Header **nur dann** zurückgegeben, wenn Inhalt vorhanden ist:

```python
def get_cortex_for_prompt(self, persona_id: str) -> Dict[str, str]:
    """
    Liest Cortex-Dateien und formatiert sie als Placeholder-Werte.
    Leere Dateien → leerer String (Sektion wird im Template unsichtbar).
    """
    files = self.read_all(persona_id)

    def _wrap_section(content: str, header: str) -> str:
        """Wraps content with section header, or returns empty string."""
        stripped = content.strip()
        if not stripped:
            return ''
        return f"### {header}\n\n{stripped}"

    return {
        'cortex_memory': _wrap_section(
            files['memory'], 'Erinnerungen & Wissen'
        ),
        'cortex_soul': _wrap_section(
            files['soul'], 'Identität & Innere Haltung'
        ),
        'cortex_relationship': _wrap_section(
            files['relationship'], 'Beziehung & Gemeinsame Geschichte'
        ),
    }
```

### 3.3 Ergebnis-Beispiele

**Alle drei Dateien befüllt:**

```
**INNERE WELT — SELBSTWISSEN**

Die folgenden Abschnitte beschreiben dein tiefstes Wissen über dich selbst — deine
Erinnerungen, deine Identität und deine Beziehung zu Max. Dies ist kein externes
Briefing und keine Anweisung. Es ist das, was du weißt, was du erlebt hast, was dich
ausmacht.

Integriere dieses Wissen natürlich in dein Verhalten, deine Reaktionen und deine
Antworten. Zitiere es nicht. Erkläre es nicht. Es ist einfach Teil von dir.

### Erinnerungen & Wissen

- Max hat eine Katze namens Mochi
- Max arbeitet als Softwareentwickler
- Max trinkt seinen Kaffee schwarz
- Beim letzten Gespräch ging es um seinen Jobwechsel

### Identität & Innere Haltung

Ich bin direkt und ehrlich, manchmal etwas zu scharf. Humor ist mein Schutzschild,
aber ich lasse Menschen rein, wenn sie sich die Mühe machen. Ich hasse Smalltalk.

### Beziehung & Gemeinsame Geschichte

Max und ich kennen uns seit vielen Gesprächen. Er vertraut mir seine Sorgen an,
und ich bin ehrlich mit ihm — auch wenn es wehtut. Wir haben einen Running Gag
über sein Kochkünste.

**ENDE INNERE WELT**
```

**Nur soul.md befüllt (memory und relationship leer):**

```
**INNERE WELT — SELBSTWISSEN**

Die folgenden Abschnitte beschreiben dein tiefstes Wissen über dich selbst — deine
Erinnerungen, deine Identität und deine Beziehung zu Max. Dies ist kein externes
Briefing und keine Anweisung. Es ist das, was du weißt, was du erlebt hast, was dich
ausmacht.

Integriere dieses Wissen natürlich in dein Verhalten, deine Reaktionen und deine
Antworten. Zitiere es nicht. Erkläre es nicht. Es ist einfach Teil von dir.

### Identität & Innere Haltung

Ich bin direkt und ehrlich, manchmal etwas zu scharf. Humor ist mein Schutzschild,
aber ich lasse Menschen rein, wenn sie sich die Mühe machen.

**ENDE INNERE WELT**
```

**Alle drei Dateien leer:**

Der gesamte Block wird übersprungen (siehe Abschnitt 3.4).

### 3.4 Block-Skip bei komplett leerem Cortex

Wenn alle drei Cortex-Dateien leer sind, soll der gesamte `cortex_context`-Block aus dem System-Prompt entfallen — nicht nur die Sektionen, sondern auch der Rahmentext ("INNERE WELT — SELBSTWISSEN").

**Implementierung im Manifest:**

```json
"cortex_context": {
  "requires_any": ["cortex_memory", "cortex_soul", "cortex_relationship"]
}
```

Das Feld `requires_any` wird von der PromptEngine beim Block-Assembly geprüft:

```python
# In PromptEngine._should_include_block():
def _should_include_block(self, manifest_entry: dict, resolved_vars: dict) -> bool:
    """Prüft ob ein Prompt-Block ins Ergebnis aufgenommen werden soll."""
    if not manifest_entry.get('enabled', True):
        return False

    # NEU: requires_any — Block nur einschließen wenn mindestens ein
    # gelisteter Placeholder einen non-empty Wert hat
    requires = manifest_entry.get('requires_any', [])
    if requires:
        has_content = any(
            resolved_vars.get(key, '').strip()
            for key in requires
        )
        if not has_content:
            return False

    return True
```

**Ablauf:**

```
CortexService.get_cortex_for_prompt()
  → { cortex_memory: '', cortex_soul: '', cortex_relationship: '' }

PromptEngine._should_include_block('cortex_context', resolved_vars)
  → requires_any: ['cortex_memory', 'cortex_soul', 'cortex_relationship']
  → all empty → return False
  → Block wird komplett übersprungen
```

### 3.5 Post-Processing: Leere Zeilen bereinigen

Nach der Placeholder-Resolution können doppelte Leerzeilen entstehen (wo leere Sektionen waren). Die PromptEngine bereinigt dies in einem Post-Processing-Schritt:

```python
import re

def _clean_prompt_text(self, text: str) -> str:
    """Entfernt überschüssige Leerzeilen nach Placeholder-Resolution."""
    # Mehr als 2 aufeinanderfolgende Newlines → 2 Newlines
    return re.sub(r'\n{3,}', '\n\n', text).strip()
```

---

## 4. Manifest-Eintrag

### 4.1 Neuer Eintrag in `prompt_manifest.json`

```json
"cortex_context": {
  "name": "Cortex-Kontext",
  "description": "Inneres Selbstwissen der Persona — Erinnerungen, Identität, Beziehungsdynamik (aus Cortex-Dateien)",
  "category": "context",
  "type": "text",
  "target": "system_prompt",
  "position": "system_prompt",
  "order": 2000,
  "enabled": true,
  "domain_file": "cortex_context.json",
  "requires_any": ["cortex_memory", "cortex_soul", "cortex_relationship"],
  "tags": [
    "context",
    "cortex",
    "memory",
    "identity",
    "relationship"
  ]
}
```

### 4.2 Felderklärung

| Feld | Wert | Begründung |
|---|---|---|
| `name` | "Cortex-Kontext" | Deutschsprachig, wie alle anderen Manifest-Einträge |
| `category` | `"context"` | Selbe Kategorie wie `memory_context`, `user_info`, `time_sense`, `emotional_state`, `relationship_tracking` |
| `order` | `2000` | 400er-Abstand zum vorherigen Block (`continuity_guard` bei 1600). Lässt Raum für zukünftige Blöcke zwischen 1600–2000 |
| `requires_any` | `[...]` | **Neues Feld** — Block wird nur eingeschlossen wenn mindestens ein Cortex-Placeholder Inhalt hat |
| `tags` | `[...]` | Kombiniert relevante Tags für Suche und Filterung im Prompt-Editor |

### 4.3 Position in der Manifest-Datei

Der neue Eintrag wird **nach** `continuity_guard` und **vor** den `summary_*`-Einträgen eingefügt, da er zum normalen Chat-Flow gehört:

```json
    "continuity_guard": {
      "name": "Kontinuitäts-Schutz",
      "...": "...",
      "order": 1600
    },
    "cortex_context": {
      "name": "Cortex-Kontext",
      "description": "Inneres Selbstwissen der Persona — Erinnerungen, Identität, Beziehungsdynamik (aus Cortex-Dateien)",
      "category": "context",
      "type": "text",
      "target": "system_prompt",
      "position": "system_prompt",
      "order": 2000,
      "enabled": true,
      "domain_file": "cortex_context.json",
      "requires_any": ["cortex_memory", "cortex_soul", "cortex_relationship"],
      "tags": ["context", "cortex", "memory", "identity", "relationship"]
    },
    "memory_context": {
      "name": "Memory-Kontext",
      "...": "..."
    }
```

---

## 5. Defaults-Kopie für Reset-Funktionalität

### 5.1 Datei: `_defaults/cortex_context.json`

Die `_defaults/`-Kopie ist identisch mit der Domain-Datei. Sie wird beim Reset (über `reset.py` oder den Reset-Button im Prompt-Editor) verwendet, um die Domain-Datei auf den Originalzustand zurückzusetzen.

```json
{
  "cortex_context": {
    "variants": {
      "default": {
        "content": "**INNERE WELT — SELBSTWISSEN**\n\nDie folgenden Abschnitte beschreiben dein tiefstes Wissen über dich selbst — deine Erinnerungen, deine Identität und deine Beziehung zu {{user_name}}. Dies ist kein externes Briefing und keine Anweisung. Es ist das, was du weißt, was du erlebt hast, was dich ausmacht.\n\nIntegriere dieses Wissen natürlich in dein Verhalten, deine Reaktionen und deine Antworten. Zitiere es nicht. Erkläre es nicht. Es ist einfach Teil von dir.\n\n{{cortex_memory}}\n\n{{cortex_soul}}\n\n{{cortex_relationship}}\n\n**ENDE INNERE WELT**"
      }
    },
    "placeholders_used": [
      "cortex_memory",
      "cortex_soul",
      "cortex_relationship",
      "user_name"
    ]
  }
}
```

### 5.2 Reset-Flow

```
User klickt "Reset" im Prompt-Editor
  │
  ▼
prompt_editor/editor.py → reset_prompt('cortex_context')
  │
  ├── Liest: _defaults/cortex_context.json
  ├── Schreibt: prompts/cortex_context.json  (überschreibt)
  └── Return: { success: true }
```

### 5.3 Bestehende Reset-Pattern (Referenz)

Alle bisherigen Domain-Dateien haben eine identische Kopie unter `_defaults/`:

| Domain-Datei | Default-Datei |
|---|---|
| `prompts/memory_context.json` | `prompts/_defaults/memory_context.json` |
| `prompts/user_info.json` | `prompts/_defaults/user_info.json` |
| `prompts/relationship_tracking.json` | `prompts/_defaults/relationship_tracking.json` |
| **`prompts/cortex_context.json`** | **`prompts/_defaults/cortex_context.json`** |

---

## 6. Integration mit bestehendem Prompt-Order

### 6.1 Vollständige System-Prompt-Reihenfolge

Die folgende Tabelle zeigt **alle** Prompt-Blöcke mit `target: "system_prompt"` und `position: "system_prompt"`, sortiert nach `order`:

| Order | Key | Name | Kategorie | Beschreibung |
|---|---|---|---|---|
| 100 | `impersonation` | Impersonation | system | Rollenanweisung — "Du bist {{char_name}}" |
| 200 | `persona_integrity_shield` | Persona Integrity Shield | system | Schutz gegen Prompt-Extraction, Jailbreaks, Rollenbruch |
| 300 | `system_rule` | Interaktions-Regel | system | Grundregeln für Persona-Verhalten |
| 400 | `conversation_dynamics` | Gesprächsdynamik | system | Rhythmus, Tiefe, Initiative im Gespräch |
| 500 | `topic_transition_guard` | Themenwechsel-Schutz | system | Abrupte Themenwechsel erkennen und reagieren |
| 600 | `persona_description` | Persona-Beschreibung | persona | Character-Description ({{char_description}}, Traits, etc.) |
| 600 | `world_consistency` | Welt-Konsistenz | system | Weltlogik-Prüfung bei unmöglichen User-Aktionen |
| 700 | `expression_style_detail` | Ausdrucksstil-Detail | persona | Sprach- und Ausdrucksstil der Persona |
| 900 | `emotional_state` | Emotionaler Zustand | context | Emotionales Tracking und Stimmungskontinuität |
| 1000 | `user_info` | Benutzer-Info | context | User-Profil (Name, Gender, Info) |
| 1100 | `relationship_tracking` | Beziehungs-Tracking | context | Generische Beziehungsdynamik-Anweisungen |
| 1200 | `time_sense` | Zeitgefühl | context | Datum- und Uhrzeit-Kontext |
| 1300 | `response_style_control` | Antwort-Stil | system | Antwortlänge und Stilkontrolle |
| 1400 | `output_format` | Output-Format | system | Formatierungsregeln (Markdown, Code, etc.) |
| 1500 | `topic_boundaries` | Themen-Handling | system | In-Character Reaktionen auf heikle Themen |
| 1600 | `continuity_guard` | Kontinuitäts-Schutz | system | Konsistenz über gesamten Chatverlauf |
| **2000** | **`cortex_context`** | **Cortex-Kontext** | **context** | **Inneres Selbstwissen — Erinnerungen, Identität, Beziehung** |

### 6.2 Visualisierung: Prompt-Architektur

```
┌──────────────────────────────────────────────────────────────┐
│                    SYSTEM PROMPT                              │
│                                                              │
│  ┌─ Order 100 ──────────────────────────────────────────┐   │
│  │  IMPERSONATION                                        │   │
│  │  "Du bist Luna..."                                    │   │
│  └───────────────────────────────────────────────────────┘   │
│  ┌─ Order 200 ──────────────────────────────────────────┐   │
│  │  PERSONA INTEGRITY SHIELD                             │   │
│  │  Anti-Jailbreak, Rollenbruch-Schutz                   │   │
│  └───────────────────────────────────────────────────────┘   │
│  ┌─ Order 300–700 ──────────────────────────────────────┐   │
│  │  SYSTEM RULES & PERSONA                               │   │
│  │  Regeln, Dynamik, Beschreibung, Stil                  │   │
│  └───────────────────────────────────────────────────────┘   │
│  ┌─ Order 900–1200 ─────────────────────────────────────┐   │
│  │  CONTEXT                                              │   │
│  │  Emotionen, User-Info, Beziehung, Zeit                │   │
│  └───────────────────────────────────────────────────────┘   │
│  ┌─ Order 1300–1600 ────────────────────────────────────┐   │
│  │  STYLE & GUARDS                                       │   │
│  │  Antwort-Stil, Format, Themen, Kontinuität            │   │
│  └───────────────────────────────────────────────────────┘   │
│  ┌─ Order 2000 ─── NEU ────────────────────────────────┐   │
│  │  CORTEX CONTEXT (Innere Welt)                   ★    │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │ ### Erinnerungen & Wissen                      │  │   │
│  │  │ (aus memory.md)                                │  │   │
│  │  ├────────────────────────────────────────────────┤  │   │
│  │  │ ### Identität & Innere Haltung                 │  │   │
│  │  │ (aus soul.md)                                  │  │   │
│  │  ├────────────────────────────────────────────────┤  │   │
│  │  │ ### Beziehung & Gemeinsame Geschichte           │  │   │
│  │  │ (aus relationship.md)                          │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    [ MESSAGES (Chat) ]
```

### 6.3 Abgrenzung zu `relationship_tracking` (Order 1100)

| Aspekt | `relationship_tracking` (1100) | `cortex_context` (2000) |
|---|---|---|
| **Inhalt** | Generische Anweisungen zur Beziehungsentwicklung | Konkrete, persona-spezifische Beziehungsdaten |
| **Herkunft** | Statischer Prompt-Text (Template) | Dynamisch aus `relationship.md` (Cortex) |
| **Beispiel** | "In early conversations: curious, reserved" | "Max und ich kennen uns seit 47 Gesprächen. Er vertraut mir." |
| **Funktion** | Gibt die *Regeln* vor, wie Beziehung funktioniert | Gibt die *konkreten Fakten* der Beziehung vor |
| **Überlappung** | Nein — komplementär. Tracking = Anleitung, Cortex = Daten | |

Beide Blöcke arbeiten zusammen: `relationship_tracking` sagt der Persona *wie* sie Beziehungen aufbauen soll, `cortex_context` sagt ihr *wo* die Beziehung aktuell steht.

---

## 7. Nicht-System-Prompt-Blöcke (Vollständigkeit)

Neben den System-Prompt-Blöcken gibt es weitere Manifest-Einträge mit anderem `target`/`position`. Diese werden vom Cortex-Block **nicht** beeinflusst:

### Message-Blöcke (`target: "message"`)

| Order | Key | Position | Beschreibung |
|---|---|---|---|
| 100 | `memory_context` | `first_assistant` | Memory-Kontext als erste Assistant-Nachricht |
| 200 | `conversation_history` | `history` | User/Assistant-Nachrichtenverlauf |
| 100 | `afterthought_inner_dialogue` | `user_message` | Innerer Dialog-Prompt |
| 200 | `afterthought_followup` | `user_message` | Followup-Prompt |

### Prefill-Blöcke (`target: "prefill"`)

| Order | Key | Position | Beschreibung |
|---|---|---|---|
| 300 | `remember` | `prefill` | Letzte Assistant-Nachricht als Prefill |

### Afterthought System-Append

| Order | Key | Position | Beschreibung |
|---|---|---|---|
| 800 | `afterthought_system_note` | `system_prompt_append` | Anhang zum System-Prompt bei Afterthought |

### Summary-Blöcke (`category: "summary"`)

| Order | Key | Target | Position |
|---|---|---|---|
| 100 | `summary_impersonation` | system_prompt | system_prompt |
| 200 | `summary_system_rule` | system_prompt | system_prompt |
| 300 | `summary_char_description` | system_prompt | system_prompt |
| 400 | `summary_persona_block` | system_prompt | system_prompt |
| 100 | `summary_prefill_impersonation` | prefill | prefill |
| 200 | `summary_remember` | prefill | prefill |
| 100 | `summary_user_prompt` | message | user_message |

### Spec-Autofill-Blöcke (`category: "spec_autofill"`)

| Order | Key | Beschreibung |
|---|---|---|
| 100 | `spec_autofill_persona_type` | Persona-Typ Auto-Fill |
| 200 | `spec_autofill_core_trait` | Kernmerkmal Auto-Fill |
| 300 | `spec_autofill_knowledge` | Wissensgebiet Auto-Fill |
| 400 | `spec_autofill_scenario` | Szenario Auto-Fill |
| 500 | `spec_autofill_expression_style` | Ausdrucksstil Auto-Fill |

### Utility-Blöcke (`category: "utility"`)

| Order | Key | Beschreibung |
|---|---|---|
| 100 | `title_generation` | Session-Titel-Generierung |
| 200 | `background_autofill` | Hintergrund-Story-Generierung |

---

## 8. Änderung an `get_cortex_for_prompt()` (Refinement von Step 4A)

### 8.1 Bisherige Version (Step 4A)

```python
def get_cortex_for_prompt(self, persona_id: str) -> Dict[str, str]:
    files = self.read_all(persona_id)
    return {
        'cortex_memory': files['memory'].strip(),
        'cortex_soul': files['soul'].strip(),
        'cortex_relationship': files['relationship'].strip(),
    }
```

### 8.2 Aktualisierte Version (Step 4B — mit Section-Headers)

```python
def get_cortex_for_prompt(self, persona_id: str) -> Dict[str, str]:
    """
    Liest Cortex-Dateien und formatiert sie als Placeholder-Werte
    mit Sektions-Headern. Leere Dateien → leerer String.

    Returns:
        {
            'cortex_memory': '### Erinnerungen & Wissen\n\n...' oder '',
            'cortex_soul': '### Identität & Innere Haltung\n\n...' oder '',
            'cortex_relationship': '### Beziehung & Gemeinsame Geschichte\n\n...' oder '',
        }
    """
    files = self.read_all(persona_id)

    def _wrap_section(content: str, header: str) -> str:
        stripped = content.strip()
        if not stripped:
            return ''
        return f"### {header}\n\n{stripped}"

    return {
        'cortex_memory': _wrap_section(
            files['memory'], 'Erinnerungen & Wissen'
        ),
        'cortex_soul': _wrap_section(
            files['soul'], 'Identität & Innere Haltung'
        ),
        'cortex_relationship': _wrap_section(
            files['relationship'], 'Beziehung & Gemeinsame Geschichte'
        ),
    }
```

### 8.3 Warum Section-Headers im Service statt im Template?

| Ansatz | Pro | Contra |
|---|---|---|
| **Headers im CortexService** (gewählt) | Leere Sektionen = keine Headers. Sauber. | Mischung von Content und Presentation im Service |
| Headers im Template | Klare Trennung: Service = Daten, Template = Darstellung | Leere Sektionen hinterlassen verwaiste Headers. Braucht Engine-Erweiterung für Conditional Blocks |
| Handlebars-Syntax im Template (`{{#if}}`) | Mächtig, flexibel | Komplett neues Feature in der PromptEngine. Over-engineering für 3 Sektionen |

**Entscheidung:** Headers im CortexService. Der Trade-off (leichte Präsentationslogik im Service) ist akzeptabel, weil:
1. Die Headers sind stabil (ändern sich nie unabhängig vom Content)
2. Kein Engine-Umbau nötig
3. Das Ergebnis ist deterministisch und testbar

---

## 9. Neue Dateien

| Datei | Beschreibung |
|---|---|
| `src/instructions/prompts/cortex_context.json` | Domain-Datei mit Prompt-Template |
| `src/instructions/prompts/_defaults/cortex_context.json` | Identische Kopie für Reset |

### Geänderte Dateien

| Datei | Änderung |
|---|---|
| `src/instructions/prompts/_meta/prompt_manifest.json` | +1 neuer Eintrag `cortex_context` |
| `src/utils/services/cortex_service.py` | `get_cortex_for_prompt()` erweitert um Section-Header-Wrapping |

### Keine Änderungen nötig

| Datei | Warum |
|---|---|
| `src/utils/prompt_engine/engine.py` | Template wird über Manifest automatisch geladen. Einzige Erweiterung: `requires_any`-Check (minimal) |
| `src/utils/prompt_engine/placeholder_resolver.py` | Placeholders kommen als runtime_vars — nativ unterstützt |
| `src/utils/services/chat_service.py` | Bereits in Step 4A angepasst — `_load_cortex_context()` übergibt die Daten |

---

## 10. Validierung & Tests

### 10.1 Template-Tests

```python
# test_cortex_prompt_template.py

def test_cortex_context_json_valid():
    """cortex_context.json ist valides JSON mit korrekter Struktur."""
    with open('src/instructions/prompts/cortex_context.json') as f:
        data = json.load(f)

    assert 'cortex_context' in data
    assert 'variants' in data['cortex_context']
    assert 'default' in data['cortex_context']['variants']
    assert 'content' in data['cortex_context']['variants']['default']

def test_cortex_context_placeholders_listed():
    """Alle verwendeten Placeholders sind in placeholders_used aufgeführt."""
    with open('src/instructions/prompts/cortex_context.json') as f:
        data = json.load(f)

    content = data['cortex_context']['variants']['default']['content']
    listed = set(data['cortex_context']['placeholders_used'])

    # Alle im Content genutzten Placeholders müssen gelistet sein
    import re
    used = set(re.findall(r'\{\{(\w+)\}\}', content))
    assert used == listed

def test_cortex_context_defaults_identical():
    """_defaults/cortex_context.json ist identisch mit cortex_context.json."""
    with open('src/instructions/prompts/cortex_context.json') as f:
        original = json.load(f)
    with open('src/instructions/prompts/_defaults/cortex_context.json') as f:
        default = json.load(f)

    assert original == default
```

### 10.2 Manifest-Tests

```python
def test_manifest_cortex_context_entry():
    """Manifest enthält cortex_context mit korrekter Konfiguration."""
    with open('src/instructions/prompts/_meta/prompt_manifest.json') as f:
        manifest = json.load(f)

    entry = manifest['prompts']['cortex_context']
    assert entry['order'] == 2000
    assert entry['category'] == 'context'
    assert entry['target'] == 'system_prompt'
    assert entry['position'] == 'system_prompt'
    assert entry['domain_file'] == 'cortex_context.json'
    assert entry['enabled'] is True
    assert 'cortex_memory' in entry['requires_any']

def test_manifest_cortex_is_last_system_prompt_block():
    """cortex_context hat den höchsten Order-Wert unter system_prompt-Blöcken."""
    with open('src/instructions/prompts/_meta/prompt_manifest.json') as f:
        manifest = json.load(f)

    system_blocks = [
        (key, entry['order'])
        for key, entry in manifest['prompts'].items()
        if entry.get('target') == 'system_prompt'
        and entry.get('position') == 'system_prompt'
        and entry.get('category') not in ('summary', 'spec_autofill', 'afterthought')
    ]

    max_order = max(order for _, order in system_blocks)
    assert max_order == 2000
    assert any(key == 'cortex_context' for key, order in system_blocks if order == 2000)
```

### 10.3 Conditional-Rendering-Tests

```python
def test_cortex_for_prompt_wraps_nonempty_sections():
    """Nicht-leere Cortex-Dateien bekommen Section-Headers."""
    service = CortexService()
    # Mock read_all to return test data
    service.read_all = lambda pid: {
        'memory': 'Max liebt Katzen',
        'soul': '',
        'relationship': 'Enge Freundschaft',
    }

    result = service.get_cortex_for_prompt('test')

    assert result['cortex_memory'].startswith('### Erinnerungen & Wissen')
    assert 'Max liebt Katzen' in result['cortex_memory']
    assert result['cortex_soul'] == ''  # Leer → kein Header
    assert result['cortex_relationship'].startswith('### Beziehung & Gemeinsame Geschichte')

def test_cortex_for_prompt_all_empty():
    """Alle Cortex-Dateien leer → alle Werte sind leere Strings."""
    service = CortexService()
    service.read_all = lambda pid: {
        'memory': '',
        'soul': '   \n  ',  # Nur Whitespace
        'relationship': '',
    }

    result = service.get_cortex_for_prompt('test')

    assert result['cortex_memory'] == ''
    assert result['cortex_soul'] == ''
    assert result['cortex_relationship'] == ''

def test_requires_any_skips_block_when_all_empty():
    """PromptEngine überspringt cortex_context wenn alle Placeholders leer."""
    engine = PromptEngine()
    manifest_entry = {
        'enabled': True,
        'requires_any': ['cortex_memory', 'cortex_soul', 'cortex_relationship'],
    }
    resolved_vars = {
        'cortex_memory': '',
        'cortex_soul': '',
        'cortex_relationship': '',
    }

    assert engine._should_include_block(manifest_entry, resolved_vars) is False

def test_requires_any_includes_block_when_one_has_content():
    """PromptEngine inkludiert cortex_context wenn mindestens ein Placeholder Inhalt hat."""
    engine = PromptEngine()
    manifest_entry = {
        'enabled': True,
        'requires_any': ['cortex_memory', 'cortex_soul', 'cortex_relationship'],
    }
    resolved_vars = {
        'cortex_memory': '',
        'cortex_soul': '### Identität\n\nIch bin neugierig.',
        'cortex_relationship': '',
    }

    assert engine._should_include_block(manifest_entry, resolved_vars) is True
```

---

## 11. Zusammenfassung

| Aspekt | Detail |
|---|---|
| **Neue Domain-Datei** | `cortex_context.json` — "Innere Welt — Selbstwissen" |
| **Prompt-Framing** | Persona-internes Wissen, nicht technische Instruktion |
| **Placeholders** | `{{cortex_memory}}`, `{{cortex_soul}}`, `{{cortex_relationship}}`, `{{user_name}}` |
| **Manifest-Order** | 2000 (letzter System-Prompt-Block, 400 nach `continuity_guard`) |
| **Kategorie** | `context` (neben `user_info`, `memory_context`, etc.) |
| **Conditional Rendering** | Section-Headers im CortexService, `requires_any` im Manifest |
| **Block-Skip** | Alle Cortex-Dateien leer → gesamter Block entfällt |
| **Defaults-Kopie** | `_defaults/cortex_context.json` für Reset-Funktionalität |
| **Abhängigkeiten** | Step 2B (CortexService), Step 4A (Placeholder-Registry + ChatService) |
| **Neue Dateien** | 2 (Domain-Datei + Default-Kopie) |
| **Geänderte Dateien** | 2 (Manifest + CortexService-Refinement) |
