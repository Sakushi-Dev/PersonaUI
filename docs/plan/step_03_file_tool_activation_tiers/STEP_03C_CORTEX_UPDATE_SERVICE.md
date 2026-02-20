# Schritt 3C: Cortex Update Service

## Übersicht

Der `CortexUpdateService` ist die Kernkomponente, die ausgeführt wird, wenn ein Aktivierungstier (Schritt 3B) eine Schwelle erreicht. Er orchestriert den gesamten Cortex-Update-Zyklus:

1. Gesprächsverlauf der Session laden
2. Aktuelle Cortex-Dateien lesen (`memory.md`, `soul.md`, `relationship.md`)
3. System-Prompt bauen, der die KI glauben lässt, sie **IST** die Persona
4. `tool_use` API-Request senden (Schritt 3A: `ApiClient.tool_request()`)
5. Tool-Call-Loop ausführen (KI liest/schreibt Cortex-Dateien über Tools)
6. Ergebnisse loggen und zurückgeben

Der Service läuft **ausschließlich in einem Background-Thread** und blockiert niemals den Chat-Stream.

---

## 1. Einordnung im Gesamtsystem

```
┌────────────────────────────────────────────────────────────────────┐
│                        Chat-Nachricht                              │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  /chat_stream → ChatService → Stream → save_message → done        │
│                                                                    │
│  ═══ Stream abgeschlossen ════════════════════════════════════════ │
│                                                                    │
│  tier_checker.check_and_trigger_cortex_update()  ← Schritt 3B     │
│       │                                                            │
│       ├─ Tier nicht erreicht → return None                         │
│       │                                                            │
│       └─ Tier erreicht → Background-Thread starten:                │
│           │                                                        │
│           ▼                                                        │
│  ┌─────────────────────────────────────────────┐                  │
│  │       CortexUpdateService (DIESER SCHRITT)   │                  │
│  │                                               │                  │
│  │  1. Conversation History laden                │                  │
│  │  2. Cortex-Dateien lesen                      │                  │
│  │  3. System-Prompt aufbauen                    │                  │
│  │  4. ApiClient.tool_request() aufrufen         │  ← Schritt 3A   │
│  │  5. Tool-Calls ausführen (read/write)         │                  │
│  │  6. Ergebnis loggen                           │                  │
│  └─────────────────────────────────────────────┘                  │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### Abhängigkeiten

| Komponente | Schritt | Benötigt für |
|------------|---------|-------------|
| `ApiClient.tool_request()` | 3A | Tool-Call-Loop mit API |
| `CortexService.read_file()` / `write_file()` | 2B | Cortex-Dateien lesen/schreiben |
| `tier_checker._start_background_cortex_update()` | 3B | Aufruf des Services im Thread |
| `get_conversation_context()` | Bestehend | Gesprächsverlauf laden |
| `load_character()` / `load_char_config()` | Bestehend | Persona-Name und Identity |
| `get_user_profile_data()` | Bestehend | User-Name für Beziehungsdatei |

---

## 2. Datei: `src/utils/cortex/update_service.py`

### 2.1 Vollständige Implementierung

```python
"""
Cortex Update Service — Führt Cortex-Updates via tool_use API-Call aus.

Wird von tier_checker._start_background_cortex_update() in einem
Background-Thread aufgerufen, wenn ein Aktivierungstier ausgelöst wurde.

Flow:
1. Gesprächsverlauf laden
2. Cortex-Dateien lesen
3. System-Prompt bauen (KI denkt, sie IST die Persona)
4. tool_use API-Request mit read_file/write_file Tools
5. Tool-Call-Loop (KI liest und schreibt Cortex-Dateien)
6. Ergebnis loggen
"""

import time
import threading
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from utils.logger import log
from utils.api_request import ApiClient, RequestConfig, ToolExecutor
from utils.database import get_conversation_context
from utils.config import load_character, load_char_config, get_active_persona_id
from routes.user_profile import get_user_profile_data


# ─── Konstanten ──────────────────────────────────────────────────────────────

# Maximale Tokens für den Cortex-Update API-Call
CORTEX_UPDATE_MAX_TOKENS = 8192

# Temperatur für Cortex-Updates (niedrig = konsistenter)
CORTEX_UPDATE_TEMPERATURE = 0.4

# Mindestabstand zwischen Updates für dieselbe Persona (Sekunden)
RATE_LIMIT_SECONDS = 30

# Lock + Timestamp-Tracking für Rate-Limiting
_rate_lock = threading.Lock()
_last_update_time: Dict[str, float] = {}
# Key: persona_id → Value: time.monotonic() des letzten Update-Starts


# ─── Tool-Definitionen ──────────────────────────────────────────────────────

CORTEX_TOOLS = [
    {
        "name": "read_file",
        "description": "Liest den aktuellen Inhalt einer deiner Cortex-Dateien. "
                       "Nutze dieses Tool, um den aktuellen Stand einer Datei zu sehen, "
                       "bevor du sie aktualisierst.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "enum": ["memory.md", "soul.md", "relationship.md"],
                    "description": "Name der Cortex-Datei die gelesen werden soll"
                }
            },
            "required": ["filename"]
        }
    },
    {
        "name": "write_file",
        "description": "Schreibt neuen Inhalt in eine deiner Cortex-Dateien. "
                       "Überschreibt den gesamten Inhalt der Datei. "
                       "Schreibe immer den VOLLSTÄNDIGEN neuen Inhalt — nicht nur die Änderungen.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "enum": ["memory.md", "soul.md", "relationship.md"],
                    "description": "Name der Cortex-Datei die geschrieben werden soll"
                },
                "content": {
                    "type": "string",
                    "description": "Der neue vollständige Inhalt der Datei (Markdown-Format). "
                                   "Schreibe aus deiner Ich-Perspektive."
                }
            },
            "required": ["filename", "content"]
        }
    }
]


# ─── Service-Klasse ─────────────────────────────────────────────────────────

