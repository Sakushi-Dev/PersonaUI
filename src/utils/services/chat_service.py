"""
Chat Service – Orchestriert Chat-Requests.

Verwendet die PromptEngine als einzige Prompt-Quelle.
- Core-System-Prompt (schlank) + read_file Tool für On-Demand Kontext
- Message-Assembly (History + User-Message + Remember)
- Stats-Berechnung (Token-Schätzungen)
- Afterthought Decision-Parsing (Ja/Nein Erkennung)
"""

from typing import Dict, Generator

from ..api_request import ApiClient, RequestConfig
from ..logger import log
from ..config import load_character


def _read_setting(key: str, default=None):
    """Liest ein Setting aus settings.json (user-Sektion) mit Defaults-Fallback."""
    try:
        from utils.settings_manager import get_value
        # cortexEnabled lives in the cortex section as 'enabled'
        if key == 'cortexEnabled':
            return get_value('cortex', 'enabled', default)
        return get_value('user', key, default)
    except Exception:
        return default


class ChatService:
    """
    Orchestriert Chat-Requests:
    PromptEngine → Messages zusammenstellen → API aufrufen → Response bereinigen
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
                log.info("ChatService: PromptEngine geladen")
            else:
                log.error("ChatService: PromptEngine nicht verfügbar!")
        except Exception as e:
            log.error("ChatService: PromptEngine konnte nicht geladen werden: %s", e)

    def _create_file_tool_executor(self, variant: str = 'default',
                                     runtime_vars: dict = None):
        """Creates the executor callback for read_file and write_file tool calls."""
        engine = self._engine

        def executor(tool_name: str, tool_input: dict):
            if tool_name == 'read_file':
                filename = tool_input.get('filename', '')
                if not filename:
                    return False, "Missing filename parameter"
                content = engine.read_prompt_file(filename, variant, runtime_vars)
                log.info("File-Tool read: %s (%d chars)", filename, len(content))
                return True, content
            elif tool_name == 'write_file':
                filename = tool_input.get('filename', '')
                content = tool_input.get('content', '')
                if not filename:
                    return False, "Missing filename parameter"
                if not content:
                    return False, "Missing content parameter"
                result = engine.write_prompt_file(filename, content, variant)
                log.info("File-Tool write: %s → %s", filename, result)
                return True, result
            else:
                return False, f"Unknown tool: {tool_name}"

        return executor

    def _load_cortex_context(self, persona_id: str = None) -> Dict[str, str]:
        """
        Lädt Cortex-Dateien als Placeholder-Werte für die PromptEngine.

        Prüft zuerst das cortexEnabled-Setting. Gibt bei deaktiviertem Cortex
        oder Fehler leere Strings zurück.

        Args:
            persona_id: Optional Persona-ID (Default: aktive Persona)

        Returns:
            Dict mit cortex_memory, cortex_soul, cortex_relationship
        """
        empty = {
            'cortex_memory': '',
            'cortex_soul': '',
            'cortex_relationship': '',
        }

        # Setting-Check: Cortex global deaktiviert?
        if not _read_setting('cortexEnabled', True):
            return empty

        try:
            from ..provider import get_cortex_service
            cortex_service = get_cortex_service()

            if persona_id is None:
                from ..config import get_active_persona_id
                persona_id = get_active_persona_id()

            return cortex_service.get_cortex_for_prompt(persona_id)
        except Exception as e:
            log.warning("Cortex-Kontext konnte nicht geladen werden: %s", e)
            return empty

    def _build_chat_messages(self, user_message: str, conversation_history: list,
                              char_name: str, user_name: str,
                              nsfw_mode: bool, pending_afterthought: str = None) -> tuple:
        """
        Baut die Messages-Liste für den Chat-Request auf.

        Einfache Struktur: History → Afterthought-Kontext → User-Message.
        Kein Prefill, keine Dialog-Injections — die API liest Kontext per File-Tool.

        Returns:
            Tuple (messages, stats_dict) mit der fertigen Messages-Liste und
            den Zeichenlängen-Schätzungen für den Token-Breakdown.
        """
        messages = []
        history_tokens_est = 0

        effective_history = list(conversation_history) if conversation_history else []

        # 1. History einfügen
        if effective_history:
            for msg in effective_history:
                messages.append(msg)
                history_tokens_est += len(msg.get('content', ''))

            log.info("API-Request: History %d msgs (roles: %s)",
                     len(effective_history),
                     ' → '.join(m['role'][0] for m in effective_history))

        # 2. Pending Afterthought: inner dialogue as context before the user message
        if pending_afterthought:
            afterthought_note = f"[Dein letzter innerer Gedanke, {user_name} könnte auch aufgefallen sein das du in Gedanken warst — nutze ihn als Kontext:]\n{pending_afterthought}"
            if messages and messages[-1]['role'] == 'assistant':
                messages[-1]['content'] += "\n\n" + afterthought_note
            else:
                messages.append({'role': 'assistant', 'content': afterthought_note})
            history_tokens_est += len(afterthought_note)
            log.info("Pending afterthought injected (%d chars)", len(pending_afterthought))

        # 3. User-Nachricht hinzufügen
        if messages and messages[-1]['role'] == 'user':
            messages[-1]['content'] += "\n\n" + user_message
        else:
            messages.append({'role': 'user', 'content': user_message})
        user_msg_est = len(user_message)

        return messages, {
            'history_est': history_tokens_est,
            'user_msg_est': user_msg_est,
            'prefill_est': 0
        }

    def chat_stream(self, user_message: str, conversation_history: list,
                    character_data: dict, language: str = 'english',
                    user_name: str = 'User', api_model: str = None,
                    api_temperature: float = None,
                    ip_address: str = None, experimental_mode: bool = False,
                    persona_id: str = None, pending_afterthought: str = None,
                    session_id: int = None) -> Generator:
        """
        Haupt-Chat-Stream.

        Yields:
            Tuples (event_type, event_data) – kompatibel mit bisherigem Interface
        """
        temperature = api_temperature if api_temperature is not None else 0.7

        if character_data is None:
            character_data = load_character()

        char_name = character_data.get('char_name', 'Assistant')

        # 1. System-Prompt via PromptEngine bauen (schlanker Core + File-Index)
        variant = 'experimental' if experimental_mode else 'default'
        system_prompt = ''
        runtime_vars = {}
        tools = []
        if self._engine:
            if ip_address:
                runtime_vars['ip_address'] = ip_address
            # Last Encounter berechnen
            try:
                from ..last_encounter import compute_last_encounter
                runtime_vars['last_encounter'] = compute_last_encounter(
                    session_id=session_id, persona_id=persona_id
                )
            except Exception as e:
                log.warning("last_encounter computation failed: %s", e)
            system_prompt = self._engine.build_core_system_prompt(variant=variant, runtime_vars=runtime_vars) or ''
            tools = self._engine.get_chat_tools(variant=variant)
        else:
            log.error("ChatService: Kein System-Prompt — PromptEngine nicht verfügbar!")
        system_prompt_est = len(system_prompt)

        # 2. Messages zusammenbauen
        messages, msg_stats = self._build_chat_messages(
            user_message, conversation_history,
            char_name, user_name, experimental_mode,
            pending_afterthought=pending_afterthought
        )

        # Debug: Zeige was tatsächlich an die API gesendet wird
        log.debug("API-Messages (%d total): %s",
                  len(messages),
                  ' → '.join(f"{m['role']}({len(m['content'])})" for m in messages))
        if conversation_history:
            log.debug("Input-History (%d msgs): starts with %s",
                      len(conversation_history),
                      conversation_history[0]['role'] if conversation_history else 'empty')

        # 3. RequestConfig erstellen
        config = RequestConfig(
            system_prompt=system_prompt,
            messages=messages,
            model=api_model,
            max_tokens=4096 if tools else 500,
            temperature=temperature,
            stream=True,
            tools=tools if tools else None,
            request_type='chat'
        )

        # 4. Stream über ApiClient (mit File-Tool Support)
        file_executor = self._create_file_tool_executor(variant, runtime_vars) if tools else None
        stream_method = (
            self.api_client.stream_with_tools(config, file_executor)
            if tools and file_executor
            else self.api_client.stream(config)
        )
        for event in stream_method:
            if event.event_type == 'chunk':
                yield ('chunk', event.data)
            elif event.event_type == 'done':
                # Stats berechnen
                total_est = system_prompt_est + msg_stats['history_est'] + msg_stats['user_msg_est'] + msg_stats['prefill_est']
                yield ('done', {
                    'response': event.data['response'],
                    'stats': {
                        'api_input_tokens': event.data.get('api_input_tokens', 0),
                        'output_tokens': event.data.get('output_tokens', 0),
                        'system_prompt_est': system_prompt_est,
                        'history_est': msg_stats['history_est'],
                        'user_msg_est': msg_stats['user_msg_est'],
                        'prefill_est': msg_stats['prefill_est'],
                        'total_est': total_est
                    }
                })
            elif event.event_type == 'error':
                yield ('error', event.data)

    def afterthought_decision(self, conversation_history: list, character_data: dict,
                               elapsed_time: str, language: str = 'english', user_name: str = 'User',
                               api_model: str = None, api_temperature: float = None,
                               ip_address: str = None, nsfw_mode: bool = False,
                               persona_id: str = None) -> dict:
        """
        Innerer Dialog der Persona.

        Returns:
            {'decision': bool, 'inner_dialogue': str, 'error': str|None}
        """
        if not self.api_client.is_ready:
            return {'decision': False, 'inner_dialogue': '', 'error': 'Client nicht initialisiert'}

        temperature = api_temperature if api_temperature is not None else 0.7

        if character_data is None:
            character_data = load_character()

        try:
            # Baue den inneren Dialog Prompt via Engine
            variant = 'experimental' if nsfw_mode else 'default'
            runtime_vars = {
                'elapsed_time': elapsed_time,
            }
            if ip_address:
                runtime_vars['ip_address'] = ip_address
            # Cortex-Daten laden und als runtime_vars hinzufügen
            cortex_data = self._load_cortex_context(persona_id)
            runtime_vars.update(cortex_data)

            if not self._engine:
                return {'decision': False, 'inner_dialogue': '', 'error': 'PromptEngine nicht verfügbar'}

            system_prompt = self._engine.build_full_system_prompt(variant=variant, runtime_vars=runtime_vars) or ''
            append = self._engine.get_system_prompt_append(variant=variant, runtime_vars=runtime_vars) or ''
            if append:
                system_prompt = system_prompt + "\n\n" + append

            inner_dialogue_instruction = self._engine.build_afterthought_inner_dialogue(
                variant=variant, runtime_vars=runtime_vars
            ) or ''

            # Nachrichtenverlauf + innere Dialog-Anweisung
            messages = []
            if conversation_history:
                messages.extend(conversation_history)

            messages.append({'role': 'user', 'content': inner_dialogue_instruction})

            config = RequestConfig(
                system_prompt=system_prompt,
                messages=messages,
                model=api_model,
                max_tokens=1500,
                temperature=temperature,
                request_type='afterthought_decision'
            )

            response = self.api_client.request(config)

            if not response.success:
                return {'decision': False, 'inner_dialogue': '', 'error': response.error}

            inner_dialogue = response.content

            # Decision-Parsing: letztes Wort prüfen
            words = inner_dialogue.split()
            last_word = words[-1].strip('.,!?:;') if words else ''
            decision = last_word.lower() == '[afterthought_ok]'

            log.debug(
                "NACHGEDANKE INNERER DIALOG (%s) | Wörter: %d | Zeichen: %d | "
                "Letztes Wort (raw): '%s' | Bereinigt: '%s' | Stop Reason: %s",
                elapsed_time, len(words), len(inner_dialogue),
                words[-1] if words else '', last_word,
                response.stop_reason
            )
            log.info(
                "Nachgedanke-Entscheidung: %s (letztes Wort: '%s')",
                '[afterthought_OK] → Ergänzung' if decision else '[i_can_wait] → Schweigen',
                last_word
            )

            return {
                'decision': decision,
                'inner_dialogue': inner_dialogue,
                'error': None
            }

        except Exception as e:
            log.error("Fehler bei Nachgedanke-Entscheidung: %s", e)
            return {'decision': False, 'inner_dialogue': '', 'error': str(e)}

    def afterthought_followup(self, conversation_history: list, character_data: dict,
                               inner_dialogue: str, elapsed_time: str,
                               language: str = 'english', user_name: str = 'User',
                               api_model: str = None, api_temperature: float = None,
                               ip_address: str = None, nsfw_mode: bool = False,
                               persona_id: str = None) -> Generator:
        """
        Streamt die Nachgedanke-Ergänzung.

        Yields:
            Tuples (event_type, event_data) – kompatibel mit bisherigem Interface
        """
        if not self.api_client.is_ready:
            yield ('error', 'Client nicht initialisiert')
            return

        temperature = api_temperature if api_temperature is not None else 0.7

        if character_data is None:
            character_data = load_character()

        try:
            # Baue den Followup-Prompt via Engine
            variant = 'experimental' if nsfw_mode else 'default'
            runtime_vars = {
                'elapsed_time': elapsed_time,
                'inner_dialogue': inner_dialogue,
            }
            if ip_address:
                runtime_vars['ip_address'] = ip_address
            # Cortex-Daten laden und als runtime_vars hinzufügen
            cortex_data = self._load_cortex_context(persona_id)
            runtime_vars.update(cortex_data)

            if not self._engine:
                yield ('error', 'PromptEngine nicht verfügbar')
                return

            system_prompt = self._engine.build_full_system_prompt(variant=variant, runtime_vars=runtime_vars) or ''
            followup_instruction = self._engine.build_afterthought_followup(
                variant=variant, runtime_vars=runtime_vars
            ) or ''
            system_prompt_est = len(system_prompt)

            # Nachrichtenverlauf + Followup-Anweisung
            messages = []
            if conversation_history:
                messages.extend(conversation_history)

            messages.append({'role': 'user', 'content': followup_instruction})

            # Prefill via Engine
            prefill_text = self._engine.build_prefill(variant=variant) or ''
            prefill_est = len(prefill_text) if prefill_text else 0

            config = RequestConfig(
                system_prompt=system_prompt,
                messages=messages,
                model=api_model,
                max_tokens=200,
                temperature=temperature,
                stream=True,
                prefill=prefill_text if prefill_text else None,
                request_type='afterthought_followup'
            )

            for event in self.api_client.stream(config):
                if event.event_type == 'chunk':
                    yield ('chunk', event.data)
                elif event.event_type == 'done':
                    yield ('done', {
                        'response': event.data['response'],
                        'stats': {
                            'api_input_tokens': event.data.get('api_input_tokens', 0),
                            'output_tokens': event.data.get('output_tokens', 0),
                            'system_prompt_est': system_prompt_est,
                            'history_est': 0,
                            'user_msg_est': 0,
                            'prefill_est': prefill_est,
                            'total_est': system_prompt_est + prefill_est
                        }
                    })
                elif event.event_type == 'error':
                    yield ('error', event.data)

        except Exception as e:
            log.error("Nachgedanke-Followup Fehler: %s", e)
            yield ('error', str(e))


