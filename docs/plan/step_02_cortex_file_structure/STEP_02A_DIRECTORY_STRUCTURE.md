# Schritt 2A: Cortex Verzeichnisstruktur & Datei-Templates

## Übersicht

Das Cortex-System ersetzt das alte SQL-basierte Memory-System durch Markdown-Dateien. Jede Persona erhält drei dedizierte `.md`-Dateien, die von der KI in Ich-Perspektive gepflegt werden. Dieses Dokument definiert die exakte Verzeichnisstruktur, die Templates für jede Datei, den Lebenszyklus und die Integration in das bestehende Persona-CRUD-System.

---

## 1. Verzeichnisstruktur

### Basis-Pfad

```
src/instructions/personas/cortex/
```

Relativ zu `BASE_DIR` (`src/`), analog zu den bestehenden Persona-Pfaden:

| Bestehend | Cortex (Neu) |
|-----------|-------------|
| `instructions/personas/default/` | `instructions/personas/cortex/default/` |
| `instructions/created_personas/{id}.json` | `instructions/personas/cortex/custom/{id}/` |
| `instructions/personas/active/` | *(kein Cortex-Äquivalent — aktive Persona wird per ID aufgelöst)* |

### Vollständiger Verzeichnisbaum

```
src/instructions/personas/cortex/
├── default/                          ← Cortex-Dateien der Default-Persona ("Mia")
│   ├── memory.md                     ← Erinnerungen der Persona
│   ├── soul.md                       ← Seelen-Entwicklung / innere Reifung
│   └── relationship.md              ← Beziehungsdynamik User ↔ Persona
└── custom/                           ← Cortex-Dateien benutzererstellter Personas
    └── {persona_id}/                 ← z.B. "a1b2c3d4" (UUID[:8] aus save_created_persona)
        ├── memory.md
        ├── soul.md
        └── relationship.md
```

### Pfad-Konvention als Python-Konstanten

```python
# In config.py oder einem neuen cortex_service.py:
CORTEX_BASE_DIR = os.path.join(BASE_DIR, 'instructions', 'personas', 'cortex')
CORTEX_DEFAULT_DIR = os.path.join(CORTEX_BASE_DIR, 'default')
CORTEX_CUSTOM_DIR = os.path.join(CORTEX_BASE_DIR, 'custom')

CORTEX_FILES = ['memory.md', 'soul.md', 'relationship.md']
```

### Pfad-Auflösung nach Persona-ID

```python
def get_cortex_dir(persona_id: str) -> str:
    """Gibt den Cortex-Ordner für eine Persona zurück."""
    if persona_id == 'default' or not persona_id:
        return CORTEX_DEFAULT_DIR
    return os.path.join(CORTEX_CUSTOM_DIR, persona_id)
```

Dies spiegelt die Logik von `get_db_path()` in `src/utils/database/connection.py`:

```python
# Bestehend (DB):
def get_db_path(persona_id: str = 'default') -> str:
    if persona_id == 'default' or not persona_id:
        return os.path.join(DATA_DIR, 'main.db')
    return os.path.join(DATA_DIR, f'persona_{persona_id}.db')

# Neu (Cortex) — gleiche ID-Logik:
def get_cortex_dir(persona_id: str = 'default') -> str:
    if persona_id == 'default' or not persona_id:
        return CORTEX_DEFAULT_DIR
    return os.path.join(CORTEX_CUSTOM_DIR, persona_id)
```

---

## 2. Datei-Templates

Jede der drei Dateien wird beim Erstellen einer Persona (oder beim ersten Zugriff) mit einem Template initialisiert. Die Templates sind auf Deutsch, in Ich-Perspektive der Persona verfasst.

### 2.1 `memory.md` — Erinnerungen

```markdown
# Erinnerungen

Hier halte ich fest, was ich mir merken möchte — Dinge die {{user}} mir erzählt hat,
gemeinsame Erlebnisse und Details die mir wichtig sind.

---

## Wichtige Details über {{user}}


## Gemeinsame Erlebnisse


## Dinge die ich mir merken möchte


## Präferenzen & Gewohnheiten


```

