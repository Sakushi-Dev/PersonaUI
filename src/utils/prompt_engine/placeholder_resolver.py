"""
Placeholder Resolver – Löst {{placeholder}} in Prompt-Texten auf.

Drei Resolution-Phasen:
1. Static:   persona_config + user_profile Werte (gecached)
2. Computed:  Dynamisch berechnete Werte (current_date, char_description, etc.)
3. Runtime:   Vom Aufrufer übergebene Werte (elapsed_time, inner_dialogue, etc.)

Placeholder-Syntax: {{key}} (doppelte geschweifte Klammern)
Unbekannte Placeholder bleiben als {{key}} stehen (kein Crash).
"""

import re
import os
import json
from typing import Dict, Any, Optional
from ..logger import log


class PlaceholderResolver:
    """Löst {{placeholder}} in Text auf. Drei Phasen: static → computed → runtime."""

    PATTERN = re.compile(r'\{\{(\w+)\}\}')

    def __init__(self, registry_data: Dict[str, Any], instructions_dir: str):
        """
        Args:
            registry_data: Dict mit 'version' und 'placeholders' (merged registry)
            instructions_dir: Pfad zum instructions/ Verzeichnis (für Datenquellen)
        """
        self._registry = registry_data.get('placeholders', {})
        self._instructions_dir = instructions_dir
        self._static_cache: Dict[str, str] = {}
        self._char_data_cache = None
        self._compute_functions: Dict[str, callable] = {}

        # Compute-Functions registrieren
        self._register_compute_functions()

    def _load_registry(self, registry_path: str) -> Dict[str, Any]:
        """DEPRECATED: Lädt die Placeholder-Registry aus JSON (legacy support)."""
        try:
            if os.path.exists(registry_path):
                with open(registry_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return data.get('placeholders', {})
        except Exception as e:
            log.error("Placeholder-Registry konnte nicht geladen werden: %s", e)
        return {}

    def _register_compute_functions(self):
        """Registriert die compute-Funktionen für computed Placeholder."""
        self._compute_functions = {
            'build_character_description': self._compute_char_description,
            'build_persona_type_description': self._compute_persona_type_description,
            'build_char_core_traits': self._compute_char_core_traits,
            'build_char_knowledge': self._compute_char_knowledge,
            'build_char_expression': self._compute_char_expression,
            'build_char_scenarios': self._compute_char_scenarios,
            'get_time_context.current_date': self._compute_current_date,
            'get_time_context.current_time': self._compute_current_time,
            'get_time_context.current_weekday': self._compute_current_weekday,
        }

    def resolve_text(self, text: str, variant: str = 'default',
                     runtime_vars: Optional[Dict[str, str]] = None) -> str:
        """
        Hauptmethode: Alle Placeholder in einem Text auflösen.

        Args:
            text: Text mit {{placeholder}} Syntax
            variant: Aktive Variante ('default' oder 'experimental')
            runtime_vars: Vom Aufrufer übergebene Werte

        Returns:
            Text mit aufgelösten Placeholders
        """
        if not text:
            return text

        variables = self._build_variables(variant, runtime_vars)
        return self.PATTERN.sub(
            lambda m: str(variables.get(m.group(1), '{{' + m.group(1) + '}}')),
            text
        )

    def get_all_values(self, variant: str = 'default',
                       runtime_vars: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Gibt alle aufgelösten Placeholder-Werte zurück."""
        return self._build_variables(variant, runtime_vars)

    def _build_variables(self, variant: str = 'default',
                         runtime_vars: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Sammelt alle Werte: static → computed → runtime."""
        variables: Dict[str, str] = {}

        # Phase 1: Static (cached)
        variables.update(self._resolve_static())

        # Phase 2: Computed (fresh jedes Mal)
        variables.update(self._resolve_computed(variant))

        # Phase 3: Runtime (vom Aufrufer)
        if runtime_vars:
            variables.update(runtime_vars)

        return variables

    def _resolve_static(self) -> Dict[str, str]:
        """Phase 1: Lädt persona_config + user_profile Werte (gecached)."""
        if self._static_cache:
            return self._static_cache.copy()

        values: Dict[str, str] = {}

        for key, meta in self._registry.items():
            if meta.get('resolve_phase') != 'static':
                continue

            source = meta.get('source')
            source_path = meta.get('source_path', '')
            default = meta.get('default', '')

            try:
                if source == 'persona_config':
                    raw = self._get_from_persona_config(source_path)
                elif source == 'user_profile':
                    raw = self._get_from_user_profile(source_path)
                else:
                    raw = default
            except Exception:
                raw = default

            # None → Default
            if raw is None:
                raw = default

            # Listen joinieren
            if meta.get('type') == 'list' and isinstance(raw, list):
                separator = meta.get('join_separator', ', ')
                values[key] = separator.join(str(item) for item in raw) if raw else ''
            else:
                values[key] = str(raw) if raw is not None else ''

        self._static_cache = values
        return values.copy()

    def _resolve_computed(self, variant: str = 'default') -> Dict[str, str]:
        """Phase 2: Berechnet dynamische Werte (nie gecached)."""
        values: Dict[str, str] = {}

        for key, meta in self._registry.items():
            if meta.get('resolve_phase') != 'computed':
                continue

            compute_fn_name = meta.get('compute_function', '')
            if not compute_fn_name:
                continue

            compute_fn = self._compute_functions.get(compute_fn_name)
            if compute_fn:
                try:
                    result = compute_fn()
                    values[key] = str(result) if result is not None else ''
                except Exception as e:
                    log.warning("Compute-Function '%s' fehlgeschlagen: %s", compute_fn_name, e)
                    values[key] = str(meta.get('default', ''))
            else:
                values[key] = str(meta.get('default', ''))

        return values

    def invalidate_cache(self):
        """Cache leeren (bei Config-Wechsel oder Persona-Wechsel)."""
        self._static_cache = {}
        self._char_data_cache = None

    def get_registry(self) -> Dict[str, Any]:
        """Gibt die Placeholder-Registry zurück (für Editor/Validierung)."""
        return self._registry.copy()

    # ===== Datenquellen =====

    def _get_from_persona_config(self, source_path: str) -> Any:
        """Liest einen Wert aus der aktiven persona_config.json."""
        try:
            config_path = os.path.join(self._instructions_dir, 'personas', 'active', 'persona_config.json')
            if not os.path.exists(config_path):
                return None

            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # Pfad navigieren: "persona_settings.name" → config["persona_settings"]["name"]
            parts = source_path.split('.')
            value = config
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    return None
            return value
        except Exception as e:
            log.debug("Persona-Config Wert '%s' nicht lesbar: %s", source_path, e)
            return None

    def _get_from_user_profile(self, source_path: str) -> Any:
        """Liest einen Wert aus user_profile.json."""
        try:
            src_dir = os.path.dirname(os.path.dirname(self._instructions_dir))
            profile_path = os.path.join(src_dir, 'settings', 'user_profile.json')
            if not os.path.exists(profile_path):
                # Fallback: Look relative to instructions_dir's parent
                profile_path = os.path.join(os.path.dirname(self._instructions_dir), 'settings', 'user_profile.json')
            if not os.path.exists(profile_path):
                return None

            with open(profile_path, 'r', encoding='utf-8') as f:
                profile = json.load(f)

            return profile.get(source_path)
        except Exception as e:
            log.debug("User-Profile Wert '%s' nicht lesbar: %s", source_path, e)
            return None

    # ===== Compute-Functions =====

    def _get_char_data(self) -> Dict[str, Any]:
        """Cached: Ruft build_character_description() einmal auf und gibt das Dict zurück."""
        if self._char_data_cache is not None:
            return self._char_data_cache
        try:
            from ..config import build_character_description
            self._char_data_cache = build_character_description()
        except Exception as e:
            log.warning("char_data konnte nicht berechnet werden: %s", e)
            self._char_data_cache = {}
        return self._char_data_cache

    def _compute_char_description(self) -> str:
        """Baut die char_description über config.build_character_description()."""
        return self._get_char_data().get('desc', '')

    def _compute_persona_type_description(self) -> str:
        """Beschreibung des Persona-Typs aus der Spec-Datei."""
        try:
            from ..config import load_char_config, load_char_profile
            config = load_char_config()
            profile = load_char_profile()
            persona_profile = profile.get('persona_spec', {})
            persona_types = persona_profile.get('persona_type', {})
            persona_type = config.get('persona', 'KI')
            return persona_types.get(persona_type, '')
        except Exception as e:
            log.warning("persona_type_description konnte nicht berechnet werden: %s", e)
            return ''

    def _compute_char_core_traits(self) -> str:
        """Aufgelöste Kernmerkmale mit Beschreibungen aus der Spec-Datei (ohne Header)."""
        try:
            from ..config import load_char_config, load_char_profile
            config = load_char_config()
            profile = load_char_profile()
            persona_profile = profile.get('persona_spec', {})
            core_traits_details = persona_profile.get('core_traits_details', {})
            selected = config.get('core_traits', [])
            if not selected:
                return ''
            parts = []
            for trait in selected:
                trait_data = core_traits_details.get(trait, {})
                if isinstance(trait_data, dict):
                    trait_desc = trait_data.get('description', trait)
                    behaviors = trait_data.get('behaviors', [])
                    parts.append(f"{trait}: {trait_desc}")
                    for b in behaviors:
                        parts.append(f"  - {b}")
                else:
                    parts.append(trait)
            return '\n'.join(parts)
        except Exception as e:
            log.warning("char_core_traits konnte nicht berechnet werden: %s", e)
            return ''

    def _compute_char_knowledge(self) -> str:
        """Aufgelöste Wissensgebiete mit Beschreibungen aus der Spec-Datei (ohne Header)."""
        try:
            from ..config import load_char_config, load_char_profile
            config = load_char_config()
            profile = load_char_profile()
            persona_profile = profile.get('persona_spec', {})
            knowledge_areas = persona_profile.get('knowledge_areas', {})
            selected = config.get('knowledge', [])
            if not selected:
                return ''
            parts = []
            for k in selected:
                desc = knowledge_areas.get(k, k)
                parts.append(f"  - {k}: {desc}")
            return '\n'.join(parts)
        except Exception as e:
            log.warning("char_knowledge konnte nicht berechnet werden: %s", e)
            return ''

    def _compute_char_expression(self) -> str:
        """Aufgelöster Kommunikationsstil mit Details aus der Spec-Datei (ohne Header)."""
        try:
            from ..config import load_char_config, load_char_profile
            config = load_char_config()
            profile = load_char_profile()
            persona_profile = profile.get('persona_spec', {})
            expression_styles = persona_profile.get('expression_styles', {})
            selected = config.get('expression', 'normal')
            expr_data = expression_styles.get(selected, {})
            if not expr_data:
                return selected
            parts = []
            expr_desc = expr_data.get('description', '')
            expr_example = expr_data.get('example', '')
            expr_chars = expr_data.get('characteristics', [])
            if expr_desc:
                parts.append(expr_desc)
            if expr_example:
                parts.append(f"Beispiel: {expr_example}")
            if expr_chars:
                for c in expr_chars:
                    parts.append(f"  - {c}")
            return '\n'.join(parts)
        except Exception as e:
            log.warning("char_expression konnte nicht berechnet werden: %s", e)
            return ''

    def _compute_char_scenarios(self) -> str:
        """Aufgelöste Szenarien mit Details aus der Spec-Datei (ohne Header)."""
        try:
            from ..config import load_char_config, load_char_profile
            config = load_char_config()
            profile = load_char_profile()
            persona_profile = profile.get('persona_spec', {})
            scenarios_details = persona_profile.get('scenarios', {})
            selected = config.get('scenarios', [])
            if not selected:
                return ''
            parts = []
            for key in selected:
                sd = scenarios_details.get(key, {})
                if isinstance(sd, dict):
                    name = sd.get('name', key)
                    desc = sd.get('description', '')
                    setting = sd.get('setting', [])
                    parts.append(f"{name}: {desc}")
                    for s in setting:
                        parts.append(f"  - {s}")
                else:
                    parts.append(key)
            return '\n'.join(parts)
        except Exception as e:
            log.warning("char_scenarios konnte nicht berechnet werden: %s", e)
            return ''

    def _compute_current_date(self) -> str:
        """Aktuelles Datum im Format DD.MM.YYYY."""
        from ..time_context import get_time_context
        return get_time_context().get('current_date', '')

    def _compute_current_time(self) -> str:
        """Aktuelle Uhrzeit im Format HH:MM."""
        from ..time_context import get_time_context
        return get_time_context().get('current_time', '')

    def _compute_current_weekday(self) -> str:
        """Aktueller Wochentag auf Deutsch."""
        from ..time_context import get_time_context
        return get_time_context().get('current_weekday', '')

