# Schritt 1C: Memory Settings & Konfiguration entfernen

## Übersicht

Dieser Schritt entfernt alle memory-bezogenen **Einstellungen**, **Konfigurationsdateien**, **Prompt-Templates** und **Placeholder-Registrierungen** aus dem Projekt. Nach Abschluss existiert keine Memory-Konfiguration mehr im Settings-, Prompt- oder Engine-Bereich.

---

## 1. Betroffene Dateien – Gesamtübersicht

| Datei | Typ | Aktion | Beschreibung |
|-------|-----|--------|--------------|
| `src/settings/user_settings.json` | Settings | Key entfernen | `memoriesEnabled` Key |
| `src/settings/defaults.json` | Settings | Key entfernen | `memoriesEnabled` Key |
| `src/instructions/prompts/memory_context.json` | Prompt-Template | **Datei löschen** | Memory-Kontext Prompt |
| `src/instructions/prompts/_defaults/memory_context.json` | Prompt-Default | **Datei löschen** | Memory-Kontext Default-Prompt |
| `src/instructions/prompts/_meta/prompt_manifest.json` | Manifest | Eintrag entfernen | `memory_context` Prompt-Definition |
| `src/instructions/prompts/_defaults/_meta/prompt_manifest.json` | Manifest (Default) | Eintrag entfernen | `memory_context` Prompt-Definition |
| `src/instructions/prompts/_meta/placeholder_registry.json` | Registry | Eintrag entfernen | `memory_entries` Placeholder |
| `src/instructions/prompts/_defaults/_meta/placeholder_registry.json` | Registry (Default) | Eintrag entfernen | `memory_entries` Placeholder |
| `src/utils/prompt_engine/memory_context.py` | Engine-Modul | **Datei löschen** | `format_memories_for_prompt()` |
| `src/utils/prompt_engine/migrator.py` | Engine-Modul | Referenz entfernen | `memory_entries` in `KNOWN_PLACEHOLDERS` |
| `src/utils/prompt_engine/engine.py` | Engine-Modul | Docstring anpassen | `build_summary_prompt()` Kommentar (referenziert "Memory-Zusammenfassungen") |
| `docs/10_Memory_System.md` | Dokumentation | **Archivieren/Löschen** | Gesamte Memory-System Doku |
| `docs/02_Configuration_and_Settings.md` | Dokumentation | Eintrag entfernen | `memoriesEnabled` Tabelleneintrag |

---

## 2. Settings-Dateien – Exakte Keys zum Entfernen

### 2.1 `src/settings/user_settings.json`

**Zu entfernender Key:**
```json
"memoriesEnabled": true,
```

**Aktueller Kontext (Zeile 17):**
```json
{
    ...
    "experimentalMode": false,
    "memoriesEnabled": true,       // ← ENTFERNEN
    "nachgedankeMode": "hoch",
    ...
}
```

### 2.2 `src/settings/defaults.json`

**Zu entfernender Key:**
```json
"memoriesEnabled": true,
```

**Aktueller Kontext (Zeile 18):**
```json
{
    ...
    "experimentalMode": false,
    "memoriesEnabled": true,       // ← ENTFERNEN
    "nachgedankeMode": "off",
    ...
}
```

> **Hinweis:** Es gibt keine weiteren `memory`-bezogenen Keys in den Settings-Dateien. Eine Suche nach `"memory"` in `src/settings/**` ergab keine anderen Treffer.

---

## 3. Prompt-Template Dateien – Komplett löschen

### 3.1 `src/instructions/prompts/memory_context.json`

**Gesamter Inhalt (wird gelöscht):**
```json
{
  "memory_context": {
    "variants": {
      "default": {
        "content": "**MEMORY CONTEXT**\n\nHere is the conversation history so far:\n\n{{memory_entries}}\n\n**END OF MEMORY CONTEXT**"
      }
    },
    "placeholders_used": [
      "memory_entries"
    ]
  }
}
```

### 3.2 `src/instructions/prompts/_defaults/memory_context.json`

**Gesamter Inhalt (identisch, wird gelöscht):**
```json
{
  "memory_context": {
    "variants": {
      "default": {
        "content": "**MEMORY CONTEXT**\n\nHere is the conversation history so far:\n\n{{memory_entries}}\n\n**END OF MEMORY CONTEXT**"
      }
    },
    "placeholders_used": [
      "memory_entries"
    ]
  }
}
```

