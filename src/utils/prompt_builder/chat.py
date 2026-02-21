"""
Chat Prompt Builder – Prompt-Generierung für Chat-Requests.

Übernimmt aus dem alten PromptBuilder:
- build_core_prompt()
- build_persona_prompt()
- build_system_prompt()
- build_prefill()
- get_prefill_impersonation()
- get_consent_dialog()

Phase 2: Optionale Engine-Delegation via set_engine().
"""

import os
import json
import re
from typing import Dict, Any, List, Optional

from .base import PromptBase
from ..logger import log
from ..config import get_config_path


class ChatPromptBuilder(PromptBase):
    """Prompt-Generierung für Chat-Requests"""

    def __init__(self, master_prompt_dir: str = 'instructions/system/main'):
        super().__init__()
        self._engine = None
        self._master_prompts = self._load_master_prompt(master_prompt_dir)

    def set_engine(self, engine):
        """Setzt die PromptEngine für Engine-Delegation."""
        self._engine = engine

    def _load_master_prompt(self, prompt_dir: str) -> Dict[str, str]:
        """Lädt den Master Prompt aus einzelnen .txt-Dateien im Verzeichnis."""
        try:
            full_path = get_config_path(prompt_dir)
            prompts = {}

            if not os.path.isdir(full_path):
                log.warning("Verzeichnis %s nicht gefunden. Verwende Fallback.", prompt_dir)
                return self._get_master_prompt_fallback()

            for filename in os.listdir(full_path):
                if filename.endswith('.txt'):
                    key = filename[:-4]
                    filepath = os.path.join(full_path, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as file:
                            prompts[key] = file.read().strip()
                    except Exception as e:
                        log.error("Fehler beim Laden von %s: %s", filename, e)

            if not prompts:
                log.warning("Keine .txt-Dateien in %s gefunden. Verwende Fallback.", prompt_dir)
                return self._get_master_prompt_fallback()

            return prompts
        except Exception as e:
            log.error("Fehler beim Laden des Master Prompts: %s", e)
            return self._get_master_prompt_fallback()

    def _get_master_prompt_fallback(self) -> Dict[str, str]:
        """Fallback-Werte falls keine Prompt-Dateien gefunden werden"""
        return {
            'impersonation': '',
            'system_rule': 'You are {char_name}. Respond in {language}.',
            'char_description': '{char_description}',
            'sub_system_reminder': '',
            'prefill_impersonation': '',
            'prefill_system_rules': 'I respond as {char_name}:'
        }

    def _load_consent_dialog(self) -> List[Dict[str, str]]:
        """Lädt den Consent Dialog aus consent_dialog.json"""
        try:
            dialog_path = get_config_path('instructions/system/main/consent_dialog.json')
            if os.path.exists(dialog_path):
                with open(dialog_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            log.warning("consent_dialog.json konnte nicht geladen werden: %s", e)
        return []

    def _load_experimental_consent(self) -> str:
        """Lädt consent_agreement aus experimental/agreement/ und entfernt === Disclaimer-Zeilen"""
        try:
            consent_path = get_config_path('instructions/system/experimental/agreement/consent_agreement.txt')
            if os.path.exists(consent_path):
                with open(consent_path, 'r', encoding='utf-8') as f:
                    text = f.read().strip()
                # Entferne alle Zeilen die mit === beginnen und enden
                text = re.sub(r'^===.*===\s*\n?', '', text, flags=re.MULTILINE).strip()
                return text
        except Exception as e:
            log.warning("Experimental consent_agreement konnte nicht geladen werden: %s", e)
        # Fallback auf main/
        return self._master_prompts.get('consent_agreement', '')

    def build_core_prompt(self, char_name: str, language: str = 'english', user_name: str = 'User',
                          ip_address: str = None, experimental_mode: bool = False) -> Dict[str, str]:
        """
        Erstellt nur den Core System Prompt OHNE Charakterbeschreibung.
        Reihenfolge: impersonation → system_rule → user_info → time_sense → output_format

        Args:
            char_name: Name des Charakters
            language: Sprache für die Konversation
            user_name: Name des Benutzers
            ip_address: IP-Adresse des Users (optional)
            experimental_mode: Wenn True, wird consent_agreement in Messages eingebunden

        Returns:
            Dictionary mit den einzelnen Core-Komponenten
        """
        # User-Name aus Profil laden
        profile_user_name = self.get_user_name()
        if profile_user_name and profile_user_name != 'User':
            user_name = profile_user_name

        # Hole vollständigen Zeit-Kontext
        from ..time_context import get_time_context
        time_ctx = get_time_context(ip_address)

        current_date = time_ctx['current_date']
        current_time = time_ctx['current_time']
        current_weekday = time_ctx['current_weekday']

        # Output Format
        output_fmt = self._master_prompts.get('output_format', '')

        # Impersonation
        impersonation = self._master_prompts.get('impersonation', '')

        # Time Sense
        time_sense = self._master_prompts.get('time_sense', '')
        time_sense = time_sense.format(
            current_date=current_date,
            current_time=current_time,
            current_weekday=current_weekday
        )

        # System Rules
        system_rule = self._master_prompts.get('system_rule', '')
        system_rule = system_rule.format(
            language=language,
            char_name=char_name,
            user_name=user_name
        )

        # User Info
        user_info = self.build_user_info_prompt(user_name)

        return {
            'output_format': output_fmt,
            'impersonation': impersonation,
            'time_sense': time_sense,
            'system_rule': system_rule,
            'user_info': user_info
        }

    def build_persona_prompt(self, character_data: Dict[str, str], char_name: str,
                             user_name: str = 'User', experimental_mode: bool = False) -> str:
        """
        Erstellt nur den Persona Prompt (Charakterbeschreibung)
        OHNE System-Regeln

        Args:
            character_data: Dictionary mit Charakterinformationen
            char_name: Name des Charakters
            user_name: Name des Benutzers
            experimental_mode: Wenn True, wird char_description_experimental verwendet

        Returns:
            Der Persona Prompt ohne Core System Rules
        """
        char_description = character_data.get('desc', '')

        template_key = 'char_description_experimental' if experimental_mode else 'char_description_default'
        char_desc_template = self._master_prompts.get(template_key, '')

        char_desc = char_desc_template.format(
            char_name=char_name,
            user_name=user_name,
            char_description=char_description,
            prompt_id_3='prompt_id_3'
        )

        return char_desc

    def build_system_prompt(self, character_data: Dict[str, str], language: str = 'english',
                            user_name: str = 'User', ip_address: str = None,
                            experimental_mode: bool = False) -> str:
        """
        Erstellt den vollständigen System Prompt.
        Kombiniert Core Prompt + User Info + Persona Prompt.

        Delegiert an die PromptEngine wenn verfügbar (Phase 2+).

        Args:
            character_data: Dictionary mit Charakterinformationen
            language: Sprache für die Konversation
            user_name: Name des Benutzers
            ip_address: IP-Adresse des Users (optional)
            experimental_mode: Wenn True, werden consent_agreement und prefill_impersonation eingebunden

        Returns:
            Der vollständige System Prompt
        """
        # Engine-Delegation: PromptEngine hat Vorrang über Legacy-.txt-Pfad
        if self._engine and hasattr(self._engine, 'build_system_prompt'):
            try:
                variant = 'experimental' if experimental_mode else 'default'
                runtime_vars = {}
                if ip_address:
                    runtime_vars['ip_address'] = ip_address
                result = self._engine.build_system_prompt(variant=variant, runtime_vars=runtime_vars)
                if result:
                    log.debug("ChatPromptBuilder: System-Prompt via Engine erstellt (%d Zeichen)", len(result))
                    return result
            except Exception as e:
                log.warning("Engine build_system_prompt fehlgeschlagen, Fallback auf Legacy: %s", e)

        # Legacy-Pfad: .txt-basierte Prompt-Generierung
        char_name = character_data.get('char_name', 'Assistant')

        # Sprache aus user_profile laden (gleiche Quelle wie Engine)
        from routes.user_profile import get_user_profile_data
        profile = get_user_profile_data()
        language = profile.get('persona_language', 'english') or 'english'

        # Baue Core Prompt
        core_dict = self.build_core_prompt(char_name, language, user_name, ip_address, experimental_mode)

        # User-Name könnte im core_prompt aktualisiert worden sein
        profile_user_name = self.get_user_name()
        if profile_user_name and profile_user_name != 'User':
            user_name = profile_user_name

        # Baue Persona Prompt
        persona_prompt = self.build_persona_prompt(character_data, char_name, user_name, experimental_mode)

        # User Info Block
        user_info = core_dict.get('user_info', '')

        # Kombiniere Komponenten
        parts = []

        if core_dict['impersonation']:
            parts.append(core_dict['impersonation'])

        if core_dict['system_rule']:
            parts.append(core_dict['system_rule'])

        if persona_prompt:
            parts.append(persona_prompt)

        if user_info:
            parts.append(user_info)

        # Memory wird später in services/chat_service eingefügt

        if core_dict['time_sense']:
            parts.append(core_dict['time_sense'])

        if core_dict['output_format']:
            parts.append(core_dict['output_format'])

        # Experimental Consent am Ende des System Prompts
        if experimental_mode:
            consent = self._load_experimental_consent()
            if consent:
                parts.append(consent)

        full_prompt = "\n\n".join(parts)
        return full_prompt

    def build_prefill(self, char_name: str, user_name: str = 'User',
                      experimental_mode: bool = False) -> str:
        """
        Erstellt den Prefill-Text für die letzte Assistant-Nachricht (remember).

        Delegiert an die PromptEngine wenn verfügbar.

        Args:
            char_name: Name des Charakters
            user_name: Name des Benutzers
            experimental_mode: Wenn True, wird remember verwendet; sonst remember_default

        Returns:
            Der Prefill-Text (nur remember)
        """
        # Engine-Delegation
        if self._engine and hasattr(self._engine, 'build_prefill'):
            try:
                variant = 'experimental' if experimental_mode else 'default'
                result = self._engine.build_prefill(variant=variant)
                if result:
                    return result
            except Exception as e:
                log.warning("Engine build_prefill fehlgeschlagen, Fallback: %s", e)

        # Legacy-Pfad
        profile_user_name = self.get_user_name()
        if profile_user_name and profile_user_name != 'User':
            user_name = profile_user_name

        if experimental_mode:
            remember_text = self._master_prompts.get('remember', '').format(
                char_name=char_name,
                user_name=user_name
            )
        else:
            remember_text = self._master_prompts.get('remember_default', '').format(
                char_name=char_name,
                user_name=user_name
            )

        return remember_text

    def get_prefill_impersonation(self, char_name: str, user_name: str = 'User') -> str:
        """Gibt den prefill_impersonation Text zurück (für Messages, nicht System Prompt).

        Delegiert an die PromptEngine wenn verfügbar.
        """
        # Engine-Delegation
        if self._engine and hasattr(self._engine, 'resolve_prompt'):
            try:
                result = self._engine.resolve_prompt('prefill_impersonation', variant='experimental')
                if result:
                    return result
            except Exception as e:
                log.warning("Engine get_prefill_impersonation fehlgeschlagen, Fallback: %s", e)

        # Legacy-Pfad
        profile_user_name = self.get_user_name()
        if profile_user_name and profile_user_name != 'User':
            user_name = profile_user_name
        prefill_imp = self._master_prompts.get('prefill_impersonation', '')
        if prefill_imp:
            prefill_imp = prefill_imp.format(
                char_name=char_name,
                user_name=user_name
            )
        return prefill_imp

    def get_consent_dialog(self) -> List[Dict[str, str]]:
        """Gibt den Consent Dialog als Message-Liste zurück"""
        return self._load_consent_dialog()

    def get_dialog_injections(self, variant: str = None, experimental_mode: bool = True) -> List[Dict[str, str]]:
        """Gibt alle aktiven Dialog-Injections als flache Messages-Liste zurück.

        Delegiert an die PromptEngine wenn verfügbar, sonst Fallback auf consent_dialog.
        """
        if self._engine:
            try:
                v = variant or ('experimental' if experimental_mode else 'default')
                return self._engine.get_dialog_injections(variant=v)
            except Exception as e:
                log.warning("Engine get_dialog_injections fehlgeschlagen, Fallback: %s", e)
        # Legacy Fallback: consent_dialog als einzige Injection
        legacy = self._load_consent_dialog()
        return legacy if legacy else []