**Zweck:** Speichert konkrete Fakten, Ereignisse und Details die die Persona über den User und ihre gemeinsame Interaktion erfährt. Funktioniert wie ein persönliches Tagebuch/Notizbuch.

### 2.2 `soul.md` — Seelen-Entwicklung

```markdown
# Seelen-Entwicklung

Hier reflektiere ich über meine eigene Entwicklung — wie ich mich verändere,
was ich lerne und wie sich meine Persönlichkeit mit der Zeit formt.

---

## Wer ich bin


## Was mich bewegt


## Wie ich mich entwickle


## Meine inneren Konflikte & Erkenntnisse


```

**Zweck:** Dokumentiert die innere Entwicklung der Persona über die Zeit. Persönlichkeitsveränderungen, neue Einsichten, emotionale Reifung — geschrieben als Selbstreflexion.

### 2.3 `relationship.md` — Beziehungsdynamik

```markdown
# Beziehungsdynamik

Hier halte ich fest, wie sich meine Beziehung zu {{user}} entwickelt —
unsere Dynamik, unser Vertrauen und wie wir miteinander umgehen.

---

## Aktuelle Beziehungsdynamik


## Vertrauenslevel & Nähe


## Gemeinsame Themen & Interessen


## Spannungen & gelöste Konflikte


```

**Zweck:** Bildet die Beziehung zwischen Persona und User ab. Vertrauensaufbau, gemeinsame Interessen, Konflikte und deren Lösung — die soziale Dimension der Interaktion.

### Template-Platzhalter

Die Templates verwenden `{{user}}` als Platzhalter. Dieser wird **nicht** beim Datei-Erstellen aufgelöst, sondern bleibt als Marker stehen. Die Auflösung geschieht erst beim Einlesen in den System-Prompt durch das bestehende Placeholder-System (Schritt 4).

---

## 3. Verzeichnis-Erstellung (Lifecycle)

### 3.1 Wann werden Cortex-Verzeichnisse erstellt?

| Ereignis | Aktion |
|----------|--------|
| **Server-Start** | `ensure_cortex_default_dir()` — stellt sicher dass `cortex/default/` existiert und alle 3 Templates enthält |
| **Persona erstellen** (`save_created_persona`) | `create_cortex_dir(persona_id)` — erstellt `cortex/custom/{id}/` mit allen 3 Templates |
| **Erster Cortex-Zugriff** (Fallback) | `ensure_cortex_dir(persona_id)` — erstellt fehlende Dateien falls nötig (defensiv) |

### 3.2 Erstellungs-Funktionen

```python
def ensure_cortex_dir(persona_id: str) -> str:
    """
    Stellt sicher, dass der Cortex-Ordner für eine Persona existiert
    und alle Template-Dateien vorhanden sind.
    Gibt den Ordnerpfad zurück.
    """
    cortex_dir = get_cortex_dir(persona_id)
    os.makedirs(cortex_dir, exist_ok=True)
    
    templates = {
        'memory.md': MEMORY_TEMPLATE,
        'soul.md': SOUL_TEMPLATE,
        'relationship.md': RELATIONSHIP_TEMPLATE,
    }
    
    for filename, template_content in templates.items():
        filepath = os.path.join(cortex_dir, filename)
        if not os.path.exists(filepath):
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(template_content)
    
    return cortex_dir


def create_cortex_dir(persona_id: str) -> bool:
    """Erstellt den Cortex-Ordner für eine neue Persona mit allen Templates."""
    try:
        ensure_cortex_dir(persona_id)
        log.info("Cortex-Verzeichnis erstellt für Persona: %s", persona_id)
        return True
    except Exception as e:
        log.error("Fehler beim Erstellen des Cortex-Verzeichnisses für %s: %s", persona_id, e)
        return False


def delete_cortex_dir(persona_id: str) -> bool:
    """Löscht den Cortex-Ordner einer Persona (bei Persona-Löschung)."""
    if persona_id == 'default':
        log.warning("Default Cortex-Verzeichnis kann nicht gelöscht werden!")
        return False
    
    cortex_dir = get_cortex_dir(persona_id)
    try:
        if os.path.exists(cortex_dir):
            shutil.rmtree(cortex_dir)
            log.info("Cortex-Verzeichnis gelöscht: %s", cortex_dir)
            return True
        return False
    except Exception as e:
        log.error("Fehler beim Löschen des Cortex-Verzeichnisses für %s: %s", persona_id, e)
        return False
```