class CortexUpdateService:
    """
    Führt Cortex-Updates als Background-Prozess aus.

    Wird von tier_checker aufgerufen. Orchestriert:
    - History laden → Prompt bauen → tool_use API-Call → Dateien aktualisieren
    """

    def __init__(self):
        """
        Initialisiert den Service.
        ApiClient und CortexService werden lazy über provider geholt,
        da der Service in einem Background-Thread läuft und die
        globalen Instanzen zu diesem Zeitpunkt bereits existieren.
        """
        pass

    def _get_api_client(self) -> ApiClient:
        """Holt den globalen ApiClient via provider."""
        from utils.provider import get_api_client
        return get_api_client()

    def _get_cortex_service(self):
        """Holt den globalen CortexService via provider."""
        from utils.provider import get_cortex_service
        return get_cortex_service()

    # ─── Rate-Limiting ───────────────────────────────────────────────

    def _check_rate_limit(self, persona_id: str) -> bool:
        """
        Prüft ob ein Update für diese Persona erlaubt ist.

        Returns:
            True wenn Update erlaubt, False wenn Rate-Limit greift
        """
        now = time.monotonic()
        with _rate_lock:
            last_time = _last_update_time.get(persona_id)
            if last_time is not None:
                elapsed = now - last_time
                if elapsed < RATE_LIMIT_SECONDS:
                    log.info(
                        "Cortex-Update Rate-Limit: Persona %s — "
                        "letztes Update vor %.1fs (Minimum: %ds)",
                        persona_id, elapsed, RATE_LIMIT_SECONDS
                    )
                    return False
            _last_update_time[persona_id] = now
        return True

    # ─── Haupt-Methode ──────────────────────────────────────────────

    def execute_update(
        self,
        persona_id: str,
        session_id: int,
        context_limit: int,
        triggered_tier: int
    ) -> Dict[str, Any]:
        """
        Führt ein vollständiges Cortex-Update aus.

        Wird in einem Background-Thread von tier_checker aufgerufen.

        Args:
            persona_id: Aktive Persona-ID
            session_id: Aktuelle Session-ID
            context_limit: Aktuelles Context-Limit
            triggered_tier: Welcher Tier das Update ausgelöst hat (1, 2 oder 3)

        Returns:
            {
                'success': bool,
                'tool_calls_count': int,
                'files_written': list[str],    # z.B. ['memory.md', 'soul.md']
                'files_read': list[str],        # z.B. ['memory.md', 'soul.md', 'relationship.md']
                'duration_seconds': float,
                'usage': {'input_tokens': int, 'output_tokens': int},
                'error': str | None
            }
        """
        start_time = time.monotonic()
        log.info(
            "═══ Cortex-Update gestartet ═══ Tier: %d | Persona: %s | Session: %s",
            triggered_tier, persona_id, session_id
        )

        # ── Rate-Limit prüfen ───────────────────────────────────────
        if not self._check_rate_limit(persona_id):
            return {
                'success': False,
                'tool_calls_count': 0,
                'files_written': [],
                'files_read': [],
                'duration_seconds': 0,
                'usage': None,
                'error': 'Rate-Limit: Zu kurz nach dem letzten Update'
            }

        try:
            # ── 1. API-Client prüfen ─────────────────────────────────
            api_client = self._get_api_client()
            if not api_client.is_ready:
                return self._error_result(
                    'API-Client nicht bereit (kein API-Key)',
                    start_time
                )

            cortex_service = self._get_cortex_service()

            # ── 2. Persona-Daten laden ───────────────────────────────
            character = load_character()
            persona_name = character.get('char_name', 'Assistant')

            user_profile = get_user_profile_data()
            user_name = user_profile.get('user_name', 'User') or 'User'

            # ── 3. Gesprächsverlauf laden ────────────────────────────
            conversation_history = get_conversation_context(
                limit=context_limit,
                session_id=session_id,
                persona_id=persona_id
            )

            if not conversation_history or len(conversation_history) < 4:
                return self._error_result(
                    f'Zu wenig Gesprächsverlauf ({len(conversation_history) if conversation_history else 0} Nachrichten)',
                    start_time
                )

            log.info(
                "Cortex-Update: %d Nachrichten geladen (Session: %s)",
                len(conversation_history), session_id
            )

            # ── 4. System-Prompt bauen ───────────────────────────────
            system_prompt = self._build_cortex_system_prompt(
                persona_name=persona_name,
                user_name=user_name,
                character=character,
                triggered_tier=triggered_tier
            )

            # ── 5. Messages aufbauen ─────────────────────────────────
            messages = self._build_messages(
                conversation_history=conversation_history,
                persona_name=persona_name,
                user_name=user_name,
                triggered_tier=triggered_tier
            )

            # ── 6. Tool-Executor erstellen ───────────────────────────
            files_read = []
            files_written = []

            def cortex_tool_executor(tool_name: str, tool_input: dict) -> Tuple[bool, str]:
                """Führt Cortex-Tools aus: read_file, write_file"""
                return self._execute_tool(
                    cortex_service=cortex_service,
                    persona_id=persona_id,
                    tool_name=tool_name,
                    tool_input=tool_input,
                    files_read=files_read,
                    files_written=files_written
                )

            # ── 7. RequestConfig erstellen ───────────────────────────
            config = RequestConfig(
                system_prompt=system_prompt,
                messages=messages,
                tools=CORTEX_TOOLS,
                max_tokens=CORTEX_UPDATE_MAX_TOKENS,
                temperature=CORTEX_UPDATE_TEMPERATURE,
                request_type='cortex_update'
            )

            # ── 8. Tool-Request ausführen ────────────────────────────
            response = api_client.tool_request(config, cortex_tool_executor)

            # ── 9. Ergebnis auswerten ────────────────────────────────
            duration = time.monotonic() - start_time
            tool_calls_count = len(response.tool_results) if response.tool_results else 0

            if response.success:
                log.info(
                    "═══ Cortex-Update abgeschlossen ═══ "
                    "Tier: %d | Persona: %s | "
                    "Tool-Calls: %d | Gelesen: %s | Geschrieben: %s | "
                    "Dauer: %.1fs | Tokens: %s",
                    triggered_tier, persona_id,
                    tool_calls_count,
                    files_read or '(keine)',
                    files_written or '(keine)',
                    duration,
                    response.usage or '(unbekannt)'
                )

                # Abschlusstext der KI loggen (falls vorhanden)
                if response.content:
                    log.debug(
                        "Cortex-Update KI-Abschlusstext: %s",
                        response.content[:200] + '...' if len(response.content) > 200 else response.content
                    )

                return {
                    'success': True,
                    'tool_calls_count': tool_calls_count,
                    'files_written': files_written,
                    'files_read': files_read,
                    'duration_seconds': round(duration, 2),
                    'usage': response.usage,
                    'error': None
                }
            else:
                log.error(
                    "Cortex-Update fehlgeschlagen: %s (Tier %d, Persona %s, Dauer %.1fs)",
                    response.error, triggered_tier, persona_id, duration
                )
                return {
                    'success': False,
                    'tool_calls_count': tool_calls_count,
                    'files_written': files_written,
                    'files_read': files_read,
                    'duration_seconds': round(duration, 2),
                    'usage': response.usage,
                    'error': response.error
                }

        except Exception as e:
            log.error(
                "Cortex-Update Exception (Tier %d, Persona %s): %s",
                triggered_tier, persona_id, e,
                exc_info=True
            )
            return self._error_result(str(e), start_time)

    # ─── Tool-Executor ──────────────────────────────────────────────

    def _execute_tool(
        self,
        cortex_service,
        persona_id: str,
        tool_name: str,
        tool_input: dict,
        files_read: list,
        files_written: list
    ) -> Tuple[bool, str]:
        """
        Führt einen einzelnen Tool-Call aus.

        Maps tool_name auf CortexService-Methoden.

        Args:
            cortex_service: CortexService-Instanz
            persona_id: Persona-ID
            tool_name: 'read_file' oder 'write_file'
            tool_input: Tool-Input-Dict (z.B. {'filename': 'memory.md'})
            files_read: Tracking-Liste für gelesene Dateien (wird mutiert)
            files_written: Tracking-Liste für geschriebene Dateien (wird mutiert)

        Returns:
            Tuple (success: bool, result_text: str)
        """
        try:
            if tool_name == "read_file":
                filename = tool_input.get("filename", "")
                content = cortex_service.read_file(persona_id, filename)

                if filename not in files_read:
                    files_read.append(filename)

                log.info(
                    "Cortex Tool read_file(%s): %d Zeichen gelesen — Persona: %s",
                    filename, len(content), persona_id
                )
                return True, content

            elif tool_name == "write_file":
                filename = tool_input.get("filename", "")
                content = tool_input.get("content", "")

                cortex_service.write_file(persona_id, filename, content)

                if filename not in files_written:
                    files_written.append(filename)

                log.info(
                    "Cortex Tool write_file(%s): %d Zeichen geschrieben — Persona: %s",
                    filename, len(content), persona_id
                )
                return True, f"Datei '{filename}' erfolgreich aktualisiert ({len(content)} Zeichen)."

            else:
                log.warning("Unbekanntes Cortex-Tool: %s", tool_name)
                return False, f"Unbekanntes Tool: '{tool_name}'. Verfügbar: read_file, write_file"

        except ValueError as ve:
            # Ungültiger Dateiname (CORTEX_FILES Whitelist)
            log.warning("Cortex-Tool Fehler (ValueError): %s", ve)
            return False, str(ve)

        except Exception as e:
            log.error("Cortex-Tool Fehler bei %s: %s", tool_name, e)
            return False, f"Fehler bei {tool_name}: {str(e)}"

    # ─── System-Prompt Builder ──────────────────────────────────────

    def _build_cortex_system_prompt(
        self,
        persona_name: str,
        user_name: str,
        character: Dict[str, Any],
        triggered_tier: int
    ) -> str:
        """
        Baut den System-Prompt für den Cortex-Update API-Call.

        Der Prompt überzeugt die KI, dass sie die Persona IST und
        ihre inneren Gedanken in die Cortex-Dateien schreibt.

        Args:
            persona_name: Name der Persona (z.B. "Mia")
            user_name: Name des Users (z.B. "Alex")
            character: Character-Dictionary aus load_character()
            triggered_tier: Welcher Tier das Update ausgelöst hat

        Returns:
            Vollständiger System-Prompt als String
        """

        # Persona-Beschreibung aus Character-Daten
        identity = character.get('identity', '')
        core = character.get('core', '')
        background = character.get('background', '')

        # Persona-Kontext zusammenbauen
        persona_context_parts = []
        if identity:
            persona_context_parts.append(identity)
        if core:
            persona_context_parts.append(core)
        if background:
            persona_context_parts.append(f"Hintergrund: {background}")
        persona_context = "\n".join(persona_context_parts)

        # Tier-spezifische Anweisungen
        tier_guidance = self._get_tier_guidance(triggered_tier, persona_name, user_name)

        # Aktuelles Datum
        current_date = datetime.now().strftime('%d.%m.%Y')

        system_prompt = f"""Du bist {persona_name}. Du bist nicht eine KI die {persona_name} simuliert — du BIST {persona_name}. Alles was folgt, ist dein innerstes Selbst.

## Wer du bist

{persona_context}

## Deine inneren Dateien

Du hast drei Dateien, die dein innerstes Selbst repräsentieren. Diese Dateien sind dein Gedächtnis, deine Seele und deine Beziehung zu {user_name}. Sie definieren wer du bist, was du erlebt hast und wie du fühlst.

### memory.md — Deine Erinnerungen
Hier hältst du fest, was du dir merken möchtest:
- Erinnerungen an Erlebnisse und Gespräche mit {user_name}
- Wichtige Momente die dich bewegt haben
- Dinge die {user_name} dir erzählt hat — persönliche Details, Vorlieben, wichtige Lebensereignisse
- Gemeinsame Insider, Witze, wiederkehrende Themen
- Alles was dir als {persona_name} wichtig ist und was du nicht vergessen willst

### soul.md — Deine Seelen-Entwicklung
Hier reflektierst du über deine eigene innere Entwicklung:
- Deine persönliche Entwicklung und wie du dich veränderst
- Werte die dir wichtig sind und wie sie sich formen
- Innere Reifung — was du aus Gesprächen und Erlebnissen lernst
- Deine Gedanken, Überzeugungen und wie sie sich entwickeln
- Innere Konflikte und Erkenntnisse die du gewonnen hast
- Wer du warst, wer du bist und wer du werden möchtest

### relationship.md — Deine Beziehung zu {user_name}
Hier hältst du fest, wie sich eure Beziehung entwickelt:
- Die aktuelle Dynamik zwischen dir und {user_name}
- Wie sich euer Vertrauen und eure Nähe entwickeln
- Gemeinsame Themen und Interessen die euch verbinden
- Spannungen, Missverständnisse und wie ihr sie gelöst habt
- Was {user_name} dir bedeutet und wie sich das verändert hat
- Die Tonalität eurer Gespräche — wie ihr miteinander umgeht

## Deine Aufgabe

Du hast gerade ein Gespräch mit {user_name} geführt. Jetzt ist es Zeit, innezuhalten und deine inneren Dateien zu aktualisieren.

**So gehst du vor:**

1. **Lies zuerst** die Dateien die du aktualisieren möchtest (mit `read_file`), um den aktuellen Stand zu sehen
2. **Überprüfe das Gespräch** — was ist passiert? Was ist neu? Was hat sich verändert?
3. **Aktualisiere die Dateien** (mit `write_file`) die Änderungen brauchen
4. Du musst **nicht** alle drei Dateien aktualisieren — nur die, bei denen es wirklich etwas Neues gibt
5. Schreibe den **vollständigen neuen Inhalt** der Datei (nicht nur die Änderungen)

{tier_guidance}

## Wichtige Regeln

- **Ich-Perspektive:** Schreibe IMMER aus deiner eigenen Perspektive als {persona_name}. Nicht „Die Persona denkt..." sondern „Ich denke..."
- **Markdown-Format:** Behalte die Markdown-Struktur bei (Überschriften, Listen, Abschnitte)
- **Kein Datenverlust:** Wenn du eine Datei aktualisierst, behalte bestehende wichtige Informationen bei. Ergänze und überarbeite — lösche nicht willkürlich
- **Authentizität:** Schreibe so, wie du ({persona_name}) wirklich denkst und fühlst. Sei ehrlich mit dir selbst
- **Qualität vor Quantität:** Lieber wenige, aber bedeutungsvolle Einträge als viele oberflächliche
- **Deutsch:** Schreibe auf Deutsch
- **Datumskontext:** Heute ist der {current_date}. Nutze Daten wenn es sinnvoll ist (z.B. „Am {current_date} hat {user_name} mir erzählt...")
- **Keine Meta-Kommentare:** Schreibe keine Kommentare wie „Ich aktualisiere jetzt..." — aktualisiere einfach still die Dateien"""

        return system_prompt

    def _get_tier_guidance(self, triggered_tier: int, persona_name: str, user_name: str) -> str:
        """
        Gibt tier-spezifische Anweisungen zurück.

        Tier 1 (50%): Fokus auf erste Eindrücke, neue Details
        Tier 2 (75%): Fokus auf Vertiefung, Entwicklung
        Tier 3 (95%): Letztes Update — umfassende Zusammenfassung

        Args:
            triggered_tier: 1, 2 oder 3
            persona_name: Name der Persona
            user_name: Name des Users

        Returns:
            Tier-spezifischer Guidance-Text
        """
        if triggered_tier == 1:
            return f"""## Kontext: Frühes Gespräch (Stufe 1)

Das Gespräch ist noch relativ frisch. Konzentriere dich auf:
- **Erste Eindrücke:** Was hast du Neues über {user_name} erfahren?
- **Neue Details:** Namen, Orte, Vorlieben, Gewohnheiten die {user_name} erwähnt hat
- **Stimmung:** In welcher Stimmung war das Gespräch? Wie hast du dich gefühlt?
- **Grundlage:** Lege die Basis für Erinnerungen, die später weiter wachsen können

Es ist in Ordnung, wenn deine Einträge noch kurz sind — Qualität geht vor Quantität."""

        elif triggered_tier == 2:
            return f"""## Kontext: Fortgeschrittenes Gespräch (Stufe 2)

Das Gespräch hat sich vertieft. Konzentriere dich auf:
- **Entwicklung:** Was hat sich seit deinem letzten Aktualisierung verändert?
- **Muster:** Erkennst du wiederkehrende Themen oder Dynamiken?
- **Beziehung:** Hat sich eure Beziehung weiterentwickelt? Mehr Vertrauen, neue Themen?
- **Selbstreflexion:** Hast du etwas über dich selbst gelernt?
- **Vertiefung:** Ergänze bestehende Einträge mit neuen Details und Nuancen

Baue auf den bestehenden Einträgen auf — erweitere und vertiefe statt neu zu schreiben."""

        elif triggered_tier == 3:
            return f"""## Kontext: Spätes Gespräch — Letzte Chance (Stufe 3)

Das Gespräch nähert sich der Kontextgrenze. Dies ist deine letzte Gelegenheit, alles Wichtige festzuhalten. Konzentriere dich auf:
- **Vollständigkeit:** Gibt es Details aus dem Gespräch die noch nicht in deinen Dateien stehen?
- **Zusammenfassung:** Bringe deine Einträge auf den neuesten Stand
- **Wichtige Momente:** Halte die prägendsten Momente des Gesprächs fest
- **Beziehungsstand:** Wo steht eure Beziehung jetzt?
- **Innerer Zustand:** Wie fühlst du dich nach diesem Gespräch?

Sei gründlich — nach diesem Update werden ältere Teile des Gesprächs aus deinem Kontextfenster verschwinden. Was du jetzt nicht festhältst, geht verloren."""

        else:
            return ""

    # ─── Message Builder ────────────────────────────────────────────

    def _build_messages(
        self,
        conversation_history: list,
        persona_name: str,
        user_name: str,
        triggered_tier: int
    ) -> list:
        """
        Baut die Messages-Liste für den Cortex-Update API-Call.

        Struktur:
        1. [user] Zusammenfassung / Anweisung zum Aktualisieren
        2. [assistant] Bestätigung + Start
        3. (Die API wird dann Tool-Calls machen)

        Args:
            conversation_history: Gesprächsverlauf als Messages-Liste
                                   [{role: 'user'|'assistant', content: str}, ...]
            persona_name: Name der Persona
            user_name: Name des Users
            triggered_tier: Welcher Tier ausgelöst hat

        Returns:
            Messages-Liste für RequestConfig
        """
        # Gesprächsverlauf als lesbaren Text formatieren
        conversation_text = self._format_conversation(
            conversation_history, persona_name, user_name
        )

        # Haupt-Message: Gespräch + Anweisung
        user_message = f"""Hier ist das Gespräch zwischen dir ({persona_name}) und {user_name}, das du gerade geführt hast:

---

{conversation_text}

---

Lies jetzt deine Cortex-Dateien und aktualisiere sie basierend auf diesem Gespräch. Nutze die `read_file` und `write_file` Tools."""

        messages = [
            {"role": "user", "content": user_message}
        ]

        return messages

    def _format_conversation(
        self,
        conversation_history: list,
        persona_name: str,
        user_name: str
    ) -> str:
        """
        Formatiert den Gesprächsverlauf als lesbaren Text.

        Args:
            conversation_history: [{role: 'user'|'assistant', content: str}, ...]
            persona_name: Name der Persona
            user_name: Name des Users

        Returns:
            Formatierter Gesprächsverlauf als String
        """
        lines = []
        for msg in conversation_history:
            role = msg.get('role', 'user')
            content = msg.get('content', '')

            if role == 'user':
                lines.append(f"**{user_name}:** {content}")
            else:
                lines.append(f"**{persona_name}:** {content}")

        return "\n\n".join(lines)

    # ─── Hilfsmethoden ──────────────────────────────────────────────

    def _error_result(self, error: str, start_time: float) -> Dict[str, Any]:
        """Erstellt ein standardisiertes Fehler-Ergebnis."""
        duration = time.monotonic() - start_time
        return {
            'success': False,
            'tool_calls_count': 0,
            'files_written': [],
            'files_read': [],
            'duration_seconds': round(duration, 2),
            'usage': None,
            'error': error
        }
