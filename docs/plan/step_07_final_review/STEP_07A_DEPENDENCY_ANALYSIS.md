# Schritt 7A: Abhängigkeits- und Konsistenzanalyse

> **⚠️ KORREKTUR v3:** Dieses Dokument basiert noch teilweise auf dem alten 3-Tier-Sequenz-Modell. Folgende Punkte sind durch das neue Single-Frequency-Modell OBSOLET oder VERÄNDERT:
>
> - **2.7 (Tier-Schwellwerte Format):** OBSOLET — Es gibt keine `tierThresholds` mehr. `cortex_settings.json` enthält nur `{"enabled": true, "frequency": "medium"}`.
> - **2.6 (cortexEnabled an zwei Orten):** GELÖST — `cortexEnabled` bleibt in `user_settings.json`, `cortex_settings.json` enthält nur `frequency`. Kein Konflikt mehr.
> - **2.8/2.9 (API-Endpunkt/fileType vs filename):** Weiterhin relevant, unverändert.
> - **5.1 (Settings-Landscape):** OBSOLET — Keine `tierThresholds` mehr. Nur `cortexEnabled` (in `user_settings.json`) und `frequency` (in `cortex_settings.json`).
> - **3.3 (Paket-Exports):** GEÄNDERT — `get_fired_tiers`, `mark_tier_fired`, `rebuild_from_message_count` entfallen. Neue Exports: `get_cycle_base`, `set_cycle_base`, `reset_session`, `reset_all`, `rebuild_cycle_base`, `get_progress`.
> - **4.2 (SSE-Done-Event):** GEÄNDERT — Backend sendet jetzt `cortex: {triggered, progress, frequency}` statt `cortex_update: {tier, status}`.
> - **Settings-Keys:** `cortexTier1/2/3` entfallen. Nur noch `cortexEnabled` + `cortexFrequency` in `user_settings.json`.

## Übersicht

Dieses Dokument analysiert die **gesamte Cortex-Migrationstrategie** (Schritte 1–6) auf:

1. **Abhängigkeitskonflikte** — Widersprüche zwischen Schrittdefinitionen
2. **Fehlende Dateien** — Referenzierte Artefakte ohne Erstellungsschritt
3. **Import/Export-Konsistenz** — Stimmen Module, Pfade und Exports überein?
4. **API-Vertragskonsistenz** — Sind Backend-Endpoints und Frontend-Calls kompatibel?
5. **Settings-Konsistenz** — Sind Keys, Speicherorte und Datenformate widerspruchsfrei?

### Bewertungsskala

| Symbol | Bedeutung |
|--------|-----------|
| 🔴 **KRITISCH** | Blockiert die Implementierung, muss VOR dem jeweiligen Schritt gelöst werden |
| 🟡 **WARNUNG** | Inkonsistenz, die Fehler verursachen kann, wenn nicht adressiert |
| 🟢 **HINWEIS** | Verbesserungsvorschlag, nicht blockierend |
| ✅ **OK** | Geprüft, konsistent |

---

## 1. Vollständiges Datei-Inventar

### 1.1 NEUE Dateien (zu erstellen)

| # | Datei | Erstellt in | Abhängig von |
|---|-------|-------------|--------------|
| N1 | `src/utils/cortex_service.py` | Step 2B | — |
| N2 | `src/routes/cortex.py` | Step 2C | N1 |
| N3 | `src/settings/cortex_settings.json` | Step 6C (Runtime) | — |
| N4 | `src/instructions/personas/cortex/default/.gitkeep` (+ 3 Template-Dateien) | Step 2B | — |
| N5 | `src/utils/cortex/__init__.py` | Step 3B | — |
| N6 | `src/utils/cortex/tier_tracker.py` | Step 3B | — |
| N7 | `src/utils/cortex/tier_checker.py` | Step 3B | N6, N3 |
| N8 | `src/utils/cortex/update_service.py` | Step 3C | N1, N7, ApiClient |
| N9 | `src/instructions/prompts/cortex_context.json` | Step 4B | — |
| N10 | `src/instructions/prompts/_defaults/cortex_context.json` | Step 4B | N9 |
| N11 | `frontend/src/features/overlays/CortexOverlay.jsx` | Step 5A | N14 |
| N12 | `frontend/src/services/cortexApi.js` | Step 5B | N2 |
| N13 | `frontend/src/features/chat/components/CortexUpdateIndicator/CortexUpdateIndicator.jsx` | Step 5C | — |
| N14 | `frontend/src/features/chat/components/CortexUpdateIndicator/CortexUpdateIndicator.module.css` | Step 5C | — |
| N15 | `src/utils/settings_migration.py` | Step 6C | — |
| N16 | `src/utils/cortex/settings.py` | Step 6C | N3 |

### 1.2 MODIFIZIERTE Dateien

