"""
PromptEngine — File-basiertes Prompt-System mit Tool-Support.

Prompts als Markdown-Dateien in 2 Kategorien:
- core/     → Immer inline im System-Prompt
- internal/ → Nur intern (Afterthought, Cortex, Autofill)

Alle Persona-Dateien (journal + cortex) aus data/{persona_id}/cortex/
werden inline im System-Prompt geladen. write_file Tool für Journal-Updates.

Placeholder-Logik in placeholders.py, Cortex in cortex.py.
"""

import os
import json
import threading
from typing import Dict, Any, Optional, List

from ..logger import log
from ..cortex import MAX_CORTEX_FILE_SIZE
from .placeholders import PlaceholderMixin
from .cortex import CortexMixin


class PromptEngine(PlaceholderMixin, CortexMixin):
    """
    File-basierte PromptEngine.
    Liest .md Dateien, löst Placeholder auf, stellt File-Tool bereit.
    """

    # Known journal files that the AI can write in cortex/
    _JOURNAL_FILES = ['bonding.md', 'growth.md']
    # Cortex files (read-only, auto-updated)
    _CORTEX_FILENAMES = ['memory.md', 'soul.md', 'relationship.md']

    def __init__(self, instructions_dir: str = None):
        if instructions_dir is None:
            src_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            instructions_dir = os.path.join(src_dir, 'instructions')

        self._instructions_dir = instructions_dir
        self._prompts_dir = os.path.join(instructions_dir, 'prompts')
        self._lock = threading.RLock()
        self._static_cache: Dict[str, str] = {}
        self._char_data_cache = None
        self._load_errors: List[str] = []

        # Validate directories exist
        for subdir in ('core', 'internal'):
            path = os.path.join(self._prompts_dir, subdir)
            if not os.path.isdir(path):
                self._load_errors.append(f"Directory missing: {subdir}/")
                log.warning("Prompt directory missing: %s", path)

        if not self._load_errors:
            log.info("PromptEngine geladen: core=%d, internal=%d",
                     len(self._list_md_files('core')),
                     len(self._list_md_files('internal')))

    # ═══════════════════════════════════════════════════════════════
    # Properties
    # ═══════════════════════════════════════════════════════════════

    @property
    def is_loaded(self) -> bool:
        return os.path.isdir(os.path.join(self._prompts_dir, 'core'))

    @property
    def load_errors(self) -> List[str]:
        return list(self._load_errors)

    # ═══════════════════════════════════════════════════════════════
    # Core System Prompt (inline, always sent)
    # ═══════════════════════════════════════════════════════════════

    def build_core_system_prompt(self, variant: str = 'default',
                                  runtime_vars: Optional[Dict[str, str]] = None) -> str:
        """
        Baut den System-Prompt aus core/*.md + Persona-Dateien inline + File-Index.
        Alle Persona-Dateien (journal + cortex) werden direkt eingebettet.
        Wird bei JEDEM Chat-Request als system_prompt gesendet.
        """
        placeholders = self._compute_placeholders(runtime_vars)
        parts: List[str] = []

        # Core files (identity, persona, rules, soul, user)
        for filename in self._list_core_files(variant):
            content = self._read_and_resolve(
                os.path.join(self._prompts_dir, 'core', filename), placeholders)
            if content:
                parts.append(content)

        # All persona files inline (journal + cortex from data/{persona_id}/cortex/)
        persona_dir = self._get_persona_files_dir()
        if persona_dir:
            for filename in self._JOURNAL_FILES + self._CORTEX_FILENAMES:
                filepath = os.path.join(persona_dir, filename)
                if os.path.exists(filepath):
                    content = self._read_and_resolve(filepath, placeholders)
                    if content:
                        parts.append(content)

        file_index = self._build_file_index(variant)
        if file_index:
            parts.append(file_index)

        return self._clean_text("\n\n".join(parts))

    def _build_file_index(self, variant: str = 'default') -> str:
        """Baut den File-Index für den System-Prompt (nur write_file Hinweis)."""
        writable = self._JOURNAL_FILES
        if not writable:
            return ''

        lines = [
            "**YOUR JOURNAL FILES** (writable with write_file):",
        ]
        for f in writable:
            lines.append(f"- {f}")
        lines.append("")
        lines.append("Your journal and cortex files are loaded above.")
        lines.append("Only use write_file when you receive a [JOURNAL REMINDER].")
        lines.append("After write_file calls, ALWAYS reply with a text message.")

        return "\n".join(lines)

    # ═══════════════════════════════════════════════════════════════
    # Full System Prompt (all prompts inline, for internal use)
    # ═══════════════════════════════════════════════════════════════

    def build_full_system_prompt(self, variant: str = 'default',
                                  runtime_vars: Optional[Dict[str, str]] = None) -> str:
        """
        Baut den vollständigen System-Prompt (core/ + alle Persona-Dateien) inline.
        Für interne Nutzung: Afterthought, Cortex-Update-Context.
        """
        placeholders = self._compute_placeholders(runtime_vars)
        parts: List[str] = []

        # Core (alles Wissen)
        for filename in self._list_core_files(variant):
            content = self._read_and_resolve(
                os.path.join(self._prompts_dir, 'core', filename), placeholders)
            if content:
                parts.append(content)

        # All persona files (journal + cortex)
        persona_dir = self._get_persona_files_dir()
        if persona_dir:
            for filename in self._JOURNAL_FILES + self._CORTEX_FILENAMES:
                filepath = os.path.join(persona_dir, filename)
                if os.path.exists(filepath):
                    content = self._read_and_resolve(filepath, placeholders)
                    if content:
                        parts.append(content)

        return self._clean_text("\n\n".join(parts))

    def build_system_prompt(self, variant: str = 'default',
                            runtime_vars: Optional[Dict[str, str]] = None,
                            category_filter: str = None) -> str:
        """Backward-compatible: baut vollständigen System-Prompt.
        category_filter='cortex' → liest internal/cortex_update_system.md statt."""
        if category_filter == 'cortex':
            return self.read_internal('cortex_update_system', variant, runtime_vars)
        return self.build_full_system_prompt(variant, runtime_vars)

    # ═══════════════════════════════════════════════════════════════
    # File Tool (write_file for API)
    # ═══════════════════════════════════════════════════════════════

    def get_chat_tools(self, variant: str = 'default') -> List[Dict[str, Any]]:
        """Returns tool definitions (write_file only) for the chat API."""
        writable = self._JOURNAL_FILES
        if not writable:
            return []

        return [{
            "name": "write_file",
            "description": (
                "Update one of your journal files. Write the complete file content. "
                "Use this to track your growth, update relationship notes, "
                "or record observations. Write naturally — these are YOUR files."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "enum": list(writable),
                        "description": "Name of the file to update"
                    },
                    "content": {
                        "type": "string",
                        "description": "The complete new content for the file"
                    }
                },
                "required": ["filename", "content"]
            }
        }]

    def get_available_files(self, variant: str = 'default') -> List[Dict[str, str]]:
        """Returns list of writable journal files for the write_file tool."""
        return [
            {
                'filename': f,
                'description': f.replace('.md', '').replace('_', ' ').title()
            }
            for f in self._JOURNAL_FILES
        ]

    def read_prompt_file(self, filename: str, variant: str = 'default',
                          runtime_vars: Optional[Dict[str, str]] = None) -> str:
        """
        Reads a prompt file and resolves placeholders.
        Checks per-persona override first, then falls back to template.
        """
        placeholders = self._compute_placeholders(runtime_vars)

        if filename in ('cortex_memory.md', 'cortex_soul.md', 'cortex_relationship.md'):
            return self._read_cortex_file(filename, placeholders)

        filepath = self._resolve_dynamic_file(filename)
        if filepath is None or not os.path.exists(filepath):
            return f"File not found: {filename}"

        return self._read_and_resolve(filepath, placeholders)

    def write_prompt_file(self, filename: str, content: str,
                           variant: str = 'default') -> str:
        """Writes/updates a journal file for the current persona."""
        if filename.startswith('cortex_'):
            return "Cannot write cortex files here."

        if filename not in self._JOURNAL_FILES:
            return f"Unknown file: {filename}"

        if len(content) > MAX_CORTEX_FILE_SIZE:
            return (f"Content too long ({len(content)} chars). "
                    f"Maximum: {MAX_CORTEX_FILE_SIZE} chars.")

        persona_dir = self._get_persona_files_dir()
        if not persona_dir:
            return "Cannot determine persona context."

        os.makedirs(persona_dir, exist_ok=True)
        filepath = os.path.join(persona_dir, filename)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            log.info("Dynamic file written: %s (%d chars)", filename, len(content))
            return f"Successfully updated {filename}"
        except Exception as e:
            log.warning("Failed to write %s: %s", filename, e)
            return f"Write failed: {e}"

    # ═══════════════════════════════════════════════════════════════
    # Internal Prompts (not exposed via tool)
    # ═══════════════════════════════════════════════════════════════

    def read_internal(self, name: str, variant: str = 'default',
                       runtime_vars: Optional[Dict[str, str]] = None) -> str:
        """Reads an internal prompt file by name (without .md extension)."""
        placeholders = self._compute_placeholders(runtime_vars)

        if variant != 'default':
            variant_path = os.path.join(
                self._prompts_dir, 'internal', f"{name}.{variant}.md")
            if os.path.exists(variant_path):
                return self._read_and_resolve(variant_path, placeholders)

        filepath = os.path.join(self._prompts_dir, 'internal', f"{name}.md")
        if not os.path.exists(filepath):
            log.warning("Internal prompt not found: %s", name)
            return ''
        return self._read_and_resolve(filepath, placeholders)

    def read_internal_json(self, name: str) -> Dict[str, Any]:
        """Reads an internal JSON file (e.g. cortex_update_tools)."""
        filepath = os.path.join(self._prompts_dir, 'internal', f"{name}.json")
        if not os.path.exists(filepath):
            return {}
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            log.warning("Internal JSON read failed: %s — %s", name, e)
            return {}

    # ═══════════════════════════════════════════════════════════════
    # Convenience Methods (backward compat + feature-specific)
    # ═══════════════════════════════════════════════════════════════

    def build_prefill(self, variant: str = 'default',
                       runtime_vars: Optional[Dict[str, str]] = None,
                       **kwargs) -> str:
        return self.read_internal('remember', variant, runtime_vars)

    def build_afterthought_inner_dialogue(self, variant: str = 'default',
                                           runtime_vars: Optional[Dict[str, str]] = None) -> str:
        return self.read_internal('afterthought_inner_dialogue', variant, runtime_vars)

    def build_afterthought_followup(self, variant: str = 'default',
                                     runtime_vars: Optional[Dict[str, str]] = None) -> str:
        return self.read_internal('afterthought_followup', variant, runtime_vars)

    def get_system_prompt_append(self, variant: str = 'default',
                                  runtime_vars: Optional[Dict[str, str]] = None) -> str:
        return self.read_internal('afterthought_system_note', variant, runtime_vars)

    def resolve_prompt(self, prompt_id: str, variant: str = 'default',
                        runtime_vars: Optional[Dict[str, str]] = None) -> Optional[str]:
        """Backward-compat: resolves a prompt by ID. Checks internal/."""
        result = self.read_internal(prompt_id, variant, runtime_vars)
        if result:
            return result
        return None

    def resolve_prompt_by_id(self, prompt_id: str, variant: str = 'default',
                              runtime_vars: Optional[Dict[str, str]] = None) -> str:
        result = self.resolve_prompt(prompt_id, variant, runtime_vars)
        if result is None:
            raise KeyError(f"Prompt '{prompt_id}' not found")
        return result

    def get_domain_data(self, prompt_id: str) -> Dict[str, Any]:
        name = prompt_id.replace('.json', '')
        return self.read_internal_json(name)

    def resolve_text(self, text: str,
                      runtime_vars: Optional[Dict[str, str]] = None) -> str:
        """Resolves placeholders in arbitrary text."""
        if not text:
            return text
        placeholders = self._compute_placeholders(runtime_vars)
        return self._resolve(text, placeholders)

    def get_dialog_injections(self, variant: str = 'default') -> List[Dict[str, str]]:
        return []

    def get_chat_message_sequence(self, variant: str = 'default') -> List[Dict[str, Any]]:
        return [
            {'position': 'first_assistant', 'order': 100},
            {'position': 'history', 'order': 200},
            {'position': 'prefill', 'order': 300},
        ]

    # ═══════════════════════════════════════════════════════════════
    # Cache Management
    # ═══════════════════════════════════════════════════════════════

    def invalidate_cache(self):
        """Clears placeholder cache (after persona switch, profile update)."""
        with self._lock:
            self._static_cache = {}
            self._char_data_cache = None

    def reload(self):
        """Reloads all data."""
        self.invalidate_cache()
        self._load_errors = []
        log.info("PromptEngine reloaded")

    # ═══════════════════════════════════════════════════════════════
    # File I/O Helpers
    # ═══════════════════════════════════════════════════════════════

    def _list_md_files(self, subdir: str) -> List[str]:
        """Lists .md files in a prompt subdirectory."""
        path = os.path.join(self._prompts_dir, subdir)
        if not os.path.isdir(path):
            return []
        return [f for f in os.listdir(path) if f.endswith('.md')]

    def _list_core_files(self, variant: str = 'default') -> List[str]:
        """Lists core .md files, handling experimental variants."""
        return self._list_variant_files('core', variant)

    def _list_variant_files(self, subdir: str, variant: str = 'default') -> List[str]:
        """Lists .md files with variant awareness (skips/swaps .experimental. files)."""
        result = []
        for filename in sorted(self._list_md_files(subdir)):
            if '.experimental.' in filename:
                if variant == 'experimental':
                    result.append(filename)
                continue
            # Check if experimental variant exists
            base = filename.rsplit('.', 1)[0]
            exp_file = f"{base}.experimental.md"
            if variant == 'experimental' and os.path.exists(
                os.path.join(self._prompts_dir, subdir, exp_file)):
                continue  # Skip default, experimental was already added
            result.append(filename)
        return result

    def _read_file(self, filepath: str) -> str:
        """Reads a text file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            log.warning("Failed to read %s: %s", filepath, e)
            return ''

    # ═══════════════════════════════════════════════════════════════
    # Per-Persona Dynamic File Helpers
    # ═══════════════════════════════════════════════════════════════

    def _get_persona_files_dir(self) -> Optional[str]:
        """Returns per-persona files dir: data/{persona_id}/cortex/"""
        try:
            from ..database.connection import get_persona_dir
            from ..config import get_active_persona_id
            persona_id = get_active_persona_id()
            if not persona_id:
                return None
            return os.path.join(get_persona_dir(persona_id), 'cortex')
        except Exception:
            return None

    def _resolve_dynamic_file(self, filename: str) -> Optional[str]:
        """Resolves a journal file from the persona's cortex directory."""
        if filename not in self._JOURNAL_FILES:
            return None
        persona_dir = self._get_persona_files_dir()
        if persona_dir:
            persona_path = os.path.join(persona_dir, filename)
            if os.path.exists(persona_path):
                return persona_path
        return None

