"""
Migrator – .txt → JSON Migration.

Konvertiert bestehende .txt-Prompt-Dateien in das neue JSON-Format.
Erstellt Manifest, Domain-Dateien und Placeholder-Registry.

Usage:
    python -m src.utils.prompt_engine.migrator
    
    Oder programmatisch:
    from utils.prompt_engine.migrator import PromptMigrator
    migrator = PromptMigrator()
    migrator.migrate()
"""

import os
import re
import json
import shutil
from typing import Dict, Any, List, Tuple
from datetime import datetime


class PromptMigrator:
    """Migriert .txt-Prompt-Dateien zu JSON-Format."""

    # Bekannte Placeholder die konvertiert werden: {key} → {{key}}
    KNOWN_PLACEHOLDERS = {
        'char_name', 'user_name', 'language', 'char_description',
        'current_date', 'current_time', 'current_weekday',
        'user_type', 'user_type_description', 'user_info',
        'elapsed_time', 'inner_dialogue', 'input',
        'experimental_01', 'experimental_02', 'experimental_03',
        'prompt_id_3', 'memory_entries'
    }

    # Mapping: .txt Datei → (prompt_id, domain_file, variante)
    MIGRATION_MAP = {
        # instructions/system/main/
        'main/impersonation.txt': ('impersonation', 'chat.json', 'default'),
        'main/system_rule.txt': ('system_rule', 'chat.json', 'default'),
        'main/char_description_default.txt': ('persona_description', 'chat.json', 'default'),
        'main/char_description_experimental.txt': ('persona_description', 'chat.json', 'experimental'),
        'main/user_info.txt': ('user_info', 'chat.json', 'default'),
        'main/time_sense.txt': ('time_sense', 'chat.json', 'default'),
        'main/output_format.txt': ('output_format', 'chat.json', 'default'),
        'main/remember_default.txt': ('remember', 'prefill.json', 'default'),
        'main/remember.txt': ('remember', 'prefill.json', 'experimental'),
        'main/prefill_impersonation.txt': ('prefill_impersonation', 'prefill.json', 'experimental'),
        'main/afterthought_inner_dialogue.txt': ('afterthought_inner_dialogue', 'afterthought.json', 'default'),
        'main/afterthought_followup.txt': ('afterthought_followup', 'afterthought.json', 'default'),

        # instructions/system/summary/
        'summary/impersonation.txt': ('summary_impersonation', 'summary.json', 'default'),
        'summary/system_rule.txt': ('summary_system_rule', 'summary.json', 'default'),
        'summary/char_description.txt': ('summary_char_description', 'summary.json', 'default'),
        'summary/remember.txt': ('summary_remember', 'summary.json', 'default'),
        'summary/prefill_impersonation.txt': ('summary_prefill_impersonation', 'summary.json', 'default'),
    }

    def __init__(self, instructions_dir: str = None):
        """
        Args:
            instructions_dir: Pfad zum instructions/ Verzeichnis
        """
        if instructions_dir is None:
            src_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            instructions_dir = os.path.join(src_dir, 'instructions')

        self._instructions_dir = instructions_dir
        self._system_dir = os.path.join(instructions_dir, 'system')
        self._prompts_dir = os.path.join(instructions_dir, 'prompts')

    def convert_placeholders(self, text: str) -> str:
        """
        Konvertiert {placeholder} → {{placeholder}} für bekannte Keys.
        Unbekannte {x} bleiben unverändert (könnten JSON-Syntax sein).
        """
        def replacer(match):
            key = match.group(1)
            if key in self.KNOWN_PLACEHOLDERS:
                return '{{' + key + '}}'
            return match.group(0)  # Unknown: leave unchanged

        return re.sub(r'\{(\w+)\}', replacer, text)

    def migrate(self, dry_run: bool = False, backup: bool = True) -> Dict[str, Any]:
        """
        Führt die komplette Migration durch.

        Args:
            dry_run: Wenn True, werden keine Dateien geschrieben
            backup: Wenn True, werden .txt-Dateien als .txt.bak gesichert

        Returns:
            Dict mit Ergebnis: migrated_files, errors, warnings
        """
        result = {
            'migrated_files': [],
            'errors': [],
            'warnings': [],
            'skipped': [],
            'timestamp': datetime.now().isoformat()
        }

        # Check if already migrated
        manifest_path = os.path.join(self._prompts_dir, '_meta', 'prompt_manifest.json')
        if os.path.exists(manifest_path) and os.path.exists(self._prompts_dir):
            result['warnings'].append("JSON-Dateien existieren bereits. Migration wird übersprungen.")
            return result

        # Sammle alle .txt Inhalte
        domain_contents: Dict[str, Dict[str, Any]] = {}

        for txt_path, (prompt_id, domain_file, variant) in self.MIGRATION_MAP.items():
            full_path = os.path.join(self._system_dir, txt_path)

            if not os.path.exists(full_path):
                result['warnings'].append(f"Datei nicht gefunden: {txt_path}")
                result['skipped'].append(txt_path)
                continue

            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    raw_content = f.read().strip()

                # Placeholder konvertieren
                converted = self.convert_placeholders(raw_content)

                # In Domain-Struktur eintragen
                if domain_file not in domain_contents:
                    domain_contents[domain_file] = {}

                if prompt_id not in domain_contents[domain_file]:
                    domain_contents[domain_file][prompt_id] = {
                        'variants': {},
                        'placeholders_used': []
                    }

                domain_contents[domain_file][prompt_id]['variants'][variant] = {
                    'content': converted
                }

                # Placeholder extrahieren
                found_placeholders = set(re.findall(r'\{\{(\w+)\}\}', converted))
                existing = set(domain_contents[domain_file][prompt_id]['placeholders_used'])
                domain_contents[domain_file][prompt_id]['placeholders_used'] = sorted(
                    existing | found_placeholders
                )

                result['migrated_files'].append(txt_path)

                # Backup erstellen
                if backup and not dry_run:
                    bak_path = full_path + '.bak'
                    if not os.path.exists(bak_path):
                        shutil.copy2(full_path, bak_path)

            except Exception as e:
                result['errors'].append(f"Fehler bei {txt_path}: {e}")

        # Consent Dialog migrieren
        try:
            consent_path = os.path.join(self._system_dir, 'main', 'consent_dialog.json')
            if os.path.exists(consent_path):
                with open(consent_path, 'r', encoding='utf-8') as f:
                    consent_data = json.load(f)

                domain_contents.setdefault('consent_dialog.json', {})
                domain_contents['consent_dialog.json']['consent_dialog'] = {
                    'variants': {
                        'experimental': {
                            'messages': consent_data
                        }
                    },
                    'placeholders_used': []
                }
                result['migrated_files'].append('main/consent_dialog.json')
        except Exception as e:
            result['errors'].append(f"Fehler bei consent_dialog.json: {e}")

        if dry_run:
            return result

        # Erstelle prompts/ Verzeichnis
        os.makedirs(self._prompts_dir, exist_ok=True)

        # Domain-Dateien schreiben
        for domain_file, content in domain_contents.items():
            try:
                filepath = os.path.join(self._prompts_dir, domain_file)
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(content, f, ensure_ascii=False, indent=2)
            except Exception as e:
                result['errors'].append(f"Fehler beim Schreiben von {domain_file}: {e}")

        return result

    def verify_parity(self, prompt_id: str, variant: str,
                       old_content: str, new_content: str) -> bool:
        """
        Vergleicht alten und neuen Prompt-Content nach Whitespace-Normalisierung.

        Returns:
            True wenn identisch
        """
        def normalize(text: str) -> str:
            text = re.sub(r'\s+', ' ', text).strip()
            return text

        return normalize(old_content) == normalize(new_content)


if __name__ == '__main__':
    """Standalone-Ausführung für einmalige Migration."""
    import sys

    migrator = PromptMigrator()

    # Erst Dry-Run
    print("=== DRY RUN ===")
    result = migrator.migrate(dry_run=True)
    print(f"  Migriert: {len(result['migrated_files'])} Dateien")
    print(f"  Fehler: {len(result['errors'])}")
    print(f"  Warnungen: {len(result['warnings'])}")
    print(f"  Übersprungen: {len(result['skipped'])}")

    for warning in result['warnings']:
        print(f"  WARNUNG: {warning}")
    for error in result['errors']:
        print(f"  FEHLER: {error}")

    if result['errors']:
        print("\nMigration abgebrochen wegen Fehlern.")
        sys.exit(1)

    # Richtige Migration
    print("\n=== MIGRATION ===")
    result = migrator.migrate(dry_run=False, backup=True)

    print(f"\n✓ {len(result['migrated_files'])} Dateien migriert")
    if result['errors']:
        print(f"✗ {len(result['errors'])} Fehler:")
        for err in result['errors']:
            print(f"  - {err}")
    if result['warnings']:
        print(f"! {len(result['warnings'])} Warnungen:")
        for warn in result['warnings']:
            print(f"  - {warn}")
