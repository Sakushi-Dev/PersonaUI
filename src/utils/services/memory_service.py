"""
Memory Service – Orchestriert Memory-Operationen.

Ersetzt utils/memory.py vollständig:
- DB laden → Prompt bauen → API aufrufen → DB speichern

Verwendet PromptEngine als einzige Prompt-Quelle.
"""

import os
import re
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..api_request import ApiClient, RequestConfig
from ..prompt_engine.memory_context import format_memories_for_prompt
from ..database import (
    get_active_memories,
    save_memory,
    get_messages_since_marker,
    get_max_message_id,
    set_last_memory_message_id,
    get_last_memory_message_id,
)
from ..logger import log


class MemoryService:
    """
    Orchestriert Memory-Operationen:
    DB laden → Prompt bauen → API aufrufen → DB speichern
    """

    def __init__(self, api_client: ApiClient):
        self.api_client = api_client

        # PromptEngine als einzige Prompt-Quelle
        self._engine = None
        try:
            from ..provider import get_prompt_engine
            engine = get_prompt_engine()
            if engine and engine.is_loaded:
                self._engine = engine
        except Exception:
            pass

    def _get_active_persona_id(self, persona_id: str = None) -> str:
        """Holt aktive Persona-ID falls keine übergeben"""
        if persona_id is not None:
            return persona_id
        try:
            from ..config import get_active_persona_id
            return get_active_persona_id()
        except Exception:
            return 'default'

    def _get_experimental_mode(self) -> bool:
        """Liest experimentalMode aus user_settings.json"""
        try:
            settings_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                'settings', 'user_settings.json'
            )
            if os.path.exists(settings_path):
                with open(settings_path, 'r', encoding='utf-8') as f:
                    user_settings = json.load(f)
                return user_settings.get('experimentalMode', False)
        except Exception:
            pass
        return False

    def get_formatted_memories(self, persona_id: str = None, max_memories: int = 30) -> str:
        """
        Holt Memories aus DB → Formatiert via memory_context.
        Wird von ChatService aufgerufen für den Memory-Kontext.
        """
        persona_id = self._get_active_persona_id(persona_id)
        memories = get_active_memories(persona_id=persona_id)
        return format_memories_for_prompt(memories, max_memories)

    def create_summary_preview(self, session_id: int, persona_id: str = None) -> Optional[str]:
        """
        Erstellt Memory-Zusammenfassung nur zur Vorschau (nicht speichern).

        Args:
            session_id: ID der Session
            persona_id: ID der Persona

        Returns:
            Zusammenfassung als String oder None
        """
        persona_id = self._get_active_persona_id(persona_id)

        # Hole Nachrichten seit letztem Marker
        result = get_messages_since_marker(session_id=session_id, persona_id=persona_id)
        messages = result['messages']

        if not messages or len(messages) < 4:
            return None

        # Konvertiere zu Format für Summary
        msg_list = self._convert_messages(messages)

        # Erstelle Summary
        summary = self._create_summary(msg_list, persona_id)
        return summary

    def save_session_memory(self, session_id: int, persona_id: str = None) -> Dict[str, Any]:
        """
        Erstellt + speichert Memory.

        Returns:
            {'success': bool, 'memory_id': int, ...} – Interface bleibt identisch!
        """
        try:
            persona_id = self._get_active_persona_id(persona_id)

            result = get_messages_since_marker(session_id=session_id, persona_id=persona_id)
            messages = result['messages']
            truncated = result.get('truncated', False)
            total_available = result.get('total', len(messages))

            if not messages or len(messages) < 4:
                return {'success': False, 'error': 'Mindestens 4 Nachrichten seit letzter Erinnerung erforderlich'}

            msg_list = self._convert_messages(messages)

            summary = self._create_summary(msg_list, persona_id)

            if summary:
                start_msg_id = messages[0].get('id') if messages else None
                end_msg_id = messages[-1].get('id') if messages else None

                memory_id = save_memory(
                    session_id, summary, persona_id=persona_id,
                    start_message_id=start_msg_id, end_message_id=end_msg_id
                )

                max_msg_id = get_max_message_id(session_id, persona_id=persona_id)
                if max_msg_id:
                    set_last_memory_message_id(session_id, max_msg_id, persona_id=persona_id)

                return {
                    'success': True,
                    'memory_id': memory_id,
                    'content': summary,
                    'last_memory_message_id': max_msg_id,
                    'context_truncated': truncated,
                    'context_total_available': total_available,
                    'context_used': len(messages)
                }
            else:
                return {'success': False, 'error': 'Zusammenfassung konnte nicht erstellt werden'}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def save_custom_memory(self, session_id: int, content: str,
                            persona_id: str = None) -> Dict[str, Any]:
        """Speichert einen vorgegebenen Memory-Content direkt"""
        try:
            persona_id = self._get_active_persona_id(persona_id)

            last_marker = get_last_memory_message_id(session_id, persona_id=persona_id)
            max_msg_id = get_max_message_id(session_id, persona_id=persona_id)

            start_msg_id = (last_marker + 1) if last_marker else 1
            end_msg_id = max_msg_id

            memory_id = save_memory(
                session_id, content, persona_id=persona_id,
                start_message_id=start_msg_id, end_message_id=end_msg_id
            )

            if max_msg_id:
                set_last_memory_message_id(session_id, max_msg_id, persona_id=persona_id)

            return {'success': True, 'memory_id': memory_id, 'last_memory_message_id': max_msg_id}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _convert_messages(self, messages: list) -> list:
        """Konvertiert DB-Messages zu Format für Summary"""
        msg_list = []
        for msg in messages:
            msg_list.append({
                'is_user': msg['is_user'],
                'message': msg['message'],
                'character_name': msg.get('character_name', 'Assistant')
            })
        return msg_list

    def _create_summary(self, msg_list: list, persona_id: str) -> Optional[str]:
        """
        Erstellt eine Memory-Zusammenfassung via API.

        Args:
            msg_list: Formatierte Nachrichtenliste
            persona_id: Persona-ID

        Returns:
            Datierte Zusammenfassung oder None
        """
        if not msg_list:
            return None

        experimental_mode = self._get_experimental_mode()
        variant = 'experimental' if experimental_mode else 'default'

        # Baue Prompts via PromptEngine
        if self._engine:
            prompt_data = self._engine.build_summary_prompt(variant=variant)

            # User-Prompt: Chat-Text formatieren + via Engine resolven
            chat_text = ""
            for msg in msg_list:
                role = "Benutzer" if msg['is_user'] else msg.get('character_name', 'Assistant')
                chat_text += f"{role}: {msg['message']}\n\n"

            runtime_vars = {'max_words': str(300), 'chat_text': chat_text.strip()}
            user_prompt = self._engine.resolve_prompt(
                'summary_user_prompt', variant='default', runtime_vars=runtime_vars
            )
        else:
            log.warning("PromptEngine nicht verfügbar für Summary-Erstellung")
            prompt_data = {'system_prompt': '', 'prefill': ''}
            user_prompt = None

        if not user_prompt:
            log.error("Summary user_prompt konnte nicht erstellt werden")
            return None

        # Baue Messages
        api_messages = [{'role': 'user', 'content': user_prompt}]

        config = RequestConfig(
            system_prompt=prompt_data['system_prompt'],
            messages=api_messages,
            prefill=prompt_data['prefill'] if prompt_data['prefill'] else None,
            max_tokens=1500,
            temperature=0.5,
            request_type='memory_summary'
        )

        response = self.api_client.request(config)

        if response.success and response.content:
            content = response.content
            content = re.sub(r'^(Tagebucheintrag|Tagebuch|Eintrag|Diary)\s*:\s*', '', content, flags=re.IGNORECASE).strip()
            dated_summary = f"Erinnerung vom {datetime.now().strftime('%d.%m.%Y %H:%M')}\n{content}"
            return dated_summary

        log.error("Memory-Summary fehlgeschlagen: %s", response.error if not response.success else "Leerer Content")
        return None