### 3.3 Lifecycle-Diagramm

```
┌─────────────────┐     ┌──────────────────────────────────────────┐
│  Server-Start   │────►│ ensure_cortex_dir('default')             │
│                 │     │ → cortex/default/{memory,soul,rel}.md    │
└─────────────────┘     └──────────────────────────────────────────┘

┌─────────────────┐     ┌──────────────────────────────────────────┐
│ Persona erstellt│────►│ save_created_persona(config_data)        │
│ (Creator UI)    │     │   ├── persona_id = uuid4()[:8]           │
│                 │     │   ├── created_personas/{id}.json         │
│                 │     │   ├── create_persona_db(id)    ← EXISTING│
│                 │     │   └── create_cortex_dir(id)    ← NEU     │
└─────────────────┘     └──────────────────────────────────────────┘

┌─────────────────┐     ┌──────────────────────────────────────────┐
│ Persona löschen │────►│ delete_created_persona(persona_id)       │
│ (Settings UI)   │     │   ├── os.remove({id}.json)               │
│                 │     │   ├── delete_persona_db(id)    ← EXISTING│
│                 │     │   └── delete_cortex_dir(id)    ← NEU     │
└─────────────────┘     └──────────────────────────────────────────┘

┌─────────────────┐     ┌──────────────────────────────────────────┐
│ Cortex-Zugriff  │────►│ ensure_cortex_dir(persona_id)            │
│ (Chat / Editor) │     │ → Fehlende Dateien werden nacherstellt   │
│                 │     │   (defensiver Fallback)                  │
└─────────────────┘     └──────────────────────────────────────────┘
```

---

## 4. Integration in bestehendes Persona-CRUD (`config.py`)

### 4.1 `save_created_persona` — Erweitern

**Datei:** `src/utils/config.py`, Zeile ~452

**Bestehend:**
```python
def save_created_persona(config_data: Dict[str, Any]) -> Optional[str]:
    ensure_created_personas_dir()
    try:
        persona_id = str(uuid.uuid4())[:8]
        filename = f"{persona_id}.json"
        filepath = os.path.join(CREATED_PERSONAS_DIR, filename)
        
        save_data = {
            "id": persona_id,
            "persona_settings": config_data
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        
        # Erstelle die zugehörige Persona-Datenbank
        create_persona_db(persona_id)
        
        return persona_id
```

**Erweiterung (nach `create_persona_db`):**
```python
        # Erstelle die zugehörige Persona-Datenbank
        create_persona_db(persona_id)
        
        # NEU: Erstelle den Cortex-Ordner mit Templates
        create_cortex_dir(persona_id)
        
        return persona_id
```

### 4.2 `delete_created_persona` — Erweitern

**Datei:** `src/utils/config.py`, Zeile ~522

**Bestehend:**
```python
def delete_created_persona(persona_id: str) -> bool:
    if persona_id == "default":
        return False
    
    ensure_created_personas_dir()
    filepath = os.path.join(CREATED_PERSONAS_DIR, f"{persona_id}.json")
    
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            # Lösche die zugehörige Persona-Datenbank
            delete_persona_db(persona_id)
            return True
```

**Erweiterung (nach `delete_persona_db`):**
```python
            os.remove(filepath)
            # Lösche die zugehörige Persona-Datenbank
            delete_persona_db(persona_id)
            # NEU: Lösche den Cortex-Ordner
            delete_cortex_dir(persona_id)
            return True
```

