"""
PlaceholderMixin — Separate _ph_<key>() method per placeholder.

Static placeholders are cached until invalidate_cache().
Computed placeholders are recalculated on every call.
"""

import os
import json
import re
from datetime import datetime
from typing import Dict, Optional

from ..logger import log


# Placeholder pattern: {{key}}
PH_PATTERN = re.compile(r'\{\{(\w+)\}\}')


class PlaceholderMixin:
    """
    Provides placeholder resolution for PromptEngine.

    Every placeholder {{key}} maps to exactly one _ph_<key>() method.
    Static = cached until invalidate_cache(); Computed = fresh per call.
    """

    _STATIC_PH = [
        'char_name', 'char_age', 'char_gender', 'char_background', 'persona_type',
        'user_name', 'user_gender', 'language', 'user_interested_in', 'user_info',
    ]

    _COMPUTED_PH = [
        'current_date', 'current_time', 'current_weekday',
        'persona_type_description', 'char_core_traits', 'char_knowledge',
        'char_expression', 'char_scenarios', 'cortex_persona_context',
    ]

    def _compute_placeholders(self, runtime_vars: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Builds flat placeholder dict: static (cached) + computed + runtime."""
        values: Dict[str, str] = {}

        # Static (cached until invalidate_cache)
        if not self._static_cache:
            self._static_cache = {key: getattr(self, f'_ph_{key}')() for key in self._STATIC_PH}
        values.update(self._static_cache)

        # Computed (fresh every call)
        for key in self._COMPUTED_PH:
            values[key] = getattr(self, f'_ph_{key}')()

        # Runtime (from caller, overrides everything)
        if runtime_vars:
            values.update(runtime_vars)

        return values

    # ── Static Placeholders (persona config) ──────────────────────

    def _load_persona_settings(self) -> dict:
        """Returns persona_settings from persona_config.json."""
        try:
            config_path = os.path.join(self._instructions_dir, 'personas', 'active', 'persona_config.json')
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f).get('persona_settings', {})
        except Exception as e:
            log.warning("Failed to load persona config: %s", e)
        return {}

    def _ph_char_name(self) -> str:
        return str(self._load_persona_settings().get('name', 'Assistant'))

    def _ph_char_age(self) -> str:
        return str(self._load_persona_settings().get('age', 18))

    def _ph_char_gender(self) -> str:
        return str(self._load_persona_settings().get('gender', 'diverse'))

    def _ph_char_background(self) -> str:
        return str(self._load_persona_settings().get('background', ''))

    def _ph_persona_type(self) -> str:
        return str(self._load_persona_settings().get('persona', 'AI'))

    # ── Static Placeholders (user profile) ────────────────────────

    def _get_profile_value(self, key: str, default: str = '') -> str:
        """Reads a single profile value from settings_manager."""
        try:
            from utils.settings_manager import get_value
            return str(get_value('profile', key) or default)
        except Exception:
            return default

    def _ph_user_name(self) -> str:
        return self._get_profile_value('userName', 'User')

    def _ph_user_gender(self) -> str:
        return self._get_profile_value('userGender', 'Not specified')

    def _ph_language(self) -> str:
        return self._get_profile_value('personaLanguage', 'english')

    def _ph_user_interested_in(self) -> str:
        try:
            from utils.settings_manager import get_value
            val = get_value('profile', 'userInterestedIn')
            if isinstance(val, list):
                return ', '.join(str(i) for i in val)
            return str(val or 'Not specified')
        except Exception:
            return 'Not specified'

    def _ph_user_info(self) -> str:
        return self._get_profile_value('userInfo', 'No information')

    # ── Computed Placeholders (time) ──────────────────────────────

    def _ph_current_date(self) -> str:
        try:
            from ..time_context import get_time_context
            return get_time_context().get('current_date', '')
        except Exception:
            return datetime.now().strftime('%d.%m.%Y')

    def _ph_current_time(self) -> str:
        try:
            from ..time_context import get_time_context
            return get_time_context().get('current_time', '')
        except Exception:
            return datetime.now().strftime('%H:%M')

    def _ph_current_weekday(self) -> str:
        try:
            from ..time_context import get_time_context
            return get_time_context().get('current_weekday', '')
        except Exception:
            return ''

    # ── Computed Placeholders (persona derived) ───────────────────

    def _get_char_config_and_profile(self):
        """Loads persona config + profile (cached per call chain)."""
        if self._char_data_cache is not None:
            return self._char_data_cache
        try:
            from ..config import load_char_config, load_char_profile
            config = load_char_config()
            profile = load_char_profile()
            self._char_data_cache = (config, profile)
        except Exception as e:
            log.warning("Failed to load char config/profile: %s", e)
            self._char_data_cache = ({}, {})
        return self._char_data_cache

    def _ph_persona_type_description(self) -> str:
        try:
            config, profile = self._get_char_config_and_profile()
            persona_spec = profile.get('persona_spec', {})
            persona_types = persona_spec.get('persona_type', {})
            persona_type = config.get('persona', 'KI')
            return str(persona_types.get(persona_type, ''))
        except Exception:
            return ''

    def _ph_char_core_traits(self) -> str:
        try:
            config, profile = self._get_char_config_and_profile()
            persona_spec = profile.get('persona_spec', {})
            details = persona_spec.get('core_traits_details', {})
            selected = config.get('core_traits', [])
            if not selected:
                return ''
            parts = []
            for trait in selected:
                trait_data = details.get(trait, {})
                if isinstance(trait_data, dict):
                    parts.append(f"{trait}: {trait_data.get('description', trait)}")
                    for b in trait_data.get('behaviors', []):
                        parts.append(f"  - {b}")
                else:
                    parts.append(trait)
            return '\n'.join(parts)
        except Exception:
            return ''

    def _ph_char_knowledge(self) -> str:
        try:
            config, profile = self._get_char_config_and_profile()
            persona_spec = profile.get('persona_spec', {})
            areas = persona_spec.get('knowledge_areas', {})
            selected = config.get('knowledge', [])
            if not selected:
                return ''
            return '\n'.join(f"  - {k}: {areas.get(k, k)}" for k in selected)
        except Exception:
            return ''

    def _ph_char_expression(self) -> str:
        try:
            config, profile = self._get_char_config_and_profile()
            persona_spec = profile.get('persona_spec', {})
            styles = persona_spec.get('expression_styles', {})
            selected = config.get('expression', 'normal')
            data = styles.get(selected, {})
            if not data:
                return selected
            parts = []
            if data.get('description'):
                parts.append(data['description'])
            if data.get('example'):
                parts.append(f"Beispiel: {data['example']}")
            for c in data.get('characteristics', []):
                parts.append(f"  - {c}")
            return '\n'.join(parts)
        except Exception:
            return ''

    def _ph_char_scenarios(self) -> str:
        try:
            config, profile = self._get_char_config_and_profile()
            persona_spec = profile.get('persona_spec', {})
            scenarios = persona_spec.get('scenarios', {})
            selected = config.get('scenarios', [])
            if not selected:
                return ''
            parts = []
            for key in selected:
                sd = scenarios.get(key, {})
                if isinstance(sd, dict):
                    parts.append(f"{sd.get('name', key)}: {sd.get('description', '')}")
                    for s in sd.get('setting', []):
                        parts.append(f"  - {s}")
                else:
                    parts.append(key)
            return '\n'.join(parts)
        except Exception:
            return ''

    def _ph_cortex_persona_context(self) -> str:
        try:
            from ..config import load_character
            character = load_character()
            parts = []
            for key in ('identity', 'core', 'background'):
                val = character.get(key, '')
                if val:
                    if key == 'background':
                        parts.append(f"Hintergrund: {val}")
                    else:
                        parts.append(val)
            return "\n".join(parts)
        except Exception:
            return ''

    # ── Resolve Helpers ───────────────────────────────────────────

    def _read_and_resolve(self, filepath: str, placeholders: Dict[str, str]) -> str:
        """Reads a file and resolves placeholders."""
        raw = self._read_file(filepath)
        if not raw:
            return ''
        return self._clean_text(self._resolve(raw, placeholders))

    @staticmethod
    def _resolve(text: str, placeholders: Dict[str, str]) -> str:
        """Replaces {{key}} with values from placeholders dict."""
        if not text:
            return text
        return PH_PATTERN.sub(
            lambda m: str(placeholders.get(m.group(1), '{{' + m.group(1) + '}}')),
            text
        )

    @staticmethod
    def _clean_text(text: str) -> str:
        """Reduces 3+ consecutive newlines to 2."""
        return re.sub(r'\n{3,}', '\n\n', text).strip()
