"""
Validator – Schema-Validierung für Prompt-System JSON-Dateien.

Validiert:
- Manifest-Struktur (Pflichtfelder, gültige Werte)
- Domain-Dateien (Content-Vollständigkeit, Variant-Konsistenz)
- Placeholder-Verknüpfungen (alle verwendeten Placeholder müssen in Registry existieren)
- Cross-References (domain_file im Manifest muss existierende Domain-Datei referenzieren)
"""

import re
from typing import Dict, Any, List

from ..logger import log


# Gültige Werte für Manifest-Felder
VALID_CATEGORIES = {'system', 'persona', 'context', 'prefill', 'dialog_injection', 'afterthought', 'summary', 'spec_autofill', 'utility', 'custom', 'cortex'}
VALID_TYPES = {'text', 'multi_turn'}
VALID_TARGETS = {'system_prompt', 'message', 'prefill'}
VALID_POSITIONS = {'system_prompt', 'first_assistant', 'consent_dialog', 'user_message', 'prefill', 'system_prompt_append', 'history'}
VALID_RESOLVE_PHASES = {'static', 'computed', 'runtime'}

PLACEHOLDER_PATTERN = re.compile(r'\{\{(\w+)\}\}')


class PromptValidator:
    """Validiert die Integrität des gesamten Prompt-Systems."""

    def validate_manifest(self, manifest: Dict[str, Any]) -> List[str]:
        """
        Validiert die Manifest-Struktur.

        Returns:
            Liste von Fehlermeldungen (leer = alles OK)
        """
        errors: List[str] = []

        if 'version' not in manifest:
            errors.append("Manifest: 'version' fehlt")

        prompts = manifest.get('prompts', {})
        if not prompts:
            errors.append("Manifest: Keine Prompts definiert")
            return errors

        for prompt_id, meta in prompts.items():
            prefix = f"Manifest[{prompt_id}]"

            # Pflichtfelder prüfen
            for field in ['name', 'type', 'target', 'position', 'order', 'enabled', 'domain_file']:
                if field not in meta:
                    errors.append(f"{prefix}: Pflichtfeld '{field}' fehlt")

            # Gültige Kategorie
            category = meta.get('category', '')
            if category and category not in VALID_CATEGORIES:
                errors.append(f"{prefix}: Ungültige category '{category}' (erlaubt: {VALID_CATEGORIES})")

            # Gültiger Typ
            prompt_type = meta.get('type', '')
            if prompt_type and prompt_type not in VALID_TYPES:
                errors.append(f"{prefix}: Ungültiger type '{prompt_type}' (erlaubt: {VALID_TYPES})")

            # Gültiges Target
            target = meta.get('target', '')
            if target and target not in VALID_TARGETS:
                errors.append(f"{prefix}: Ungültiges target '{target}' (erlaubt: {VALID_TARGETS})")

            # Gültige Position
            position = meta.get('position', '')
            if position and position not in VALID_POSITIONS:
                errors.append(f"{prefix}: Ungültige position '{position}' (erlaubt: {VALID_POSITIONS})")

            # Order muss eine Zahl sein
            order = meta.get('order')
            if order is not None and not isinstance(order, (int, float)):
                errors.append(f"{prefix}: 'order' muss eine Zahl sein, ist {type(order).__name__}")

        return errors

    def validate_domain(self, domain_data: Dict[str, Any],
                        manifest_prompts: Dict[str, Any]) -> List[str]:
        """
        Validiert eine Domain-Datei gegen das Manifest.

        Args:
            domain_data: Inhalt der Domain-Datei
            manifest_prompts: Prompts aus dem Manifest die auf diese Domain zeigen

        Returns:
            Liste von Fehlermeldungen
        """
        errors: List[str] = []

        for prompt_id, meta in manifest_prompts.items():
            prefix = f"Domain[{prompt_id}]"
            prompt_type = meta.get('type', 'text')

            if prompt_id not in domain_data:
                errors.append(f"{prefix}: Prompt-ID nicht in Domain-Datei gefunden")
                continue

            prompt_content = domain_data[prompt_id]
            variants = prompt_content.get('variants', {})

            if not variants:
                errors.append(f"{prefix}: Keine Varianten definiert")
                continue

            # Varianten prüfen
            for variant_name, variant_data in variants.items():
                vpfx = f"{prefix}.{variant_name}"

                if prompt_type == 'text':
                    if 'content' not in variant_data:
                        errors.append(f"{vpfx}: 'content' fehlt")
                elif prompt_type == 'multi_turn':
                    if 'messages' not in variant_data:
                        errors.append(f"{vpfx}: 'messages' fehlt (multi_turn)")
                    else:
                        for i, msg in enumerate(variant_data['messages']):
                            if 'role' not in msg or 'content' not in msg:
                                errors.append(f"{vpfx}.messages[{i}]: 'role' oder 'content' fehlt")

        return errors

    def validate_placeholders(self, domain_data: Dict[str, Any],
                               registry: Dict[str, Any]) -> List[str]:
        """
        Prüft ob alle verwendeten Placeholder in der Registry definiert sind.

        Args:
            domain_data: Inhalt einer Domain-Datei
            registry: Placeholder-Registry

        Returns:
            Liste von Warnungen (keine Fehler – unbekannte Placeholder bleiben als Text stehen)
        """
        warnings: List[str] = []
        registry_keys = set(registry.get('placeholders', {}).keys())

        for prompt_id, prompt_content in domain_data.items():
            declared_placeholders = set(prompt_content.get('placeholders_used', []))
            variants = prompt_content.get('variants', {})

            for variant_name, variant_data in variants.items():
                content = variant_data.get('content', '')
                if not content:
                    continue

                # Finde alle {{key}} im Content
                found_placeholders = set(PLACEHOLDER_PATTERN.findall(content))

                # Prüfe gegen deklarierte Liste
                undeclared = found_placeholders - declared_placeholders
                if undeclared:
                    for ph in undeclared:
                        warnings.append(
                            f"{prompt_id}.{variant_name}: Placeholder '{{{{{ph}}}}}' "
                            f"wird verwendet aber nicht in placeholders_used deklariert"
                        )

                # Prüfe gegen Registry
                unknown = found_placeholders - registry_keys
                if unknown:
                    for ph in unknown:
                        warnings.append(
                            f"{prompt_id}.{variant_name}: Placeholder '{{{{{ph}}}}}' "
                            f"ist nicht in der Placeholder-Registry definiert"
                        )

        return warnings

    def validate_cross_references(self, manifest: Dict[str, Any],
                                    available_domains: set) -> List[str]:
        """
        Prüft ob alle domain_file Referenzen im Manifest gültig sind.

        Args:
            manifest: Das Manifest
            available_domains: Set von verfügbaren Domain-Dateinamen

        Returns:
            Liste von Fehlermeldungen
        """
        errors: List[str] = []
        for prompt_id, meta in manifest.get('prompts', {}).items():
            domain_file = meta.get('domain_file', '')
            if domain_file and domain_file not in available_domains:
                errors.append(
                    f"Manifest[{prompt_id}]: domain_file '{domain_file}' nicht gefunden "
                    f"(verfügbar: {available_domains})"
                )
        return errors

    def validate_all(self, manifest: Dict[str, Any],
                     domains: Dict[str, Any],
                     registry: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Führt alle Validierungen durch.

        Returns:
            Dictionary mit 'errors' und 'warnings' Listen
        """
        errors: List[str] = []
        warnings: List[str] = []

        # 1. Manifest validieren
        errors.extend(self.validate_manifest(manifest))

        # 2. Cross-References prüfen
        errors.extend(self.validate_cross_references(manifest, set(domains.keys())))

        # 3. requires_any Referenzen prüfen
        warnings.extend(self.validate_requires_any(manifest, registry))

        # 4. Domain-Dateien validieren
        prompts_by_domain: Dict[str, Dict] = {}
        for prompt_id, meta in manifest.get('prompts', {}).items():
            domain_file = meta.get('domain_file', '')
            if domain_file not in prompts_by_domain:
                prompts_by_domain[domain_file] = {}
            prompts_by_domain[domain_file][prompt_id] = meta

        for domain_file, domain_prompts in prompts_by_domain.items():
            if domain_file in domains:
                errors.extend(self.validate_domain(domains[domain_file], domain_prompts))
                warnings.extend(self.validate_placeholders(domains[domain_file], registry))

        return {
            'errors': errors,
            'warnings': warnings
        }

    def validate_requires_any(self, manifest: Dict[str, Any],
                               registry: Dict[str, Any]) -> List[str]:
        """
        Prüft ob requires_any-Referenzen in der Registry existieren.

        Returns:
            Liste von Warnungen (leer = alles OK)
        """
        warnings: List[str] = []
        registry_keys = set(registry.get('placeholders', {}).keys())

        for prompt_id, meta in manifest.get('prompts', {}).items():
            requires = meta.get('requires_any', [])
            for key in requires:
                if key not in registry_keys:
                    warnings.append(
                        f"Manifest[{prompt_id}]: requires_any referenziert "
                        f"unbekannten Placeholder '{key}'"
                    )

        return warnings