| # | Datei | Geändert in | Art der Änderung |
|---|-------|-------------|------------------|
| M1 | `src/utils/provider.py` | Step 2B, 6B | `_memory_service` → `_cortex_service`, neue Accessor-Funktion |
| M2 | `src/utils/config.py` | Step 2B, 6B | `create_cortex_dir()` / `delete_cortex_dir()` Aufrufe in Persona-Lifecycle |
| M3 | `src/routes/__init__.py` | Step 2C, 6B | `memory_bp` → `cortex_bp` |
| M4 | `src/utils/api_request/types.py` | Step 3A | `tools` Feld in `RequestConfig`, `tool_results` in `ApiResponse` |
| M5 | `src/utils/api_request/client.py` | Step 3A | `tool_request()` Methode, `ToolExecutor` Typ, `MAX_TOOL_ROUNDS` |
| M6 | `src/utils/api_request/__init__.py` | Step 3A | Export `ToolExecutor` |
| M7 | `src/routes/chat.py` | Step 3B, 6A | Tier-Check in `generate()`, `cortex_update` im Done-Event |
| M8 | `src/utils/services/chat_service.py` | Step 4A, 6A | `_load_cortex_context()`, runtime_vars, memory-Entfernung |
| M9 | `src/utils/cortex_service.py` | Step 4B | `get_cortex_for_prompt()` Refinement mit Section-Headers |
| M10 | `src/utils/prompt_engine/engine.py` | Step 4C | `_should_include_block()`, `_clean_resolved_text()`, `requires_any` |
| M11 | `src/utils/prompt_engine/validator.py` | Step 4C | `validate_requires_any()` |
| M12 | `src/instructions/prompts/_meta/prompt_manifest.json` | Step 4B/4C | `+cortex_context` Eintrag |
| M13 | `src/instructions/prompts/_meta/placeholder_registry.json` | Step 4A | +3 Cortex-Placeholder-Einträge |
| M14 | `src/instructions/prompts/_defaults/_meta/prompt_manifest.json` | Step 4C | Identische Defaults-Kopie |
| M15 | `src/instructions/prompts/_defaults/_meta/placeholder_registry.json` | Step 4A | Identische Defaults-Kopie |
| M16 | `src/settings/defaults.json` | Step 4C, 6C | `memoriesEnabled` → `cortexEnabled: true` |
| M17 | `frontend/src/features/overlays/index.js` | Step 5A, 5C | `MemoryOverlay` → `CortexOverlay` Export |
| M18 | `frontend/src/features/overlays/Overlays.module.css` | Step 5A | Neue Cortex-CSS-Klassen |
| M19 | `frontend/src/features/chat/ChatPage.jsx` | Step 5C | Import, Hook, Render (Memory→Cortex), CortexUpdateIndicator |
| M20 | `frontend/src/features/chat/components/Header/Header.jsx` | Step 5C | `onOpenMemory` → `onOpenCortex`, Polling entfernen |
| M21 | `frontend/src/features/chat/components/Header/Header.module.css` | Step 5C | `.memory*` → `.cortex*` Klassen |
| M22 | `frontend/src/context/SessionContext.jsx` | Step 5C | `lastMemoryMessageId` entfernen |
| M23 | `frontend/src/features/chat/hooks/useMessages.js` | Step 5C | `cortex-update` CustomEvent dispatchen |
| M24 | `frontend/src/features/overlays/DebugOverlay.jsx` | Step 5C | Memory-Debug → Cortex-Debug-Felder |
| M25 | `src/splash_screen/utils/startup.py` | Step 6B, 6C | `ensure_cortex_dirs()` + `migrate_settings()` Aufrufe |
| M26 | `src/app.py` | Step 6B, 6C | `ensure_cortex_dirs()` + `migrate_settings()` in Fallback-Pfaden |
| M27 | `.gitignore` | Step 2C | Cortex-User-Daten-Patterns |

### 1.3 ZU LÖSCHENDE Dateien

| # | Datei | Gelöscht in | Prüfung: Referenzen entfernt? |
|---|-------|-------------|-------------------------------|
| D1 | `src/utils/database/memories.py` | Step 1A | ✅ Provider + `__init__` bereinigt |
| D2 | `src/utils/services/memory_service.py` | Step 1A | ✅ Provider + `__init__` bereinigt |
| D3 | `src/utils/prompt_engine/memory_context.py` | Step 1A | ✅ ChatService-Import entfernt |
| D4 | `src/routes/memory.py` | Step 1A | ✅ `__init__` bereinigt |
| D5 | `src/sql/memories.sql` | Step 1A | 🔴 Enthält `upsert_db_info` - muss relocated werden! |
| D6 | `src/instructions/prompts/memory_context.json` | Step 1A | ✅ Manifest bereinigt |
| D7 | `src/instructions/prompts/_defaults/memory_context.json` | Step 1A | ✅ |
| D8 | 7× `src/instructions/prompts/summary_*.json` | Step 1A | ✅ |
| D9 | `tests/test_services/test_memory_service.py` | Step 1A | ✅ |
| D10 | `frontend/src/features/overlays/MemoryOverlay.jsx` | Step 5C | ✅ CortexOverlay als Ersatz |
| D11 | `frontend/src/services/memoryApi.js` | Step 5C | ✅ cortexApi.js als Ersatz |
| D12 | `src/static/js/modules/MemoryManager.js` | Step 1B | ✅ Legacy-Frontend |
| D13 | `src/templates/chat/_overlay_memory.html` | Step 1B | ✅ Legacy-Template |

---

## 2. Gefundene Inkonsistenzen & Konflikte

### 2.1 🔴 KRITISCH: Duplizierte `execute_cortex_update()` Implementierung

**Betroffene Schritte:** Step 2B vs. Step 3C

**Problem:** Step 2B definiert in `CortexService` eine eigene `execute_cortex_update()`-Methode, die direkt `self.api_client.client.messages.create(...)` aufruft — d.h. die Anthropic-SDK direkt nutzt und den `ApiClient` umgeht. Step 3C erstellt eine separate Klasse `CortexUpdateService` mit einer eigenen `execute_update()`-Methode, die `ApiClient.tool_request()` nutzt.

**Konsequenz:** Zwei divergierende Implementierungen für dieselbe Aufgabe. Beide enthalten Tool-Definitionen (`CORTEX_TOOLS`), System-Prompt-Builder und Executor-Logik.