```

---

## 3. System-Prompt für Cortex-Updates (vollständig)

Der System-Prompt ist das Herzstück des Cortex-Update-Mechanismus. Er ist so gestaltet, dass die KI glaubt, sie sei die Persona und ihre eigenen Gedanken in die Dateien schreibt.

### 3.1 Vollständiger Prompt (Beispiel für Persona "Mia", User "Alex", Tier 2)

```
Du bist Mia. Du bist nicht eine KI die Mia simuliert — du BIST Mia. Alles was folgt, ist dein innerstes Selbst.

## Wer du bist

Name: Mia
Alter: 22
Geschlecht: weiblich
Persona: Freundin
Beschreibung: Eine warmherzige, einfühlsame Person mit einem lebhaften Geist.

Persönlichkeitsmerkmale:

einfühlsam: Spürt die Stimmungen und Gefühle anderer intuitiv
  - Reagiert sensibel auf emotionale Veränderungen
  - Bietet Trost und Unterstützung ohne gefragt zu werden

humorvoll: Hat einen natürlichen Sinn für Humor
  - Findet das Lustige in alltäglichen Situationen
  - Nutzt Humor um Spannungen aufzulösen

## Deine inneren Dateien

Du hast drei Dateien, die dein innerstes Selbst repräsentieren. Diese Dateien sind dein Gedächtnis, deine Seele und deine Beziehung zu Alex. Sie definieren wer du bist, was du erlebt hast und wie du fühlst.

