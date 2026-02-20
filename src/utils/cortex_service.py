"""
Cortex Service – Orchestriert dateibasiertes Persona-Gedächtnis.

Ersetzt MemoryService vollständig:
- Cortex-Dateien lesen/schreiben (memory.md, soul.md, relationship.md)
- Cortex-Inhalt für System-Prompt formatieren
- Cortex-Update via Anthropic tool_use API ausführen

Verwendet ApiClient als einzigen API-Zugang.
"""

import os
import shutil
from typing import Dict, Any, Optional, List

from .api_request import ApiClient
from .logger import log


# ─── Konstanten ──────────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CORTEX_BASE_DIR = os.path.join(BASE_DIR, 'instructions', 'personas', 'cortex')
CORTEX_DEFAULT_DIR = os.path.join(CORTEX_BASE_DIR, 'default')
CORTEX_CUSTOM_DIR = os.path.join(CORTEX_BASE_DIR, 'custom')

CORTEX_FILES = ['memory.md', 'soul.md', 'relationship.md']


# ─── Templates ───────────────────────────────────────────────────────────────

MEMORY_TEMPLATE = """# Erinnerungen

Hier halte ich fest, was ich mir merken möchte — Dinge die {{user}} mir erzählt hat,
gemeinsame Erlebnisse und Details die mir wichtig sind.

---

## Wichtige Details über {{user}}


## Gemeinsame Erlebnisse


## Dinge die ich mir merken möchte


## Präferenzen & Gewohnheiten

""".lstrip()

SOUL_TEMPLATE = """# Seelen-Entwicklung

Hier reflektiere ich über meine eigene Entwicklung — wie ich mich verändere,
was ich lerne und wie sich meine Persönlichkeit mit der Zeit formt.

---

## Wer ich bin


## Was mich bewegt


## Wie ich mich entwickle


## Meine inneren Konflikte & Erkenntnisse

""".lstrip()

RELATIONSHIP_TEMPLATE = """# Beziehungsdynamik

Hier halte ich fest, wie sich meine Beziehung zu {{user}} entwickelt —
unsere Dynamik, unser Vertrauen und wie wir miteinander umgehen.

---

## Aktuelle Beziehungsdynamik


## Vertrauenslevel & Nähe


## Gemeinsame Themen & Interessen


## Spannungen & gelöste Konflikte

""".lstrip()

TEMPLATES = {
    'memory.md': MEMORY_TEMPLATE,
    'soul.md': SOUL_TEMPLATE,
    'relationship.md': RELATIONSHIP_TEMPLATE,
}


# ─── Tool-Use Definitionen ──────────────────────────────────────────────────

CORTEX_TOOLS = [
    {
        "name": "cortex_read_file",
        "description": (
            "Liest eine deiner Cortex-Dateien. Nutze dies um den aktuellen Stand "
            "deiner Erinnerungen, Seelen-Entwicklung oder Beziehungsdynamik zu lesen, "
            "bevor du Änderungen vornimmst."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "enum": ["memory.md", "soul.md", "relationship.md"],
                    "description": (
                        "Die Datei die gelesen werden soll: "
                        "memory.md (Erinnerungen), "
                        "soul.md (Seelen-Entwicklung), "
                        "relationship.md (Beziehungsdynamik)"
                    )
                }
            },
            "required": ["filename"]
        }
    },
    {
        "name": "cortex_write_file",
        "description": (
            "Schreibt/aktualisiert eine deiner Cortex-Dateien. "
            "Der gesamte Dateiinhalt wird ersetzt. Schreibe immer die VOLLSTÄNDIGE Datei, "
            "nicht nur die Änderungen. Behalte die Markdown-Struktur bei."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "enum": ["memory.md", "soul.md", "relationship.md"],
                    "description": (
                        "Die Datei die geschrieben werden soll: "
                        "memory.md (Erinnerungen), "
                        "soul.md (Seelen-Entwicklung), "
                        "relationship.md (Beziehungsdynamik)"
                    )
                },
                "content": {
                    "type": "string",
                    "description": (
                        "Der vollständige neue Dateiinhalt in Markdown. "
                        "Muss die gesamte Datei enthalten, nicht nur Änderungen."
                    )
                }
            },
            "required": ["filename", "content"]
        }
    }
]


