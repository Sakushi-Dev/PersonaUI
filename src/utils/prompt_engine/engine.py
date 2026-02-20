"""
PromptEngine – Haupt-Engine-Klasse.

Reine Python-Library – kein Flask, kein PyWebView.
Liest JSON-Dateien, löst Placeholder auf, gibt fertige Strings zurück.

Usage:
    engine = PromptEngine()
    system_prompt = engine.build_system_prompt(variant='default', runtime_vars={...})
    prefill = engine.build_prefill(variant='default', runtime_vars={...})
"""

import os
import re
import json
import shutil
import tempfile
import threading
import zipfile
from datetime import datetime
from typing import Dict, Any, Optional, List

from .loader import PromptLoader
from .placeholder_resolver import PlaceholderResolver
from .validator import PromptValidator
from ..logger import log


class PromptEngine:
    """
    Reine Python-Library – kein Flask, kein PyWebView.
    Liest JSON-Dateien, löst Placeholder auf, gibt fertige Strings zurück.
    """

    def __init__(self, instructions_dir: str = None):
        """
        Lädt Manifest, Domain-Dateien und Placeholder-Registry.

        Args:
            instructions_dir: Pfad zum instructions/ Verzeichnis.
                              Default: src/instructions/ (relativ zum Modul-Pfad)
        """
        if instructions_dir is None:
            # Standard-Pfad: src/instructions/
            src_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            instructions_dir = os.path.join(src_dir, 'instructions')

        self._instructions_dir = instructions_dir
        self._lock = threading.RLock()

        # Submodule
        self._loader = PromptLoader(instructions_dir)
        self._validator = PromptValidator()

        # Daten
        self._manifest: Dict[str, Any] = {}          # Merged View (System + User)
        self._system_manifest: Dict[str, Any] = {}   # System-Manifest (Git-tracked)
        self._user_manifest: Dict[str, Any] = {}     # User-Manifest (Gitignored)
        self._user_prompt_ids: set = set()            # IDs die dem User-Manifest gehören
        self._domains: Dict[str, Any] = {}
        self._registry: Dict[str, Any] = {}           # Merged View (System + User)
        self._system_registry: Dict[str, Any] = {}    # System-Registry (Git-tracked)
        self._user_registry: Dict[str, Any] = {}      # User-Registry (Gitignored)
        self._user_placeholder_keys: set = set()      # Keys die der User-Registry gehören
        self._resolver: Optional[PlaceholderResolver] = None
        self._load_errors: List[str] = []

        # Initial laden
        self._load_all()

    def _load_all(self):
        """Lädt alle Dateien. Thread-safe."""
        with self._lock:
            self._load_errors = []

            # 0. Migration prüfen (einmalig: single manifest → dual manifest)
            from .manifest_migrator import ManifestMigrator
            migrator = ManifestMigrator(self._instructions_dir)
            if migrator.needs_migration():
                log.info("Manifest-Migration erforderlich \u2013 starte Split...")
                migration_result = migrator.migrate()
                if migration_result.get('errors'):
                    self._load_errors.extend(migration_result['errors'])
                else:
                    log.info("Migration abgeschlossen: %d System, %d User Prompts",
                             migration_result.get('system_prompts', 0),
                             migration_result.get('migrated_user_prompts', 0))
            else:
                # Erstinstallation oder bereits migriert – leeres User-Manifest anlegen
                migrator.ensure_user_manifest_exists()

            try:
                # 1a. System-Manifest laden (Git-tracked)
                self._system_manifest = self._loader.load_manifest()
                log.debug("System-Manifest geladen (Version %s)",
                          self._system_manifest.get('version'))
            except Exception as e:
                self._load_errors.append(f"System-Manifest: {e}")
                log.error("System-Manifest konnte nicht geladen werden: %s", e)
                self._system_manifest = {'version': '0', 'prompts': {}}

            try:
                # 1b. User-Manifest laden (gitignored, fehlt beim First Start)
                self._user_manifest = self._loader.load_user_manifest()
                user_count = len(self._user_manifest.get('prompts', {}))
                if user_count:
                    log.debug("User-Manifest geladen (%d Prompts)", user_count)
            except Exception as e:
                self._load_errors.append(f"User-Manifest: {e}")
                log.warning("User-Manifest konnte nicht geladen werden: %s", e)
                self._user_manifest = {'version': '2.0', 'prompts': {}}

            # 1c. Merged Manifest erstellen
            self._manifest = self._merge_manifests()

            try:
                # 2a. System-Registry laden (Git-tracked)
                self._system_registry = self._loader.load_registry()
                log.debug("System-Registry geladen (Version %s)",
                          self._system_registry.get('version'))
            except Exception as e:
                self._load_errors.append(f"System-Registry: {e}")
                log.error("Placeholder-Registry konnte nicht geladen werden: %s", e)
                self._system_registry = {'version': '2.0', 'placeholders': {}}

            try:
                # 2b. User-Registry laden (gitignored, fehlt beim First Start)
                self._user_registry = self._loader.load_user_registry()
                user_ph_count = len(self._user_registry.get('placeholders', {}))
                if user_ph_count:
                    log.debug("User-Registry geladen (%d Placeholders)", user_ph_count)
            except Exception as e:
                self._load_errors.append(f"User-Registry: {e}")
                log.warning("User-Registry konnte nicht geladen werden: %s", e)
                self._user_registry = {'version': '2.0', 'placeholders': {}}

            # 2c. Merged Registry erstellen
            self._registry = self._merge_registries()

            # 3. Domain-Dateien laden
            self._domains, domain_errors = self._loader.load_all_domains(self._manifest)
            self._load_errors.extend(domain_errors)

            # 4. Placeholder Resolver erstellen (mit merged registry)
            self._resolver = PlaceholderResolver(
                self._registry,
                self._instructions_dir
            )

            # 5. Validierung (nur Warnings loggen, keine Fehler werfen)
            validation = self._validator.validate_all(
                self._manifest, self._domains, self._registry
            )
            if validation['errors']:
                for err in validation['errors']:
                    log.warning("Validierungsfehler: %s", err)
                self._load_errors.extend(validation['errors'])
            if validation['warnings']:
                for warn in validation['warnings']:
                    log.debug("Validierungswarnung: %s", warn)

            prompt_count = len(self._manifest.get('prompts', {}))
            domain_count = len(self._domains)
            user_count = len(self._user_prompt_ids)
            ph_count = len(self._registry.get('placeholders', {}))
            user_ph_count = len(self._user_placeholder_keys)
            log.info(
                "PromptEngine geladen: %d Prompts (%d System, %d User), %d Domain-Dateien, %d Placeholders (%d System, %d User), %d Fehler",
                prompt_count, prompt_count - user_count, user_count,
                domain_count, ph_count, ph_count - user_ph_count, user_ph_count, len(self._load_errors)
            )

    def _merge_manifests(self) -> Dict[str, Any]:
        """Merged System- und User-Manifest zu einem einheitlichen View.

        Merge-Strategie:
        - System-Prompts sind die Basis
        - User-Prompts werden dar\u00fcber gelegt
        - Bei ID-Kollision: User gewinnt (User-Anpassung hat Vorrang)
        - self._user_prompt_ids wird f\u00fcr Write-Routing neu aufgebaut
        """
        merged = {
            'version': self._system_manifest.get('version', '0'),
            'prompts': {}
        }

        # System-Prompts als Basis
        system_prompts = self._system_manifest.get('prompts', {})
        for pid, meta in system_prompts.items():
            merged['prompts'][pid] = {**meta, 'source': 'system'}

        # User-Prompts dar\u00fcber (Override bei Kollision)
        user_prompts = self._user_manifest.get('prompts', {})
        for pid, meta in user_prompts.items():
            if pid in merged['prompts']:
                log.warning("ID-Kollision: '%s' in beiden Manifesten \u2013 User-Version gewinnt", pid)
            merged['prompts'][pid] = {**meta, 'source': meta.get('source', 'user')}

        # Tracking-Set f\u00fcr Write-Routing
        self._user_prompt_ids = set(user_prompts.keys())

        return merged

    def _merge_registries(self) -> Dict[str, Any]:
        """Merged System- und User-Registry zu einem einheitlichen View.

        Merge-Strategie:
        - System-Placeholders sind die Basis
        - User-Placeholders werden darüber gelegt
        - Bei Key-Kollision: User gewinnt (User-Anpassung hat Vorrang)
        - self._user_placeholder_keys wird für Write-Routing neu aufgebaut
        """
        merged = {
            'version': self._system_registry.get('version', '2.0'),
            'placeholders': {}
        }

        # System-Placeholders als Basis
        system_phs = self._system_registry.get('placeholders', {})
        for key, meta in system_phs.items():
            merged['placeholders'][key] = {**meta, '_origin': 'system'}

        # User-Placeholders darüber (Override bei Kollision)
        user_phs = self._user_registry.get('placeholders', {})
        for key, meta in user_phs.items():
            if key in merged['placeholders']:
                log.warning("Key-Kollision: '%s' in beiden Registries – User-Version gewinnt", key)
            merged['placeholders'][key] = {**meta, '_origin': 'user'}

        # Tracking-Set für Write-Routing
        self._user_placeholder_keys = set(user_phs.keys())

        return merged

    def _is_user_placeholder(self, key: str) -> bool:
        """Prüft ob ein Placeholder der User-Registry gehört."""
        return key in self._user_placeholder_keys

    def _is_user_prompt(self, prompt_id: str) -> bool:
        """Pr\u00fcft ob ein Prompt dem User-Manifest geh\u00f6rt."""
        return prompt_id in self._user_prompt_ids

    def _save_manifest_for_prompt(self, prompt_id: str) -> None:
        """Speichert in das richtige Manifest basierend auf Prompt-Zugeh\u00f6rigkeit."""
        meta = self._manifest.get('prompts', {}).get(prompt_id)
        if not meta:
            return

        # source-Feld nicht in die Datei schreiben (wird beim Merge gesetzt)
        clean_meta = {k: v for k, v in meta.items() if k != 'source'}

        if self._is_user_prompt(prompt_id):
            self._user_manifest.setdefault('prompts', {})[prompt_id] = clean_meta
            self._loader.save_user_manifest(self._user_manifest)
        else:
            self._system_manifest.setdefault('prompts', {})[prompt_id] = clean_meta
            self._loader.save_manifest(self._system_manifest)

    def reload(self):
        """Re-lädt alle JSON-Dateien von Disk. Thread-safe via Lock."""
        log.info("PromptEngine: Reload gestartet")
        if self._resolver:
            self._resolver.invalidate_cache()
        self._load_all()

    @property
    def is_loaded(self) -> bool:
        """True wenn Manifest und mindestens eine Domain geladen sind."""
        return bool(self._manifest.get('prompts')) and bool(self._domains)

    @property
    def load_errors(self) -> List[str]:
        """Gibt die Liste der Fehler beim Laden zurück."""
        return self._load_errors.copy()

    # ===== Prompt-Zugriff =====

    def get_all_prompts(self) -> Dict[str, Any]:
        """Alle registrierten Prompts mit Metadata (für Editor-Sidebar)."""
        return self._manifest.get('prompts', {}).copy()

    def get_prompt(self, prompt_id: str) -> Optional[Dict[str, Any]]:
        """Ein einzelner Prompt mit Content + Metadata."""
        meta = self._manifest.get('prompts', {}).get(prompt_id)
        if not meta:
            return None

        domain_file = meta.get('domain_file', '')
        domain_data = self._domains.get(domain_file, {})
        content_data = domain_data.get(prompt_id, {})

        return {
            'id': prompt_id,
            'meta': meta,
            'content': content_data
        }

    def get_prompts_by_target(self, target: str, category_filter: str = None) -> List[Dict[str, Any]]:
        """
        Alle Prompts für ein bestimmtes Target, sortiert nach Order.

        Args:
            target: Ziel (system_prompt, message, prefill)
            category_filter: Optionaler Kategorie-Filter

        Returns:
            Sortierte Liste von {id, meta, content} Dicts
        """
        result = []
        for prompt_id, meta in self._manifest.get('prompts', {}).items():
            if meta.get('target') != target:
                continue
            if not meta.get('enabled', True):
                continue
            if category_filter and meta.get('category') != category_filter:
                continue

            domain_file = meta.get('domain_file', '')
            domain_data = self._domains.get(domain_file, {})
            content_data = domain_data.get(prompt_id, {})

            result.append({
                'id': prompt_id,
                'meta': meta,
                'content': content_data
            })

        # Sortiere nach order
        result.sort(key=lambda x: x['meta'].get('order', 9999))
        return result

    def get_prompts_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Alle Prompts einer Kategorie."""
        result = []
        for prompt_id, meta in self._manifest.get('prompts', {}).items():
            if meta.get('category') == category:
                domain_file = meta.get('domain_file', '')
                domain_data = self._domains.get(domain_file, {})
                content_data = domain_data.get(prompt_id, {})
                result.append({
                    'id': prompt_id,
                    'meta': meta,
                    'content': content_data
                })
        result.sort(key=lambda x: x['meta'].get('order', 9999))
        return result

    # ===== Placeholder-Zugriff =====

    def get_all_placeholders(self) -> Dict[str, Any]:
        """Alle registrierten Placeholder (für Editor-Manager)."""
        return self._registry.get('placeholders', {}).copy()

    def get_current_values(self, variant: str = 'default',
                           runtime_vars: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Alle aufgelösten Placeholder-Werte (für Editor-Preview)."""
        if not self._resolver:
            return {}
        return self._resolver.get_all_values(variant, runtime_vars)

    # ===== Prompt-Building =====

    def build_system_prompt(self, variant: str = 'default',
                            runtime_vars: Optional[Dict[str, str]] = None,
                            category_filter: str = None) -> str:
        """
        Baut den System-Prompt aus allen aktiven Prompts
        mit target=system_prompt, sortiert nach order.

        Args:
            variant: Variante (default/experimental)
            runtime_vars: Runtime-Variablen
            category_filter: Optionaler Kategorie-Filter (z.B. 'summary')

        Returns:
            Der vollständige System-Prompt
        """
        prompts = self.get_prompts_by_target('system_prompt', category_filter)
        parts: List[str] = []

        # Kategorien die nur für spezifische Kontexte bestimmt sind
        # und NICHT in reguläre Chat-Prompts gehören
        NON_CHAT_CATEGORIES = {'summary', 'spec_autofill'}

        for prompt_data in prompts:
            meta = prompt_data['meta']
            position = meta.get('position', 'system_prompt')

            # system_prompt_append werden separat behandelt
            if position == 'system_prompt_append':
                continue

            # Wenn kein expliziter category_filter gesetzt ist,
            # nicht-chat Kategorien ausschließen (Summary, Spec-Autofill)
            if not category_filter and meta.get('category') in NON_CHAT_CATEGORIES:
                continue

            content = self._resolve_prompt_content(prompt_data, variant, runtime_vars)
            if content:
                parts.append(content)

        return "\n\n".join(parts)

    def get_system_prompt_append(self, variant: str = 'default',
                                  runtime_vars: Optional[Dict[str, str]] = None) -> str:
        """Gibt den System-Prompt-Append zurück (z.B. Afterthought-Note)."""
        prompts = self.get_prompts_by_target('system_prompt')
        parts: List[str] = []

        for prompt_data in prompts:
            meta = prompt_data['meta']
            if meta.get('position') != 'system_prompt_append':
                continue

            content = self._resolve_prompt_content(prompt_data, variant, runtime_vars)
            if content:
                parts.append(content)

        return "\n\n".join(parts)

    def build_prefill(self, variant: str = 'default',
                      runtime_vars: Optional[Dict[str, str]] = None,
                      category_filter: str = None) -> str:
        """Baut den Prefill aus allen aktiven Prompts mit target=prefill.

        Args:
            variant: Variante (default/experimental)
            runtime_vars: Runtime-Variablen
            category_filter: Optionaler Kategorie-Filter (z.B. 'summary')
        """
        prompts = self.get_prompts_by_target('prefill')
        parts: List[str] = []

        # Kategorien die nur für spezifische Kontexte bestimmt sind
        # und NICHT in reguläre Chat-Prefills gehören
        NON_CHAT_CATEGORIES = {'summary', 'spec_autofill'}

        for prompt_data in prompts:
            meta = prompt_data.get('meta', {})

            # Wenn kein expliziter category_filter gesetzt ist,
            # nicht-chat Kategorien ausschließen (Summary, Spec-Autofill)
            if not category_filter and meta.get('category') in NON_CHAT_CATEGORIES:
                continue

            # Wenn category_filter gesetzt ist, nur passende Kategorien einbeziehen
            if category_filter and meta.get('category') != category_filter:
                continue

            content = self._resolve_prompt_content(prompt_data, variant, runtime_vars)
            if content:
                parts.append(content)

        return "\n\n".join(parts)

    def get_first_assistant_content(self, variant: str = 'default',
                                     runtime_vars: Optional[Dict[str, str]] = None) -> str:
        """Baut den Content für die erste Assistant-Message."""
        prompts = self.get_prompts_by_target('message')
        parts: List[str] = []

        for prompt_data in prompts:
            meta = prompt_data['meta']
            if meta.get('position') != 'first_assistant':
                continue

            content = self._resolve_prompt_content(prompt_data, variant, runtime_vars)
            if content:
                parts.append(content)

        return "\n\n".join(parts)

    def get_chat_message_sequence(self, variant: str = 'default') -> List[Dict[str, Any]]:
        """
        Gibt die geordnete Positionen-Sequenz für Chat-Message-Assembly zurück.

        Sammelt message-Prompts (first_assistant, history) und prefill-Prompts
        für Chat-relevante Kategorien, sortiert nach order.

        Returns:
            Sortierte Liste von Dicts: {'id': str, 'position': str, 'order': int}
            Positionen: first_assistant, history, prefill
        """
        sequence: List[Dict[str, Any]] = []

        # Message-Prompts (first_assistant, history)
        for prompt_data in self.get_prompts_by_target('message'):
            meta = prompt_data['meta']
            position = meta.get('position', '')
            category = meta.get('category', '')

            # Nur chat-relevante Message-Prompts
            if category in ('afterthought', 'utility', 'summary'):
                continue

            variant_condition = meta.get('variant_condition')
            if variant_condition and variant_condition != variant:
                continue

            if position in ('first_assistant', 'history'):
                sequence.append({
                    'id': prompt_data['id'],
                    'position': position,
                    'order': meta.get('order', 9999),
                })

        # Prefill-Prompts (kein Summary)
        for prompt_data in self.get_prompts_by_target('prefill'):
            meta = prompt_data['meta']
            category = meta.get('category', '')

            if category == 'summary':
                continue

            variant_condition = meta.get('variant_condition')
            if variant_condition and variant_condition != variant:
                continue

            sequence.append({
                'id': prompt_data['id'],
                'position': 'prefill',
                'order': meta.get('order', 9999),
            })

        sequence.sort(key=lambda x: x['order'])
        return sequence

    def get_consent_dialog(self, variant: str = 'default') -> Optional[List[Dict[str, str]]]:
        """Gibt den Consent Dialog als Message-Array zurück, oder None.
        Backward-Compat-Wrapper für get_dialog_injections()."""
        injections = self.get_dialog_injections(variant)
        return injections if injections else None

    def get_dialog_injections(self, variant: str = 'default') -> List[Dict[str, str]]:
        """
        Sammelt alle aktiven Dialog-Injections (category=dialog_injection, type=multi_turn).
        Gibt eine flache Messages-Liste zurück, sortiert nach order.
        """
        all_messages: List[Dict[str, str]] = []

        for prompt_id, meta in sorted(
            self._manifest.get('prompts', {}).items(),
            key=lambda x: x[1].get('order', 9999)
        ):
            if meta.get('category') != 'dialog_injection':
                continue
            if not meta.get('enabled', True):
                continue
            if meta.get('type') != 'multi_turn':
                continue

            # variant_condition prüfen
            variant_condition = meta.get('variant_condition')
            if variant_condition and variant_condition != variant:
                continue

            domain_file = meta.get('domain_file', '')
            domain_data = self._domains.get(domain_file, {})
            content_data = domain_data.get(prompt_id, {})
            variants = content_data.get('variants', {})

            variant_data = variants.get(variant) or variants.get('default')
            if variant_data and 'messages' in variant_data:
                all_messages.extend(variant_data['messages'])

        return all_messages

    def resolve_prompt(self, prompt_id: str, variant: str = 'default',
                       runtime_vars: Optional[Dict[str, str]] = None) -> Optional[str]:
        """
        Löst einen einzelnen Prompt auf (Content + Placeholder).

        Args:
            prompt_id: ID des Prompts
            variant: Variante
            runtime_vars: Runtime-Variablen

        Returns:
            Aufgelöster Prompt-Text oder None
        """
        prompt_data = self.get_prompt(prompt_id)
        if not prompt_data:
            return None

        return self._resolve_prompt_content(prompt_data, variant, runtime_vars)

    def build_afterthought_inner_dialogue(self, variant: str = 'default',
                                           runtime_vars: Optional[Dict[str, str]] = None) -> Optional[str]:
        """Baut den Afterthought Inner Dialogue Prompt."""
        return self.resolve_prompt('afterthought_inner_dialogue', variant, runtime_vars)

    def build_afterthought_followup(self, variant: str = 'default',
                                     runtime_vars: Optional[Dict[str, str]] = None) -> Optional[str]:
        """Baut den Afterthought Followup Prompt."""
        return self.resolve_prompt('afterthought_followup', variant, runtime_vars)

    def build_spec_autofill_prompt(self, spec_type: str, input_text: str,
                                    variant: str = 'default') -> Optional[str]:
        """
        Baut einen Spec-Autofill Prompt.

        Args:
            spec_type: Typ (persona_type, core_trait, knowledge, scenario, expression_style)
            input_text: Input-Text für den Platzhalter
            variant: Variante

        Returns:
            Fertiger Prompt-String oder None
        """
        prompt_id = f'spec_autofill_{spec_type}'
        runtime_vars = {'input': input_text}
        return self.resolve_prompt(prompt_id, variant, runtime_vars)

    # ===== Interne Methoden =====

    def _resolve_prompt_content(self, prompt_data: Dict[str, Any],
                                 variant: str = 'default',
                                 runtime_vars: Optional[Dict[str, str]] = None) -> str:
        """
        Löst den Content eines Prompts auf (Variante + Placeholder).

        Logik:
        1. variant_condition prüfen (wenn gesetzt, muss Variante matchen)
        2. Variante wählen: erst spezifisch, dann 'default' Fallback
        3. Placeholder auflösen
        """
        meta = prompt_data.get('meta', {})
        content_data = prompt_data.get('content', {})

        # variant_condition: Prompt nur aktiv wenn Variante matcht
        variant_condition = meta.get('variant_condition')
        if variant_condition and variant_condition != variant:
            return ''

        # Variante wählen
        variants = content_data.get('variants', {})
        variant_data = variants.get(variant) or variants.get('default')
        if not variant_data:
            return ''

        # Content extrahieren
        prompt_type = meta.get('type', 'text')
        if prompt_type == 'text':
            raw_content = variant_data.get('content', '')
        elif prompt_type == 'multi_turn':
            # Multi-turn: Wird als JSON-String zurückgegeben
            return ''  # Multi-turn wird über get_consent_dialog() behandelt
        else:
            raw_content = variant_data.get('content', '')

        if not raw_content:
            return ''

        # Placeholder auflösen
        if self._resolver:
            return self._resolver.resolve_text(raw_content, variant, runtime_vars)
        return raw_content

    # ===== Mutation (für Editor) =====

    def save_prompt(self, prompt_id: str, data: Dict[str, Any]) -> bool:
        """Speichert einen Prompt (Content + Metadata). Atomarer Write."""
        with self._lock:
            try:
                meta = self._manifest.get('prompts', {}).get(prompt_id)
                if not meta:
                    log.error("Prompt '%s' nicht im Manifest gefunden", prompt_id)
                    return False

                domain_file = meta.get('domain_file', '')
                domain_data = self._domains.get(domain_file, {})

                # Content aktualisieren
                if 'content' in data:
                    domain_data[prompt_id] = data['content']
                    self._loader.save_domain_file(domain_file, domain_data)
                    self._domains[domain_file] = domain_data

                # Metadata aktualisieren
                if 'meta' in data:
                    self._manifest['prompts'][prompt_id].update(data['meta'])
                    self._save_manifest_for_prompt(prompt_id)

                return True
            except Exception as e:
                log.error("Fehler beim Speichern von Prompt '%s': %s", prompt_id, e)
                return False

    def create_prompt(self, data: Dict[str, Any]) -> Optional[str]:
        """Erstellt einen neuen Prompt, gibt ID zurück. Immer im User-Manifest."""
        with self._lock:
            try:
                prompt_id = data.get('id')
                if not prompt_id:
                    log.error("Neue Prompt-ID fehlt")
                    return None

                if prompt_id in self._manifest.get('prompts', {}):
                    log.error("Prompt-ID '%s' existiert bereits", prompt_id)
                    return None

                # Auto-generate domain_file if not specified
                meta = data.get('meta', {})
                if not meta.get('domain_file'):
                    meta['domain_file'] = f"{prompt_id}.json"
                    data['meta'] = meta

                # Neue Prompts gehen IMMER ins User-Manifest
                clean_meta = {k: v for k, v in meta.items() if k != 'source'}
                self._user_manifest.setdefault('prompts', {})[prompt_id] = clean_meta
                self._user_prompt_ids.add(prompt_id)
                self._loader.save_user_manifest(self._user_manifest)

                # Merged View aktualisieren
                self._manifest.setdefault('prompts', {})[prompt_id] = {**meta, 'source': 'user'}

                # Domain-Datei aktualisieren
                domain_file = meta.get('domain_file', '')
                if domain_file:
                    domain_data = self._domains.get(domain_file, {})
                    domain_data[prompt_id] = data.get('content', {})
                    self._loader.save_domain_file(domain_file, domain_data)
                    self._domains[domain_file] = domain_data

                return prompt_id
            except Exception as e:
                log.error("Fehler beim Erstellen von Prompt: %s", e)
                return None

    def delete_prompt(self, prompt_id: str) -> bool:
        """Löscht einen Prompt aus Manifest + Domain-Datei."""
        with self._lock:
            try:
                meta = self._manifest.get('prompts', {}).get(prompt_id)
                if not meta:
                    return False

                # System-Prompts können nicht gelöscht werden (nur deaktiviert)
                if not self._is_user_prompt(prompt_id):
                    log.warning("System-Prompt '%s' kann nicht gelöscht werden "
                                "(nur deaktivieren möglich)", prompt_id)
                    return False

                # Aus merged View entfernen
                self._manifest.get('prompts', {}).pop(prompt_id, None)

                # Aus User-Manifest entfernen
                self._user_manifest.get('prompts', {}).pop(prompt_id, None)
                self._user_prompt_ids.discard(prompt_id)
                self._loader.save_user_manifest(self._user_manifest)

                # Domain-Datei aufräumen
                domain_file = meta.get('domain_file', '')
                if domain_file and domain_file in self._domains:
                    self._domains[domain_file].pop(prompt_id, None)
                    remaining = self._domains[domain_file]
                    if not remaining:
                        # Domain file is now empty – remove from disk and cache
                        domain_path = os.path.join(self._instructions_dir, 'prompts', domain_file)
                        if os.path.isfile(domain_path):
                            os.remove(domain_path)
                        del self._domains[domain_file]
                    else:
                        self._loader.save_domain_file(domain_file, remaining)

                return True
            except Exception as e:
                log.error("Fehler beim Löschen von Prompt '%s': %s", prompt_id, e)
                return False

    def reorder_prompts(self, new_order: Dict[str, int]) -> bool:
        """Aktualisiert die Order-Werte. {prompt_id: new_order}."""
        with self._lock:
            try:
                system_changed = False
                user_changed = False

                for prompt_id, order_val in new_order.items():
                    if prompt_id in self._manifest.get('prompts', {}):
                        self._manifest['prompts'][prompt_id]['order'] = order_val
                        if self._is_user_prompt(prompt_id):
                            self._user_manifest['prompts'][prompt_id]['order'] = order_val
                            user_changed = True
                        elif prompt_id in self._system_manifest.get('prompts', {}):
                            self._system_manifest['prompts'][prompt_id]['order'] = order_val
                            system_changed = True

                if system_changed:
                    self._loader.save_manifest(self._system_manifest)
                if user_changed:
                    self._loader.save_user_manifest(self._user_manifest)
                return True
            except Exception as e:
                log.error("Fehler beim Reorder: %s", e)
                return False

    def update_placeholders_used(self, prompt_id: str, placeholders: List[str]) -> bool:
        """Aktualisiert die placeholders_used-Liste in der Domain-Datei."""
        with self._lock:
            try:
                meta = self._manifest.get('prompts', {}).get(prompt_id)
                if not meta:
                    log.error("Prompt '%s' nicht im Manifest gefunden", prompt_id)
                    return False

                domain_file = meta.get('domain_file', '')
                domain_data = self._domains.get(domain_file, {})
                prompt_data = domain_data.get(prompt_id, {})

                prompt_data['placeholders_used'] = sorted(set(placeholders))
                domain_data[prompt_id] = prompt_data
                self._loader.save_domain_file(domain_file, domain_data)
                self._domains[domain_file] = domain_data
                return True
            except Exception as e:
                log.error("Fehler beim Update von placeholders_used für '%s': %s", prompt_id, e)
                return False

    def toggle_prompt(self, prompt_id: str, enabled: bool) -> bool:
        """Aktiviert/Deaktiviert einen Prompt."""
        return self.save_prompt(prompt_id, {'meta': {'enabled': enabled}})

    def create_placeholder(self, key: str, data: Dict[str, Any]) -> bool:
        """Registriert einen neuen statischen Placeholder in der User-Registry.

        Args:
            key: Placeholder-Key (snake_case)
            data: Dict mit name, description, default, category
        """
        try:
            # Prüfen ob Key bereits existiert (in merged registry)
            if key in self._registry.get('placeholders', {}):
                log.error("Placeholder '%s' existiert bereits", key)
                return False

            # In User-Registry speichern
            user_placeholders = self._user_registry.setdefault('placeholders', {})
            user_placeholders[key] = {
                'name': data.get('name', key),
                'description': data.get('description', ''),
                'source': 'static',
                'type': 'string',
                'default': data.get('default', ''),
                'category': data.get('category', 'custom'),
                'resolve_phase': 'static',
            }

            self._loader.save_user_registry(self._user_registry)
            self.reload()
            log.info("Placeholder '%s' in User-Registry erstellt", key)
            return True
        except Exception as e:
            log.error("Fehler beim Erstellen von Placeholder '%s': %s", key, e)
            return False

    def delete_placeholder(self, key: str) -> bool:
        """Löscht einen Placeholder aus der Registry.

        Args:
            key: Placeholder-Key
        """
        try:
            # Prüfen ob existiert (in merged registry)
            placeholders = self._registry.get('placeholders', {})
            if key not in placeholders:
                log.error("Placeholder '%s' nicht gefunden", key)
                return False

            # Nur statische/custom Placeholder dürfen gelöscht werden
            ph = placeholders[key]
            if ph.get('source') not in ('static', 'custom', 'user'):
                log.error("Placeholder '%s' hat source='%s', nur static/custom/user können gelöscht werden",
                          key, ph.get('source'))
                return False

            # Aus der richtigen Registry löschen
            if self._is_user_placeholder(key):
                user_placeholders = self._user_registry.get('placeholders', {})
                if key in user_placeholders:
                    del user_placeholders[key]
                self._loader.save_user_registry(self._user_registry)
                log.info("Placeholder '%s' aus User-Registry gelöscht", key)
            else:
                system_placeholders = self._system_registry.get('placeholders', {})
                if key in system_placeholders:
                    del system_placeholders[key]
                self._loader.save_registry(self._system_registry)
                log.info("Placeholder '%s' aus System-Registry gelöscht", key)

            self.reload()
            return True
        except Exception as e:
            log.error("Fehler beim Löschen von Placeholder '%s': %s", key, e)
            return False

    # ===== Validierung =====

    def validate_prompt(self, prompt_data: Dict[str, Any]) -> List[str]:
        """Validiert einen einzelnen Prompt. Gibt Liste von Fehlern zurück."""
        # Erstelle ein Mini-Manifest/Domain für die Validierung
        errors: List[str] = []
        prompt_id = prompt_data.get('id', 'unknown')
        meta = prompt_data.get('meta', {})
        content = prompt_data.get('content', {})

        mini_manifest = {'prompts': {prompt_id: meta}}
        errors.extend(self._validator.validate_manifest(mini_manifest))

        if content:
            errors.extend(self._validator.validate_domain({prompt_id: content}, {prompt_id: meta}))

        return errors

    def validate_all(self) -> Dict[str, List[str]]:
        """Validiert alle Prompts + Placeholder-Verknüpfungen."""
        return self._validator.validate_all(self._manifest, self._domains, self._registry)

    def invalidate_cache(self):
        """Leert den Placeholder-Cache (z.B. bei Persona-Wechsel)."""
        if self._resolver:
            self._resolver.invalidate_cache()

    # ===== Export / Import / Factory-Reset =====

    def export_prompt_set(self, output_path: str) -> str:
        """Exportiert alle Prompts als ZIP-Archiv.

        Enthält:
        - _meta/prompt_manifest.json (System-Manifest)
        - _meta/user_manifest.json (User-Manifest, wenn vorhanden)
        - _meta/placeholder_registry.json
        - prompts/*.json (alle Domain-Dateien)
        - metadata.json (Export-Datum, Version, Prompt-Count)

        Args:
            output_path: Zielpfad für das ZIP-Archiv

        Returns:
            Pfad zur erstellten ZIP-Datei

        Raises:
            IOError: Wenn das Archiv nicht erstellt werden kann
        """
        with self._lock:
            # Sicherstellen dass Zielverzeichnis existiert
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                # System-Manifest
                manifest_path = self._loader.manifest_path
                if os.path.exists(manifest_path):
                    zf.write(manifest_path, '_meta/prompt_manifest.json')

                # User-Manifest (wenn vorhanden)
                user_manifest_path = self._loader.user_manifest_path
                if os.path.exists(user_manifest_path):
                    zf.write(user_manifest_path, '_meta/user_manifest.json')

                # Registry
                registry_path = self._loader.registry_path
                if os.path.exists(registry_path):
                    zf.write(registry_path, '_meta/placeholder_registry.json')

                # Domain-Dateien
                prompts_dir = os.path.join(self._instructions_dir, 'prompts')
                if os.path.isdir(prompts_dir):
                    for filename in os.listdir(prompts_dir):
                        if filename.endswith('.json'):
                            filepath = os.path.join(prompts_dir, filename)
                            if os.path.isfile(filepath):
                                zf.write(filepath, f'prompts/{filename}')

                # Metadata
                metadata = {
                    'export_date': datetime.now().isoformat(),
                    'version': self._manifest.get('version', 'unknown'),
                    'prompt_count': len(self._manifest.get('prompts', {})),
                    'domain_files': sorted(self._domains.keys()),
                    'placeholder_count': len(self._registry.get('placeholders', {})),
                }
                zf.writestr('metadata.json', json.dumps(metadata, ensure_ascii=False, indent=2))

            log.info("Prompt-Set exportiert nach: %s", output_path)
            return output_path

    def import_prompt_set(self, zip_path: str, merge_mode: str = 'replace') -> Dict[str, Any]:
        """Importiert ein Prompt-Set aus einem ZIP-Archiv.

        Args:
            zip_path: Pfad zum ZIP-Archiv
            merge_mode: Import-Modus:
                - 'replace': Komplett ersetzen (Factory-Reset-Stil)
                - 'merge': Fehlende ergänzen, bestehende behalten
                - 'overwrite': Fehlende ergänzen, bestehende überschreiben

        Returns:
            Dict mit {imported: int, skipped: int, errors: list}

        Raises:
            FileNotFoundError: Wenn ZIP nicht existiert
            ValueError: Wenn merge_mode ungültig
        """
        if merge_mode not in ('replace', 'merge', 'overwrite'):
            raise ValueError(f"Ungültiger merge_mode: {merge_mode} (erlaubt: replace, merge, overwrite)")

        if not os.path.exists(zip_path):
            raise FileNotFoundError(f"ZIP-Datei nicht gefunden: {zip_path}")

        result: Dict[str, Any] = {'imported': 0, 'skipped': 0, 'errors': []}

        with self._lock:
            try:
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    # Validierung: Manifest muss enthalten sein
                    names = zf.namelist()
                    if '_meta/prompt_manifest.json' not in names:
                        result['errors'].append("ZIP enthält kein _meta/prompt_manifest.json")
                        return result

                    if merge_mode == 'replace':
                        result = self._import_replace(zf)
                    elif merge_mode == 'merge':
                        result = self._import_merge(zf, overwrite=False)
                    elif merge_mode == 'overwrite':
                        result = self._import_merge(zf, overwrite=True)

                # Neu laden nach Import
                self.reload()
                log.info("Prompt-Set importiert (Modus: %s): %d importiert, %d übersprungen, %d Fehler",
                         merge_mode, result['imported'], result['skipped'], len(result['errors']))
            except zipfile.BadZipFile:
                result['errors'].append("Datei ist kein gültiges ZIP-Archiv")
            except Exception as e:
                result['errors'].append(f"Import-Fehler: {e}")
                log.error("Import fehlgeschlagen: %s", e)

        return result

    def _import_replace(self, zf: zipfile.ZipFile) -> Dict[str, Any]:
        """Import-Modus 'replace': Ersetzt alles komplett."""
        result: Dict[str, Any] = {'imported': 0, 'skipped': 0, 'errors': []}

        # System-Manifest ersetzen
        try:
            manifest_data = zf.read('_meta/prompt_manifest.json')
            json.loads(manifest_data)  # Validierung
            with open(self._loader.manifest_path, 'wb') as f:
                f.write(manifest_data)
            result['imported'] += 1
        except Exception as e:
            result['errors'].append(f"Manifest: {e}")

        # User-Manifest ersetzen (wenn im ZIP vorhanden)
        if '_meta/user_manifest.json' in zf.namelist():
            try:
                user_data = zf.read('_meta/user_manifest.json')
                json.loads(user_data)  # Validierung
                with open(self._loader.user_manifest_path, 'wb') as f:
                    f.write(user_data)
                result['imported'] += 1
            except Exception as e:
                result['errors'].append(f"User-Manifest: {e}")
        else:
            # Kein User-Manifest im ZIP → vorhandenes löschen
            if os.path.isfile(self._loader.user_manifest_path):
                try:
                    os.remove(self._loader.user_manifest_path)
                except Exception as e:
                    result['errors'].append(f"User-Manifest löschen: {e}")

        # Registry ersetzen (wenn vorhanden)
        if '_meta/placeholder_registry.json' in zf.namelist():
            try:
                registry_data = zf.read('_meta/placeholder_registry.json')
                json.loads(registry_data)  # Validierung
                with open(self._loader.registry_path, 'wb') as f:
                    f.write(registry_data)
                result['imported'] += 1
            except Exception as e:
                result['errors'].append(f"Registry: {e}")

        # Domain-Dateien ersetzen
        prompts_dir = os.path.join(self._instructions_dir, 'prompts')
        os.makedirs(prompts_dir, exist_ok=True)

        for name in zf.namelist():
            if name.startswith('prompts/') and name.endswith('.json'):
                filename = os.path.basename(name)
                if not filename or filename.startswith('_'):
                    continue
                try:
                    data = zf.read(name)
                    json.loads(data)  # Validierung
                    filepath = os.path.join(prompts_dir, filename)
                    with open(filepath, 'wb') as f:
                        f.write(data)
                    result['imported'] += 1
                except Exception as e:
                    result['errors'].append(f"Domain {filename}: {e}")

        return result

    def _import_merge(self, zf: zipfile.ZipFile, overwrite: bool = False) -> Dict[str, Any]:
        """Import-Modus 'merge'/'overwrite': Ergänzt fehlende, optional überschreibt bestehende."""
        result: Dict[str, Any] = {'imported': 0, 'skipped': 0, 'errors': []}
        prompts_dir = os.path.join(self._instructions_dir, 'prompts')

        for name in zf.namelist():
            if name == 'metadata.json':
                continue

            if name == '_meta/prompt_manifest.json':
                target = self._loader.manifest_path
            elif name == '_meta/user_manifest.json':
                target = self._loader.user_manifest_path
            elif name == '_meta/placeholder_registry.json':
                target = self._loader.registry_path
            elif name.startswith('prompts/') and name.endswith('.json'):
                filename = os.path.basename(name)
                if not filename or filename.startswith('_'):
                    continue
                target = os.path.join(prompts_dir, filename)
            else:
                continue

            if os.path.exists(target) and not overwrite:
                result['skipped'] += 1
                continue

            try:
                data = zf.read(name)
                json.loads(data)  # Validierung
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with open(target, 'wb') as f:
                    f.write(data)
                result['imported'] += 1
            except Exception as e:
                result['errors'].append(f"{name}: {e}")

        return result

    def factory_reset(self, scope: str = 'system') -> Dict[str, Any]:
        """Setzt Prompts auf Factory-Defaults zurück.

        Kopiert die Dateien aus prompts/_defaults/ zurück in den aktiven Pfad.

        Args:
            scope: 'system' = nur System-Manifest (User-Prompts bleiben erhalten)
                   'full'   = alles zurücksetzen inkl. User-Manifest löschen

        Returns:
            Dict mit {restored: int, errors: list, scope: str}
        """
        result: Dict[str, Any] = {'restored': 0, 'errors': [], 'scope': scope}
        defaults_dir = os.path.join(self._instructions_dir, 'prompts', '_defaults')

        if not os.path.isdir(defaults_dir):
            result['errors'].append(f"Factory-Defaults Verzeichnis nicht gefunden: {defaults_dir}")
            log.error("Factory-Reset: _defaults/ Verzeichnis fehlt")
            return result

        with self._lock:
            # Domain-Dateien aus _defaults/ wiederherstellen
            prompts_dir = os.path.join(self._instructions_dir, 'prompts')
            for filename in os.listdir(defaults_dir):
                if not filename.endswith('.json'):
                    continue

                src = os.path.join(defaults_dir, filename)
                dst = os.path.join(prompts_dir, filename)
                try:
                    shutil.copy2(src, dst)
                    result['restored'] += 1
                    log.info("Factory-Reset: %s wiederhergestellt", filename)
                except Exception as e:
                    result['errors'].append(f"{filename}: {e}")
                    log.error("Factory-Reset: %s fehlgeschlagen: %s", filename, e)

            # _meta/ Dateien aus _defaults/_meta/ wiederherstellen (nur System-Manifest)
            defaults_meta_dir = os.path.join(defaults_dir, '_meta')
            if os.path.isdir(defaults_meta_dir):
                meta_dir = os.path.join(prompts_dir, '_meta')
                os.makedirs(meta_dir, exist_ok=True)
                for filename in os.listdir(defaults_meta_dir):
                    if not filename.endswith('.json'):
                        continue

                    src = os.path.join(defaults_meta_dir, filename)
                    dst = os.path.join(meta_dir, filename)
                    try:
                        shutil.copy2(src, dst)
                        result['restored'] += 1
                        log.info("Factory-Reset: _meta/%s wiederhergestellt", filename)
                    except Exception as e:
                        result['errors'].append(f"_meta/{filename}: {e}")
                        log.error("Factory-Reset: _meta/%s fehlgeschlagen: %s", filename, e)

            # Bei 'full'-Reset: User-Manifest löschen
            if scope == 'full':
                user_manifest_path = self._loader.user_manifest_path
                if os.path.isfile(user_manifest_path):
                    try:
                        os.remove(user_manifest_path)
                        log.info("Factory-Reset: User-Manifest gelöscht")
                    except Exception as e:
                        result['errors'].append(f"user_manifest.json: {e}")
                        log.error("Factory-Reset: User-Manifest löschen fehlgeschlagen: %s", e)

            # Neu laden
            self.reload()

        log.info("Factory-Reset (%s) abgeschlossen: %d Dateien wiederhergestellt, %d Fehler",
                 scope, result['restored'], len(result['errors']))
        return result

    # ===== Per-Prompt Reset =====

    def reset_prompt_to_default(self, prompt_id: str) -> bool:
        """Setzt einen einzelnen Prompt auf Factory-Default zurück.

        Für System-Prompts: Liest den Original-Content aus _defaults/ und
        überschreibt nur diesen Prompt in der aktiven Domain-Datei.
        Für User-Prompts: Löscht den Prompt komplett (da kein Default existiert).

        Returns:
            True bei Erfolg
        """
        try:
            meta = self._manifest.get('prompts', {}).get(prompt_id)
            if not meta:
                log.error("Prompt '%s' nicht im Manifest", prompt_id)
                return False

            # User-Prompts haben kein Default → komplett löschen
            if self._is_user_prompt(prompt_id):
                log.info("User-Prompt '%s' hat kein Default – wird gelöscht", prompt_id)
                return self.delete_prompt(prompt_id)

            domain_file = meta.get('domain_file', '')
            defaults_path = os.path.join(self._instructions_dir, 'prompts', '_defaults', domain_file)

            if not os.path.exists(defaults_path):
                log.error("Default-Datei nicht gefunden: %s", defaults_path)
                return False

            with open(defaults_path, 'r', encoding='utf-8') as f:
                defaults_domain = json.load(f)

            if prompt_id not in defaults_domain:
                log.error("Prompt '%s' nicht in _defaults enthalten", prompt_id)
                return False

            # Nur diesen Prompt in der Domain-Datei ersetzen
            domain_data = self._domains.get(domain_file, {})
            domain_data[prompt_id] = defaults_domain[prompt_id]
            self._loader.save_domain_file(domain_file, domain_data)
            self._domains[domain_file] = domain_data

            # Auch Manifest-Metadaten auf Default zurücksetzen
            defaults_meta_path = os.path.join(
                self._instructions_dir, 'prompts', '_defaults', '_meta', 'prompt_manifest.json')
            if os.path.exists(defaults_meta_path):
                with open(defaults_meta_path, 'r', encoding='utf-8') as f:
                    defaults_manifest = json.load(f)
                default_meta = defaults_manifest.get('prompts', {}).get(prompt_id)
                if default_meta:
                    self._system_manifest['prompts'][prompt_id] = default_meta
                    self._loader.save_manifest(self._system_manifest)
                    self._manifest['prompts'][prompt_id] = {**default_meta, 'source': 'system'}

            log.info("Prompt '%s' auf Factory-Default zurückgesetzt", prompt_id)
            return True
        except Exception as e:
            log.error("reset_prompt_to_default fehlgeschlagen: %s", e)
            return False

    # ===== Startup-Validierung & Recovery =====

    def validate_integrity(self) -> Dict[str, Any]:
        """Prüft die Integrität aller JSON-Dateien beim Startup.

        Versucht bei korrupten Dateien automatisch aus _defaults wiederherzustellen.
        Prüft sowohl System- als auch User-Manifest.

        Returns:
            Dict mit {valid: bool, checked: int, recovered: int, errors: list}
        """
        result: Dict[str, Any] = {'valid': True, 'checked': 0, 'recovered': 0, 'errors': []}

        # 1. System-Manifest prüfen
        result['checked'] += 1
        if not self._validate_and_recover(self._loader.manifest_path, '_meta/prompt_manifest.json', result):
            result['valid'] = False

        # 2. User-Manifest prüfen (wenn vorhanden – kein Recovery nötig da kein Default)
        user_manifest_path = self._loader.user_manifest_path
        if os.path.isfile(user_manifest_path):
            result['checked'] += 1
            try:
                with open(user_manifest_path, 'r', encoding='utf-8') as f:
                    json.load(f)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                log.warning("User-Manifest korrupt: %s – wird entfernt", e)
                try:
                    os.remove(user_manifest_path)
                    result['recovered'] += 1
                    result['errors'].append(f"user_manifest.json: Korrupt, wurde entfernt")
                except Exception as del_err:
                    result['errors'].append(f"user_manifest.json: Korrupt und Löschen fehlgeschlagen: {del_err}")
                    result['valid'] = False

        # 3. Registry prüfen
        result['checked'] += 1
        if not self._validate_and_recover(self._loader.registry_path, '_meta/placeholder_registry.json', result):
            result['valid'] = False

        # 4. Domain-Dateien prüfen (existierende + im Manifest referenzierte)
        prompts_dir = os.path.join(self._instructions_dir, 'prompts')
        domain_files_to_check: set = set()

        # Dateien im Verzeichnis
        if os.path.isdir(prompts_dir):
            for filename in os.listdir(prompts_dir):
                if filename.endswith('.json') and not filename.startswith('_'):
                    domain_files_to_check.add(filename)

        # Dateien aus Manifest (könnten gelöscht worden sein)
        for prompt_info in self._manifest.get('prompts', {}).values():
            domain_file = prompt_info.get('domain_file', '')
            if domain_file:
                domain_files_to_check.add(domain_file)

        for filename in sorted(domain_files_to_check):
            result['checked'] += 1
            filepath = os.path.join(prompts_dir, filename)
            if not self._validate_and_recover(filepath, filename, result):
                result['valid'] = False

        log.info("Integritätsprüfung: %d geprüft, %d recovered, valid=%s",
                 result['checked'], result['recovered'], result['valid'])
        return result

    def _validate_and_recover(self, filepath: str, name: str,
                               result: Dict[str, Any]) -> bool:
        """Prüft eine JSON-Datei und versucht Recovery aus _defaults.

        Returns:
            True wenn Datei valide (oder erfolgreich recovered)
        """
        if not os.path.exists(filepath):
            # Datei fehlt – versuche aus _defaults
            defaults_path = os.path.join(self._instructions_dir, 'prompts', '_defaults', name)
            if os.path.exists(defaults_path):
                try:
                    os.makedirs(os.path.dirname(filepath), exist_ok=True)
                    shutil.copy2(defaults_path, filepath)
                    result['recovered'] += 1
                    log.warning("Fehlende Datei '%s' aus _defaults wiederhergestellt", name)
                    return True
                except Exception as e:
                    result['errors'].append(f"{name}: Fehlt und Recovery fehlgeschlagen: {e}")
                    return False
            result['errors'].append(f"{name}: Datei fehlt")
            return False

        # Datei existiert – JSON-Validierung
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                json.load(f)
            return True
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            log.warning("Korrupte Datei erkannt: %s (%s)", name, e)

            # Recovery aus _defaults
            defaults_path = os.path.join(self._instructions_dir, 'prompts', '_defaults', name)
            if os.path.exists(defaults_path):
                try:
                    shutil.copy2(defaults_path, filepath)
                    result['recovered'] += 1
                    log.info("Datei '%s' aus _defaults wiederhergestellt", name)
                    return True
                except Exception as recovery_err:
                    result['errors'].append(f"{name}: Recovery fehlgeschlagen: {recovery_err}")

            result['errors'].append(f"{name}: Korrupt und nicht wiederherstellbar")
            return False