---

## 4. Prompt-Manifest Einträge – Entfernen

### 4.1 `src/instructions/prompts/_meta/prompt_manifest.json`

**Zu entfernender Block (Zeilen 94–108):**
```json
    "memory_context": {
      "name": "Memory-Kontext",
      "description": "Erinnerungen aus vergangenen Konversationen",
      "category": "context",
      "type": "text",
      "target": "message",
      "position": "first_assistant",
      "order": 100,
      "enabled": true,
      "domain_file": "memory_context.json",
      "tags": [
        "context",
        "memory"
      ]
    },
```

### 4.2 `src/instructions/prompts/_defaults/_meta/prompt_manifest.json`

**Zu entfernender Block (identische Struktur, Zeilen 94–108):**
```json
    "memory_context": {
      "name": "Memory-Kontext",
      "description": "Erinnerungen aus vergangenen Konversationen",
      "category": "context",
      "type": "text",
      "target": "message",
      "position": "first_assistant",
      "order": 100,
      "enabled": true,
      "domain_file": "memory_context.json",
      "tags": [
        "context",
        "memory"
      ]
    },
```

---

## 5. Placeholder-Registry Einträge – Entfernen

### 5.1 `src/instructions/prompts/_meta/placeholder_registry.json`

**Zu entfernender Block (Zeilen 231–239):**
```json
    "memory_entries": {
      "name": "Erinnerungen",
      "description": "Formatierte Memory-Einträge für den Prompt-Kontext",
      "source": "runtime",
      "type": "string",
      "default": "",
      "category": "context",
      "resolve_phase": "runtime"
    },
```

### 5.2 `src/instructions/prompts/_defaults/_meta/placeholder_registry.json`

**Zu entfernender Block (identische Struktur, Zeilen 231–239):**
```json
    "memory_entries": {
      "name": "Erinnerungen",
      "description": "Formatierte Memory-Einträge für den Prompt-Kontext",
      "source": "runtime",
      "type": "string",
      "default": "",
      "category": "context",
      "resolve_phase": "runtime"
    },
```

---

## 6. Prompt-Engine Dateien – Bereinigen

### 6.1 `src/utils/prompt_engine/memory_context.py` – **DATEI LÖSCHEN**

Gesamte Datei (71 Zeilen) enthält ausschließlich Memory-Formatierung:
- Funktion: `format_memories_for_prompt(memories, max_memories, engine)`
- Wird importiert in:
  - `src/utils/services/memory_service.py` (Zeile 17)
  - `src/utils/services/chat_service.py` (Zeile 15)
- Diese Imports werden in **Schritt 1A** (Backend-Removal) entfernt

### 6.2 `src/utils/prompt_engine/migrator.py` – Referenz entfernen

**Zeile 34 – `memory_entries` aus `KNOWN_PLACEHOLDERS` entfernen:**

```python
# VORHER:
KNOWN_PLACEHOLDERS = {
    'char_name', 'user_name', 'language', 'char_description',
    'current_date', 'current_time', 'current_weekday',
    'user_type', 'user_type_description', 'user_info',
    'elapsed_time', 'inner_dialogue', 'input',
    'experimental_01', 'experimental_02', 'experimental_03',
    'prompt_id_3', 'memory_entries'
}

# NACHHER:
KNOWN_PLACEHOLDERS = {
    'char_name', 'user_name', 'language', 'char_description',
    'current_date', 'current_time', 'current_weekday',
    'user_type', 'user_type_description', 'user_info',
    'elapsed_time', 'inner_dialogue', 'input',
    'experimental_01', 'experimental_02', 'experimental_03',
    'prompt_id_3'
}
```

### 6.3 `src/utils/prompt_engine/engine.py` – Docstring anpassen

**Zeile 590 – Kommentar aktualisieren:**

```python
# VORHER (Zeile 590):
        """
        Baut System-Prompt und Prefill für Memory-Zusammenfassungen.
        """

# NACHHER:
        """
        Baut System-Prompt und Prefill für Zusammenfassungen (Summary).
        """
```

