"""
Loader – JSON-Dateien laden und validieren.

Lädt:
- _meta/prompt_manifest.json (Manifest mit Metadata)
- _meta/placeholder_registry.json (Placeholder-Definitionen)
- prompts/*.json (Domain-Dateien mit Content)

Fehler werden isoliert behandelt: Eine korrupte Domain-Datei 
deaktiviert nur diese Domain, nicht das ganze System.
"""

import os
import json
import tempfile
from typing import Dict, Any, Tuple, List
from ..logger import log


class PromptLoader:
    """Lädt alle JSON-Dateien für die PromptEngine."""

    def __init__(self, instructions_dir: str):
        """
        Args:
            instructions_dir: Pfad zum instructions/ Verzeichnis
        """
        self._instructions_dir = instructions_dir
        self._prompts_dir = os.path.join(instructions_dir, 'prompts')
        self._meta_dir = os.path.join(self._prompts_dir, '_meta')
        self._manifest_path = os.path.join(self._meta_dir, 'prompt_manifest.json')
        self._user_manifest_path = os.path.join(self._meta_dir, 'user_manifest.json')
        self._registry_path = os.path.join(self._meta_dir, 'placeholder_registry.json')
        self._user_registry_path = os.path.join(self._meta_dir, 'user_placeholder_registry.json')

    @property
    def manifest_path(self) -> str:
        return self._manifest_path

    @property
    def user_manifest_path(self) -> str:
        return self._user_manifest_path

    @property
    def registry_path(self) -> str:
        return self._registry_path

    @property
    def user_registry_path(self) -> str:
        return self._user_registry_path

    @property
    def instructions_dir(self) -> str:
        return self._instructions_dir

    def load_manifest(self) -> Dict[str, Any]:
        """
        Lädt prompt_manifest.json.

        Returns:
            Manifest-Dict mit 'version' und 'prompts'

        Raises:
            FileNotFoundError: Wenn Manifest nicht existiert
            json.JSONDecodeError: Wenn JSON ungültig
        """
        return self._load_json(self._manifest_path, "prompt_manifest.json")

    def load_user_manifest(self) -> Dict[str, Any]:
        """Lädt user_manifest.json. Gibt leeres Manifest zurück wenn Datei nicht existiert.

        Returns:
            User-Manifest-Dict mit 'version' und 'prompts'
        """
        if not os.path.exists(self._user_manifest_path):
            return {'version': '2.0', 'prompts': {}}
        return self._load_json(self._user_manifest_path, "user_manifest.json")

    def load_registry(self) -> Dict[str, Any]:
        """
        Lädt placeholder_registry.json.

        Returns:
            Registry-Dict mit 'version' und 'placeholders'

        Raises:
            FileNotFoundError: Wenn Registry nicht existiert
            json.JSONDecodeError: Wenn JSON ungültig
        """
        return self._load_json(self._registry_path, "placeholder_registry.json")

    def load_user_registry(self) -> Dict[str, Any]:
        """Lädt user_placeholder_registry.json. Gibt leere Registry zurück wenn Datei nicht existiert.

        Returns:
            User-Registry-Dict mit 'version' und 'placeholders'
        """
        if not os.path.exists(self._user_registry_path):
            return {'version': '2.0', 'placeholders': {}}
        return self._load_json(self._user_registry_path, "user_placeholder_registry.json")

    def load_domain_file(self, filename: str) -> Dict[str, Any]:
        """
        Lädt eine einzelne Domain-Datei aus prompts/.

        Args:
            filename: Name der Domain-Datei (z.B. 'chat.json')

        Returns:
            Domain-Dict mit Prompt-Daten

        Raises:
            FileNotFoundError: Wenn Datei nicht existiert
            json.JSONDecodeError: Wenn JSON ungültig
        """
        filepath = os.path.join(self._prompts_dir, filename)
        return self._load_json(filepath, filename)

    def load_all_domains(self, manifest: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        """
        Lädt alle Domain-Dateien die im Manifest referenziert werden.

        Args:
            manifest: Das geladene Manifest

        Returns:
            Tuple von (domain_data_dict, error_list)
            domain_data_dict: {filename: content_dict}
            error_list: Liste von Fehlermeldungen
        """
        domains: Dict[str, Any] = {}
        errors: List[str] = []

        # Sammle alle referenzierten Domain-Dateien
        domain_files = set()
        for prompt_meta in manifest.get('prompts', {}).values():
            domain_file = prompt_meta.get('domain_file')
            if domain_file:
                domain_files.add(domain_file)

        # Lade jede Domain-Datei
        for filename in sorted(domain_files):
            try:
                domains[filename] = self.load_domain_file(filename)
                log.debug("Domain-Datei geladen: %s", filename)
            except FileNotFoundError:
                errors.append(f"Domain-Datei nicht gefunden: {filename}")
                log.warning("Domain-Datei nicht gefunden: %s", filename)
            except json.JSONDecodeError as e:
                errors.append(f"Domain-Datei ungültig: {filename} ({e})")
                log.error("JSON-Fehler in %s: %s", filename, e)
            except Exception as e:
                errors.append(f"Fehler beim Laden von {filename}: {e}")
                log.error("Unerwarteter Fehler beim Laden von %s: %s", filename, e)

        return domains, errors

    def _load_json(self, filepath: str, name: str) -> Dict[str, Any]:
        """Lädt eine JSON-Datei mit Fehlerbehandlung."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"{name} nicht gefunden: {filepath}")

        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)

    # ===== Schreiboperationen =====

    def save_domain_file(self, filename: str, data: Dict[str, Any]) -> None:
        """
        Speichert eine Domain-Datei atomar.

        Args:
            filename: Name der Domain-Datei
            data: Daten zum Speichern
        """
        filepath = os.path.join(self._prompts_dir, filename)
        self._atomic_json_write(filepath, data)

    def save_manifest(self, data: Dict[str, Any]) -> None:
        """Speichert das System-Manifest atomar."""
        self._atomic_json_write(self._manifest_path, data)

    def save_user_manifest(self, data: Dict[str, Any]) -> None:
        """Speichert das User-Manifest atomar."""
        self._atomic_json_write(self._user_manifest_path, data)

    def save_registry(self, data: Dict[str, Any]) -> None:
        """Speichert die System-Registry atomar."""
        self._atomic_json_write(self._registry_path, data)

    def save_user_registry(self, data: Dict[str, Any]) -> None:
        """Speichert die User-Registry atomar."""
        self._atomic_json_write(self._user_registry_path, data)

    def _atomic_json_write(self, filepath: str, data: Dict[str, Any]) -> None:
        """
        Schreibt JSON atomar: temp-file → os.replace().
        """
        dir_path = os.path.dirname(filepath)
        os.makedirs(dir_path, exist_ok=True)

        # Atomar schreiben
        try:
            with tempfile.NamedTemporaryFile(
                mode='w', suffix='.tmp', dir=dir_path,
                delete=False, encoding='utf-8'
            ) as tmp:
                json.dump(data, tmp, ensure_ascii=False, indent=2)
                tmp_path = tmp.name

            os.replace(tmp_path, filepath)
        except Exception:
            # Cleanup on error
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
            raise

    def file_exists(self, filename: str) -> bool:
        """Prüft ob eine Domain-Datei existiert."""
        return os.path.exists(os.path.join(self._prompts_dir, filename))

    def manifest_exists(self) -> bool:
        """Prüft ob das System-Manifest existiert."""
        return os.path.exists(self._manifest_path)

    def user_manifest_exists(self) -> bool:
        """Prüft ob das User-Manifest existiert."""
        return os.path.exists(self._user_manifest_path)

    def registry_exists(self) -> bool:
        """Prüft ob die System-Registry existiert."""
        return os.path.exists(self._registry_path)

    def user_registry_exists(self) -> bool:
        """Prüft ob die User-Registry existiert."""
        return os.path.exists(self._user_registry_path)
