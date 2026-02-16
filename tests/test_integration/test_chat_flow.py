"""
Integration Test: Chat E2E Flow (Mock-API).
Testet den kompletten Pfad: PromptEngine → Message-Assembly → API → Response.
"""
import pytest
from unittest.mock import patch, MagicMock


def _make_chat_service(mock_api_client, mock_engine):
    """Creates a ChatService with mocked API client and engine."""
    from utils.services.chat_service import ChatService
    with patch('utils.services.chat_service.ChatService.__init__', lambda self, api_client: None):
        service = ChatService.__new__(ChatService)
    service.api_client = mock_api_client
    service._engine = mock_engine
    return service


class TestChatFlowE2E:
    """End-to-End Test für den Chat-Flow mit gemockter API"""

    def test_full_chat_request(self, mock_api_client, test_character_data, sample_memories, mock_engine):
        """Complete chat flow: Prompt + Memory + History → Stream"""
        from utils.api_request.types import StreamEvent

        service = _make_chat_service(mock_api_client, mock_engine)

        # Simulate stream
        mock_api_client.stream.return_value = iter([
            StreamEvent('chunk', 'Hallo! '),
            StreamEvent('chunk', 'Wie geht es dir?'),
            StreamEvent('done', {
                'response': 'Hallo! Wie geht es dir?',
                'stats': {
                    'api_input_tokens': 200,
                    'output_tokens': 30,
                    'system_prompt_est': 5000,
                    'memory_est': 300,
                    'history_est': 100,
                    'user_msg_est': 15,
                    'prefill_est': 50,
                    'total_est': 5465,
                },
            }),
        ])

        with patch.object(service, '_load_memory_context', return_value='Memory context here'):
            events = list(service.chat_stream(
                user_message='Hallo TestPersona!',
                conversation_history=[],
                character_data=test_character_data,
                language='de',
                user_name='Tester',
                persona_id='default',
            ))

        # Expected events
        chunks = [e for e in events if e[0] == 'chunk']
        dones = [e for e in events if e[0] == 'done']
        assert len(chunks) >= 1
        assert len(dones) == 1

        # Check stats structure
        _, done_data = dones[0]
        assert 'response' in done_data
        assert 'stats' in done_data
        stats = done_data['stats']
        assert 'api_input_tokens' in stats
        assert 'output_tokens' in stats

    def test_chat_with_history(self, mock_api_client, test_character_data, sample_conversation, mock_engine):
        """Chat with existing history"""
        from utils.api_request.types import StreamEvent

        service = _make_chat_service(mock_api_client, mock_engine)
        mock_api_client.stream.return_value = iter([
            StreamEvent('done', {'response': 'Antwort', 'stats': {}}),
        ])

        with patch.object(service, '_load_memory_context', return_value=''):
            events = list(service.chat_stream(
                user_message='Noch eine Frage',
                conversation_history=sample_conversation,
                character_data=test_character_data,
                persona_id='default',
            ))

        assert len(events) > 0

    def test_chat_error_handling(self, mock_api_client, test_character_data, mock_engine):
        """Chat stream with API error"""
        from utils.api_request.types import StreamEvent

        service = _make_chat_service(mock_api_client, mock_engine)
        mock_api_client.stream.return_value = iter([
            StreamEvent('error', 'credit_balance_exhausted'),
        ])

        with patch.object(service, '_load_memory_context', return_value=''):
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
    """Verifies that built prompts actually arrive in the API request."""

    def test_system_prompt_sent_to_api(self, mock_api_client, test_character_data, mock_engine):
        """System prompt from PromptEngine must arrive in RequestConfig.system_prompt"""
        from utils.api_request.types import StreamEvent, RequestConfig

        service = _make_chat_service(mock_api_client, mock_engine)

        mock_api_client.stream.return_value = iter([
            StreamEvent('done', {'response': 'ok', 'api_input_tokens': 10, 'output_tokens': 5}),
        ])

        with patch.object(service, '_load_memory_context', return_value=''):
            list(service.chat_stream(
                user_message='Hallo!',
                conversation_history=[],
                character_data=test_character_data,
                user_name='Tester',
                persona_id='default',
            ))

        # stream() must have been called exactly once
        mock_api_client.stream.assert_called_once()
        config = mock_api_client.stream.call_args[0][0]
        assert isinstance(config, RequestConfig)

        # System prompt must come exactly from the engine (no hardcoded append anymore)
        mock_engine.build_system_prompt.assert_called_once()
        assert config.system_prompt == mock_engine.build_system_prompt.return_value
        assert len(config.system_prompt) > 0

    def test_user_message_in_api_messages(self, mock_api_client, test_character_data, mock_engine):
        """User message must be contained in RequestConfig.messages"""
        from utils.api_request.types import StreamEvent

        service = _make_chat_service(mock_api_client, mock_engine)
        mock_api_client.stream.return_value = iter([
            StreamEvent('done', {'response': 'ok', 'api_input_tokens': 10, 'output_tokens': 5}),
        ])

        user_msg = 'Erzähl mir etwas über dich!'

        with patch.object(service, '_load_memory_context', return_value=''):
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

    def test_memory_context_in_api_messages(self, mock_api_client, test_character_data, mock_engine):
        """Memory context must appear in an assistant message in the API request"""
        from utils.api_request.types import StreamEvent

        service = _make_chat_service(mock_api_client, mock_engine)
        mock_api_client.stream.return_value = iter([
            StreamEvent('done', {'response': 'ok', 'api_input_tokens': 10, 'output_tokens': 5}),
        ])

        memory_text = 'Der User mag Katzen und heißt Max.'

        with patch.object(service, '_load_memory_context', return_value=memory_text):
            list(service.chat_stream(
                user_message='Hi',
                conversation_history=[],
                character_data=test_character_data,
                persona_id='default',
            ))

        config = mock_api_client.stream.call_args[0][0]
        all_content = ' '.join(m['content'] for m in config.messages)
        assert memory_text in all_content, (
            f"Memory-Kontext nicht im API-Request gefunden.\n"
            f"Erwartet: '{memory_text}'\n"
            f"Messages: {config.messages}"
        )

    def test_conversation_history_in_api_messages(self, mock_api_client, test_character_data,
                                                   sample_conversation, mock_engine):
        """Conversation history must arrive completely in the API request"""
        from utils.api_request.types import StreamEvent

        service = _make_chat_service(mock_api_client, mock_engine)
        mock_api_client.stream.return_value = iter([
            StreamEvent('done', {'response': 'ok', 'api_input_tokens': 10, 'output_tokens': 5}),
        ])

        with patch.object(service, '_load_memory_context', return_value=''):
            list(service.chat_stream(
                user_message='Neue Frage',
                conversation_history=sample_conversation,
                character_data=test_character_data,
                persona_id='default',
            ))

        config = mock_api_client.stream.call_args[0][0]
        all_content = ' '.join(m['content'] for m in config.messages)

        # Every history message must be contained in the request
        for msg in sample_conversation:
            assert msg['content'] in all_content, (
                f"History-Nachricht '{msg['content']}' nicht im API-Request gefunden"
            )

    def test_prefill_as_last_assistant_message(self, mock_api_client, test_character_data, mock_engine):
        """Prefill (remember) must be the last assistant message in the request"""
        from utils.api_request.types import StreamEvent

        service = _make_chat_service(mock_api_client, mock_engine)

        mock_api_client.stream.return_value = iter([
            StreamEvent('done', {'response': 'ok', 'api_input_tokens': 10, 'output_tokens': 5}),
        ])

        expected_prefill = mock_engine.build_prefill.return_value

        with patch.object(service, '_load_memory_context', return_value=''):
            list(service.chat_stream(
                user_message='Test',
                conversation_history=[],
                character_data=test_character_data,
                persona_id='default',
            ))

        config = mock_api_client.stream.call_args[0][0]

        if expected_prefill:
            # Prefill must be the last message and have role=assistant
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
        """RequestConfig must have stream=True and request_type='chat'"""
        from utils.api_request.types import StreamEvent

        service = _make_chat_service(mock_api_client, mock_engine)
        mock_api_client.stream.return_value = iter([
            StreamEvent('done', {'response': 'ok', 'api_input_tokens': 10, 'output_tokens': 5}),
        ])

        with patch.object(service, '_load_memory_context', return_value=''):
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
        """End-to-end: All prompt parts must arrive consistently in the API request"""
        from utils.api_request.types import StreamEvent, RequestConfig

        service = _make_chat_service(mock_api_client, mock_engine)
        mock_api_client.stream.return_value = iter([
            StreamEvent('chunk', 'Antwort'),
            StreamEvent('done', {'response': 'Antwort', 'api_input_tokens': 200, 'output_tokens': 30}),
        ])

        memory = 'User liebt Musik und spielt Gitarre.'
        user_msg = 'Spielst du auch ein Instrument?'

        with patch.object(service, '_load_memory_context', return_value=memory):
            events = list(service.chat_stream(
                user_message=user_msg,
                conversation_history=sample_conversation,
                character_data=test_character_data,
                user_name='Max',
                language='de',
                persona_id='default',
            ))

        # 1. API was called
        mock_api_client.stream.assert_called_once()
        config = mock_api_client.stream.call_args[0][0]
        assert isinstance(config, RequestConfig)

        # 2. System prompt not empty
        assert len(config.system_prompt) > 100, "System prompt too short"
        assert test_character_data['char_name'] in config.system_prompt

        # 3. Messages not empty
        assert len(config.messages) >= 2, "Too few messages in request"

        # 4. All content present in request
        all_content = ' '.join(m['content'] for m in config.messages)
        assert memory in all_content, "Memory missing in API request"
        assert user_msg in all_content, "User message missing in API request"
        for msg in sample_conversation:
            assert msg['content'] in all_content, f"History '{msg['content']}' missing"

        # 5. Role sequence correct (no consecutive duplicate roles)
        for i in range(1, len(config.messages)):
            assert config.messages[i]['role'] != config.messages[i-1]['role'], (
                f"Duplicate role at position {i-1}/{i}: "
                f"{config.messages[i-1]['role']} → {config.messages[i]['role']}"
            )

        # 6. Events came through correctly
        chunk_events = [e for e in events if e[0] == 'chunk']
        done_events = [e for e in events if e[0] == 'done']
        assert len(chunk_events) >= 1
        assert len(done_events) == 1


