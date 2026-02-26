"""
Chat Service – Orchestriert Chat-Requests.

Verwendet die PromptEngine als einzige Prompt-Quelle.
- Message-Assembly (Prefill + Dialog-Injections + History + User-Message + Remember)
- Stats-Berechnung (Token-Schätzungen)
- Afterthought Decision-Parsing (Ja/Nein Erkennung)
"""

from typing import Dict, Any, List, Generator

from ..api_request import ApiClient, RequestConfig, StreamEvent
from ..api_request.response_cleaner import clean_api_response
from ..logger import log
from ..config import load_character


def _read_setting(key: str, default=None):
    """Liest ein Setting aus user_settings.json mit defaults.json Fallback."""
    import os
    import json
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # user_settings.json
    path = os.path.join(base_dir, 'settings', 'user_settings.json')
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if key in data:
                return data[key]
    except Exception:
        pass

    # defaults.json Fallback
    path = os.path.join(base_dir, 'settings', 'defaults.json')
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get(key, default)
    except Exception:
        pass

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

    def _load_cortex_context(self, persona_id: str = None) -> Dict[str, str]:
        """
        Lädt Cortex-Dateien als Placeholder-Werte für die PromptEngine.

        Prüft zuerst das cortexEnabled-Setting. Gibt bei deaktiviertem Cortex
        oder Fehler leere Strings zurück (der requires_any-Check in der Engine
        überspringt dann den Cortex-Block).

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

        Die Reihenfolge wird durch die PromptEngine-Sequenz bestimmt:
        - first_assistant: Prefill-Impersonation
        - history: Konversationsverlauf ({{history}})
        - prefill: Remember als letzte Assistant-Message

        Returns:
            Tuple (messages, stats_dict) mit der fertigen Messages-Liste und
            den Zeichenlängen-Schätzungen für den Token-Breakdown.
        """
        messages = []
        history_tokens_est = 0
        variant = 'experimental' if nsfw_mode else 'default'

        effective_history = list(conversation_history) if conversation_history else []

        # Prefill-Impersonation nur im experimental mode
        prefill_imp_text = ''
        if nsfw_mode and self._engine:
            prefill_imp_text = self._engine.resolve_prompt('prefill_impersonation', variant='experimental') or ''

        # Dialog-Injections via Engine
        dialog_injections = []
        if nsfw_mode and self._engine:
            dialog_injections = self._engine.get_dialog_injections(variant=variant)

        # Message-Sequenz von Engine holen (bestimmt Reihenfolge)
        sequence = []
        if self._engine:
            try:
                sequence = self._engine.get_chat_message_sequence(variant=variant)
            except Exception:
                sequence = []

        # Fallback wenn keine Sequenz verfügbar
        if not sequence:
            sequence = [
                {'position': 'first_assistant', 'order': 100},
                {'position': 'history', 'order': 200},
                {'position': 'prefill', 'order': 300},
            ]

        prefill_text = ''
        history_processed = False

        for template in sequence:
            position = template['position']

            if position == 'first_assistant':
                # Prefill-Impersonation
                first_parts = []
                if prefill_imp_text:
                    first_parts.append(prefill_imp_text)

                if dialog_injections:
                    if first_parts and dialog_injections[0].get('role') == 'assistant':
                        combined = "\n\n".join(first_parts) + "\n\n" + dialog_injections[0].get('content', '')
                        messages.append({'role': 'assistant', 'content': combined})
                        history_tokens_est += len(combined)
                        for msg in dialog_injections[1:]:
                            messages.append(msg)
                            history_tokens_est += len(msg.get('content', ''))
                    elif first_parts:
                        first_assistant = "\n\n".join(first_parts)
                        messages.append({'role': 'assistant', 'content': first_assistant})
                        history_tokens_est += len(first_assistant)
                        for msg in dialog_injections:
                            messages.append(msg)
                            history_tokens_est += len(msg.get('content', ''))
                    else:
                        for msg in dialog_injections:
                            messages.append(msg)
                            history_tokens_est += len(msg.get('content', ''))
                    dialog_injections = []  # consumed
                elif first_parts:
                    first_assistant = "\n\n".join(first_parts)
                    messages.append({'role': 'assistant', 'content': first_assistant})
                    history_tokens_est += len(first_assistant)

            elif position == 'history':
                # {{history}} expandieren: Konversationsverlauf einfügen
                history_processed = True
                if effective_history:
                    # Wenn History mit assistant beginnt und letzte Message auch assistant ist
                    # (z.B. Auto-First-Message), Bridge einfügen statt zu mergen.
                    if messages and effective_history[0]['role'] == messages[-1]['role']:
                        if effective_history[0]['role'] == 'assistant':
                            # Bridge-Message damit erste Nachricht als eigene Nachricht bleibt
                            messages.append({'role': 'user', 'content': '[Beginn der Konversation]'})
                            log.debug("History-Bridge eingefügt (Auto-First-Message)")
                        else:
                            # Seltener Fall: beide user → zusammenführen
                            messages[-1]['content'] += "\n\n" + effective_history[0]['content']
                            history_tokens_est += len(effective_history[0].get('content', ''))
                            effective_history = effective_history[1:]

                    for msg in effective_history:
                        messages.append(msg)
                        history_tokens_est += len(msg.get('content', ''))

                    log.info("API-Request: History %d msgs (roles: %s)",
                             len(effective_history),
                             ' → '.join(m['role'][0] for m in effective_history))

            elif position == 'prefill':
                # Prefill-Content aus Engine holen
                if self._engine:
                    pf = self._engine.build_prefill(variant=variant) or ''
                    if pf:
                        if history_processed:
                            # Nach History → echter Prefill (nach user_message)
                            prefill_text = pf
                        else:
                            # Vor History → reguläre Assistant-Message
                            if messages and messages[-1]['role'] == 'assistant':
                                messages[-1]['content'] += "\n\n" + pf
                            else:
                                messages.append({'role': 'assistant', 'content': pf})
                            history_tokens_est += len(pf)

        # Safety: Falls History nicht in der Sequenz war, trotzdem einfügen
        if not history_processed and effective_history:
            log.warning("History wurde nicht durch Sequenz verarbeitet – Fallback-Einfügung")
            if messages and effective_history[0]['role'] == messages[-1]['role']:
                if effective_history[0]['role'] == 'assistant':
                    messages.append({'role': 'user', 'content': '[Beginn der Konversation]'})
                else:
                    messages[-1]['content'] += "\n\n" + effective_history[0]['content']
                    history_tokens_est += len(effective_history[0].get('content', ''))
                    effective_history = effective_history[1:]
            for msg in effective_history:
                messages.append(msg)
                history_tokens_est += len(msg.get('content', ''))

        # Pending Afterthought: inject the persona's last inner dialogue (from [i_can_wait])
        # as context before the user message so the persona remembers what it was thinking.
        if pending_afterthought:
            afterthought_note = f"[Dein letzter innerer Gedanke, {user_name} könnte auch aufgefallen sein das du in Gedanken warst — nutze ihn als Kontext:]\n{pending_afterthought}"
            if messages and messages[-1]['role'] == 'assistant':
                messages[-1]['content'] += "\n\n" + afterthought_note
            else:
                messages.append({'role': 'assistant', 'content': afterthought_note})
            history_tokens_est += len(afterthought_note)
            log.info("Pending afterthought injected (%d chars)", len(pending_afterthought))

        # User-Nachricht hinzufügen
        # Falls History mit user endet, zusammenführen um doppelte user-Rolle zu vermeiden
        if messages and messages[-1]['role'] == 'user':
            messages[-1]['content'] += "\n\n" + user_message
        else:
            messages.append({'role': 'user', 'content': user_message})
        user_msg_est = len(user_message)

        # Prefill als letzte Assistant-Nachricht (wenn nach History)
        prefill_est = 0
        if prefill_text:
            messages.append({'role': 'assistant', 'content': prefill_text})
            prefill_est = len(prefill_text)

        return messages, {
            'history_est': history_tokens_est,
            'user_msg_est': user_msg_est,
            'prefill_est': prefill_est
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

        # 1. System-Prompt via PromptEngine bauen
        variant = 'experimental' if experimental_mode else 'default'
        system_prompt = ''
        if self._engine:
            runtime_vars = {}
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
            # Cortex-Daten laden und als runtime_vars hinzufügen
            cortex_data = self._load_cortex_context(persona_id)
            runtime_vars.update(cortex_data)
            system_prompt = self._engine.build_system_prompt(variant=variant, runtime_vars=runtime_vars) or ''
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
            max_tokens=500,
            temperature=temperature,
            stream=True,
            request_type='chat'
        )

        # 4. Stream über ApiClient
        for event in self.api_client.stream(config):
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

        char_name = character_data.get('char_name', 'Assistant')

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

            system_prompt = self._engine.build_system_prompt(variant=variant, runtime_vars=runtime_vars) or ''
            append = self._engine.get_system_prompt_append(variant=variant, runtime_vars=runtime_vars) or ''
            if append:
                system_prompt = system_prompt + append

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

        char_name = character_data.get('char_name', 'Assistant')

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

            system_prompt = self._engine.build_system_prompt(variant=variant, runtime_vars=runtime_vars) or ''
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

    def generate_session_title(self, prompt: str, api_model: str = None) -> str:
        """Generiert einen kurzen Session-Titel"""
        config = RequestConfig(
            system_prompt='',
            messages=[{'role': 'user', 'content': prompt}],
            model=api_model,
            max_tokens=50,
            request_type='session_title'
        )
        response = self.api_client.request(config)
        return response.content if response.success else 'Neue Konversation'

