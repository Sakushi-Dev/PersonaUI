"""
CortexService — orchestrates file-based persona memory.

Read/write cortex files, build prompt context, execute cortex updates via tool_use API.
"""

import os
import tempfile
import threading
from typing import Dict

from ..api_request import ApiClient
from ..logger import log
from .constants import CORTEX_FILES, MAX_CORTEX_FILE_SIZE
from . import directories


class CortexService:
    """
    Orchestrates file-based persona memory:
    Read/write files → build prompt context → execute tool_use API calls.

    Features:
    - Atomic writes (tempfile + os.replace)
    - File size limit (MAX_CORTEX_FILE_SIZE)
    - In-memory cache with write-through (thread-safe)
    """

    def __init__(self, api_client: ApiClient):
        self.api_client = api_client
        self._cache: Dict[str, Dict[str, str]] = {}
        self._cache_lock = threading.Lock()

    # ─── Path Resolution ────────────────────────────────────────────────

    def get_cortex_path(self, persona_id: str) -> str:
        """Returns the cortex directory path for a persona."""
        return directories.get_cortex_dir(persona_id)

    # ─── File Lifecycle ─────────────────────────────────────────────────

    def ensure_cortex_files(self, persona_id: str) -> None:
        """Ensures cortex dir exists with all template files."""
        directories.ensure_cortex_dir(persona_id)

    def delete_cortex_dir(self, persona_id: str) -> bool:
        """Deletes cortex directory for a persona."""
        result = directories.delete_cortex_dir(persona_id)
        if result:
            with self._cache_lock:
                self._cache.pop(persona_id, None)
        return result

    # ─── File I/O ───────────────────────────────────────────────────────

    def read_file(self, persona_id: str, filename: str) -> str:
        """Reads a single cortex file. Returns empty string on error."""
        if filename not in CORTEX_FILES:
            raise ValueError(f"Ungültige Cortex-Datei: {filename}. "
                             f"Erlaubt: {CORTEX_FILES}")

        with self._cache_lock:
            cached = self._cache.get(persona_id, {}).get(filename)
            if cached is not None:
                return cached

        self.ensure_cortex_files(persona_id)

        filepath = os.path.join(self.get_cortex_path(persona_id), filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            with self._cache_lock:
                self._cache.setdefault(persona_id, {})[filename] = content
            return content
        except Exception as e:
            log.error("Fehler beim Lesen von %s/%s: %s", persona_id, filename, e)
            return ''

    def write_file(self, persona_id: str, filename: str, content: str) -> None:
        """Writes a single cortex file (atomic replace)."""
        if filename not in CORTEX_FILES:
            raise ValueError(f"Ungültige Cortex-Datei: {filename}. "
                             f"Erlaubt: {CORTEX_FILES}")

        original_len = len(content)
        if original_len > MAX_CORTEX_FILE_SIZE:
            content = content[:MAX_CORTEX_FILE_SIZE]
            log.warning(
                "Cortex-Datei gekürzt: %s/%s — %d → %d Zeichen",
                persona_id, filename, original_len, MAX_CORTEX_FILE_SIZE
            )

        self.ensure_cortex_files(persona_id)

        filepath = os.path.join(self.get_cortex_path(persona_id), filename)
        dir_path = os.path.dirname(filepath)

        fd = None
        tmp_path = None
        try:
            fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix='.tmp')
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                fd = None
                f.write(content)
            os.replace(tmp_path, filepath)
            tmp_path = None

            with self._cache_lock:
                self._cache.setdefault(persona_id, {})[filename] = content

            log.info("Cortex-Datei geschrieben: %s/%s (%d Zeichen)",
                     persona_id, filename, len(content))
        except Exception as e:
            log.error("Fehler beim Schreiben von %s/%s: %s",
                      persona_id, filename, e)
            raise
        finally:
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    def read_all(self, persona_id: str) -> Dict[str, str]:
        """Reads all three cortex files for a persona."""
        return {
            'memory': self.read_file(persona_id, 'memory.md'),
            'soul': self.read_file(persona_id, 'soul.md'),
            'relationship': self.read_file(persona_id, 'relationship.md'),
        }

    # ─── Prompt Integration ─────────────────────────────────────────────

    def get_cortex_for_prompt(self, persona_id: str) -> Dict[str, str]:
        """Reads cortex files and formats them as placeholder values with section headers."""
        files = self.read_all(persona_id)

        def _wrap_section(content: str, header: str) -> str:
            stripped = content.strip()
            if not stripped:
                return ''
            return f"### {header}\n\n{stripped}"

        return {
            'cortex_memory': _wrap_section(
                files['memory'], 'Memories & Knowledge'
            ),
            'cortex_soul': _wrap_section(
                files['soul'], 'Identity & Inner Self'
            ),
            'cortex_relationship': _wrap_section(
                files['relationship'], 'Relationship & Shared History'
            ),
        }