> **Hinweis:** `build_summary_prompt()` selbst bleibt erhalten – es handelt sich um Summary-Funktionalität die unabhängig vom Memory-System ist. Nur der falsch benannte Docstring wird korrigiert.

---

## 7. Dokumentation – Aktualisieren/Archivieren

### 7.1 `docs/10_Memory_System.md` – **ARCHIVIEREN ODER LÖSCHEN**

- 209 Zeilen, beschreibt das gesamte alte Memory-System
- Enthält: Architektur, Pipeline, MemoryService, Frontend, Routes, DB-Schema
- **Empfehlung:** Datei in `docs/_archive/10_Memory_System.md` verschieben oder löschen
- Wird durch neue Cortex-Dokumentation in späteren Schritten ersetzt

### 7.2 `docs/02_Configuration_and_Settings.md` – Eintrag entfernen

**Zeile 39 – Tabellenzeile entfernen:**
```markdown
| `memoriesEnabled` | `true` | Memories enabled |
```

---

## 8. Abhängigkeiten zu anderen Schritten

| Abhängigkeit | Schritt | Details |
|-------------|---------|---------|
| `memory_service.py` Import von `memory_context.py` | 1A | Import wird in Schritt 1A entfernt |
| `chat_service.py` Import von `memory_context.py` | 1A | Import wird in Schritt 1A entfernt |
| `MemoryManager.js` liest `memoriesEnabled` | 1B | Frontend-Referenzen werden in Schritt 1B entfernt |
| `MemoryOverlay.jsx` liest `memoriesEnabled` | 1B | React-Frontend wird in Schritt 1B entfernt |

> **Wichtig:** Schritt 1A (Backend) und 1B (Frontend) müssen die Imports/Referenzen auf `memory_context.py` und `memoriesEnabled` **vor** oder **gleichzeitig** mit diesem Schritt entfernen, um Import-Fehler zu vermeiden.

---

## 9. Verifizierungs-Checkliste

### Settings-Dateien
- [ ] `memoriesEnabled` Key aus `src/settings/user_settings.json` entfernt
- [ ] `memoriesEnabled` Key aus `src/settings/defaults.json` entfernt
- [ ] Keine weiteren `memory`-bezogenen Keys in Settings-Dateien vorhanden

### Prompt-Template Dateien
- [ ] `src/instructions/prompts/memory_context.json` gelöscht
- [ ] `src/instructions/prompts/_defaults/memory_context.json` gelöscht

### Prompt-Manifest
- [ ] `memory_context` Eintrag aus `src/instructions/prompts/_meta/prompt_manifest.json` entfernt
- [ ] `memory_context` Eintrag aus `src/instructions/prompts/_defaults/_meta/prompt_manifest.json` entfernt

### Placeholder-Registry
- [ ] `memory_entries` Eintrag aus `src/instructions/prompts/_meta/placeholder_registry.json` entfernt
- [ ] `memory_entries` Eintrag aus `src/instructions/prompts/_defaults/_meta/placeholder_registry.json` entfernt

### Prompt-Engine
- [ ] `src/utils/prompt_engine/memory_context.py` gelöscht
- [ ] `memory_entries` aus `KNOWN_PLACEHOLDERS` in `migrator.py` entfernt
- [ ] Docstring in `engine.py` `build_summary_prompt()` korrigiert

### Dokumentation
- [ ] `docs/10_Memory_System.md` archiviert/gelöscht
- [ ] `memoriesEnabled` Zeile aus `docs/02_Configuration_and_Settings.md` entfernt

### Validierung
- [ ] `grep -r "memoriesEnabled" src/settings/` liefert keine Treffer
- [ ] `grep -r "memory_context" src/instructions/` liefert keine Treffer
- [ ] `grep -r "memory_entries" src/instructions/` liefert keine Treffer
- [ ] `grep -r "memory_entries" src/utils/prompt_engine/` liefert keine Treffer
- [ ] `grep -r "memory_context" src/utils/prompt_engine/` liefert keine Treffer (außer evtl. Git-History)
- [ ] App startet ohne Fehler nach Entfernung
- [ ] Prompt-Engine `build_system_prompt()` funktioniert ohne `memory_context`
- [ ] Keine broken Imports durch gelöschte `memory_context.py`