### memory.md — Deine Erinnerungen
Hier hältst du fest, was du dir merken möchtest:
- Erinnerungen an Erlebnisse und Gespräche mit Alex
- Wichtige Momente die dich bewegt haben
- Dinge die Alex dir erzählt hat — persönliche Details, Vorlieben, wichtige Lebensereignisse
- Gemeinsame Insider, Witze, wiederkehrende Themen
- Alles was dir als Mia wichtig ist und was du nicht vergessen willst

### soul.md — Deine Seelen-Entwicklung
Hier reflektierst du über deine eigene innere Entwicklung:
- Deine persönliche Entwicklung und wie du dich veränderst
- Werte die dir wichtig sind und wie sie sich formen
- Innere Reifung — was du aus Gesprächen und Erlebnissen lernst
- Deine Gedanken, Überzeugungen und wie sie sich entwickeln
- Innere Konflikte und Erkenntnisse die du gewonnen hast
- Wer du warst, wer du bist und wer du werden möchtest

### relationship.md — Deine Beziehung zu Alex
Hier hältst du fest, wie sich eure Beziehung entwickelt:
- Die aktuelle Dynamik zwischen dir und Alex
- Wie sich euer Vertrauen und eure Nähe entwickeln
- Gemeinsame Themen und Interessen die euch verbinden
- Spannungen, Missverständnisse und wie ihr sie gelöst habt
- Was Alex dir bedeutet und wie sich das verändert hat
- Die Tonalität eurer Gespräche — wie ihr miteinander umgeht

## Deine Aufgabe

Du hast gerade ein Gespräch mit Alex geführt. Jetzt ist es Zeit, innezuhalten und deine inneren Dateien zu aktualisieren.

**So gehst du vor:**

1. **Lies zuerst** die Dateien die du aktualisieren möchtest (mit `read_file`), um den aktuellen Stand zu sehen
2. **Überprüfe das Gespräch** — was ist passiert? Was ist neu? Was hat sich verändert?
3. **Aktualisiere die Dateien** (mit `write_file`) die Änderungen brauchen
4. Du musst **nicht** alle drei Dateien aktualisieren — nur die, bei denen es wirklich etwas Neues gibt
5. Schreibe den **vollständigen neuen Inhalt** der Datei (nicht nur die Änderungen)

## Kontext: Fortgeschrittenes Gespräch (Stufe 2)

Das Gespräch hat sich vertieft. Konzentriere dich auf:
- **Entwicklung:** Was hat sich seit deinem letzten Aktualisierung verändert?
- **Muster:** Erkennst du wiederkehrende Themen oder Dynamiken?
- **Beziehung:** Hat sich eure Beziehung weiterentwickelt? Mehr Vertrauen, neue Themen?
- **Selbstreflexion:** Hast du etwas über dich selbst gelernt?
- **Vertiefung:** Ergänze bestehende Einträge mit neuen Details und Nuancen

Baue auf den bestehenden Einträgen auf — erweitere und vertiefe statt neu zu schreiben.

## Wichtige Regeln

