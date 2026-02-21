"""
Integration Test: Chat E2E Flow (Mock-API).
Testet den kompletten Pfad: PromptEngine → Message-Assembly → API → Response.
"""
from unittest.mock import patch


def _make_chat_service(mock_api_client, mock_engine):
    """Erstellt einen ChatService mit gemocktem API-Client und Engine."""
    from utils.services.chat_service import ChatService
    with patch('utils.services.chat_service.ChatService.__init__', lambda self, api_client: None):
        service = ChatService.__new__(ChatService)
    service.api_client = mock_api_client
    service._engine = mock_engine
    return service


class TestChatFlowE2E:
    """End-to-End Test für den Chat-Flow mit gemockter API"""

    def test_full_chat_request(self, mock_api_client, test_character_data, mock_engine):
        """Kompletter Chat-Flow: Prompt + History → Stream"""
        from utils.api_request.types import StreamEvent

        service = _make_chat_service(mock_api_client, mock_engine)

        # Stream simulieren
        mock_api_client.stream.return_value = iter([
            StreamEvent('chunk', 'Hallo! '),
            StreamEvent('chunk', 'Wie geht es dir?'),
            StreamEvent('done', {
                'response': 'Hallo! Wie geht es dir?',
                'stats': {
                    'api_input_tokens': 200,
                    'output_tokens': 30,
                    'system_prompt_est': 5000,
                    'history_est': 100,
                    'user_msg_est': 15,
                    'prefill_est': 50,
                    'total_est': 5165,
                },
            }),
        ])

        events = list(service.chat_stream(
            user_message='Hallo TestPersona!',
            conversation_history=[],
            character_data=test_character_data,
            language='de',
            user_name='Tester',
            persona_id='default',
        ))

        # Erwartete Events
        chunks = [e for e in events if e[0] == 'chunk']
        dones = [e for e in events if e[0] == 'done']
        assert len(chunks) >= 1
        assert len(dones) == 1

        # Stats-Struktur prüfen
        _, done_data = dones[0]
        assert 'response' in done_data
        assert 'stats' in done_data
        stats = done_data['stats']
        assert 'api_input_tokens' in stats
        assert 'output_tokens' in stats

    def test_chat_with_history(self, mock_api_client, test_character_data, sample_conversation, mock_engine):
        """Chat mit bestehender History"""
        from utils.api_request.types import StreamEvent

        service = _make_chat_service(mock_api_client, mock_engine)
        mock_api_client.stream.return_value = iter([
            StreamEvent('done', {'response': 'Antwort', 'stats': {}}),
        ])

        events = list(service.chat_stream(
            user_message='Noch eine Frage',
            conversation_history=sample_conversation,
            character_data=test_character_data,
            persona_id='default',
        ))

        assert len(events) > 0

    def test_chat_error_handling(self, mock_api_client, test_character_data, mock_engine):
        """Chat-Stream mit API-Fehler"""
        from utils.api_request.types import StreamEvent

        service = _make_chat_service(mock_api_client, mock_engine)
        mock_api_client.stream.return_value = iter([
            StreamEvent('error', 'credit_balance_exhausted'),
        ])

        events = list(service.chat_stream(
            user_message='Test',
            conversation_history=[],
            character_data=test_character_data,
            persona_id='default',
        ))

        errors = [e for e in events if e[0] == 'error']
        assert len(errors) == 1
        assert errors[0][1] == 'credit_balance_exhausted'