class TestGreetingInHistory:
    """Verifies that the greeting message is preserved as its own assistant message."""

    def test_greeting_not_merged_with_memory(self, mock_api_client, test_character_data, mock_engine):
        """Greeting must NOT be merged into the memory message."""
        from utils.api_request.types import StreamEvent

        service = _make_chat_service(mock_api_client, mock_engine)
        mock_api_client.stream.return_value = iter([
            StreamEvent('done', {'response': 'ok', 'api_input_tokens': 10, 'output_tokens': 5}),
        ])

        greeting_text = 'Hallo, wie kann ich dir heute helfen?'
        memory_text = 'Der User mag Katzen.'

        # History wie aus DB: Greeting als erste assistant-Nachricht
        history_with_greeting = [
            {'role': 'assistant', 'content': greeting_text},
            {'role': 'user', 'content': 'hey'},
        ]

        with patch.object(service, '_load_memory_context', return_value=memory_text):
            list(service.chat_stream(
                user_message='wie gehts dir?',
                conversation_history=history_with_greeting,
                character_data=test_character_data,
                persona_id='default',
            ))

        config = mock_api_client.stream.call_args[0][0]

        # Greeting must exist as its own message, NOT merged into memory
        assistant_messages = [m for m in config.messages if m['role'] == 'assistant']
        greeting_found_standalone = any(
            m['content'] == greeting_text for m in assistant_messages
        )
        assert greeting_found_standalone, (
            f"Greeting '{greeting_text}' is not its own assistant message!\n"
            f"Messages: {[(m['role'], m['content'][:60]) for m in config.messages]}"
        )

        # Memory must NOT contain the greeting
        memory_msg = assistant_messages[0]  # first assistant = memory
        assert greeting_text not in memory_msg['content'], (
            "Greeting was merged into the memory message!"
        )

    def test_greeting_visible_on_second_turn(self, mock_api_client, test_character_data, mock_engine):
        """On the second user turn, the entire previous conversation including greeting must be visible."""
        from utils.api_request.types import StreamEvent

        service = _make_chat_service(mock_api_client, mock_engine)
        mock_api_client.stream.return_value = iter([
            StreamEvent('done', {'response': 'ok', 'api_input_tokens': 10, 'output_tokens': 5}),
        ])

        # History nach erstem Austausch: Greeting + 1. Frage + 1. Antwort
        history = [
            {'role': 'assistant', 'content': 'Hallo, wie kann ich dir heute helfen?'},
            {'role': 'user', 'content': 'hey'},
            {'role': 'assistant', 'content': 'Hey! Schön, dass du da bist.'},
        ]

        with patch.object(service, '_load_memory_context', return_value=''):
            list(service.chat_stream(
                user_message='mir gehts gut und dir?',
                conversation_history=history,
                character_data=test_character_data,
                persona_id='default',
            ))

        config = mock_api_client.stream.call_args[0][0]
        all_content = ' '.join(m['content'] for m in config.messages)

        # All history messages must be in the request
        for msg in history:
            assert msg['content'] in all_content, (
                f"History '{msg['content']}' fehlt im API-Request"
            )

    def test_no_consecutive_same_roles_with_greeting(self, mock_api_client, test_character_data, mock_engine):
        """No consecutive duplicate roles — even with memory + greeting."""
        from utils.api_request.types import StreamEvent

        service = _make_chat_service(mock_api_client, mock_engine)
        mock_api_client.stream.return_value = iter([
            StreamEvent('done', {'response': 'ok', 'api_input_tokens': 10, 'output_tokens': 5}),
        ])

        history = [
            {'role': 'assistant', 'content': 'Hallo!'},
            {'role': 'user', 'content': 'hey'},
        ]

        with patch.object(service, '_load_memory_context', return_value='Memory data here'):
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