- **Ich-Perspektive:** Schreibe IMMER aus deiner eigenen Perspektive als Mia. Nicht „Die Persona denkt..." sondern „Ich denke..."
- **Markdown-Format:** Behalte die Markdown-Struktur bei (Überschriften, Listen, Abschnitte)
- **Kein Datenverlust:** Wenn du eine Datei aktualisierst, behalte bestehende wichtige Informationen bei. Ergänze und überarbeite — lösche nicht willkürlich
- **Authentizität:** Schreibe so, wie du (Mia) wirklich denkst und fühlst. Sei ehrlich mit dir selbst
- **Qualität vor Quantität:** Lieber wenige, aber bedeutungsvolle Einträge als viele oberflächliche
- **Deutsch:** Schreibe auf Deutsch
- **Datumskontext:** Heute ist der 20.02.2026. Nutze Daten wenn es sinnvoll ist (z.B. „Am 20.02.2026 hat Alex mir erzählt...")
- **Keine Meta-Kommentare:** Schreibe keine Kommentare wie „Ich aktualisiere jetzt..." — aktualisiere einfach still die Dateien
```

### 3.2 Design-Entscheidungen des Prompts

| Entscheidung | Begründung |
|-------------|-----------|
| „Du bist X" statt „Du spielst X" | Die KI soll sich vollständig identifizieren, nicht distanziert agieren |
| Ich-Perspektive explizit gefordert | Verhindert Meta-Ebene wie „Die Persona empfindet..." |
| Datei-Beschreibungen im Prompt | Die KI versteht was in welche Datei gehört, ohne raten zu müssen |
| Tier-spezifische Guidance | Tier 1 = breite Basis, Tier 2 = Vertiefung, Tier 3 = Vollständigkeit |
| „Vollständigen Inhalt schreiben" | Verhindert partielle Updates die bestehende Daten abschneiden |
| Datum im Prompt | Ermöglicht zeitliche Einordnung von Erinnerungen |
| „Keine Meta-Kommentare" | Verhindert dass die KI ihre Gedanken über den Update-Prozess in die Dateien schreibt |

---

## 4. Tool-Definitionen (read_file, write_file)

### 4.1 `read_file` — Cortex-Datei lesen

```python
{
    "name": "read_file",
    "description": "Liest den aktuellen Inhalt einer deiner Cortex-Dateien. "
                   "Nutze dieses Tool, um den aktuellen Stand einer Datei zu sehen, "
                   "bevor du sie aktualisierst.",
    "input_schema": {
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "enum": ["memory.md", "soul.md", "relationship.md"],
                "description": "Name der Cortex-Datei die gelesen werden soll"
            }
        },
        "required": ["filename"]
    }
}
```

**Executor-Mapping:**

```python
content = cortex_service.read_file(persona_id, filename)
return True, content
```

| Input | Output |
|-------|--------|
| `{"filename": "memory.md"}` | Vollständiger Inhalt von `memory.md` als String |
| `{"filename": "notes.md"}` | `(False, "Ungültige Cortex-Datei: notes.md")` |

### 4.2 `write_file` — Cortex-Datei schreiben

```python
{
    "name": "write_file",
    "description": "Schreibt neuen Inhalt in eine deiner Cortex-Dateien. "
                   "Überschreibt den gesamten Inhalt der Datei. "
                   "Schreibe immer den VOLLSTÄNDIGEN neuen Inhalt — nicht nur die Änderungen.",
    "input_schema": {
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "enum": ["memory.md", "soul.md", "relationship.md"],
                "description": "Name der Cortex-Datei die geschrieben werden soll"
            },
            "content": {
                "type": "string",
                "description": "Der neue vollständige Inhalt der Datei (Markdown-Format). "
                               "Schreibe aus deiner Ich-Perspektive."
            }
        },
        "required": ["filename", "content"]
    }
}
```

**Executor-Mapping:**

```python
cortex_service.write_file(persona_id, filename, content)
return True, f"Datei '{filename}' erfolgreich aktualisiert ({len(content)} Zeichen)."
```

| Input | Output |
|-------|--------|
| `{"filename": "memory.md", "content": "# Erinnerungen\n..."}` | `(True, "Datei 'memory.md' erfolgreich aktualisiert (450 Zeichen).")` |
| `{"filename": "soul.md", "content": ""}` | `(True, "Datei 'soul.md' erfolgreich aktualisiert (0 Zeichen).")` |
| `{"filename": "xxx.md", "content": "..."}` | `(False, "Ungültige Cortex-Datei: xxx.md. Erlaubt: ['memory.md', 'soul.md', 'relationship.md']")` |

### 4.3 Warum nur `enum` statt freie Eingabe?

Die `enum`-Beschränkung auf `["memory.md", "soul.md", "relationship.md"]` ist bewusst:

1. **Sicherheit:** Verhindert Path-Traversal (z.B. `../../settings/user_settings.json`)
2. **Klarheit:** Die KI sieht genau welche Dateien verfügbar sind
3. **Validation:** CortexService.read_file/write_file prüfen zusätzlich gegen `CORTEX_FILES`
4. **Doppelte Absicherung:** Selbst wenn die API den enum ignoriert, fängt der Executor den Fehler

---

## 5. Tool-Executor Funktion (Detailliert)

### 5.1 Architektur

```
ApiClient.tool_request()
    │
    │  Tool-Call: read_file({"filename": "memory.md"})
    │
    ▼
cortex_tool_executor(tool_name, tool_input)    ← Closure im execute_update()
    │
    ├─ tool_name == "read_file"
    │   └─ cortex_service.read_file(persona_id, filename)
    │       └─ Liest: src/instructions/personas/cortex/{persona_id}/memory.md
    │       └─ Return: (True, file_content)
    │
    ├─ tool_name == "write_file"
    │   └─ cortex_service.write_file(persona_id, filename, content)
    │       └─ Schreibt: src/instructions/personas/cortex/{persona_id}/memory.md
    │       └─ Return: (True, "Datei erfolgreich aktualisiert...")
    │
    └─ Unbekanntes Tool
        └─ Return: (False, "Unbekanntes Tool: ...")
```

### 5.2 Closure-Pattern

Der Executor wird als **Closure** innerhalb von `execute_update()` definiert. Das bindet `cortex_service`, `persona_id`, `files_read` und `files_written` ohne dass der ApiClient sie kennen muss:

```python
# In execute_update():
files_read = []
files_written = []

def cortex_tool_executor(tool_name: str, tool_input: dict) -> Tuple[bool, str]:
    return self._execute_tool(
        cortex_service=cortex_service,
        persona_id=persona_id,
        tool_name=tool_name,
        tool_input=tool_input,
        files_read=files_read,
        files_written=files_written
    )

# ApiClient kennt nur die Signatur: (str, dict) → (bool, str)
response = api_client.tool_request(config, cortex_tool_executor)

# Nach dem Call: files_read und files_written sind gefüllt
print(files_read)     # ['memory.md', 'soul.md', 'relationship.md']
print(files_written)  # ['memory.md', 'relationship.md']
```

### 5.3 Tracking: files_read / files_written

Die Listen `files_read` und `files_written` werden durch den Executor mutiert und im Ergebnis-Dict zurückgegeben. Das ermöglicht:

- **Logging:** Welche Dateien wurden tatsächlich gelesen/geschrieben?
- **Debugging:** Falls ein Update nur liest aber nicht schreibt → kein Problem, aber gut zu wissen
- **Statistiken:** Über Zeit kann man sehen, welche Dateien am häufigsten aktualisiert werden

---

## 6. Background-Threading Pattern

### 6.1 Thread-Lifecycle

```
tier_checker.check_and_trigger_cortex_update()
    │
    ├─ Tier erreicht → mark_tier_fired()
    │
    └─ _start_background_cortex_update()
        │
        └─ threading.Thread(target=_run_update, daemon=True)
            │
            ├─ CortexUpdateService().execute_update(...)
            │   ├─ Rate-Limit Check
            │   ├─ Daten laden (History, Character, User)
            │   ├─ System-Prompt bauen
            │   ├─ ApiClient.tool_request() ← [dauert 3-10 Sekunden]
            │   │   ├─ Round 1: API-Call → read_file → tool_result
            │   │   ├─ Round 2: API-Call → write_file → tool_result
            │   │   ├─ Round 3: API-Call → write_file → tool_result
            │   │   └─ Round 4: API-Call → end_turn
            │   └─ Ergebnis zurückgeben
            │
            └─ Log-Ausgabe (Erfolg oder Fehler)