**Empfohlene Lösung:**
- `CortexService` (Step 2B) behält **nur** Dateisystem-Operationen: `read_file()`, `write_file()`, `read_all()`, `get_cortex_for_prompt()`, `ensure_cortex_files()`, `delete_cortex_dir()`
- `execute_cortex_update()` wird aus `CortexService` **entfernt** — die Verantwortung liegt bei `CortexUpdateService` (Step 3C)
- `CORTEX_TOOLS`-Definition und `CORTEX_UPDATE_SYSTEM_PROMPT` werden in `CortexUpdateService` zentralisiert
- Step 2B-Dokument muss entsprechend korrigiert werden

---

### 2.2 🔴 KRITISCH: Tool-Namen Inkonsistenz

**Betroffene Schritte:** Step 2B vs. Step 3C

**Problem:**
- Step 2B definiert Tool-Namen als `cortex_read_file` und `cortex_write_file`
- Step 3C definiert Tool-Namen als `read_file` und `write_file`

Die Tool-Namen stehen in den `CORTEX_TOOLS`-Definitionen, die an die Anthropic-API gesendet werden. Wenn auch der Tool-Executor diese Namen zum Dispatching nutzt, entsteht ein Mismatch.

**Empfohlene Lösung:**
- Standardisiere auf `read_file` / `write_file` (Step 3C Variante)
- Kein `cortex_`-Prefix nötig, da die Tools nur im isolierten Cortex-Update-Kontext verwendet werden
- Step 2B-Definitionen entfernen (da die gesamte Update-Logik zu Step 3C gehört)

---

### 2.3 🔴 KRITISCH: `_load_cortex_context()` Rückgabetyp-Widerspruch

**Betroffene Schritte:** Step 2B vs. Step 4A

**Problem:**
- Step 2B definiert `_load_cortex_context()` im `ChatService` als Methode, die einen **formatierten String** zurückgibt (ein einzelner Text-Block für `first_assistant`)
- Step 4A definiert `_load_cortex_context()` im `ChatService` als Methode, die ein **Dict[str, str]** zurückgibt (`{'cortex_memory': '...', 'cortex_soul': '...', 'cortex_relationship': '...'}`) für `runtime_vars`

Dies sind zwei unvereinbare Ansätze für dieselbe Methode.

**Empfohlene Lösung:**
- Step 4A (Dict-Variante) ist die korrekte, finale Version — Cortex-Daten fließen als `runtime_vars` in den System-Prompt
- Step 2B's String-Variante stammt aus einer früheren Konzeptphase und muss im Planungsdokument als überholt gekennzeichnet werden
- Die `_build_chat_messages()` Methode benötigt keinen `memory_context` Parameter mehr (bestätigt in Step 6A)

---

### 2.4 🟡 WARNUNG: Tier-Check Positionierung (BEFORE vs. AFTER done yield)

**Betroffene Schritte:** Step 3B vs. Step 6A

**Problem:**
- Step 3B Abschnitt 3.2 positioniert den Tier-Check **nach** dem letzten `yield` in `generate()` — der Client hat das Done-Event bereits erhalten
- Step 3B Abschnitt 8.2 schlägt alternativ vor, den Tier-Check **vor** dem Done-Yield zu machen, um `cortex_update` ins Done-Event einzubauen
- Step 6A entscheidet sich definitiv für **vor** dem Done-Yield (synchron, ~5ms)

**Konsequenz:** Kein Code-Konflikt, da Step 6A die finale Architekturentscheidung trifft. Aber Step 3B enthält widersprüchliche Empfehlungen.

**Empfohlene Lösung:**
- Step 3B Abschnitt 3.2 als überholt markieren
- Step 6A Abschnitt 3.3 ist maßgeblich: Tier-Check **vor** Done-Yield, Ergebnis im Done-Event
- Bei der Implementierung von Step 3B den `chat.py`-Code so vorbereiten, dass er den Tier-Check vor dem Yield ausführt (nicht erst in Step 6A umbauen)

---

### 2.5 🟡 WARNUNG: CortexService Import-Pfad Unstimmigkeit

**Betroffene Schritte:** Step 2B vs. Step 6B

**Problem:**
- Step 2B platziert `CortexService` unter `src/utils/cortex_service.py` (flaches Modul)
- Step 6B referenziert `from .cortex.service import CortexService` (als Package `src/utils/cortex/service.py`)
- Step 3B/3C erstellt das Package `src/utils/cortex/` mit `__init__.py`, `tier_tracker.py`, `tier_checker.py`, `update_service.py`

Es ist unklar, ob `CortexService` als eigenständige Datei `cortex_service.py` oder als Teil des `cortex/` Packages (`cortex/service.py`) leben soll.

**Empfohlene Lösung:**
- `CortexService` in das `cortex/` Package verschieben: `src/utils/cortex/service.py`
- Dies gruppiert alle Cortex-Funktionalität in ein kohärentes Package:
  ```
  src/utils/cortex/
  ├── __init__.py
  ├── service.py          (CortexService - Dateisystem-Ops)
  ├── tier_tracker.py     (In-Memory Tier-State)
  ├── tier_checker.py     (Threshold-Berechnung + Trigger)
  ├── update_service.py   (CortexUpdateService - API Tool-Use)
  └── settings.py         (cortex_settings.json Lesen/Schreiben)
  ```
- Alle Imports entsprechend anpassen: `from utils.cortex.service import CortexService`
- Step 2B Pfad-Angabe korrigieren

---

### 2.6 🟡 WARNUNG: `cortexEnabled` existiert an zwei Orten

**Betroffene Schritte:** Step 5A vs. Step 6C

**Problem:**
- Step 5A (`CortexOverlay.jsx`) liest `cortexEnabled` über `useSettings().get('cortexEnabled')` und speichert über `setMany()` → `user_settings.json`
- Step 6C definiert `cortexEnabled` auch in `cortex_settings.json`
- Step 6C Abschnitt 3.4 erklärt, dass `user_settings.json` maßgeblich ist und `cortex_settings.json` nur als "Referenz-Default" dient

