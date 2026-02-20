# Cortex System — Gesamtplan

## Projektziel

Ersetzung des alten SQL-basierten Memory-Systems durch ein dateibasiertes **Cortex-System**. Die KI nutzt Anthropics `tool_use` Feature um Markdown-Dateien zu pflegen, die die Persona-Erinnerungen, Seelen-Entwicklung und Beziehungsdynamik festhalten.

---

## Architektur-Übersicht

```
┌──────────────────────────────────────────────────────────┐
│                    CORTEX SYSTEM                          │
│                                                          │
│  Dateistruktur:                                          │
│  src/instructions/personas/cortex/                       │
│  ├── default/                                            │
│  │   ├── memory.md        (Erinnerungen)                 │
│  │   ├── soul.md          (Persona-Entwicklung)          │
│  │   └── relationship.md  (Beziehungsdynamik)            │
│  └── custom/                                             │
│      └── {persona_id}/                                   │
│          ├── memory.md                                   │
│          ├── soul.md                                     │
│          └── relationship.md                             │
│                                                          │
│  Aktivierungs-Schwellen (% von contextLimit):            │
│  ├── Stufe 1: 50%  → Cortex-Update auslösen             │
│  ├── Stufe 2: 75%  → Cortex-Update auslösen             │
│  └── Stufe 3: 95%  → Cortex-Update auslösen             │
│                                                          │
│  Tool-Use API-Call:                                      │
│  ├── Prompt: Persona schreibt in Ich-Perspektive         │
│  ├── Referenz: Gesprächsverlauf + aktuelle Files         │
│  ├── Tools: read_file, write_file (cortex/*.md)          │
│  └── Ergebnis: Aktualisierte .md Dateien                 │
│                                                          │
│  System-Prompt Integration:                              │
│  ├── Computed Placeholders:                              │
│  │   {{cortex_memory}}, {{cortex_soul}},                 │
│  │   {{cortex_relationship}}                             │
│  ├── Prompt-Template: cortex_context.json                │
│  └── Position: Letzter Block im System-Prompt            │
│                                                          │
│  UI:                                                     │
│  ├── CortexOverlay.jsx (Settings anzeigen/bearbeiten)    │
│  ├── Aktivierungs-Schwellen konfigurierbar               │
│  └── Markdown-Editor für alle 3 Dateien                  │
└──────────────────────────────────────────────────────────┘
```

---

## Schritte

| # | Schritt | Beschreibung | Status |
|---|---------|-------------|--------|
| 1 | [Altes Memory-System entfernen](step_01_remove_old_memory/) | SQL-Tabellen, Routes, Services, Frontend-Komponenten komplett entfernen | ⬜ |
| 2 | [Cortex Dateistruktur](step_02_cortex_file_structure/) | Verzeichnisstruktur, CortexService, API-Endpunkte für Dateizugriff | ⬜ |
| 3 | [File Tool & Aktivierungsstufen](step_03_file_tool_activation_tiers/) | tool_use im API-Client, Schwellen-Erkennung, Trigger-Logik | ⬜ |
| 4 | [Cortex Prompts & Placeholders](step_04_cortex_prompts_placeholders/) | Computed Placeholders, Prompt-Templates, System-Prompt Integration | ⬜ |
| 5 | [Cortex Settings UI](step_05_cortex_settings_ui/) | CortexOverlay.jsx, Markdown-Editor, Schwellen-Konfiguration | ⬜ |
| 6 | [API Integration](step_06_api_integration/) | Chat-Flow Modifikation, Tier-Erkennung, Tool-Call Ausführung | ⬜ |
| 7 | [Final Review](step_07_final_review/) | Logikprüfung, Abhängigkeiten, Vollständigkeitskontrolle | ⬜ |

---

## Abhängigkeiten

```
Schritt 1 ──► Schritt 2 ──► Schritt 3
                  │              │
                  ▼              ▼
              Schritt 4 ◄── Schritt 6
                  │
                  ▼
              Schritt 5
                  │
                  ▼
              Schritt 7
```

- **Schritt 1** muss zuerst abgeschlossen sein (Clean Slate)
- **Schritt 2 + 3** können teilweise parallel bearbeitet werden
- **Schritt 4** braucht Schritt 2 (Dateien existieren) + Schritt 3 (Tool-Definitions)
- **Schritt 5** braucht Schritt 2 (API-Endpunkte) + Schritt 4 (Settings-Keys)
- **Schritt 6** integriert alles
- **Schritt 7** ist die Abschluss-Prüfung