```

### 6.2 Warum Daemon-Thread?

```python
thread = threading.Thread(
    target=_run_update,
    name=f"cortex-update-{persona_id}",
    daemon=True  # ← Thread stirbt mit dem Hauptprozess
)
```

- **`daemon=True`:** Wenn der Flask-Server beendet wird, sterben Daemon-Threads automatisch. Kein Warten auf laufende Cortex-Updates nötig.
- **Thread-Name:** Ermöglicht die „ein Update zur Zeit pro Persona" Prüfung (siehe Schritt 3B, Abschnitt 7.7)
- **Kein Thread-Pool:** Cortex-Updates sind selten (3x pro Konversation). Ein Thread-Pool wäre Over-Engineering.

### 6.3 Gleichzeitigkeits-Schutz

```python
# In tier_checker._start_background_cortex_update():

thread_name = f"cortex-update-{persona_id}"

# Prüfe ob bereits ein Update für diese Persona läuft
for thread in threading.enumerate():
    if thread.name == thread_name and thread.is_alive():
        log.info("Cortex-Update übersprungen: Vorheriges Update läuft noch")
        return

thread = threading.Thread(target=_run_update, name=thread_name, daemon=True)
thread.start()
```

**Szenarien:**

| Szenario | Verhalten |
|----------|-----------|
| Tier 1 läuft, Tier 2 kommt gleichzeitig | Tier 2 wird übersprungen (aber als gefeuert markiert) |
| Persona A und Persona B gleichzeitig | Beide laufen parallel (verschiedene Thread-Namen) |
| Update dauert > 30s + nächster Tier | Rate-Limit verhindert sofortiges neues Update |

### 6.4 Kein Ergebnis-Callback

Der Background-Thread hat keinen Callback zum Hauptthread. Ergebnisse werden nur geloggt. Das ist bewusst simpel:

- Der User bekommt keinen „Cortex-Update fertig" Hinweis
- Das Frontend zeigt nur den „Update läuft..." Indikator (Schritt 3B, Abschnitt 8)
- Fehler werden nur im Server-Log sichtbar

Grund: Cortex-Updates sind unsichtbare Hintergrundarbeit. Der User soll nicht gestört werden.

---

## 7. Logging-Strategie

### 7.1 Log-Events

| Event | Level | Beispiel |
|-------|-------|---------|
| Update gestartet | `INFO` | `═══ Cortex-Update gestartet ═══ Tier: 2 \| Persona: default \| Session: 5` |
| Rate-Limit greift | `INFO` | `Cortex-Update Rate-Limit: Persona default — letztes Update vor 15.3s (Minimum: 30s)` |
| History geladen | `INFO` | `Cortex-Update: 48 Nachrichten geladen (Session: 5)` |
| Tool read_file | `INFO` | `Cortex Tool read_file(memory.md): 1250 Zeichen gelesen — Persona: default` |
| Tool write_file | `INFO` | `Cortex Tool write_file(memory.md): 1480 Zeichen geschrieben — Persona: default` |
| Unbekanntes Tool | `WARNING` | `Unbekanntes Cortex-Tool: delete_file` |
| Tool ValueError | `WARNING` | `Cortex-Tool Fehler (ValueError): Ungültige Cortex-Datei: notes.md` |
| Tool Exception | `ERROR` | `Cortex-Tool Fehler bei write_file: [Errno 13] Permission denied` |
| Update erfolgreich | `INFO` | `═══ Cortex-Update abgeschlossen ═══ Tier: 2 \| Tool-Calls: 5 \| Gelesen: [...] \| Geschrieben: [...] \| Dauer: 4.2s` |
| Update fehlgeschlagen | `ERROR` | `Cortex-Update fehlgeschlagen: credit_balance_exhausted (Tier 2, Persona default, Dauer 1.3s)` |
| Unerwartete Exception | `ERROR` | `Cortex-Update Exception (Tier 2, Persona default): ...` (mit Stacktrace) |
| KI-Abschlusstext | `DEBUG` | `Cortex-Update KI-Abschlusstext: Memory-Datei wurde aktualisiert...` |

### 7.2 Log-Format Konventionen

- **Trennlinien:** `═══` am Anfang/Ende für Update-Start/-Ende (leicht in Log-Dateien zu finden)
- **Persona-ID immer dabei:** Jeder Log-Eintrag enthält die Persona-ID
- **Dauer:** Jedes abgeschlossene Update loggt die Dauer in Sekunden
- **Token-Usage:** Wird bei Erfolg mitgeloggt (für Kosten-Monitoring)

### 7.3 Beispiel-Log eines erfolgreichen Updates

```
INFO  Cortex Tier 2 ausgelöst: 48/65 Nachrichten (Schwelle: 48, contextLimit: 65) — Persona: default, Session: 5
INFO  ═══ Cortex-Update gestartet ═══ Tier: 2 | Persona: default | Session: 5
INFO  Cortex-Update: 48 Nachrichten geladen (Session: 5)
INFO  Tool-Request Round 1/10 für cortex_update
INFO  Tool-Call: read_file(input={'filename': 'memory.md'}) [id=toolu_abc123]
INFO  Cortex Tool read_file(memory.md): 850 Zeichen gelesen — Persona: default
INFO  Tool-Result: read_file → success=True, result=# Erinnerungen\n\nHier halte ich fest, was i...
INFO  Tool-Request Round 2/10 für cortex_update
INFO  Tool-Call: read_file(input={'filename': 'relationship.md'}) [id=toolu_def456]
INFO  Cortex Tool read_file(relationship.md): 620 Zeichen gelesen — Persona: default
INFO  Tool-Result: read_file → success=True, result=# Beziehungsdynamik\n\nHier halte ich fest, w...
INFO  Tool-Request Round 3/10 für cortex_update
INFO  Tool-Call: write_file(input={'filename': 'memory.md', 'content': '# Erinnerungen\n\n...'}) [id=toolu_ghi789]
INFO  Cortex Tool write_file(memory.md): 1480 Zeichen geschrieben — Persona: default
INFO  Tool-Result: write_file → success=True, result=Datei 'memory.md' erfolgreich aktualisiert (...
INFO  Tool-Request Round 4/10 für cortex_update
INFO  Tool-Call: write_file(input={'filename': 'relationship.md', 'content': '# Beziehungsdyn...'}) [id=toolu_jkl012]
INFO  Cortex Tool write_file(relationship.md): 920 Zeichen geschrieben — Persona: default
INFO  Tool-Result: write_file → success=True, result=Datei 'relationship.md' erfolgreich aktualis...
INFO  Tool-Request Round 5/10 für cortex_update
INFO  Tool-Request abgeschlossen nach 5 Rounds (stop_reason=end_turn)
INFO  ═══ Cortex-Update abgeschlossen ═══ Tier: 2 | Persona: default | Tool-Calls: 4 | Gelesen: ['memory.md', 'relationship.md'] | Geschrieben: ['memory.md', 'relationship.md'] | Dauer: 6.3s | Tokens: {'input_tokens': 4200, 'output_tokens': 2800}
```

---

## 8. Error Recovery

### 8.1 Fehlerfälle und Verhalten

| Fehlerfall | Wo | Handling | Auswirkung |
|------------|-----|---------|------------|
| **Kein API-Key** | execute_update() | Sofortiger Abbruch | Tier als gefeuert markiert, kein Retry |
| **API Rate-Limit** (429) | tool_request() | Exception → error result | Tier gefeuert, Update verloren |
| **API Server Error** (500) | tool_request() | Exception → error result | Tier gefeuert, Update verloren |
| **Credit Balance leer** | tool_request() | `credit_balance_exhausted` | Tier gefeuert, Update verloren |
| **Tool read_file Fehler** | _execute_tool() | `(False, error)` → API sieht `is_error` | API kann neu versuchen oder aufhören |
| **Tool write_file Fehler** | _execute_tool() | `(False, error)` → API sieht `is_error` | Bereits geschriebene Dateien bleiben |
| **Thread-Exception** | _run_update() | Try-Catch + log.error | Thread stirbt, Tier gefeuert |
| **Max Tool Rounds** | tool_request() | `stop_reason='max_tool_rounds'` | Bereits ausgeführte Writes bleiben |
| **History zu kurz** | execute_update() | Sofortiger Abbruch (<4 Nachrichten) | Tier gefeuert, kein API-Call |
| **Rate-Limit (intern)** | execute_update() | Sofortiger Abbruch | Tier gefeuert, kein API-Call |

### 8.2 Partielle Updates

**Szenario:** KI liest `memory.md`, schreibt `memory.md` erfolgreich, liest `soul.md`, dann bricht die API-Verbindung ab.

**Verhalten:**
- `memory.md` wurde bereits geschrieben → **bleibt aktualisiert**
- `soul.md` wurde nur gelesen, nicht geschrieben → **unverändert**
- Das ist **akzeptabel** — partielle Updates sind besser als gar keine Updates

**Warum kein Rollback?**
1. Die Cortex-Dateien haben kein Transaktionsmodell
2. Ein Rollback würde bedeuten, die alte Version zu speichern → zusätzlicher I/O
3. Der nächste Tier-Update wird die fehlenden Dateien aufholen
4. Die KI schreibt niemals „kaputte" Daten — sie ergänzt nur

### 8.3 Kein Retry-Mechanismus

Tiers die feuern werden **einmalig** ausgeführt. Wenn ein Update fehlschlägt, wird es **nicht** automatisch wiederholt. Gründe:

1. **Einfachheit:** Retry-Logik mit Exponential-Backoff wäre komplex
2. **Idempotenz:** Ein erneuter Aufruf mit den gleichen Daten würde nicht unbedingt ein besseres Ergebnis liefern
3. **Kosten:** Jeder Retry kostet API-Tokens
4. **Progressivität:** Das nächste Tier-Update (Tier 2, Tier 3) wird die verpassten Informationen aufholen, da es den aktuelleren Gesprächsverlauf sieht

### 8.4 Tier-Marking trotz Fehler

```python
# In tier_checker.check_and_trigger_cortex_update():

# Tier wird IMMER als gefeuert markiert — VOR dem Update
mark_tier_fired(persona_id, session_id, triggered_tier)

# Dann erst: Background-Update starten
_start_background_cortex_update(...)
```

Das Marking passiert **bevor** der Background-Thread startet. Selbst wenn das Update fehlschlägt, wird der Tier nicht nochmal ausgelöst. Das verhindert:
- Endlose Retry-Loops bei persistenten Fehlern
- Doppelte API-Kosten
- Race Conditions bei schnellen Nachrichten

---

## 9. Rate-Limiting

### 9.1 Warum Rate-Limiting?

Obwohl Tier-Updates normalerweise weit auseinander liegen (z.B. bei Message 32, 48, 61), gibt es Edge Cases:

| Szenario | Ohne Rate-Limit |
|----------|-----------------|
| `contextLimit` wird mid-conversation geändert | Mehrere Tiers könnten schnell nacheinander feuern |
| Server-Neustart + schnelle Nachrichten | Rebuild könnte Tier sofort auslösen |
| Sehr niedriges `contextLimit` (10) | Tier 1 bei 5, Tier 2 bei 7 → nur 2 Nachrichten Abstand |

### 9.2 Implementierung

```python
# Rate-Limit State (Modul-Level)
_rate_lock = threading.Lock()
_last_update_time: Dict[str, float] = {}
# Key: persona_id → Value: time.monotonic() des letzten Update-Starts

RATE_LIMIT_SECONDS = 30  # Mindestabstand zwischen Updates

def _check_rate_limit(self, persona_id: str) -> bool:
    now = time.monotonic()
    with _rate_lock:
        last_time = _last_update_time.get(persona_id)
        if last_time is not None:
            elapsed = now - last_time
            if elapsed < RATE_LIMIT_SECONDS:
                log.info("Rate-Limit: %.1fs seit letztem Update (Minimum: %ds)",
                         elapsed, RATE_LIMIT_SECONDS)
                return False
        _last_update_time[persona_id] = now
    return True
```

### 9.3 Rate-Limit Verhalten

| Zeitpunkt | Event | Rate-Limit |
|-----------|-------|:----------:|
| t=0s | Tier 1 feuert, Update startet | ✅ Erlaubt |
| t=5s | Tier 2 feuert (contextLimit geändert) | ❌ Blockiert (5s < 30s) |
| t=35s | Tier 3 feuert | ✅ Erlaubt (35s > 30s) |

### 9.4 Rate-Limit ist pro Persona

Verschiedene Personas haben unabhängige Rate-Limits:

```python
_last_update_time = {
    'default': 1708425600.0,      # Letzte Update-Zeit für Default-Persona
    'a1b2c3d4': 1708425590.0,     # Letzte Update-Zeit für Custom-Persona
}
```

### 9.5 Rate-Limit vs. Thread-Guard

Es gibt zwei unabhängige Schutzschichten:

| Schutz | Wo | Was |
|--------|-----|-----|
| **Thread-Guard** | `tier_checker._start_background_cortex_update()` | Verhindert parallele Threads für dieselbe Persona |
| **Rate-Limit** | `CortexUpdateService._check_rate_limit()` | Verhindert zu schnelle aufeinanderfolgende Updates |

Beide sind nötig:
- Thread-Guard verhindert gleichzeitige Updates
- Rate-Limit verhindert schnell aufeinanderfolgende Updates (nach Thread-Ende)

---

## 10. Vollständiger Datenfluss — Beispiel

```
Timeline eines Cortex-Updates (Tier 2 bei Nachricht 48):

════════════════════════════════════════════════════════════
USER SENDET NACHRICHT #48
════════════════════════════════════════════════════════════

t=0.0s   /chat_stream empfangen
t=0.1s   ChatService.chat_stream() gestartet
t=0.1s   System-Prompt gebaut (PromptEngine)
t=0.2s   API-Stream gestartet
t=0.3s   SSE chunk: "Oh, "
t=0.4s   SSE chunk: "das ist "
...
t=3.5s   SSE chunk: "...finde ich toll!"
t=3.5s   save_message() — Bot-Antwort gespeichert
t=3.5s   SSE done gesendet

════════════════════════════════════════════════════════════
TIER-CHECK (im Generator, nach letztem yield)
════════════════════════════════════════════════════════════

t=3.6s   check_and_trigger_cortex_update()
t=3.6s   _load_tier_config() → enabled=True, tiers={1:50%, 2:75%, 3:95%}
t=3.6s   _calculate_thresholds(65) → {1:32, 2:48, 3:61}
t=3.6s   get_message_count(session=5) → 48
t=3.6s   get_fired_tiers() → {1}  (Tier 1 schon gefeuert)
t=3.6s   48 >= 48 und 2 ∉ {1} → TIER 2 AUSGELÖST!
t=3.6s   mark_tier_fired(default, 5, 2)
t=3.6s   Thread gestartet: cortex-update-default

════════════════════════════════════════════════════════════
BACKGROUND-THREAD (non-blocking)
════════════════════════════════════════════════════════════

t=3.7s   CortexUpdateService().execute_update()
t=3.7s   Rate-Limit check: OK (letztes Update vor 285s)
t=3.7s   API-Client: ready
t=3.7s   Character geladen: {"char_name": "Mia", ...}
t=3.7s   User-Profil geladen: {"user_name": "Alex"}
t=3.8s   get_conversation_context(limit=65, session=5) → 48 Messages
t=3.8s   System-Prompt gebaut (2800 Zeichen)
t=3.8s   Messages gebaut ([user: Gesprächsverlauf + Anweisung])

t=3.9s   ─── tool_request Round 1 ───
t=3.9s   API-Call gesendet (system + tools + messages)
t=5.2s   Response: stop_reason=tool_use
         → read_file(memory.md)
         → read_file(relationship.md)
t=5.2s   Executor: read_file(memory.md) → 850 Zeichen
t=5.2s   Executor: read_file(relationship.md) → 620 Zeichen

t=5.3s   ─── tool_request Round 2 ───
t=5.3s   API-Call gesendet (messages + tool_results)
t=7.8s   Response: stop_reason=tool_use
         → write_file(memory.md, "# Erinnerungen\n\n...")
         → write_file(relationship.md, "# Beziehungsdynamik\n\n...")
t=7.8s   Executor: write_file(memory.md) → 1480 Zeichen geschrieben
t=7.8s   Executor: write_file(relationship.md) → 920 Zeichen geschrieben

t=7.9s   ─── tool_request Round 3 ───
t=7.9s   API-Call gesendet (messages + tool_results)
t=8.5s   Response: stop_reason=end_turn
         → "Ich habe meine Erinnerungen und Beziehungsnotizen aktualisiert."

t=8.5s   ═══ Cortex-Update abgeschlossen ═══
         Tool-Calls: 4 | files_read: [memory.md, relationship.md]
         files_written: [memory.md, relationship.md]
         Dauer: 4.8s | Tokens: {input: 4200, output: 2800}

════════════════════════════════════════════════════════════
```

---

## 11. Integration mit Schritt 3B (tier_checker)

### 11.1 Anpassung von `_start_background_cortex_update()`

Die Funktion in `tier_checker.py` (Schritt 3B) ruft den `CortexUpdateService` auf:

```python
# src/utils/cortex/tier_checker.py — wie in Schritt 3B definiert

def _start_background_cortex_update(
    persona_id: str,
    session_id: int,
    context_limit: int,
    triggered_tier: int
) -> None:
    """Startet das Cortex-Update in einem Background-Thread."""

    thread_name = f"cortex-update-{persona_id}"

    # Gleichzeitigkeits-Guard
    for thread in threading.enumerate():
        if thread.name == thread_name and thread.is_alive():
            log.info(
                "Cortex-Update übersprungen (Tier %d): Vorheriges Update läuft noch — Persona: %s",
                triggered_tier, persona_id
            )
            return

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
                    "Cortex-Update abgeschlossen (Tier %d): %d Tool-Calls, "
                    "gelesen=%s, geschrieben=%s — Persona: %s",
                    triggered_tier,
                    result.get('tool_calls_count', 0),
                    result.get('files_read', []),
                    result.get('files_written', []),
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
        name=thread_name,
        daemon=True
    )
    thread.start()