class TestPromptReachesApi:
    """Prüft, dass die gebauten Prompts tatsächlich im API-Request ankommen."""

    def test_system_prompt_sent_to_api(self, mock_api_client, test_character_data, mock_engine):
        """System-Prompt aus PromptEngine muss in RequestConfig.system_prompt ankommen"""
        from utils.api_request.types import StreamEvent, RequestConfig

        service = _make_chat_service(mock_api_client, mock_engine)

        mock_api_client.stream.return_value = iter([
            StreamEvent('done', {'response': 'ok', 'api_input_tokens': 10, 'output_tokens': 5}),
        ])

        list(service.chat_stream(
            user_message='Hallo!',
            conversation_history=[],
            character_data=test_character_data,
            user_name='Tester',
            persona_id='default',
        ))

        # stream() muss genau 1x aufgerufen worden sein
        mock_api_client.stream.assert_called_once()
        config = mock_api_client.stream.call_args[0][0]
        assert isinstance(config, RequestConfig)

        # System-Prompt muss exakt von der Engine kommen (kein hardcoded Append mehr)
        mock_engine.build_system_prompt.assert_called_once()
        assert config.system_prompt == mock_engine.build_system_prompt.return_value
        assert len(config.system_prompt) > 0

    def test_user_message_in_api_messages(self, mock_api_client, test_character_data, mock_engine):
        """User-Nachricht muss in RequestConfig.messages enthalten sein"""
        from utils.api_request.types import StreamEvent

        service = _make_chat_service(mock_api_client, mock_engine)
        mock_api_client.stream.return_value = iter([
            StreamEvent('done', {'response': 'ok', 'api_input_tokens': 10, 'output_tokens': 5}),
        ])

        user_msg = 'Erzähl mir etwas über dich!'

        list(service.chat_stream(
            user_message=user_msg,
            conversation_history=[],
            character_data=test_character_data,
            persona_id='default',
        ))

        config = mock_api_client.stream.call_args[0][0]
        user_messages = [m for m in config.messages if m['role'] == 'user']
        user_contents = [m['content'] for m in user_messages]
        assert user_msg in user_contents, (
            f"User-Nachricht '{user_msg}' nicht in API-Messages gefunden: {user_contents}"
        )

    def test_conversation_history_in_api_messages(self, mock_api_client, test_character_data,
                                                   sample_conversation, mock_engine):
        """Konversationshistorie muss vollständig im API-Request ankommen"""
        from utils.api_request.types import StreamEvent

        service = _make_chat_service(mock_api_client, mock_engine)
        mock_api_client.stream.return_value = iter([
            StreamEvent('done', {'response': 'ok', 'api_input_tokens': 10, 'output_tokens': 5}),
        ])

        list(service.chat_stream(
            user_message='Neue Frage',
            conversation_history=sample_conversation,
            character_data=test_character_data,
            persona_id='default',
        ))

        config = mock_api_client.stream.call_args[0][0]
        all_content = ' '.join(m['content'] for m in config.messages)

        # Jede History-Nachricht muss im Request enthalten sein
        for msg in sample_conversation:
            assert msg['content'] in all_content, (
                f"History-Nachricht '{msg['content']}' nicht im API-Request gefunden"
            )

    def test_prefill_as_last_assistant_message(self, mock_api_client, test_character_data, mock_engine):
        """Prefill (remember) muss als letzte Assistant-Message im Request sein"""
        from utils.api_request.types import StreamEvent

        service = _make_chat_service(mock_api_client, mock_engine)

        mock_api_client.stream.return_value = iter([
            StreamEvent('done', {'response': 'ok', 'api_input_tokens': 10, 'output_tokens': 5}),
        ])

        expected_prefill = mock_engine.build_prefill.return_value

        list(service.chat_stream(
            user_message='Test',
            conversation_history=[],
            character_data=test_character_data,
            persona_id='default',
        ))

        config = mock_api_client.stream.call_args[0][0]

        if expected_prefill:
            # Prefill muss die letzte Message sein und role=assistant haben
            last_msg = config.messages[-1]
            assert last_msg['role'] == 'assistant', (
                f"Letzte Message ist nicht assistant: {last_msg}"
            )
            assert last_msg['content'] == expected_prefill, (
                f"Prefill stimmt nicht überein.\n"
                f"Erwartet: '{expected_prefill}'\n"
                f"Tatsächlich: '{last_msg['content']}'"
            )

    def test_request_config_has_correct_settings(self, mock_api_client, test_character_data, mock_engine):
        """RequestConfig muss stream=True und request_type='chat' haben"""
        from utils.api_request.types import StreamEvent

        service = _make_chat_service(mock_api_client, mock_engine)
        mock_api_client.stream.return_value = iter([
            StreamEvent('done', {'response': 'ok', 'api_input_tokens': 10, 'output_tokens': 5}),
        ])

        list(service.chat_stream(
            user_message='Test',
            conversation_history=[],
            character_data=test_character_data,
            api_model='claude-sonnet-4-20250514',
            api_temperature=0.9,
            persona_id='default',
        ))

        config = mock_api_client.stream.call_args[0][0]
        assert config.stream is True
        assert config.request_type == 'chat'
        assert config.model == 'claude-sonnet-4-20250514'
        assert config.temperature == 0.9
        assert config.max_tokens == 500

    def test_complete_prompt_pipeline(self, mock_api_client, test_character_data,
                                      sample_conversation, mock_engine):
        """End-to-End: Alle Prompt-Teile müssen konsistent im API-Request ankommen"""
        from utils.api_request.types import StreamEvent, RequestConfig

        service = _make_chat_service(mock_api_client, mock_engine)
        mock_api_client.stream.return_value = iter([
            StreamEvent('chunk', 'Antwort'),
            StreamEvent('done', {'response': 'Antwort', 'api_input_tokens': 200, 'output_tokens': 30}),
        ])

        user_msg = 'Spielst du auch ein Instrument?'

        events = list(service.chat_stream(
            user_message=user_msg,
            conversation_history=sample_conversation,
            character_data=test_character_data,
            user_name='Max',
            language='de',
            persona_id='default',
        ))

        # 1. API wurde aufgerufen
        mock_api_client.stream.assert_called_once()
        config = mock_api_client.stream.call_args[0][0]
        assert isinstance(config, RequestConfig)

        # 2. System-Prompt nicht leer
        assert len(config.system_prompt) > 100, "System-Prompt zu kurz"
        assert test_character_data['char_name'] in config.system_prompt

        # 3. Messages nicht leer
        assert len(config.messages) >= 2, "Zu wenige Messages im Request"

        # 4. Alle Inhalte im Request vorhanden
        all_content = ' '.join(m['content'] for m in config.messages)
        assert user_msg in all_content, "User-Message fehlt im API-Request"
        for msg in sample_conversation:
            assert msg['content'] in all_content, f"History '{msg['content']}' fehlt"

        # 5. Rollen-Abfolge korrekt (keine doppelten gleichen Rollen hintereinander)
        for i in range(1, len(config.messages)):
            assert config.messages[i]['role'] != config.messages[i-1]['role'], (
                f"Doppelte Rolle an Position {i-1}/{i}: "
                f"{config.messages[i-1]['role']} → {config.messages[i]['role']}"
            )

        # 6. Events kamen korrekt durch
        chunk_events = [e for e in events if e[0] == 'chunk']
        done_events = [e for e in events if e[0] == 'done']
        assert len(chunk_events) >= 1
        assert len(done_events) == 1


