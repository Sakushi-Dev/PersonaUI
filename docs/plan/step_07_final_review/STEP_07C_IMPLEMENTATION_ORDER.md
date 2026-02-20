# Schritt 7C: Finale Implementierungsreihenfolge

## Übersicht

Dieses Dokument definiert die **verbindliche Implementierungsreihenfolge** für die Cortex-Migration. Es basiert auf:

- **7A:** 3 kritische + 9 Warnungen (Abhängigkeiten & Konsistenz)
- **7B:** 2 kritische + 6 hohe Issues (Logikfehler & Laufzeitrisiken)
- **00_OVERVIEW:** Architektur-Referenz und Abhängigkeitsgraph

Jede Phase ist **eigenständig testbar**, enthält alle identifizierten Fixes, und kann bei Fehler isoliert zurückgerollt werden.

### Konventionen

| Symbol | Bedeutung |
|--------|-----------|
| 📄 **CREATE** | Neue Datei erstellen |
| ✏️ **MODIFY** | Bestehende Datei ändern |
| 🗑️ **DELETE** | Datei löschen |
| 🔧 **FIX** | Korrektur aus 7A/7B einarbeiten |
| ⏱️ | Geschätzter Aufwand |

---

## Phase 1: Altes Memory-System entfernen

> **Ziel:** Clean Slate — alle Memory-Artefakte entfernen, ohne neue Funktionalität einzuführen.
>
> ⏱️ **Geschätzter Aufwand: 3–4 Stunden**

### 1.1 Dateien (in Reihenfolge)