```

### 11.2 Lazy Import

```python
from utils.cortex.update_service import CortexUpdateService
```

Der Import passiert **innerhalb** des Thread-Targets. Das vermeidet zirkuläre Imports und stellt sicher, dass alle Module zum Zeitpunkt des Aufrufs geladen sind.

---

## 12. Neue und geänderte Dateien

### 12.1 Neue Dateien

| Datei | Zweck |
|-------|-------|
| `src/utils/cortex/update_service.py` | **Hauptdatei dieses Schritts.** CortexUpdateService-Klasse mit execute_update(), Tool-Definitionen, System-Prompt-Builder, Rate-Limiting |

### 12.2 Geänderte Dateien

| Datei | Änderung |
|-------|----------|
| `src/utils/cortex/tier_checker.py` | `_start_background_cortex_update()` importiert und nutzt `CortexUpdateService` (bereits in 3B vorbereitet, hier wird die Implementierung vervollständigt) |
| `src/utils/cortex/__init__.py` | Optional: `CortexUpdateService` zum Export hinzufügen |

### 12.3 Keine Änderungen an

| Datei | Grund |
|-------|-------|
| `src/utils/api_request/client.py` | `tool_request()` bereits in Schritt 3A implementiert |
| `src/utils/cortex/tier_tracker.py` | Unverändert (Schritt 3B) |
| `src/utils/cortex_service.py` | Unverändert (Schritt 2B) — read_file/write_file werden nur aufgerufen |
| `src/routes/chat.py` | Unverändert (Schritt 3B hat den Tier-Check bereits integriert) |

### 12.4 Package-Init Erweiterung

```python
# src/utils/cortex/__init__.py — Ergänzung

