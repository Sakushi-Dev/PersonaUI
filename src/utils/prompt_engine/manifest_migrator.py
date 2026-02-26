"""Einmalige Migration: Single Manifest → Dual Manifest (System + User).

Vergleicht das aktive prompt_manifest.json mit dem Factory-Default aus
_defaults/_meta/prompt_manifest.json. Prompt-IDs die im Default NICHT
vorkommen, werden als User-Prompts klassifiziert und in eine neue
user_manifest.json verschoben.

Die Migration läuft nur EINMAL – sobald user_manifest.json existiert
(auch wenn leer), wird needs_migration() == False.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Set

log = logging.getLogger(__name__)


class ManifestMigrator:
    """Migriert ein Single-Manifest-Setup zu Dual-Manifest (System + User)."""

    def __init__(self, instructions_dir: str):
        self._instructions_dir = instructions_dir
        self._prompts_dir = os.path.join(instructions_dir, 'prompts')
        self._meta_dir = os.path.join(self._prompts_dir, '_meta')

        # Aktives System-Manifest (wird zu reinem System-Manifest)
        self._manifest_path = os.path.join(self._meta_dir, 'prompt_manifest.json')
        # Neues User-Manifest
        self._user_manifest_path = os.path.join(self._meta_dir, 'user_manifest.json')
        # Factory default as ground truth for system prompt IDs
        self._defaults_manifest_path = os.path.join(
            self._prompts_dir, '_defaults', '_meta', 'prompt_manifest.json')

    def needs_migration(self) -> bool:
        """Prüft ob Migration nötig ist.

        Migration ist nötig wenn:
        1. user_manifest.json NICHT existiert
        2. UND das aktive Manifest Prompt-IDs enthält, die nicht im Default sind

        Returns:
            True wenn Migration durchgeführt werden sollte
        """
        # Wenn User-Manifest bereits existiert → keine Migration
        if os.path.isfile(self._user_manifest_path):
            return False

        # Wenn kein aktives Manifest existiert → keine Migration
        if not os.path.isfile(self._manifest_path):
            return False

        # If no default manifest exists → cannot compare
        if not os.path.isfile(self._defaults_manifest_path):
            log.warning("Factory-Default Manifest fehlt – Migration übersprungen")
            return False

        try:
            active_ids = self._load_prompt_ids(self._manifest_path)
            default_ids = self._load_prompt_ids(self._defaults_manifest_path)
            user_ids = active_ids - default_ids

            if user_ids:
                log.info("Migration nötig: %d User-Prompts gefunden (%s)",
                         len(user_ids), ', '.join(sorted(user_ids)))
                return True

            # Keine User-Prompts → trotzdem User-Manifest anlegen (leeres),
            # so that migration doesn't check again
            return False

        except Exception as e:
            log.error("Fehler bei Migration-Prüfung: %s", e)
            return False

    def migrate(self) -> Dict[str, Any]:
        """Führt die Migration durch.

        1. Backup des aktiven Manifests
        2. Klassifiziere Prompts (System vs User)
        3. Schreibe User-Prompts in user_manifest.json
        4. Entferne User-Prompts aus dem System-Manifest

        Returns:
            Dict mit {system_prompts, migrated_user_prompts, errors, backup_path}
        """
        result: Dict[str, Any] = {
            'system_prompts': 0,
            'migrated_user_prompts': 0,
            'errors': [],
            'backup_path': None
        }

        try:
            # 1. Aktives Manifest laden
            with open(self._manifest_path, 'r', encoding='utf-8') as f:
                active_manifest = json.load(f)

            # 2. Default-Manifest laden (Ground Truth)
            with open(self._defaults_manifest_path, 'r', encoding='utf-8') as f:
                default_manifest = json.load(f)

            default_ids = set(default_manifest.get('prompts', {}).keys())
            active_prompts = active_manifest.get('prompts', {})

            # 3. Backup erstellen
            backup_path = self._create_backup(active_manifest)
            result['backup_path'] = backup_path
            log.info("Migration-Backup erstellt: %s", backup_path)

            # 4. Klassifizieren
            system_prompts: Dict[str, Any] = {}
            user_prompts: Dict[str, Any] = {}

            for pid, meta in active_prompts.items():
                if pid in default_ids:
                    system_prompts[pid] = meta
                else:
                    user_prompts[pid] = meta

            result['system_prompts'] = len(system_prompts)
            result['migrated_user_prompts'] = len(user_prompts)

            # 5. User-Manifest schreiben
            user_manifest = {
                'version': active_manifest.get('version', '1'),
                'migrated_at': datetime.now().isoformat(),
                'prompts': user_prompts
            }
            self._write_json(self._user_manifest_path, user_manifest)
            log.info("User-Manifest erstellt mit %d Prompts", len(user_prompts))

            # 6. System-Manifest bereinigen (nur System-Prompts behalten)
            # We don't overwrite with default, but keep
            # the active metadata (e.g. changed order values)
            active_manifest['prompts'] = system_prompts
            self._write_json(self._manifest_path, active_manifest)
            log.info("System-Manifest bereinigt: %d Prompts", len(system_prompts))

        except Exception as e:
            error_msg = f"Migration fehlgeschlagen: {e}"
            result['errors'].append(error_msg)
            log.error(error_msg)

        return result

    def ensure_user_manifest_exists(self) -> None:
        """Stellt sicher, dass ein User-Manifest existiert (mindestens leer).

        Wird aufgerufen wenn needs_migration() == False ist, aber das
        User-Manifest noch nicht existiert (Erstinstallation ohne User-Prompts).
        """
        if not os.path.isfile(self._user_manifest_path):
            empty_manifest = {'version': '1', 'prompts': {}}
            self._write_json(self._user_manifest_path, empty_manifest)
            log.info("Leeres User-Manifest erstellt (Erstinstallation)")

    # ===== Hilfsmethoden =====

    def _load_prompt_ids(self, manifest_path: str) -> Set[str]:
        """Lädt die Prompt-IDs aus einem Manifest."""
        with open(manifest_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return set(data.get('prompts', {}).keys())

    def _create_backup(self, manifest_data: Dict[str, Any]) -> str:
        """Erstellt ein Backup des Manifests vor der Migration."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = os.path.join(self._meta_dir, '_backups')
        os.makedirs(backup_dir, exist_ok=True)
        backup_path = os.path.join(backup_dir, f'pre_migration_{timestamp}.json')
        self._write_json(backup_path, manifest_data)
        return backup_path

    def _write_json(self, path: str, data: Dict[str, Any]) -> None:
        """Schreibt JSON atomar (write + flush)."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