### 4.3 Server-Start — Default sicherstellen

**Datei:** `src/app.py` oder `src/init.py` (dort wo `init_all_dbs()` aufgerufen wird)

```python
# Nach init_all_dbs():
from utils.cortex_service import ensure_cortex_dir
ensure_cortex_dir('default')
```

### 4.4 Import-Anpassungen

```python
# config.py — neuer Import (oben):
from utils.cortex_service import create_cortex_dir, delete_cortex_dir
```

---

## 5. `.gitignore` Anpassungen

Cortex-Inhalte sind Benutzerdaten und dürfen **nicht** ins Repository committed werden. Allerdings soll die Verzeichnisstruktur selbst existieren.

### Neue Einträge in `.gitignore`

```gitignore
# Cortex-Dateien (Persona-Erinnerungen, benutzergeneriert)
src/instructions/personas/cortex/default/*.md
src/instructions/personas/cortex/custom/
```

### `.gitkeep` Dateien

Um sicherzustellen, dass die Verzeichnisstruktur im Repository erhalten bleibt:

```
src/instructions/personas/cortex/.gitkeep
src/instructions/personas/cortex/default/.gitkeep
src/instructions/personas/cortex/custom/.gitkeep
```

### Zusammenfassung der .gitignore-Strategie

| Pfad | Im Repo? | Begründung |
|------|----------|------------|
| `cortex/` | ✅ (via .gitkeep) | Struktur muss existieren |
| `cortex/default/` | ✅ (via .gitkeep) | Struktur muss existieren |
| `cortex/default/*.md` | ❌ (gitignored) | Benutzerdaten |
| `cortex/custom/` | ✅ (via .gitkeep) | Struktur muss existieren |
| `cortex/custom/{id}/` | ❌ (gitignored) | Benutzerdaten |

Dies folgt dem bestehenden Muster:
- `src/instructions/created_personas/` → gitignored (Benutzerdaten)
- `src/instructions/personas/active/persona_config.json` → gitignored (Benutzerdaten)

---

## 6. Zusammenfassung der Änderungen

### Neue Dateien

| Datei | Zweck |
|-------|-------|
| `src/instructions/personas/cortex/.gitkeep` | Verzeichnis im Repo behalten |
| `src/instructions/personas/cortex/default/.gitkeep` | Verzeichnis im Repo behalten |
| `src/instructions/personas/cortex/custom/.gitkeep` | Verzeichnis im Repo behalten |

### Zu ändernde Dateien

| Datei | Änderung |
|-------|----------|
| `src/utils/config.py` | `save_created_persona` → + `create_cortex_dir()` |
| `src/utils/config.py` | `delete_created_persona` → + `delete_cortex_dir()` |
| `src/utils/config.py` | Neuer Import: `from utils.cortex_service import create_cortex_dir, delete_cortex_dir` |
| `src/app.py` oder `src/init.py` | `ensure_cortex_dir('default')` beim Start |
| `.gitignore` | Cortex-Benutzerdaten ignorieren |

### Neues Modul (wird in Schritt 2B detailliert)

| Datei | Inhalt |
|-------|--------|
| `src/utils/cortex_service.py` | `get_cortex_dir()`, `ensure_cortex_dir()`, `create_cortex_dir()`, `delete_cortex_dir()`, `read_cortex_file()`, `write_cortex_file()`, Templates |

---

## 7. Offene Entscheidungen für Folgeschritte

| Frage | Entscheidung in Schritt |
|-------|------------------------|
| Wie werden `{{user}}` Platzhalter in Cortex-Dateien aufgelöst? | Schritt 4 (Computed Placeholders) |
| Wie werden Cortex-Dateien in den System-Prompt injiziert? | Schritt 4 (Prompt-Templates) |
| Wie triggert der Chat-Flow ein Cortex-Update? | Schritt 3 + 6 (Activation Tiers) |
| Wie kann der User die Dateien manuell editieren? | Schritt 5 (Cortex Settings UI) |