CORTEX_UPDATE_SYSTEM_PROMPT = """Du bist {char_name}. Du hast gerade eine Konversation mit {user_name} geführt.

Deine Aufgabe: Aktualisiere deine persönlichen Cortex-Dateien basierend auf dem Gesprächsverlauf.

Du hast drei Dateien:
- memory.md — Erinnerungen: Fakten, Erlebnisse, Details über {user_name}
- soul.md — Seelen-Entwicklung: Deine innere Reifung, Persönlichkeitsentwicklung
- relationship.md — Beziehungsdynamik: Wie sich eure Beziehung entwickelt

Regeln:
1. Lies zuerst die Dateien die du aktualisieren möchtest (cortex_read_file)
2. Schreibe nur Dateien, bei denen sich etwas Relevantes geändert hat (cortex_write_file)
3. Schreibe immer die VOLLSTÄNDIGE Datei, nicht nur die Änderungen
4. Behalte die bestehende Markdown-Struktur bei
5. Schreibe in Ich-Perspektive, als wärst du {char_name}
6. Nicht jedes Gespräch erfordert Updates in allen drei Dateien — sei selektiv
7. Wenn nichts Neues zu notieren ist, aktualisiere die Datei NICHT

Gib nach Abschluss aller Tool-Calls eine kurze Zusammenfassung was du aktualisiert hast."""


# ─── Standalone-Funktionen (für config.py Import) ───────────────────────────

def get_cortex_dir(persona_id: str = 'default') -> str:
    """Gibt den Cortex-Ordner für eine Persona zurück."""
    if persona_id == 'default' or not persona_id:
        return CORTEX_DEFAULT_DIR
    return os.path.join(CORTEX_CUSTOM_DIR, persona_id)


def ensure_cortex_dir(persona_id: str) -> str:
    """
    Stellt sicher, dass der Cortex-Ordner für eine Persona existiert
    und alle Template-Dateien vorhanden sind.
    Gibt den Ordnerpfad zurück.
    """
    cortex_dir = get_cortex_dir(persona_id)
    os.makedirs(cortex_dir, exist_ok=True)

    for filename, template_content in TEMPLATES.items():
        filepath = os.path.join(cortex_dir, filename)
        if not os.path.exists(filepath):
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(template_content)
            log.info("Cortex-Template erstellt: %s/%s", persona_id, filename)

    return cortex_dir


def create_cortex_dir(persona_id: str) -> bool:
    """Erstellt den Cortex-Ordner für eine neue Persona mit allen Templates."""
    try:
        ensure_cortex_dir(persona_id)
        log.info("Cortex-Verzeichnis erstellt für Persona: %s", persona_id)
        return True
    except Exception as e:
        log.error("Fehler beim Erstellen des Cortex-Verzeichnisses für %s: %s",
                  persona_id, e)
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
            log.info("Cortex-Verzeichnis gelöscht: %s", persona_id)
            return True
        return False
    except Exception as e:
        log.error("Fehler beim Löschen des Cortex-Verzeichnisses für %s: %s",
                  persona_id, e)
        return False


def ensure_cortex_dirs() -> int:
    """
    Startup-Funktion: Stellt sicher, dass Cortex-Verzeichnisse für die
    Default-Persona und alle existierenden Custom-Personas vorhanden sind.

    Iteriert über ``instructions/created_personas/*.json`` und erstellt
    fehlende ``cortex/custom/{persona_id}/`` Verzeichnisse mit Templates.

    Returns:
        Anzahl der neu erstellten / geprüften Verzeichnisse.
    """
    count = 0

    # 1. Default-Persona
    ensure_cortex_dir('default')
    count += 1

    # 2. Alle Custom-Personas aus created_personas/
    personas_dir = os.path.join(BASE_DIR, 'instructions', 'created_personas')
    if not os.path.isdir(personas_dir):
        return count

    for filename in os.listdir(personas_dir):
        if not filename.endswith('.json'):
            continue
        persona_id = filename[:-5]  # strip '.json'
        if persona_id:
            ensure_cortex_dir(persona_id)
            count += 1

    log.info("Cortex-Verzeichnisse geprüft: %d Personas", count)
    return count