**Konsequenz:** Zwei Quellen der Wahrheit für `cortexEnabled`. Der `tier_checker.py` (Step 3B) liest aus `cortex_settings.json`, aber der ChatService (Step 4C) prüft `user_settings.json` via `get_setting('cortexEnabled')`. Wenn ein User den Toggle im Overlay ändert (→ `user_settings.json`), greift der Tier-Checker ggf. noch auf den alten Wert in `cortex_settings.json` zu.

**Empfohlene Lösung:**
- **Option A (Empfohlen):** `cortexEnabled` nur in `user_settings.json` speichern. `cortex_settings.json` enthält **nur** Tier-Schwellwerte und andere domänenspezifische Parameter. Der `tier_checker` liest `cortexEnabled` über `get_setting()`.
- **Option B:** `cortexEnabled` in `cortex_settings.json` als Single Source of Truth. CortexOverlay speichert über `/api/cortex/settings`. Erfordert Änderung am SettingsContext-Pattern.
- Option A ist besser, weil es das bestehende Settings-Pattern beibehält.

---

### 2.7 🟡 WARNUNG: Tier-Schwellwerte Frontend vs. Backend Datenformat

**Betroffene Schritte:** Step 5A vs. Step 6C vs. Step 3B

**Problem:**
- Step 5A (CortexOverlay) speichert Tiers über `useSettings().setMany()` als **String-Werte** in `user_settings.json`: `cortexTier1: "50"`, `cortexTier2: "75"`, `cortexTier3: "95"`
- Step 6C (cortex_settings.json) definiert Tiers als **Integer** in verschachtelter Struktur: `tierThresholds: { tier1: 50, tier2: 75, tier3: 95 }`
- Step 3B (tier_checker) liest Tier-Schwellwerte aus `cortex_settings.json` via `_load_tier_config()`

**Konsequenz:** Das Frontend schreibt Tiers in `user_settings.json` (flach, als Strings), der Backend-Tier-Checker liest aus `cortex_settings.json` (verschachtelt, als Integers). Die Werte werden **nicht synchronisiert**.

**Empfohlene Lösung:**
- **Option A (Empfohlen):** CortexOverlay speichert Tiers über die Cortex-Settings-API (`PUT /api/cortex/settings`) statt über `setMany()`. Die Tier-Schwellwerte gehören nicht in `user_settings.json`, sondern in `cortex_settings.json`. Der `useSettings()`-Hook wird nur für `cortexEnabled` verwendet.
- CortexOverlay muss beim Öffnen die Tier-Werte via `GET /api/cortex/settings` laden (nicht über `useSettings().get()`).
- Step 5A Code-Beispiel muss angepasst werden: Trennung zwischen `cortexEnabled` (useSettings) und Tier-Parametern (cortexApi).

---

### 2.8 🟡 WARNUNG: API-Endpunkt-Signaturen variieren

**Betroffene Schritte:** Step 2C vs. Step 5A vs. Step 5B

**Problem:** Die REST-Endpunkte werden an verschiedenen Stellen mit leicht abweichenden Signaturen referenziert:

| Endpoint | Step 2C (Backend-Def) | Step 5A (Frontend-Def) | Step 5B (cortexApi.js) |
|---|---|---|---|
| Files laden | `GET /api/cortex/files?persona_id=` | `GET /api/cortex/files?persona_id=` | `GET /api/cortex/files?persona_id=` |
| File speichern | `PUT /api/cortex/file/<filename>` | `PUT /api/cortex/files` (Body: `file_type`) | `PUT /api/cortex/file/<filename>` |
| File resetten | `POST /api/cortex/reset/<filename>` | `POST /api/cortex/files/reset` (Body: `file_type`) | `POST /api/cortex/reset/<filename>` |

Step 5A definiert in Abschnitt 3 vereinfachte Endpunkt-Varianten (`/api/cortex/files` für PUT, `/api/cortex/files/reset` für POST mit `file_type` im Body), während Step 2C und Step 5B die Dateinamen im URL-Pfad verwenden.

**Empfohlene Lösung:**
- Step 2C und Step 5B sind konsistent (Dateiname im Pfad) → dies ist die maßgebliche API-Definition
- Step 5A Abschnitt 3 enthält eine vereinfachte Vorab-Skizze → in der CortexOverlay-Implementierung müssen die korrekten Endpunkte aus Step 5B (`cortexApi.js`) verwendet werden
- Step 5A Inline-Servicedefinition (Abschnitt 3) als veraltet markieren — `cortexApi.js` ist die offizielle Service-Schicht

---

### 2.9 🟡 WARNUNG: `fileType` vs. `filename` Parameterbezeichnung

**Betroffene Schritte:** Step 5A vs. Step 5B

**Problem:**
- Step 5A (CortexOverlay) verwendet `fileType` als Konzept: `'memory'`, `'soul'`, `'relationship'` (ohne `.md` Extension)
- Step 5B (cortexApi.js) verwendet `filename`: `'memory.md'`, `'soul.md'`, `'relationship.md'` (mit `.md`)
- Step 2C (Backend) erwartet `filename` im URL-Pfad: `/api/cortex/file/memory.md`

**Konsequenz:** Das CortexOverlay muss beim API-Call `.md` an den `fileType` anhängen, oder die Mapping-Logik liegt im cortexApi Service.

**Empfohlene Lösung:**
- CortexOverlay-Tabs verwenden intern `fileType` ohne Extension (`'memory'`, `'soul'`, `'relationship'`)
- Beim Aufruf von `cortexApi.saveCortexFile()` wird `.md` angehängt: `saveCortexFile(personaId, fileType + '.md', content)`
- Alternativ: cortexApi-Funktionen akzeptieren beides und normalisieren intern