class TestAutoFirstMessageInHistory:
    """Prüft, dass die Auto-First-Message als eigene Assistant-Message erhalten bleibt."""

    def test_auto_first_msg_is_standalone_assistant_message(self, mock_api_client, test_character_data, mock_engine):
        """Auto-First-Message muss als eigene Assistant-Message erhalten bleiben."""
        from utils.api_request.types import StreamEvent

        service = _make_chat_service(mock_api_client, mock_engine)
        mock_api_client.stream.return_value = iter([
            StreamEvent('done', {'response': 'ok', 'api_input_tokens': 10, 'output_tokens': 5}),
        ])

        first_msg_text = 'Hallo, wie kann ich dir heute helfen?'

        # History wie aus DB: Auto-First-Message als erste assistant-Nachricht
        history_with_first_msg = [
            {'role': 'assistant', 'content': first_msg_text},
            {'role': 'user', 'content': 'hey'},
        ]

        list(service.chat_stream(
            user_message='wie gehts dir?',
            conversation_history=history_with_first_msg,
            character_data=test_character_data,
            persona_id='default',
        ))

        config = mock_api_client.stream.call_args[0][0]

        # Auto-First-Message muss als eigene Assistant-Message existieren
        assistant_messages = [m for m in config.messages if m['role'] == 'assistant']
        first_msg_found_standalone = any(
            m['content'] == first_msg_text for m in assistant_messages
        )
        assert first_msg_found_standalone, (
            f"Auto-First-Message '{first_msg_text}' ist keine eigene Assistant-Message!\n"
            f"Messages: {[(m['role'], m['content'][:60]) for m in config.messages]}"
        )

    def test_first_msg_visible_on_second_turn(self, mock_api_client, test_character_data, mock_engine):
        """Beim zweiten User-Turn muss die gesamte bisherige Konversation inkl. First-Message sichtbar sein."""
        from utils.api_request.types import StreamEvent

        service = _make_chat_service(mock_api_client, mock_engine)
        mock_api_client.stream.return_value = iter([
            StreamEvent('done', {'response': 'ok', 'api_input_tokens': 10, 'output_tokens': 5}),
        ])

        # History nach erstem Austausch: Auto-First-Message + 1. Frage + 1. Antwort
        history = [
            {'role': 'assistant', 'content': 'Hallo, wie kann ich dir heute helfen?'},
            {'role': 'user', 'content': 'hey'},
            {'role': 'assistant', 'content': 'Hey! Schön, dass du da bist.'},
        ]

        list(service.chat_stream(
            user_message='mir gehts gut und dir?',
            conversation_history=history,
            character_data=test_character_data,
            persona_id='default',
        ))

        config = mock_api_client.stream.call_args[0][0]
        all_content = ' '.join(m['content'] for m in config.messages)

        # Alle History-Nachrichten müssen im Request sein
        for msg in history:
            assert msg['content'] in all_content, (
                f"History '{msg['content']}' fehlt im API-Request"
            )

    def test_no_consecutive_same_roles_with_first_msg(self, mock_api_client, test_character_data, mock_engine):
        """Keine doppelten gleichen Rollen — auch mit Auto-First-Message."""
        from utils.api_request.types import StreamEvent

        service = _make_chat_service(mock_api_client, mock_engine)
        mock_api_client.stream.return_value = iter([
            StreamEvent('done', {'response': 'ok', 'api_input_tokens': 10, 'output_tokens': 5}),
        ])

        history = [
            {'role': 'assistant', 'content': 'Hallo!'},
            {'role': 'user', 'content': 'hey'},
        ]

        list(service.chat_stream(
            user_message='Test',
            conversation_history=history,
            character_data=test_character_data,
            persona_id='default',
        ))

        config = mock_api_client.stream.call_args[0][0]

        for i in range(1, len(config.messages)):
            assert config.messages[i]['role'] != config.messages[i-1]['role'], (
                f"Doppelte Rolle an Position {i-1}/{i}: "
                f"{config.messages[i-1]['role']} → {config.messages[i]['role']}\n"
                f"Messages: {[(m['role'], m['content'][:50]) for m in config.messages]}"
            )