| # | Aktion | Datei | Beschreibung |
|---|--------|-------|--------------|
| 1 | 🔧 **FIX (7A #10)** | `src/sql/memories.sql` | `upsert_db_info` Query nach `src/sql/chat.sql` verschieben **BEVOR** Löschung |
| 2 | ✏️ MODIFY | `src/sql/chat.sql` | `upsert_db_info` Query einfügen (aus `memories.sql` übernommen) |
| 3 | ✏️ MODIFY | Referenzen auf `upsert_db_info` | Import-Pfade aktualisieren (z.B. `load_query('memories', 'upsert_db_info')` → `load_query('chat', 'upsert_db_info')`) |
| 4 | 🗑️ DELETE | `src/utils/database/memories.py` | Memory-DB-Layer |
| 5 | 🗑️ DELETE | `src/utils/services/memory_service.py` | Memory-Service |
| 6 | 🗑️ DELETE | `src/utils/prompt_engine/memory_context.py` | Memory-Prompt-Kontext |
| 7 | 🗑️ DELETE | `src/routes/memory.py` | Memory-API-Routen |
| 8 | 🗑️ DELETE | `src/sql/memories.sql` | Memory-SQL (nach Query-Migration) |
| 9 | 🗑️ DELETE | `src/instructions/prompts/memory_context.json` | Memory-Prompt-Template |
| 10 | 🗑️ DELETE | `src/instructions/prompts/_defaults/memory_context.json` | Memory-Prompt-Default |
| 11 | 🗑️ DELETE | `src/instructions/prompts/summary_*.json` (7 Dateien) | Summary-Prompt-Templates |
| 12 | 🗑️ DELETE | `tests/test_services/test_memory_service.py` | Memory-Tests |
| 13 | ✏️ MODIFY | `src/utils/provider.py` | `_memory_service` Registrierung entfernen, `get_memory_service()` entfernen |
| 14 | ✏️ MODIFY | `src/routes/__init__.py` | `memory_bp` Import + Registrierung entfernen |
| 15 | ✏️ MODIFY | `src/utils/services/chat_service.py` | Memory-Imports entfernen, `include_memories` Parameter entfernen, `_build_memory_context()` entfernen |
| 16 | ✏️ MODIFY | `src/utils/prompt_engine/engine.py` | `memory_context` Import/Referenz entfernen |
| 17 | 🔧 **FIX (7A #16)** | `src/instructions/prompts/_meta/placeholder_registry.json` | `memory_entries` Placeholder entfernen |
| 18 | 🔧 **FIX (7A #16)** | `src/instructions/prompts/_defaults/_meta/placeholder_registry.json` | `memory_entries` Placeholder entfernen |
| 19 | ✏️ MODIFY | `src/instructions/prompts/_meta/prompt_manifest.json` | `memory_context` Eintrag entfernen |
| 20 | ✏️ MODIFY | `src/instructions/prompts/_defaults/_meta/prompt_manifest.json` | `memory_context` Eintrag entfernen |
| 21 | 🗑️ DELETE | `src/static/js/modules/MemoryManager.js` | Legacy-Frontend Memory-Manager |
| 22 | 🗑️ DELETE | `src/templates/chat/_overlay_memory.html` | Legacy-Memory-Template |
| 23 | 🗑️ DELETE | `frontend/src/features/overlays/MemoryOverlay.jsx` | React Memory-Overlay |
| 24 | 🗑️ DELETE | `frontend/src/services/memoryApi.js` | Memory-API-Service |
| 25 | ✏️ MODIFY | `frontend/src/features/overlays/index.js` | `MemoryOverlay` Export entfernen |
| 26 | ✏️ MODIFY | `frontend/src/features/chat/ChatPage.jsx` | Memory-Overlay Import + Render entfernen |
| 27 | ✏️ MODIFY | `frontend/src/features/chat/components/Header/Header.jsx` | `onOpenMemory` Prop + Memory-Button entfernen, Memory-Polling entfernen |
| 28 | ✏️ MODIFY | `frontend/src/features/chat/components/Header/Header.module.css` | `.memory*` CSS-Klassen entfernen |
| 29 | ✏️ MODIFY | `frontend/src/context/SessionContext.jsx` | `lastMemoryMessageId` State entfernen |
| 30 | ✏️ MODIFY | `frontend/src/features/overlays/DebugOverlay.jsx` | Memory-Debug-Felder entfernen |

### 1.2 Einzuarbeitende Fixes

| Fix-ID | Quelle | Beschreibung | Angewendet bei |
|--------|--------|--------------|----------------|
| 7A #10 | `upsert_db_info` Relocation | Query nach `chat.sql` verschieben bevor `memories.sql` gelöscht wird | Schritt 1–3 |
| 7A #16 | `memory_entries` Placeholder | Aus Registry entfernen (koordiniert mit Phase 4) | Schritt 17–18 |
| 7B #11 | `include_memories` Parameter | Vor Entfernung alle Aufrufer prüfen (`grep -r "include_memories" src/`) | Schritt 15 |

### 1.3 Testkriterien

- [ ] Server startet ohne Fehler (`python src/app.py`)
- [ ] Kein Import-Error in Logs (alle Memory-Referenzen entfernt)
- [ ] Chat-Funktion arbeitet normal (ohne Memory-Kontext)
- [ ] `grep -r "memory_service\|MemoryOverlay\|memoryApi\|memories\.sql\|memory_context" src/ frontend/src/` findet **keine** aktiven Referenzen
- [ ] Frontend baut ohne Fehler (`cd frontend && npm run build`)
- [ ] Bestehende Tests laufen (minus gelöschte Memory-Tests): `pytest -x`

### 1.4 Rollback-Strategie

```bash
git stash  # oder: git checkout -- .
# Alle gelöschten Dateien über git restore wiederherstellen
git restore src/utils/database/memories.py src/utils/services/memory_service.py ...
```

Phase 1 ist rein subtraktiv — kein neuer Code wird eingeführt. Vollständiges Rollback über Git.

---

## Phase 2: Cortex-Datei-Infrastruktur erstellen

> **Ziel:** Verzeichnisstruktur, CortexService (Dateisystem-Ops), API-Routen für Dateizugriff.
>
> ⏱️ **Geschätzter Aufwand: 4–6 Stunden**

### 2.1 Dateien (in Reihenfolge)

| # | Aktion | Datei | Beschreibung |
|---|--------|-------|--------------|
| 1 | 📄 CREATE | `src/utils/cortex/__init__.py` | Package-Init, Exports |
| 2 | 🔧📄 **FIX (7A #5) + CREATE** | `src/utils/cortex/service.py` | `CortexService` — **NUR** Dateisystem-Ops (read, write, ensure, delete). Pfad: `cortex/service.py` statt `cortex_service.py` |
| 3 | 🔧 **FIX (7B #1)** | `src/utils/cortex/service.py` | Atomarer Schreibvorgang via `tempfile` + `os.replace()` in `write_file()` |
| 4 | 🔧 **FIX (7B #2)** | `src/utils/cortex/service.py` | `MAX_CORTEX_FILE_SIZE = 8000` Zeichen-Limit in `write_file()` |
| 5 | 🔧 **FIX (7B #7)** | `src/utils/cortex/service.py` | In-Memory-Cache mit `_cache_lock` für read/write-through |
| 6 | 🔧 **FIX (7B #6)** | `src/utils/cortex/service.py` | `write_file()` prüft Verzeichnis-Existenz — kein auto-`makedirs` |
| 7 | 🔧 **FIX (7A #11)** | `src/utils/cortex/service.py` | `ensure_cortex_dirs()` als Modul-Level-Funktion (iteriert über alle Personas) |
| 8 | 📄 CREATE | `src/instructions/personas/cortex/default/memory.md` | Default-Template für Memory |
| 9 | 📄 CREATE | `src/instructions/personas/cortex/default/soul.md` | Default-Template für Soul |
| 10 | 📄 CREATE | `src/instructions/personas/cortex/default/relationship.md` | Default-Template für Relationship |
| 11 | 📄 CREATE | `src/instructions/personas/cortex/default/.gitkeep` | Git-Tracking des Verzeichnisses |
| 12 | 📄 CREATE | `src/routes/cortex.py` | Blueprint `cortex_bp` mit allen Cortex-Endpoints |
| 13 | ✏️ MODIFY | `src/routes/__init__.py` | `cortex_bp` Import + Registrierung |
| 14 | ✏️ MODIFY | `src/utils/provider.py` | `_cortex_service` Registrierung + `get_cortex_service()` Accessor |
| 15 | ✏️ MODIFY | `src/utils/config.py` | `create_cortex_dir(persona_id)` / `delete_cortex_dir(persona_id)` in Persona-Lifecycle |
| 16 | ✏️ MODIFY | `.gitignore` | Cortex-User-Daten-Patterns (`instructions/personas/cortex/custom/`) |
| 17 | 📄 CREATE | `src/utils/cortex/settings.py` | Lesen/Schreiben von `cortex_settings.json` |
| 18 | 📄 CREATE | `src/settings/cortex_settings.json` | Default-Konfiguration (Tier-Schwellwerte) |

### 2.2 Einzuarbeitende Fixes

| Fix-ID | Quelle | Beschreibung | Angewendet bei |
|--------|--------|--------------|----------------|
| 7A #1 | Duplizierte `execute_cortex_update()` | **NICHT** in `CortexService` implementieren — nur Dateisystem-Ops. Update-Logik kommt erst in Phase 3 (`CortexUpdateService`) | Schritt 2 |
| 7A #2 | Tool-Namen | Keine Tool-Definitionen in `CortexService` — gehören zu `CortexUpdateService` (Phase 3) | Schritt 2 |
| 7A #5 | Import-Pfad | `src/utils/cortex/service.py` (Package), nicht `src/utils/cortex_service.py` (flach) | Schritt 2 |
| 7A #11 | `ensure_cortex_dirs()` | Als eigenständige Funktion definieren, die über alle Personas iteriert | Schritt 7 |
| 7B #1 | Race Condition | Atomarer Write via `tempfile.mkstemp()` + `os.replace()` | Schritt 3 |
| 7B #2 | Dateigröße-Limit | `MAX_CORTEX_FILE_SIZE = 8000` Zeichen, Truncation + Warning-Log | Schritt 4 |
| 7B #6 | Persona-Delete während Update | `write_file()` prüft Verzeichnis-Existenz, wirft `FileNotFoundError` | Schritt 6 |
| 7B #7 | Kein Caching | In-Memory-Cache `Dict[str, Dict[str, str]]` mit `threading.Lock`, Write-Through | Schritt 5 |
| 7A #15 | Verzeichnisstruktur | `default/` + `custom/{persona_id}/` Variante (Step 6B) verwenden | Schritt 2, 8–11 |

### 2.3 Testkriterien

- [ ] `CortexService` kann Dateien lesen/schreiben/löschen
- [ ] Atomarer Write: Parallel-Test — Lesen während Schreiben liefert immer vollständige Datei
- [ ] Dateigröße-Limit: Content > 8000 Zeichen wird gekürzt + Log-Warning
- [ ] Cache: Zweiter Read nach Write liefert neuen Content ohne Disk-Zugriff
- [ ] `ensure_cortex_dirs()` erstellt Verzeichnisse für Default + alle Custom-Personas
- [ ] API-Endpoints funktional:
  - `GET /api/cortex/files?persona_id=default` → 200 + 3 Dateien
  - `PUT /api/cortex/file/memory.md` → 200 + Content gespeichert
  - `POST /api/cortex/reset/memory.md` → 200 + Default-Content restored
  - `GET /api/cortex/settings` → 200 + Tier-Defaults
  - `PUT /api/cortex/settings` → 200 + Settings aktualisiert
- [ ] Server startet ohne Fehler
- [ ] Bestehende Tests laufen weiterhin

### 2.4 Rollback-Strategie

```bash
# Neue Dateien löschen
rm -rf src/utils/cortex/ src/routes/cortex.py src/settings/cortex_settings.json
rm -rf src/instructions/personas/cortex/
# Geänderte Dateien zurücksetzen
git checkout -- src/routes/__init__.py src/utils/provider.py src/utils/config.py .gitignore
```

---

## Phase 3: Tool-Use API-Erweiterung + Cortex-Update-Service

> **Ziel:** `ApiClient` um `tool_request()` erweitern, Tier-System implementieren, `CortexUpdateService` erstellen.
>
> ⏱️ **Geschätzter Aufwand: 6–8 Stunden**

### 3.1 Dateien (in Reihenfolge)

| # | Aktion | Datei | Beschreibung |
|---|--------|-------|--------------|
| 1 | ✏️ MODIFY | `src/utils/api_request/types.py` | `tools` Feld in `RequestConfig`, `tool_results` in `ApiResponse` |
| 2 | ✏️ MODIFY | `src/utils/api_request/client.py` | `tool_request()` Methode, `ToolExecutor` Typ, `MAX_TOOL_ROUNDS` |
| 3 | ✏️ MODIFY | `src/utils/api_request/__init__.py` | Export `ToolExecutor` |
| 4 | 📄 CREATE | `src/utils/cortex/tier_tracker.py` | In-Memory Tier-State (`_fired_tiers`, `_last_update_time`) |
| 5 | 🔧📄 **FIX (7B #3, #5) + CREATE** | `src/utils/cortex/tier_checker.py` | Tier-Threshold-Berechnung + Trigger-Logik. Fixes: Höchsten Tier feuern bei Kaskade; Minimum-Schwellwert Tier 1 ≥ 8 |
| 6 | 🔧 **FIX (7B #4)** | `src/utils/cortex/tier_checker.py` | Lazy-Rebuild: `check_and_trigger_cortex_update()` prüft ob Session in `_fired_tiers` bekannt, sonst `rebuild_from_message_count()` |
| 7 | 🔧 **FIX (7B #13)** | `src/utils/cortex/tier_checker.py` | Lazy-Init bei Session-Wechsel (`key not in _fired_tiers` → rebuild) |
| 8 | 🔧📄 **FIX (7A #1, #2) + CREATE** | `src/utils/cortex/update_service.py` | `CortexUpdateService` — einzige Quelle für Update-Logik. Tool-Namen: `read_file` / `write_file` (ohne Prefix) |
| 9 | 🔧 **FIX (7B #15)** | `src/utils/cortex/update_service.py` | Thread-Guard via `_active_updates` Dict statt `threading.enumerate()` |
| 10 | ✏️ MODIFY | `src/utils/cortex/__init__.py` | Exports aktualisieren: `get_fired_tiers`, `mark_tier_fired`, `reset_session`, `reset_all`, `rebuild_from_message_count`, `check_and_trigger_cortex_update`, `CortexUpdateService` |

### 3.2 Einzuarbeitende Fixes

| Fix-ID | Quelle | Beschreibung | Angewendet bei |
|--------|--------|--------------|----------------|
| 7A #1 | Duplizierte Update-Logik | `CortexUpdateService` ist die **einzige** Implementierung von `execute_update()`. Keine Update-Logik in `CortexService` | Schritt 8 |
| 7A #2 | Tool-Namen | `read_file` / `write_file` (ohne `cortex_`-Prefix). Tools nur in `CORTEX_TOOLS` des `CortexUpdateService` definiert | Schritt 8 |
| 7A #4 | Tier-Check Position | Tier-Check direkt **VOR** Done-Yield implementieren (Step 6A maßgeblich), nicht danach | Schritt 5 — Vorbereitung der Check-Funktion |
| 7B #3 | Tier-Kaskade | Bei Überschreitung mehrerer Tiers nur den **höchsten** feuern, niedrigere als gefeuert markieren | Schritt 5 |
| 7B #4 | Lazy Rebuild | Kein Startup-Rebuild. Rebuild beim **ersten Chat-Request** einer unbekannten Session | Schritt 6 |
| 7B #5 | Minimal-Konversation | `MINIMUM_TIER1_THRESHOLD = 8` — Tier 1 feuert frühestens bei 8 Nachrichten | Schritt 5 |
| 7B #13 | Session-Wechsel | `check_and_trigger_cortex_update()` prüft `key not in _fired_tiers` → Lazy-Init | Schritt 7 |
| 7B #15 | Thread-Enumeration | `_active_updates: Dict[str, threading.Thread]` mit Lock statt `threading.enumerate()` | Schritt 9 |

### 3.3 Testkriterien

- [ ] `ApiClient.tool_request()` führt Tool-Use-Loop korrekt aus (Mock-Test)
- [ ] `ToolExecutor` Typ-Definition funktional
- [ ] Tier-Schwellwerte korrekt berechnet: `contextLimit=100` → T1=50, T2=75, T3=95
- [ ] Tier-Schwellwerte mit Minimum: `contextLimit=10` → T1=**8** (nicht 5), T2=7→8, T3=9
- [ ] Tier-Kaskade: Bei Überschreitung aller 3 Tiers wird nur Tier 3 gefeuert, T1+T2 als gefeuert markiert
- [ ] Lazy Rebuild: Unbekannte Session löst Rebuild aus, nicht der Startup
- [ ] Thread-Guard: Zweiter Update für gleiche Persona wird blockiert wenn erster noch läuft
- [ ] `CortexUpdateService.execute_update()` ruft Tool-Loop korrekt aus (Integration-Test mit Mock-API)
- [ ] Rate-Limiting verhindert Updates innerhalb von 30 Sekunden
- [ ] Bestehende Tests laufen weiterhin

### 3.4 Rollback-Strategie

```bash
# Neue Dateien löschen
rm src/utils/cortex/tier_tracker.py src/utils/cortex/tier_checker.py src/utils/cortex/update_service.py
# Geänderte Dateien zurücksetzen
git checkout -- src/utils/api_request/types.py src/utils/api_request/client.py src/utils/api_request/__init__.py src/utils/cortex/__init__.py
```

Phase 2 (CortexService + Routes) bleibt funktional — Phase 3 ist additiv.

---

## Phase 4: Prompt-Templates + Placeholder-Integration

> **Ziel:** Cortex-Daten als `{{cortex_*}}` Placeholder im System-Prompt verfügbar machen.
>
> ⏱️ **Geschätzter Aufwand: 4–5 Stunden**

### 4.1 Dateien (in Reihenfolge)

| # | Aktion | Datei | Beschreibung |
|---|--------|-------|--------------|
| 1 | 🔧✏️ **FIX (7A #3) + MODIFY** | `src/utils/services/chat_service.py` | `_load_cortex_context()` gibt `Dict[str, str]` zurück (nicht String). Direkt die Step-4A-Variante implementieren. Inkl. `cortexEnabled`-Check (Step 4C) |
| 2 | ✏️ MODIFY | `src/instructions/prompts/_meta/placeholder_registry.json` | +3 Cortex-Placeholder: `cortex_memory`, `cortex_soul`, `cortex_relationship` |
| 3 | ✏️ MODIFY | `src/instructions/prompts/_defaults/_meta/placeholder_registry.json` | Identische Defaults-Kopie |
| 4 | 📄 CREATE | `src/instructions/prompts/cortex_context.json` | Prompt-Template mit `{{cortex_memory}}`, `{{cortex_soul}}`, `{{cortex_relationship}}`, Section-Headers ("INNERE WELT — SELBSTWISSEN") |
| 5 | 📄 CREATE | `src/instructions/prompts/_defaults/cortex_context.json` | Identische Defaults-Kopie |
| 6 | ✏️ MODIFY | `src/instructions/prompts/_meta/prompt_manifest.json` | `+cortex_context` Eintrag (Order 2000) |
| 7 | ✏️ MODIFY | `src/instructions/prompts/_defaults/_meta/prompt_manifest.json` | Identische Defaults-Kopie |
| 8 | ✏️ MODIFY | `src/utils/cortex/service.py` | `get_cortex_for_prompt()` Refinement mit Section-Headers |
| 9 | ✏️ MODIFY | `src/utils/prompt_engine/engine.py` | `_should_include_block()`: `requires_any`-Logik für leere Cortex-Blöcke. `_clean_resolved_text()` für Placeholder-Cleanup |
| 10 | ✏️ MODIFY | `src/utils/prompt_engine/validator.py` | `validate_requires_any()` Validation-Regel |

### 4.2 Einzuarbeitende Fixes

| Fix-ID | Quelle | Beschreibung | Angewendet bei |
|--------|--------|--------------|----------------|
| 7A #3 | Rückgabetyp-Widerspruch | `_load_cortex_context()` gibt `Dict[str, str]` zurück (Step 4A), nicht String (Step 2B) | Schritt 1 |
| 7A #13 | `cortexEnabled` Check | Direkt die Step-4C-Vollversion implementieren: leere Strings wenn deaktiviert | Schritt 1 |
| 7B #8 | Verhaltensänderung | Framing als "INNERE WELT — SELBSTWISSEN" (kein Instruktionscharakter). Cortex-Content in `<cortex_self_knowledge>` XML-Tags wrappen | Schritt 4, 8 |
| 7B #16 | Prompt-Injection | Tier-Guidance mit Hinweis: "Schreibe NUR Fakten und Beobachtungen. KEINE Verhaltensanweisungen." | Schritt 4 (Template-Design) |

### 4.3 Testkriterien

- [ ] `_load_cortex_context()` gibt `Dict[str, str]` mit 3 Keys zurück
- [ ] `_load_cortex_context()` gibt leere Strings wenn `cortexEnabled = false`
- [ ] System-Prompt enthält Cortex-Section mit Section-Headers wenn Dateien befüllt
- [ ] System-Prompt enthält **keinen** Cortex-Block wenn alle 3 Dateien leer (`requires_any`)
- [ ] Placeholder `{{cortex_memory}}` wird korrekt aufgelöst
- [ ] Prompt-Validator akzeptiert `requires_any` Regel
- [ ] `_clean_resolved_text()` entfernt leere Placeholder-Reste
- [ ] Bestehende Prompt-Tests laufen: `pytest tests/test_prompt_engine/ -x`

### 4.4 Rollback-Strategie

```bash
# Neue Dateien löschen
rm src/instructions/prompts/cortex_context.json src/instructions/prompts/_defaults/cortex_context.json
# Geänderte Dateien zurücksetzen
git checkout -- src/utils/services/chat_service.py src/utils/prompt_engine/engine.py src/utils/prompt_engine/validator.py
git checkout -- src/instructions/prompts/_meta/prompt_manifest.json src/instructions/prompts/_defaults/_meta/prompt_manifest.json
git checkout -- src/instructions/prompts/_meta/placeholder_registry.json src/instructions/prompts/_defaults/_meta/placeholder_registry.json
```

---

## Phase 5: Frontend — CortexOverlay + API-Service

> **Ziel:** CortexOverlay mit Markdown-Editor + Tier-Konfiguration, cortexApi Service-Layer.
>
> ⏱️ **Geschätzter Aufwand: 5–7 Stunden**

### 5.1 Dateien (in Reihenfolge)

| # | Aktion | Datei | Beschreibung |
|---|--------|-------|--------------|
| 1 | 🔧📄 **FIX (7A #8, #9) + CREATE** | `frontend/src/services/cortexApi.js` | API-Funktionen. Endpunkte aus Step 5B (maßgeblich, nicht Step 5A). `filename` mit `.md` Extension |
| 2 | 📄 CREATE | `frontend/src/features/overlays/CortexOverlay.jsx` | Overlay mit Tabs (Memory, Soul, Relationship), Markdown-Editor, Tier-Sliders |
| 3 | 🔧 **FIX (7A #7)** | `frontend/src/features/overlays/CortexOverlay.jsx` | Tier-Schwellwerte über `cortexApi.getCortexSettings()` / `saveCortexSettings()` laden/speichern (nicht `useSettings()`). Nur `cortexEnabled` über `useSettings()` |
| 4 | 🔧 **FIX (7A #9)** | `frontend/src/features/overlays/CortexOverlay.jsx` | `fileType` intern ohne `.md`, beim API-Call `fileType + '.md'` anhängen |
| 5 | ✏️ MODIFY | `frontend/src/features/overlays/Overlays.module.css` | Neue Cortex-CSS-Klassen |
| 6 | ✏️ MODIFY | `frontend/src/features/overlays/index.js` | `CortexOverlay` Export hinzufügen |
| 7 | 📄 CREATE | `frontend/src/features/chat/components/CortexUpdateIndicator/CortexUpdateIndicator.jsx` | Visueller Indikator für laufende Updates |
| 8 | 📄 CREATE | `frontend/src/features/chat/components/CortexUpdateIndicator/CortexUpdateIndicator.module.css` | Styling für Indikator |

### 5.2 Einzuarbeitende Fixes

| Fix-ID | Quelle | Beschreibung | Angewendet bei |
|--------|--------|--------------|----------------|
| 7A #7 | Tier-Schwellwerte Format | CortexOverlay nutzt `cortexApi.getCortexSettings()` / `saveCortexSettings()` für Tiers. `useSettings()` nur für `cortexEnabled` | Schritt 3 |
| 7A #8 | API-Endpunkt-Varianten | Step 5B `cortexApi.js` Endpunkte sind maßgeblich. Step 5A Inline-Definitionen ignorieren | Schritt 1 |
| 7A #9 | `fileType` vs. `filename` | CortexOverlay mappt intern `fileType → filename` (`'memory' → 'memory.md'`) | Schritt 4 |
| 7A #6 | `cortexEnabled` Ort | Nur über `useSettings()` → `user_settings.json`. Nicht in `cortex_settings.json` duplizieren | Schritt 3 |

### 5.3 Testkriterien

- [ ] CortexOverlay öffnet und zeigt 3 Tabs (Memory, Soul, Relationship)
- [ ] Markdown-Editor lädt Datei-Content via API
- [ ] Änderungen speichern über `PUT /api/cortex/file/<filename>.md`
- [ ] Reset-Button setzt auf Default-Template zurück
- [ ] Tier-Slider-Werte laden aus `GET /api/cortex/settings`
- [ ] Tier-Slider speichern über `PUT /api/cortex/settings`
- [ ] `cortexEnabled` Toggle nutzt `useSettings().setMany()`
- [ ] CortexUpdateIndicator rendert nicht ohne Event
- [ ] Frontend baut ohne Fehler: `cd frontend && npm run build`

### 5.4 Rollback-Strategie

```bash
# Neue Dateien löschen
rm frontend/src/services/cortexApi.js
rm frontend/src/features/overlays/CortexOverlay.jsx
rm -rf frontend/src/features/chat/components/CortexUpdateIndicator/
# Geänderte Dateien zurücksetzen
git checkout -- frontend/src/features/overlays/Overlays.module.css frontend/src/features/overlays/index.js
```

---

## Phase 6: Chat-Flow-Integration + Tier-System

> **Ziel:** Tier-Check in den Chat-Flow einbauen, SSE-Events erweitern, CortexUpdateIndicator verdrahten.
>
> ⏱️ **Geschätzter Aufwand: 5–7 Stunden**

### 6.1 Dateien (in Reihenfolge)

| # | Aktion | Datei | Beschreibung |
|---|--------|-------|--------------|
| 1 | ✏️ MODIFY | `src/routes/chat.py` | Tier-Check **VOR** Done-Yield in `generate()`. `cortex_update` Objekt im Done-Event. Tier-Check auch in `api_regenerate()` |
| 2 | ✏️ MODIFY | `src/utils/services/chat_service.py` | `runtime_vars` mit Cortex-Daten befüllen. Memory-Reste endgültig entfernen. `_build_chat_messages()` ohne `memory_context` Parameter |
| 3 | 🔧✏️ **FIX (7A #12) + MODIFY** | `frontend/src/features/chat/hooks/useMessages.js` | SSE-Done-Handler: `if (data.cortex_update)` (Objekt-Existenz), nicht `data.cortex_update?.triggered`. CustomEvent dispatchen mit `tier` + `status` |
| 4 | ✏️ MODIFY | `frontend/src/features/chat/ChatPage.jsx` | Import `CortexOverlay` + `CortexUpdateIndicator`. `onOpenCortex` Handler. Render-Integration |
| 5 | ✏️ MODIFY | `frontend/src/features/chat/components/Header/Header.jsx` | `onOpenCortex` Prop (statt `onOpenMemory`). Cortex-Button im Header |
| 6 | ✏️ MODIFY | `frontend/src/features/chat/components/Header/Header.module.css` | `.cortex*` CSS-Klassen |

### 6.2 Einzuarbeitende Fixes

| Fix-ID | Quelle | Beschreibung | Angewendet bei |
|--------|--------|--------------|----------------|
| 7A #4 | Tier-Check Position | **VOR** Done-Yield, Ergebnis im Done-Event (~5ms synchron) | Schritt 1 |
| 7A #12 | SSE Property Mismatch | `data.cortex_update` (Existenz prüfen), nicht `data.cortex_update?.triggered` | Schritt 3 |
| 7A #14 | Regenerate Tier-Check | Tier-Check auch in `api_regenerate()` (Step 6A ist maßgeblich) | Schritt 1 |
| 7B #9 | SSE-Done-Event Property | Frontend-Check: `if (data.cortex_update)` mit `detail: { tier, status }` | Schritt 3 |

### 6.3 Testkriterien

- [ ] Chat-Request löst Tier-Check aus
- [ ] Bei 50% context_limit → Tier 1 gefeuert → Background-Thread gestartet
- [ ] Done-Event enthält `cortex_update: { tier: 1, status: 'started' }` wenn Tier gefeuert
- [ ] Done-Event enthält **kein** `cortex_update` wenn kein Tier gefeuert
- [ ] CortexUpdateIndicator erscheint bei `cortex-update` CustomEvent
- [ ] Cortex-Button im Header öffnet CortexOverlay
- [ ] Regenerate löst ebenfalls Tier-Check aus
- [ ] Chat-Funktion bleibt stabil bei deaktiviertem Cortex (`cortexEnabled: false`)
- [ ] Vollständiger Chat-Zyklus: Nachricht senden → Antwort empfangen → Cortex-Dateien aktualisiert

### 6.4 Rollback-Strategie

```bash
git checkout -- src/routes/chat.py src/utils/services/chat_service.py
git checkout -- frontend/src/features/chat/hooks/useMessages.js
git checkout -- frontend/src/features/chat/ChatPage.jsx
git checkout -- frontend/src/features/chat/components/Header/Header.jsx
git checkout -- frontend/src/features/chat/components/Header/Header.module.css
```

Phasen 2–5 bleiben funktional — Phase 6 verdrahtet nur bestehende Komponenten.

---

## Phase 7: Settings-Migration + Startup-Hooks

> **Ziel:** `memoriesEnabled` → `cortexEnabled` Migration, Startup-Initialisierung, Defaults-Aktualisierung.
>
> ⏱️ **Geschätzter Aufwand: 2–3 Stunden**

### 7.1 Dateien (in Reihenfolge)

| # | Aktion | Datei | Beschreibung |
|---|--------|-------|--------------|
| 1 | 📄 CREATE | `src/utils/settings_migration.py` | `migrate_settings()` — idempotent, forward-compatible: `memoriesEnabled` → `cortexEnabled` in `user_settings.json` |
| 2 | ✏️ MODIFY | `src/settings/defaults.json` | `memoriesEnabled` entfernen, `cortexEnabled: true` hinzufügen |
| 3 | ✏️ MODIFY | `src/splash_screen/utils/startup.py` | `ensure_cortex_dirs()` + `migrate_settings()` Aufrufe im Startup-Flow |
| 4 | ✏️ MODIFY | `src/app.py` | `ensure_cortex_dirs()` + `migrate_settings()` in Fallback-Pfaden (wenn kein Splash-Screen) |

### 7.2 Einzuarbeitende Fixes

| Fix-ID | Quelle | Beschreibung | Angewendet bei |
|--------|--------|--------------|----------------|
| 7A #6 | `cortexEnabled` Ort | `cortexEnabled` **nur** in `user_settings.json`. `cortex_settings.json` enthält nur Tier-Parameter | Bestätigung: Schritt 1–2 |

### 7.3 Testkriterien

- [ ] Frischer Start (keine `user_settings.json`): `cortexEnabled` wird aus `defaults.json` übernommen
- [ ] Bestehende `user_settings.json` mit `memoriesEnabled: true`: Migration setzt `cortexEnabled: true`, entfernt `memoriesEnabled`
- [ ] Bestehende `user_settings.json` mit `memoriesEnabled: false`: Migration setzt `cortexEnabled: false`, entfernt `memoriesEnabled`
- [ ] Bestehende `user_settings.json` ohne `memoriesEnabled`: `cortexEnabled: true` Default wird gesetzt
- [ ] Migration ist idempotent: Zweiter Aufruf ändert nichts
- [ ] `ensure_cortex_dirs()` läuft beim Startup und erstellt fehlende Verzeichnisse
- [ ] Server startet korrekt über `src/app.py` (ohne Splash-Screen)
- [ ] Server startet korrekt über Splash-Screen (normaler Startup-Flow)

### 7.4 Rollback-Strategie

```bash
rm src/utils/settings_migration.py
git checkout -- src/settings/defaults.json src/splash_screen/utils/startup.py src/app.py
# User-Settings manuell korrigieren: cortexEnabled → memoriesEnabled
```

---

## Phase 8: Testing + Validierung

> **Ziel:** Vollständige Testabdeckung, End-to-End-Validierung, Dokumentation.
>
> ⏱️ **Geschätzter Aufwand: 4–6 Stunden**

### 8.1 Dateien (in Reihenfolge)

| # | Aktion | Datei | Beschreibung |
|---|--------|-------|--------------|
| 1 | 📄 CREATE | `tests/test_services/test_cortex_service.py` | Unit-Tests: read/write/cache/atomic/size-limit/ensure_dirs |
| 2 | 📄 CREATE | `tests/test_services/test_cortex_tier.py` | Unit-Tests: Schwellwert-Berechnung, Kaskade, Minimum, Rebuild |
| 3 | 📄 CREATE | `tests/test_services/test_cortex_update_service.py` | Integration-Tests: Tool-Loop, Write-Guard, Thread-Safety |
| 4 | 📄 CREATE | `tests/test_prompt_engine/test_cortex_placeholders.py` | Tests: Placeholder-Auflösung, `requires_any`, leere Dateien |
| 5 | 📄 CREATE | `tests/test_integration/test_cortex_chat_flow.py` | End-to-End: Chat → Tier-Check → Update → Dateien aktualisiert |
| 6 | ✏️ MODIFY | `tests/conftest.py` | Cortex-Fixtures: Temp-Cortex-Verzeichnis, Mock-CortexService |
| 7 | ✏️ MODIFY | `tests/test_api_client.py` | `tool_request()` Tests hinzufügen |

### 8.2 Test-Szenarien

| # | Szenario | Erwartung |
|---|----------|-----------|
| T1 | Chat mit `cortexEnabled: false` | Kein Cortex-Content im System-Prompt, kein Tier-Check |
| T2 | Chat mit `cortexEnabled: true`, 0 Nachrichten | Cortex-Dateien leer → `requires_any` → kein Cortex-Block im Prompt |
| T3 | Chat bei 50% contextLimit | Tier 1 gefeuert, Background-Update startet |
| T4 | Chat bei 75% contextLimit (Tier 1 bereits gefeuert) | Tier 2 gefeuert |
| T5 | Alle 3 Tiers gleichzeitig überschritten | Nur Tier 3 gefeuert, T1+T2 als gefeuert markiert |
| T6 | Server-Neustart → erster Chat-Request | Lazy-Rebuild rekonstruiert Tier-State |
| T7 | contextLimit von 100 auf 20 reduziert | Höchster passender Tier wird gefeuert |
| T8 | Persona-Löschen während Update | Thread-Exception geloggt, kein Crash |
| T9 | Cortex-Datei > 8000 Zeichen | Truncation + Warning-Log |
| T10 | Paralleler Read/Write auf Cortex-Datei | Stets vollständige Datei gelesen (atomarer Write) |
| T11 | CortexOverlay öffnen → Dateien bearbeiten → speichern | Korrekte API-Calls, Dateien auf Disk aktualisiert |
| T12 | Tier-Slider ändern → nächster Chat nutzt neue Schwellwerte | `cortex_settings.json` aktualisiert, Tier-Checker liest neue Werte |

### 8.3 Testkriterien

- [ ] `pytest -x` → alle Tests grün
- [ ] `pytest --cov=src/utils/cortex` → >80% Coverage
- [ ] `cd frontend && npm run build` → kein Fehler
- [ ] Manueller E2E-Test: Vollständige Konversation mit 3 Tier-Auslösungen
- [ ] Manueller E2E-Test: Persona-Wechsel, Cortex-Dateien korrekt isoliert
- [ ] Manueller E2E-Test: Server-Neustart, Chat fortsetzen, Tiers korrekt rekonstruiert

### 8.4 Rollback-Strategie

Phase 8 ist rein additiv (Tests + Validierung). Kein Rollback nötig.

---

## Master-Checkliste

### Phase 1 — Altes Memory-System entfernen
- [ ] `upsert_db_info` Query nach `chat.sql` verschoben (7A #10)
- [ ] Alle Memory-Backend-Dateien gelöscht (6 Dateien)
- [ ] Alle Memory-SQL gelöscht (1 Datei)
- [ ] Alle Memory-Prompt-Templates gelöscht (9 Dateien)
- [ ] Memory-Tests gelöscht (1 Datei)
- [ ] `provider.py` bereinigt (Memory-Service entfernt)
- [ ] `routes/__init__.py` bereinigt (Memory-Blueprint entfernt)
- [ ] `chat_service.py` bereinigt (Memory-Logik entfernt, `include_memories` Parameter geprüft/entfernt)
- [ ] `engine.py` bereinigt (Memory-Referenzen entfernt)
- [ ] Placeholder-Registry bereinigt (`memory_entries` entfernt) (7A #16)
- [ ] Prompt-Manifest bereinigt (`memory_context` entfernt)
- [ ] Legacy-Frontend-Dateien gelöscht (2 Dateien)
- [ ] React-Frontend-Dateien gelöscht (2 Dateien)
- [ ] Frontend-Overlay-Index bereinigt
- [ ] ChatPage, Header, SessionContext, DebugOverlay bereinigt
- [ ] **VALIDIERUNG:** Server startet, Chat funktioniert, `grep` findet keine Memory-Reste

### Phase 2 — Cortex-Datei-Infrastruktur
- [ ] `src/utils/cortex/` Package erstellt mit `__init__.py`
- [ ] `CortexService` in `cortex/service.py` (7A #5)
- [ ] Atomarer Write implementiert (`os.replace`) (7B #1)
- [ ] Dateigröße-Limit implementiert (8000 Zeichen) (7B #2)
- [ ] Read-Cache implementiert mit Lock (7B #7)
- [ ] Write-Guard: kein auto-makedirs (7B #6)
- [ ] `ensure_cortex_dirs()` Modul-Funktion (7A #11)
- [ ] Default-Templates erstellt (3 Dateien + `.gitkeep`)
- [ ] `src/routes/cortex.py` mit allen Endpoints
- [ ] `provider.py` aktualisiert (cortex_service)
- [ ] `config.py` aktualisiert (Persona-Lifecycle)
- [ ] `.gitignore` aktualisiert
- [ ] `cortex/settings.py` + `cortex_settings.json`
- [ ] **VALIDIERUNG:** API-Endpoints funktional, CRUD auf Cortex-Dateien

### Phase 3 — Tool-Use + Cortex-Update-Service
- [ ] `ApiClient.tool_request()` implementiert
- [ ] `ToolExecutor` Typ + `MAX_TOOL_ROUNDS`
- [ ] `tier_tracker.py` — In-Memory State
- [ ] `tier_checker.py` — Schwellwert-Berechnung
- [ ] Tier-Kaskade: Höchsten Tier feuern (7B #3)
- [ ] Minimum-Schwellwert: Tier 1 ≥ 8 (7B #5)
- [ ] Lazy-Rebuild bei unbekannter Session (7B #4, 7B #13)
- [ ] `CortexUpdateService` — einzige Update-Implementierung (7A #1, #2)
- [ ] Thread-Guard via `_active_updates` Dict (7B #15)
- [ ] `__init__.py` Exports vollständig
- [ ] **VALIDIERUNG:** Tier-Berechnung, Thread-Safety, Mock-API-Test

### Phase 4 — Prompt-Templates + Placeholders
- [ ] `_load_cortex_context()` gibt `Dict[str, str]` zurück (7A #3)
- [ ] `cortexEnabled`-Check direkt integriert (7A #13)
- [ ] Placeholder-Registry: 3 Cortex-Einträge
- [ ] `cortex_context.json` Template mit XML-Tags (7B #8)
- [ ] Prompt-Manifest: `cortex_context` Eintrag (Order 2000)
- [ ] `get_cortex_for_prompt()` mit Section-Headers
- [ ] `requires_any` Logik in Engine
- [ ] `_clean_resolved_text()` für Placeholder-Cleanup
- [ ] `validate_requires_any()` in Validator
- [ ] **VALIDIERUNG:** Prompt-Tests grün, Cortex im System-Prompt sichtbar

### Phase 5 — Frontend CortexOverlay + API
- [ ] `cortexApi.js` mit korrekten Endpoints (7A #8)
- [ ] `CortexOverlay.jsx` mit Tabs + Editor
- [ ] Tier-Settings über `cortexApi` (nicht `useSettings`) (7A #7)
- [ ] `fileType` → `filename` Mapping mit `.md` (7A #9)
- [ ] `cortexEnabled` über `useSettings()` (7A #6)
- [ ] CSS-Klassen für Cortex-Overlay
- [ ] Overlay-Index aktualisiert
- [ ] `CortexUpdateIndicator` Komponente + CSS
- [ ] **VALIDIERUNG:** Frontend baut, Overlay funktional

### Phase 6 — Chat-Flow-Integration
- [ ] Tier-Check VOR Done-Yield (7A #4)
- [ ] `cortex_update` im Done-Event
- [ ] Tier-Check in `api_regenerate()` (7A #14)
- [ ] `runtime_vars` mit Cortex-Daten
- [ ] SSE-Handler: `data.cortex_update` Existenzprüfung (7A #12)
- [ ] CortexUpdateIndicator verdrahtet
- [ ] ChatPage + Header Integration
- [ ] **VALIDIERUNG:** E2E Chat-Zyklus mit Cortex-Update

### Phase 7 — Settings-Migration + Startup
- [ ] `settings_migration.py` idempotent
- [ ] `defaults.json` aktualisiert
- [ ] Startup-Hooks in `startup.py`
- [ ] Fallback-Hooks in `app.py`
- [ ] **VALIDIERUNG:** Migration korrekt, Startup stabil

### Phase 8 — Testing + Validierung
- [ ] Unit-Tests: CortexService
- [ ] Unit-Tests: Tier-System
- [ ] Unit-Tests: CortexUpdateService
- [ ] Unit-Tests: Cortex-Placeholders
- [ ] Integration-Tests: Chat-Flow
- [ ] Fixtures in `conftest.py`
- [ ] `tool_request()` Tests
- [ ] Alle Tests grün, >80% Coverage
- [ ] Manueller E2E-Test vollständig
- [ ] **VALIDIERUNG:** Alles grün, Deployment-ready

---

## Risikominderung — Alle Fixes aus 7A + 7B

### Kritische Fixes (Blockierend — müssen in der jeweiligen Phase gelöst sein)

| ID | Quelle | Beschreibung | Phase | Status |
|----|--------|--------------|-------|--------|
| 7A #1 | KRITISCH | Duplizierte `execute_cortex_update()` — nur in `CortexUpdateService` | Phase 2 + 3 | ⬜ |
| 7A #2 | KRITISCH | Tool-Namen standardisieren auf `read_file`/`write_file` | Phase 3 | ⬜ |
| 7A #3 | KRITISCH | `_load_cortex_context()` → `Dict[str, str]` (nicht String) | Phase 4 | ⬜ |
| 7B #1 | KRITISCH | Race Condition → Atomarer Write (`tempfile` + `os.replace`) | Phase 2 | ⬜ |
| 7B #2 | KRITISCH | Keine Dateigröße-Beschränkung → `MAX_CORTEX_FILE_SIZE = 8000` | Phase 2 | ⬜ |

### Hohe Priorität (Sollten in der jeweiligen Phase gelöst werden)

| ID | Quelle | Beschreibung | Phase | Status |
|----|--------|--------------|-------|--------|
| 7B #3 | HOCH | Tier-Kaskade → Höchsten Tier feuern, niedrigere markieren | Phase 3 | ⬜ |
| 7B #4 | HOCH | Lazy Rebuild nach Restart (nicht Startup) | Phase 3 | ⬜ |
| 7B #5 | HOCH | Minimal-Konversation → `MINIMUM_TIER1_THRESHOLD = 8` | Phase 3 | ⬜ |
| 7B #6 | HOCH | Persona-Delete während Update → Write-Guard ohne auto-makedirs | Phase 2 | ⬜ |
| 7B #7 | HOCH | Kein Caching → In-Memory-Cache mit Write-Through | Phase 2 | ⬜ |
| 7B #8 | HOCH | Verhaltensänderung → Framing als Selbstwissen, XML-Tags | Phase 4 | ⬜ |

### Warnungen (Berücksichtigen bei Implementierung)

| ID | Quelle | Beschreibung | Phase | Status |
|----|--------|--------------|-------|--------|
| 7A #4 | WARNUNG | Tier-Check Position → VOR Done-Yield (Step 6A maßgeblich) | Phase 6 | ⬜ |
| 7A #5 | WARNUNG | CortexService Pfad → `cortex/service.py` (Package) | Phase 2 | ⬜ |
| 7A #6 | WARNUNG | `cortexEnabled` → nur in `user_settings.json` | Phase 5 + 7 | ⬜ |
| 7A #7 | WARNUNG | Tier-Schwellwerte → CortexOverlay nutzt Cortex-API | Phase 5 | ⬜ |
| 7A #8 | WARNUNG | API-Endpunkte → Step 5B cortexApi.js maßgeblich | Phase 5 | ⬜ |
| 7A #9 | WARNUNG | `fileType` → `filename` → `.md` anhängen | Phase 5 | ⬜ |
| 7A #10 | WARNUNG | `upsert_db_info` → vor Löschung relocaten | Phase 1 | ⬜ |
| 7A #11 | WARNUNG | `ensure_cortex_dirs()` → Modul-Level-Funktion | Phase 2 | ⬜ |
| 7A #12 | WARNUNG | SSE `cortex_update.triggered` → Objekt-Existenz prüfen | Phase 6 | ⬜ |
| 7A #13 | HINWEIS | `cortexEnabled` Check → Step-4C-Version direkt | Phase 4 | ⬜ |
| 7A #14 | HINWEIS | Regenerate Tier-Check → Step 6A korrekt | Phase 6 | ⬜ |
| 7A #15 | HINWEIS | Verzeichnisstruktur → `default/` + `custom/` | Phase 2 | ⬜ |
| 7A #16 | HINWEIS | `memory_entries` Placeholder koordiniert entfernen | Phase 1 | ⬜ |

### Mittlere Priorität (Aus 7B — dokumentiert, in jeweiliger Phase beachten)

| ID | Quelle | Beschreibung | Phase | Status |
|----|--------|--------------|-------|--------|
| 7B #9 | MITTEL | SSE-Done-Event Property Mismatch | Phase 6 | ⬜ |
| 7B #10 | MITTEL | Plan-Inkonsistenz Tier-Check Timeline (Doku-Fix) | Phase 3 | ⬜ |
| 7B #11 | MITTEL | `include_memories` Rückwärtskompatibilität prüfen | Phase 1 | ⬜ |
| 7B #12 | MITTEL | Mehrere User über Netzwerk (Dokumentations-Limitation) | Phase 8 | ⬜ |
| 7B #13 | MITTEL | Session-Wechsel Rebuild | Phase 3 | ⬜ |
| 7B #14 | MITTEL | API-Kosten Transparenz (Logging + UI-Hinweis) | Phase 5 | ⬜ |
| 7B #15 | MITTEL | `threading.enumerate()` → Explizites Tracking | Phase 3 | ⬜ |
| 7B #16 | MITTEL | Prompt-Injection Hardening | Phase 4 | ⬜ |

---

## Implementierungs-Zeitplan

### Geschätzter Gesamtaufwand: 33–46 Stunden

| Phase | Aufwand | Kumulativ | Abhängigkeit |
|-------|---------|-----------|--------------|
| Phase 1: Memory entfernen | 3–4h | 3–4h | — |
| Phase 2: Cortex-Infrastruktur | 4–6h | 7–10h | Phase 1 ✅ |
| Phase 3: Tool-Use + Update-Service | 6–8h | 13–18h | Phase 2 ✅ |
| Phase 4: Prompts + Placeholders | 4–5h | 17–23h | Phase 2 ✅ (parallel zu Phase 3 möglich) |
| Phase 5: Frontend CortexOverlay | 5–7h | 22–30h | Phase 2 ✅ (parallel zu Phase 3+4 möglich) |
| Phase 6: Chat-Flow-Integration | 5–7h | 27–37h | Phasen 3 + 4 + 5 ✅ |
| Phase 7: Settings-Migration | 2–3h | 29–40h | Phase 2 ✅ (parallel zu Phase 3–6 möglich) |
| Phase 8: Testing | 4–6h | 33–46h | Alle Phasen ✅ |

### Parallelisierungsmöglichkeiten

```
Phase 1  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━▶ (seriell, muss zuerst)
                                        │
Phase 2  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━▶
                                               │
                          ┌────────────────────┼─────────────────────┐
                          │                    │                     │
Phase 3  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━▶              │
Phase 4  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━▶ (parallel zu 3)           │
Phase 5  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━▶ (parallel zu 3+4)   │
Phase 7  ━━━━━━━━━━━━━━━━━▶ (parallel zu 3–6)                      │
                          │                    │                     │
                          └────────────────────┼─────────────────────┘
                                               │
Phase 6  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━▶ (braucht 3+4+5)
                                                        │
Phase 8  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━▶ (braucht alles)
```

**Optimaler Pfad (1 Entwickler):** Phase 1 → 2 → 3+4 parallel → 5+7 parallel → 6 → 8

**Geschätzter optimaler Zeitrahmen:** ~28–38 Stunden (durch Parallelisierung)

---

## Risiko-Hotspots

Die folgenden Dateien werden in **3+ Phasen** geändert und erfordern besondere Aufmerksamkeit:

| Datei | Geändert in Phasen | Risiko |
|-------|---------------------|--------|
| `src/utils/services/chat_service.py` | 1, 4, 6 | **HOCH** — Kernstück des Chat-Flows. Änderungen müssen aufeinander aufbauen. |
| `src/utils/provider.py` | 1, 2, (6) | **MITTEL** — Service-Registry. Jede Phase add/remove Einträge. |
| `src/routes/__init__.py` | 1, 2, (6) | **MITTEL** — Blueprint-Registry. Sequenzielle Änderung. |
| `frontend/src/features/chat/ChatPage.jsx` | 1, 5, 6 | **MITTEL** — Erster Entfernung (Phase 1), dann Neuverkabelung (Phase 5+6). |

### Empfehlung

- Phasen 1–7 auf einem **einzigen Feature-Branch** entwickeln
- Zwischen den Phasen: `git commit` mit Phase-Bezeichnung als Tag
- Keinen Feature-Branch für Parallelentwicklung der Hotspot-Dateien splitten
- Jede Phase mit `pytest -x` und Frontend-Build validieren bevor die nächste beginnt

---

## Abschluss-Kriterien (Definition of Done)

Die Cortex-Migration gilt als **abgeschlossen** wenn:

1. **Alle Checkboxen** in der Master-Checkliste sind ✅
2. **Alle 5 kritischen Fixes** (7A #1–3, 7B #1–2) sind implementiert
3. **Alle 6 hohen Fixes** (7B #3–8) sind implementiert
4. **`pytest -x`** läuft ohne Fehler
5. **`npm run build`** (Frontend) läuft ohne Fehler
6. **Manueller E2E-Test** mit 3 Tier-Auslösungen erfolgreich
7. **Kein `grep`-Treffer** für alte Memory-Artefakte in `src/` und `frontend/src/`
8. **Server-Neustart** → Chat mit bestehender Session → Cortex-State korrekt rekonstruiert
9. **Settings-Migration** → Bestandsdaten korrekt migriert, keine Datenverluste