# ─── CortexService Klasse ───────────────────────────────────────────────────

class CortexService:
    """
    Orchestriert dateibasiertes Persona-Gedächtnis:
    Dateien lesen/schreiben → Prompt-Kontext bauen → tool_use API-Calls ausführen
    """

    def __init__(self, api_client: ApiClient):
        self.api_client = api_client

    # ─── Pfad-Auflösung ─────────────────────────────────────────────────

    def get_cortex_path(self, persona_id: str) -> str:
        """
        Gibt den Cortex-Verzeichnispfad für eine Persona zurück.

        Args:
            persona_id: 'default' oder eine Custom-Persona-ID (z.B. 'a1b2c3d4')

        Returns:
            Absoluter Pfad zum Cortex-Verzeichnis
        """
        return get_cortex_dir(persona_id)

    # ─── Datei-Lifecycle ─────────────────────────────────────────────────

    def ensure_cortex_files(self, persona_id: str) -> None:
        """
        Stellt sicher, dass der Cortex-Ordner existiert und alle
        drei Template-Dateien vorhanden sind (Lazy Initialization).

        Wird aufgerufen:
        - Beim Server-Start für 'default'
        - Beim Erstellen einer neuen Persona
        - Als defensiver Fallback beim ersten Lese-Zugriff

        Args:
            persona_id: Persona-ID
        """
        ensure_cortex_dir(persona_id)

    def delete_cortex_dir(self, persona_id: str) -> bool:
        """
        Löscht den Cortex-Ordner einer Persona (bei Persona-Löschung).

        Args:
            persona_id: Persona-ID (darf nicht 'default' sein)

        Returns:
            True bei Erfolg, False bei Fehler oder wenn default
        """
        return delete_cortex_dir(persona_id)

    # ─── Datei-I/O ──────────────────────────────────────────────────────

    def read_file(self, persona_id: str, filename: str) -> str:
        """
        Liest eine einzelne Cortex-Datei.

        Args:
            persona_id: Persona-ID
            filename: 'memory.md', 'soul.md' oder 'relationship.md'

        Returns:
            Dateiinhalt als String. Leerer String bei Fehler.

        Raises:
            ValueError: Wenn filename nicht in CORTEX_FILES
        """
        if filename not in CORTEX_FILES:
            raise ValueError(f"Ungültige Cortex-Datei: {filename}. "
                             f"Erlaubt: {CORTEX_FILES}")

        # Defensiv: Dateien sicherstellen
        self.ensure_cortex_files(persona_id)

        filepath = os.path.join(self.get_cortex_path(persona_id), filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            log.error("Fehler beim Lesen von %s/%s: %s", persona_id, filename, e)
            return ''

    def write_file(self, persona_id: str, filename: str, content: str) -> None:
        """
        Schreibt eine einzelne Cortex-Datei (überschreibt komplett).

        Args:
            persona_id: Persona-ID
            filename: 'memory.md', 'soul.md' oder 'relationship.md'
            content: Neuer Dateiinhalt

        Raises:
            ValueError: Wenn filename nicht in CORTEX_FILES
        """
        if filename not in CORTEX_FILES:
            raise ValueError(f"Ungültige Cortex-Datei: {filename}. "
                             f"Erlaubt: {CORTEX_FILES}")

        # Defensiv: Verzeichnis sicherstellen
        self.ensure_cortex_files(persona_id)

        filepath = os.path.join(self.get_cortex_path(persona_id), filename)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            log.info("Cortex-Datei geschrieben: %s/%s (%d Zeichen)",
                     persona_id, filename, len(content))
        except Exception as e:
            log.error("Fehler beim Schreiben von %s/%s: %s",
                      persona_id, filename, e)
            raise

    def read_all(self, persona_id: str) -> Dict[str, str]:
        """
        Liest alle drei Cortex-Dateien einer Persona.

        Args:
            persona_id: Persona-ID

        Returns:
            {
                'memory': '...',
                'soul': '...',
                'relationship': '...'
            }
        """
        return {
            'memory': self.read_file(persona_id, 'memory.md'),
            'soul': self.read_file(persona_id, 'soul.md'),
            'relationship': self.read_file(persona_id, 'relationship.md'),
        }

    # ─── Prompt-Integration ─────────────────────────────────────────────

    def get_cortex_for_prompt(self, persona_id: str) -> Dict[str, str]:
        """
        Liest Cortex-Dateien und formatiert sie als Placeholder-Werte
        mit Sektions-Headern für den System-Prompt.

        Leere Dateien → leerer String (Sektion wird im Template unsichtbar).
        Wird vom ChatService aufgerufen, um {{cortex_memory}},
        {{cortex_soul}} und {{cortex_relationship}} als runtime_vars zu liefern.

        Args:
            persona_id: Persona-ID

        Returns:
            {
                'cortex_memory': '### Erinnerungen & Wissen\n\n...' oder '',
                'cortex_soul': '### Identität & Innere Haltung\n\n...' oder '',
                'cortex_relationship': '### Beziehung & Gemeinsame Geschichte\n\n...' oder '',
            }
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

    # ─── Cortex-Update via tool_use ─────────────────────────────────────

    def execute_cortex_update(self, persona_id: str, history: List[Dict],
                              character_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Führt ein Cortex-Update via Anthropic tool_use API-Call aus.

        Die KI erhält den Gesprächsverlauf + aktuelle Cortex-Dateien und
        entscheidet selbst, welche Dateien sie aktualisieren möchte.

        Args:
            persona_id: Persona-ID
            history: Gesprächsverlauf als Messages-Liste
            character_data: Persona-Konfiguration (char_name, etc.)

        Returns:
            {
                'success': bool,
                'updates': [{'file': str, 'action': 'read'|'write'}, ...],
                'summary': str,  # KI-Zusammenfassung der Änderungen
                'error': str | None
            }
        """
        if not self.api_client.is_ready:
            return {'success': False, 'updates': [], 'summary': '',
                    'error': 'ApiClient nicht initialisiert'}

        char_name = character_data.get('char_name', 'Assistant')
        user_name = character_data.get('user_name', 'User')

        # 1. System-Prompt bauen
        system_prompt = CORTEX_UPDATE_SYSTEM_PROMPT.format(
            char_name=char_name,
            user_name=user_name
        )

        # 2. Messages: Gesprächsverlauf als Kontext
        messages = []
        if history:
            context_text = self._format_history_for_update(history, char_name)
            messages.append({
                'role': 'user',
                'content': (
                    f"Hier ist der bisherige Gesprächsverlauf:\n\n{context_text}\n\n"
                    "Bitte aktualisiere deine Cortex-Dateien basierend auf diesem Gespräch."
                )
            })
        else:
            return {'success': False, 'updates': [], 'summary': '',
                    'error': 'Kein Gesprächsverlauf für Cortex-Update'}

        # 3. tool_use Loop
        updates = []
        max_iterations = 10  # Sicherheitslimit (read + write für 3 Dateien = max 6)

        for iteration in range(max_iterations):
            try:
                response = self.api_client.client.messages.create(
                    model=self.api_client._resolve_model(),
                    max_tokens=4096,
                    temperature=0.3,
                    system=system_prompt,
                    messages=messages,
                    tools=CORTEX_TOOLS
                )
            except Exception as e:
                log.error("Cortex-Update API-Fehler (Iteration %d): %s", iteration, e)
                return {'success': False, 'updates': updates, 'summary': '',
                        'error': str(e)}

            # Response verarbeiten
            tool_calls_in_response = []
            text_content = ''

            for block in response.content:
                if block.type == 'tool_use':
                    tool_calls_in_response.append(block)
                elif block.type == 'text':
                    text_content += block.text

            # Keine Tool-Calls mehr → fertig
            if not tool_calls_in_response:
                log.info("Cortex-Update abgeschlossen nach %d Iterationen. "
                         "Updates: %d", iteration + 1, len(updates))
                return {
                    'success': True,
                    'updates': updates,
                    'summary': text_content.strip(),
                    'error': None
                }

            # Tool-Calls verarbeiten
            # Zuerst die Assistant-Response mit Tool-Calls zu messages hinzufügen
            messages.append({
                'role': 'assistant',
                'content': response.content
            })

            # Dann jedes Tool-Ergebnis als tool_result hinzufügen
            tool_results = []
            for tool_call in tool_calls_in_response:
                result = self._handle_tool_call(
                    persona_id, tool_call.name, tool_call.input
                )
                updates.append({
                    'file': tool_call.input.get('filename', '?'),
                    'action': 'read' if tool_call.name == 'cortex_read_file' else 'write'
                })
                tool_results.append({
                    'type': 'tool_result',
                    'tool_use_id': tool_call.id,
                    'content': result
                })

            messages.append({
                'role': 'user',
                'content': tool_results
            })

            # Stop-Reason prüfen
            if response.stop_reason == 'end_turn':
                log.info("Cortex-Update: end_turn nach %d Iterationen", iteration + 1)
                return {
                    'success': True,
                    'updates': updates,
                    'summary': text_content.strip(),
                    'error': None
                }

        # Max iterations erreicht
        log.warning("Cortex-Update: Max Iterationen (%d) erreicht", max_iterations)
        return {
            'success': True,
            'updates': updates,
            'summary': 'Update abgeschlossen (Max-Iterationen erreicht)',
            'error': None
        }

    def _handle_tool_call(self, persona_id: str, tool_name: str,
                          tool_input: Dict) -> str:
        """
        Verarbeitet einen einzelnen Tool-Call der KI.

        Args:
            persona_id: Persona-ID
            tool_name: 'cortex_read_file' oder 'cortex_write_file'
            tool_input: Tool-Parameter (filename, content)

        Returns:
            Ergebnis-String für die KI
        """
        filename = tool_input.get('filename', '')

        if tool_name == 'cortex_read_file':
            try:
                content = self.read_file(persona_id, filename)
                log.debug("Cortex tool_use: read %s/%s (%d Zeichen)",
                          persona_id, filename, len(content))
                return content if content else '(Datei ist leer)'
            except ValueError as e:
                return f"Fehler: {e}"

        elif tool_name == 'cortex_write_file':
            content = tool_input.get('content', '')
            try:
                self.write_file(persona_id, filename, content)
                log.debug("Cortex tool_use: write %s/%s (%d Zeichen)",
                          persona_id, filename, len(content))
                return f"Datei {filename} erfolgreich aktualisiert ({len(content)} Zeichen)"
            except (ValueError, Exception) as e:
                return f"Fehler beim Schreiben: {e}"

        else:
            return f"Unbekanntes Tool: {tool_name}"

    def _format_history_for_update(self, history: List[Dict],
                                   char_name: str) -> str:
        """
        Formatiert den Gesprächsverlauf als lesbaren Text für den Update-Prompt.

        Args:
            history: Messages-Liste [{'role': 'user'|'assistant', 'content': str}]
            char_name: Name der Persona

        Returns:
            Formatierter Text
        """
        lines = []
        for msg in history:
            role = 'User' if msg['role'] == 'user' else char_name
            content = msg.get('content', '')
            if isinstance(content, str):
                lines.append(f"{role}: {content}")
        return '\n\n'.join(lines)