---

### 2.10 🟡 WARNUNG: `upsert_db_info` in `memories.sql`

**Betroffene Schritte:** Step 1A

**Problem:** Step 1A identifiziert korrekt, dass `memories.sql` die SQL-Query `upsert_db_info` enthält, die **nicht** memory-spezifisch ist, sondern allgemein verwendet wird. Wenn `memories.sql` gelöscht wird, geht diese Query verloren.

**Empfohlene Lösung:**
- **Vor** dem Löschen von `memories.sql`: `upsert_db_info` Query nach `chat.sql` oder eine neue `db_utils.sql` verschieben
- Alle Referenzen auf `upsert_db_info` prüfen und Import-Pfade aktualisieren

---

### 2.11 🟡 WARNUNG: `ensure_cortex_dirs()` fehlende Definition

**Betroffene Schritte:** Step 6B

**Problem:** Step 6B referenziert eine Funktion `ensure_cortex_dirs()` die beim Startup aufgerufen wird, aber:
- Step 2B definiert `ensure_cortex_files(persona_id)` im `CortexService` (pro Persona)
- Step 6B referenziert `ensure_cortex_dirs()` als eigenständige Funktion (iteriert über alle Personas)
- Es gibt keine explizite Definition von `ensure_cortex_dirs()` in einem der Plan-Dokumente

**Empfohlene Lösung:**
- `ensure_cortex_dirs()` als eigenständige Funktion in `src/utils/cortex/service.py` definieren:
  ```python
  def ensure_cortex_dirs():
      """Erstellt Cortex-Verzeichnisse für Default + alle Custom-Personas."""
      cortex_service = CortexService()
      cortex_service.ensure_cortex_files('default')
      for persona_file in glob.glob('instructions/created_personas/*.json'):
          persona_id = os.path.splitext(os.path.basename(persona_file))[0]
          cortex_service.ensure_cortex_files(persona_id)
  ```
- Alternativ als statische Methode oder Modul-Level-Funktion im `cortex/service.py`

---

### 2.12 🟢 HINWEIS: `cortexEnabled` Setting-Check in `_load_cortex_context()`

**Betroffene Schritte:** Step 4A vs. Step 4C

**Problem:** 
- Step 4A definiert `_load_cortex_context()` ohne `cortexEnabled`-Prüfung — gibt immer Cortex-Daten zurück
- Step 4C erweitert `_load_cortex_context()` um einen `cortexEnabled`-Check, der leere Strings zurückgibt wenn deaktiviert

**Bewertung:** Kein echter Konflikt — Step 4C ist die finale, vollständige Version, die Step 4A ergänzt. In der Implementierung sollte direkt die Step 4C-Version umgesetzt werden.

---

### 2.13 🟢 HINWEIS: Regenerate und Tier-Check

**Betroffene Schritte:** Step 3B vs. Step 5C vs. Step 6A

**Problem:** 
- Step 3B Abschnitt 9 sagt: Regenerate ändert die Nachrichtenanzahl nicht → kein Tier-Check nötig
- Step 5C Abschnitt 7.2 bestätigt: kein Cortex-Event bei `regenerateLastMsg`
- Step 6A Abschnitt 3.4 fügt den Tier-Check aber **auch** in `api_regenerate()` ein

**Bewertung:** Step 6A behandelt den Fall korrekt — ein Regenerate erzeugt eine neue Bot-Antwort, die die Nachrichtenanzahl der Session durchaus verändern kann (z.B. wenn die letzte Bot-Nachricht ersetzt wird). Der Tier-Check in `api_regenerate()` schadet nicht und fängt Edge-Cases ab.

---

### 2.14 🟢 HINWEIS: Cortex-Verzeichnisstruktur (default vs. custom)

**Betroffene Schritte:** Step 2B vs. Step 6B

**Problem:**
- Step 2B verwendet `instructions/personas/cortex/{persona_id}/` (flach)
- Step 6B verwendet `instructions/personas/cortex/default/` und `instructions/personas/cortex/custom/{persona_id}/`

**Bewertung:** Step 6B hat die differenziertere Struktur. Empfehlung: Step 6B Variante mit `default/` und `custom/` Unterverzeichnissen verwenden, und `get_cortex_dir()` entsprechend implementieren.

---

### 2.15 🟢 HINWEIS: `memory_entries` Placeholder in Registry

**Betroffene Schritte:** Step 1A vs. Step 4A

**Problem:** Step 1A erwähnt das Entfernen von `memory_entries` aus der Placeholder-Registry. Step 4A fügt 3 neue Cortex-Placeholders hinzu. Es wird nicht explizit bestätigt, dass `memory_entries` gleichzeitig entfernt wird.

**Empfohlene Lösung:** Step 1A und Step 4A koordiniert umsetzen — beim Hinzufügen der Cortex-Placeholders gleichzeitig `memory_entries` entfernen.

---

## 3. Import/Export-Konsistenz

### 3.1 Backend Python Imports