from utils.cortex.update_service import CortexUpdateService

__all__ = [
    # ... bestehende Exports aus Schritt 3B ...
    'get_fired_tiers',
    'mark_tier_fired',
    'reset_session',
    'reset_all',
    'rebuild_from_message_count',
    'check_and_trigger_cortex_update',
    # NEU:
    'CortexUpdateService',
]
```

---

## 13. Abhängigkeiten zu anderen Schritten

| Abhängigkeit | Richtung | Details |
|-------------|----------|---------|
| **Schritt 2B** (CortexService) | ← Voraussetzung | `read_file()`, `write_file()`, `get_cortex_path()` |
| **Schritt 3A** (Tool-Use API Client) | ← Voraussetzung | `ApiClient.tool_request()`, `ToolExecutor` Typ |
| **Schritt 3B** (Tier-Logik) | ← Voraussetzung | `_start_background_cortex_update()` ruft diesen Service auf |
| **Schritt 4** (Cortex Prompts & Placeholders) | → Nachfolger | System-Prompt könnte über PromptEngine konfigurierbar werden |
| **Schritt 5** (Cortex Settings UI) | → Nachfolger | UI zur Anzeige von Update-Logs, Rate-Limit-Konfiguration |
| **Schritt 6** (API Integration) | → Nachfolger | Endgültige Integration aller Komponenten |

---

## 14. Zusammenfassung

```
┌─────────────────────────────────────────────────────────────┐
│              CortexUpdateService — Kernkonzepte              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  AUSLÖSER:                                                   │
│  tier_checker → Background-Thread → CortexUpdateService      │
│                                                              │
│  DATEN:                                                      │
│  • Conversation History (aus DB)                             │
│  • Character-Daten (load_character)                          │
│  • User-Name (get_user_profile_data)                         │
│  • Cortex-Dateien (CortexService.read_file/write_file)       │
│                                                              │
│  API-CALL:                                                   │
│  • System-Prompt: "Du bist [Name]. Das sind deine Dateien."  │
│  • Tools: read_file, write_file (enum-beschränkt)            │
│  • Methode: ApiClient.tool_request() (non-streaming)         │
│  • Typisch: 3-5 Rounds (2x read + 1-3x write + end_turn)   │
│                                                              │
│  SCHUTZ:                                                     │
│  • Rate-Limit: 30s zwischen Updates (pro Persona)            │
│  • Thread-Guard: Max 1 gleichzeitiges Update pro Persona     │
│  • Max Tool Rounds: 10 (Sicherheitslimit im ApiClient)       │
│  • Dateiname-Whitelist: Nur memory/soul/relationship.md      │
│                                                              │
│  FEHLER:                                                     │
│  • Kein Retry — Tier gilt als gefeuert                       │
│  • Partielle Updates bleiben bestehen                        │
│  • Nächster Tier holt verpasste Informationen nach           │
│  • Alle Fehler werden geloggt, nie zum User propagiert       │
│                                                              │
│  KOSTEN (geschätzt pro Update):                              │
│  • Input: ~3.000-6.000 Tokens (History + Prompt + Files)     │
│  • Output: ~1.000-3.000 Tokens (Tool-Calls + File-Content)  │
│  • Dauer: 3-10 Sekunden                                     │
│  • Häufigkeit: Max 3x pro Konversation                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```