| Quellmodul | Import-Pfad | Definiert in | Status |
|---|---|---|---|
| `provider.py` → `CortexService` | `from .cortex.service import CortexService` (Step 6B) / `from .cortex_service import CortexService` (Step 2B) | Step 2B / reorganisiert in 6B | 🟡 Pfad muss vereinheitlicht werden (siehe 2.5) |
| `config.py` → `create_cortex_dir` | `from utils.cortex.service import create_cortex_dir` | Step 6B | ✅ |
| `config.py` → `delete_cortex_dir` | `from utils.cortex.service import delete_cortex_dir` | Step 6B | ✅ |
| `chat.py` → `check_and_trigger_cortex_update` | `from utils.cortex.tier_checker import check_and_trigger_cortex_update` | Step 3B | ✅ |
| `tier_checker.py` → `CortexUpdateService` | `from utils.cortex.update_service import CortexUpdateService` (lazy) | Step 3C | ✅ |
| `update_service.py` → `CortexService` | Implizit via `provider.get_cortex_service()` | Step 2B | ✅ |
| `update_service.py` → `ApiClient` | Via `provider.get_api_client()` | Bestehend | ✅ |
| `chat_service.py` → `get_cortex_service` | `from ..provider import get_cortex_service` | Step 2B | ✅ |
| `routes/__init__.py` → `cortex_bp` | `from routes.cortex import cortex_bp` | Step 2C | ✅ |
| `startup.py` → `ensure_cortex_dirs` | `from utils.cortex.service import ensure_cortex_dirs` | Step 6B | 🟡 Funktion muss noch definiert werden (siehe 2.11) |
| `startup.py` → `migrate_settings` | `from utils.settings_migration import migrate_settings` | Step 6C | ✅ |

### 3.2 Frontend JavaScript Imports

| Quellmodul | Import | Definiert in | Status |
|---|---|---|---|
| `ChatPage.jsx` → `CortexOverlay` | `from '../overlays'` (barrel) | Step 5A via `index.js` | ✅ |
| `ChatPage.jsx` → `CortexUpdateIndicator` | `from './components/CortexUpdateIndicator/CortexUpdateIndicator'` | Step 5C | ✅ |
| `CortexOverlay.jsx` → cortexApi | `from '../../services/cortexApi'` | Step 5B | ✅ |
| `DebugOverlay.jsx` → `getCortexFiles` | `from '../../services/cortexApi'` | Step 5B | ✅ |
| `Header.jsx` → ~~`checkMemoryAvailability`~~ | ENTFERNT | Step 5C | ✅ |

### 3.3 Paket-Exports

| Paket | Export | Importiert von | Status |
|---|---|---|---|
| `src/utils/cortex/__init__.py` | `get_fired_tiers`, `mark_tier_fired`, `reset_session`, `reset_all`, `rebuild_from_message_count`, `check_and_trigger_cortex_update`, `CortexUpdateService` | `tier_checker.py`, `chat.py` | ✅ |
| `src/utils/api_request/__init__.py` | `ApiClient`, `ToolExecutor` | `update_service.py` | ✅ |
| `frontend/src/features/overlays/index.js` | `CortexOverlay` (statt `MemoryOverlay`) | `ChatPage.jsx` | ✅ |

---

## 4. API-Vertragskonsistenz

### 4.1 REST-Endpunkte: Backend-Definition vs. Frontend-Konsumption

| Endpoint | Backend (Step 2C) | Frontend (Step 5B) | Status |
|---|---|---|---|
| `GET /api/cortex/files` | Query: `persona_id`. Response: `{ success, files: {memory, soul, relationship}, persona_id }` | `getCortexFiles(personaId)` → `apiGet('/api/cortex/files?persona_id=...')` | ✅ |
| `GET /api/cortex/file/<filename>` | Query: `persona_id`. Response: `{ success, filename, content, persona_id }` | `getCortexFile(personaId, filename)` → `apiGet('/api/cortex/file/${filename}?persona_id=...')` | ✅ |
| `PUT /api/cortex/file/<filename>` | Body: `{ content, persona_id }`. Response: `{ success, filename, persona_id }` | `saveCortexFile(personaId, filename, content)` → `apiPut('/api/cortex/file/${filename}', { content, persona_id })` | ✅ |
| `POST /api/cortex/reset/<filename>` | Body: `{ persona_id }`. Response: `{ success, filename, content, persona_id }` | `resetCortexFile(personaId, filename)` → `apiPost('/api/cortex/reset/${filename}', { persona_id })` | ✅ |
| `POST /api/cortex/reset` | Body: `{ persona_id }`. Response: `{ success, files: {...}, persona_id }` | `resetAllCortexFiles(personaId)` → `apiPost('/api/cortex/reset', { persona_id })` | ✅ |
| `GET /api/cortex/settings` | Response: `{ success, settings, defaults }` | `getCortexSettings()` → `apiGet('/api/cortex/settings')` | ✅ |
| `PUT /api/cortex/settings` | Body: partial settings. Response: `{ success, settings, defaults }` | `saveCortexSettings(settings)` → `apiPut('/api/cortex/settings', settings)` | ✅ |

### 4.2 SSE-Event-Vertrag

| Event | Backend (Step 6A) | Frontend (Step 5C) | Status |
|---|---|---|---|
| `done` | `{ type: 'done', response, stats, character_name, cortex_update?: { tier, status } }` | `data.cortex_update?.triggered` → CustomEvent | 🟡 |

**Problem bei SSE-Done-Event:**
- Backend sendet `cortex_update: { tier: 2, status: 'started' }`
- Frontend (Step 5C, useMessages.js) prüft `data.cortex_update?.triggered`

Das Backend sendet **kein** `triggered` Feld — es sendet `tier` und `status`. Das Frontend prüft fälschlicherweise auf `triggered`.

**Empfohlene Lösung:**
- Frontend-Check anpassen: `if (data.cortex_update)` (Existenz des Objekts reicht)
- Oder Backend erweitern: `cortex_update: { triggered: true, tier: 2, status: 'started' }`

---

### 4.3 Stats-Objekt

| Feld | Vorher | Nachher (Step 6A) | Frontend-Kompatibilität |
|---|---|---|---|
| `memory_est` | Vorhanden (int) | **Entfernt** | 🟡 Frontend muss defensiv `stats.memory_est ?? 0` verwenden |
| `system_prompt_est` | Enthielt nur Prompt-Text | Enthält jetzt auch Cortex-Daten | ✅ Wert steigt, kein Breaking Change |

---

## 5. Settings-Konsistenz

### 5.1 Settings-Landscape nach Migration

| Key | Speicherort | Gelesen von | Geschrieben von | Default |
|---|---|---|---|---|
| `cortexEnabled` | `user_settings.json` | ChatService, SettingsContext | CortexOverlay (via Settings-API) | `true` |
| `tierThresholds.tier1` | `cortex_settings.json` | `tier_checker.py` | CortexOverlay (via Cortex-API) | `50` |
| `tierThresholds.tier2` | `cortex_settings.json` | `tier_checker.py` | CortexOverlay (via Cortex-API) | `75` |
| `tierThresholds.tier3` | `cortex_settings.json` | `tier_checker.py` | CortexOverlay (via Cortex-API) | `95` |

### 5.2 🟡 Redundanz: `cortexEnabled` in zwei Dateien

Wie in 2.6 beschrieben — `cortexEnabled` erscheint sowohl in `user_settings.json` als auch in `cortex_settings.json`. **Empfehlung:** Nur in `user_settings.json`, `cortex_settings.json` enthält nur domänenspezifische Parameter.

### 5.3 ✅ Defaults-Migration

Die Migration von `memoriesEnabled` → `cortexEnabled` in `user_settings.json` ist konsistent definiert (Step 6C). Idempotent, forward-compatible, mit korrekter Fehlerbehandlung.

### 5.4 ✅ Settings-Reset-Verhalten

- Reset → `defaults.json` wird geschrieben → `cortexEnabled: true`
- `cortex_settings.json` wird **nicht** beim Settings-Reset zurückgesetzt → Tier-Werte bleiben erhalten
- Dies ist gewünscht und konsistent dokumentiert

---

## 6. Abhängigkeitsmatrix

### 6.1 Implementierungsreihenfolge (Dependency Graph)

```
Step 1 (Remove Old Memory)
  │
  ├──► Step 2B (CortexService)
  │       │
  │       ├──► Step 2C (Cortex API Routes)
  │       │       │
  │       │       └──► Step 5A (CortexOverlay)
  │       │               │
  │       │               └──► Step 5B (cortexApi.js)
  │       │
  │       └──► Step 3A (Tool-Use API Extensions)
  │               │
  │               ├──► Step 3B (Tier Logic)
  │               │       │
  │               │       └──► Step 3C (CortexUpdateService)
  │               │
  │               └ (implizit: ApiClient Erweiterungen)
  │
  ├──► Step 4A (Placeholders)
  │       │
  │       └──► Step 4B (Prompt Template)
  │               │
  │               └──► Step 4C (Engine Integration)
  │
  ├──► Step 5C (ChatPage Wiring) ← benötigt 5A, 5B, 3B
  │
  ├──► Step 6A (Chat-Flow Modification) ← benötigt 2B, 3B, 4A/4C
  │
  ├──► Step 6B (End-to-End Integration) ← benötigt ALLE vorherigen
  │
  └──► Step 6C (Settings Migration) ← benötigt nur defaults.json Kenntnis
```

### 6.2 Parallelisierung

Folgende Schritte können **parallel** implementiert werden:

| Parallele Gruppe | Schritte | Voraussetzung |
|---|---|---|
| Gruppe A: Dateisystem + API | Step 2B, 2C | Step 1 abgeschlossen |
| Gruppe B: Prompt-System | Step 4A, 4B | Step 1 abgeschlossen (Memory-Placeholder entfernt) |
| Gruppe C: Frontend | Step 5A, 5B | Step 2C implementiert |
| Gruppe D: Tool-Use | Step 3A | Keine Abhängigkeit zu Step 2 |

**Serielle Abhängigkeiten (NICHT parallelisierbar):**
- Step 3B → Step 3C (Tier-Checker muss vor UpdateService existieren)
- Step 4A → 4B → 4C (Aufbauend)
- Step 6A → 6B (Chat-Flow vor End-to-End)

---

## 7. Zusammenfassung der Findings

### 7.1 Kritische Issues (müssen vor Implementierung gelöst werden)

| # | Issue | Betroffene Schritte | Lösung |
|---|-------|---------------------|--------|
| 1 | Duplizierte `execute_cortex_update()` | 2B vs. 3C | Aus CortexService entfernen, nur in CortexUpdateService |
| 2 | Tool-Namen `cortex_read_file` vs. `read_file` | 2B vs. 3C | Standardisiere auf `read_file`/`write_file` |
| 3 | `_load_cortex_context()` returns `str` vs. `Dict` | 2B vs. 4A | Step 4A Dict-Variante ist korrekt, Step 2B überholt |

### 7.2 Warnungen (sollten bei Implementierung berücksichtigt werden)

| # | Issue | Betroffene Schritte | Lösung |
|---|-------|---------------------|--------|
| 4 | Tier-Check Position (before/after yield) | 3B vs. 6A | Step 6A maßgeblich (before yield) |
| 5 | CortexService Import-Pfad | 2B vs. 6B | Verschiebe in `cortex/service.py` Package |
| 6 | `cortexEnabled` an zwei Orten | 5A vs. 6C | Nur in `user_settings.json` |
| 7 | Tier-Schwellwerte Format (String vs. Int, flach vs. verschachtelt) | 5A vs. 6C vs. 3B | CortexOverlay nutzt Cortex-API für Tiers |
| 8 | API-Endpunkt-Varianten in Step 5A | 5A vs. 2C/5B | Step 5B cortexApi.js ist maßgeblich |
| 9 | `fileType` vs. `filename` (`.md` Extension) | 5A vs. 5B | CortexOverlay hängt `.md` an beim API-Call |
| 10 | `upsert_db_info` in `memories.sql` | 1A | Vor Löschung nach `chat.sql` verschieben |
| 11 | `ensure_cortex_dirs()` nicht explizit definiert | 6B | Funktion in `cortex/service.py` erstellen |
| 12 | SSE `cortex_update.triggered` vs. Objekt-Existenz | 5C vs. 6A | Frontend auf Objekt-Existenz prüfen |

### 7.3 Hinweise (nicht blockierend)

| # | Issue | Empfehlung |
|---|-------|------------|
| 13 | `cortexEnabled` Setting-Check Timing (4A vs. 4C) | Step 4C Version direkt umsetzen |
| 14 | Regenerate Tier-Check (3B vs. 6A) | Step 6A ist korrekt — Tier-Check auch bei Regenerate |
| 15 | Cortex-Verzeichnisstruktur (`default/` vs. `custom/`) | Step 6B Variante verwenden |
| 16 | `memory_entries` Placeholder entfernen | Koordiniert mit Step 4A Cortex-Placeholder-Hinzufügung |

---

## 8. Empfohlene Handlungsschritte

### 8.1 Vor Implementierungsbeginn

1. **Step 2B Dokument bereinigen:**
   - `execute_cortex_update()` Methode als "verschoben nach Step 3C" markieren
   - `CORTEX_TOOLS` und `CORTEX_UPDATE_SYSTEM_PROMPT` als "definiert in Step 3C" markieren
   - Import-Pfad auf `src/utils/cortex/service.py` korrigieren
   - `_load_cortex_context()` String-Variante als "überholt, siehe Step 4A" markieren

2. **Step 3B Dokument bereinigen:**
   - Abschnitt 3.2 (Tier-Check nach Yield) als "überholt, siehe Step 6A" markieren
   - Abschnitt 8.2 (alternative Position) als "bestätigt in Step 6A" markieren

3. **Step 5A Settings-Integration klären:**
   - Tier-Schwellwerte über Cortex-API statt `useSettings()` 
   - `cortexEnabled` bleibt in `useSettings()`

4. **Step 5C SSE-Handler korrigieren:**
   - `data.cortex_update?.triggered` → `data.cortex_update` (Existenzprüfung)

### 8.2 Während der Implementierung

5. **Step 1A: `upsert_db_info` Query** aus `memories.sql` nach `chat.sql` verschieben **bevor** `memories.sql` gelöscht wird

6. **Step 2B: CortexService Pfad** direkt als `src/utils/cortex/service.py` (im Package) anlegen — nicht als `src/utils/cortex_service.py`

7. **Step 6B: `ensure_cortex_dirs()`** als eigenständige Funktion implementieren, die über alle Personas iteriert

8. **Dateiname-Mapping im Frontend:** Sicherstellen, dass `CortexOverlay` den `fileType` (`'memory'`) korrekt auf den `filename` (`'memory.md'`) mappt beim API-Call

---

## 9. Datei-Änderungs-Heatmap

Dateien nach Anzahl der Schritte, die sie modifizieren:

| Datei | Modifiziert in Schritten | Anz. |
|---|---|---|
| `src/utils/services/chat_service.py` | 1A, 4A, 6A | 3 |
| `src/utils/provider.py` | 1A, 2B, 6B | 3 |
| `src/routes/__init__.py` | 1A, 2C, 6B | 3 |
| `src/routes/chat.py` | 3B, 6A | 2 |
| `src/utils/prompt_engine/engine.py` | 1A, 4C | 2 |
| `src/settings/defaults.json` | 4C, 6C | 2 |
| `src/app.py` | 6B, 6C | 2 |
| `src/splash_screen/utils/startup.py` | 6B, 6C | 2 |
| `frontend/src/features/chat/ChatPage.jsx` | 1B, 5C | 2 |
| `frontend/src/features/chat/components/Header/Header.jsx` | 1B, 5C | 2 |

> **Risiko-Hotspot:** `chat_service.py`, `provider.py` und `routes/__init__.py` werden in 3 verschiedenen Schritten geändert. Entwickler sollten Merge-Konflikte erwarten und diese Dateien nicht parallel in verschiedenen Feature-Branches bearbeiten.

---

## 10. Gesamtbewertung

| Aspekt | Bewertung |
|--------|-----------|
| **Planungstiefe** | Sehr hoch — jeder Schritt enthält detaillierte Codebeispiele, Edge-Cases und Begründungen |
| **Architekturelle Sauberkeit** | Gut — klare Trennung von Zuständigkeiten (Service, Route, Engine, Frontend) |
| **Kritische Probleme** | 3 echte Konflikte (duplizierte Update-Logik, Tool-Namen, Rückgabetyp) — alle in Step 2B verortet |
| **Konsistenz Backend-Frontend** | 1 echtes Problem (SSE `triggered` Feld), Rest kleinere Naming-Diskrepanzen |
| **Settings-Architektur** | Leicht verworren (2 Dateien, 2 API-Pfade) — mit empfohlener Bereinigung gut handhabbar |
| **Implementierungsrisiko** | Mittel — alle kritischen Issues sind lösbar durch Bereinigung der Plan-Dokumente |
| **Parallelisierungspotential** | Hoch — 4 parallele Gruppen möglich nach Step 1 Abschluss |

**Fazit:** Der Migrationsplan ist solid und detailliert. Die drei kritischen Konflikte stammen alle aus Step 2B, das eine frühe Konzeptphase widerspiegelt, die von späteren Schritten (3C, 4A, 6A) verfeinert wurde. Durch Bereinigung der Step-2B-Dokumentation (Entfernung der Update-Logik, Korrektur des Import-Pfads, Überholt-Markierung der String-Variante) werden alle 🔴-Issues aufgelöst. Die 🟡-Warnungen erfordern punktuelle Korrekturen bei der Implementierung, sind aber nicht blockierend.
