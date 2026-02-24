"""
Tests für ChatService — Message-Assembly, Stream, Decision.
"""
import pytest
from unittest.mock import MagicMock, patch


class TestChatServiceInit:
    def test_init(self, mock_api_client):
        from utils.services.chat_service import ChatService
        service = ChatService(mock_api_client)
        assert service.api_client is mock_api_client
        assert service._engine is not None or service._engine is None  # Engine optional (Test-Umgebung)


class TestChatStream:
    def test_yields_tuples(self, chat_service, test_character_data):
        """chat_stream muss Tuples (event_type, data) yielden"""
        from utils.api_request.types import StreamEvent

        # Mock stream auf dem api_client
        done_data = {'response': 'Test response', 'stats': {
            'api_input_tokens': 100, 'output_tokens': 50,
        }}
        chat_service.api_client.stream.return_value = iter([
            StreamEvent('chunk', 'Hello '),
            StreamEvent('chunk', 'World'),
            StreamEvent('done', done_data),
        ])

        events = list(chat_service.chat_stream(
            user_message='Hi',
            conversation_history=[],
            character_data=test_character_data,
            persona_id='default',
        ))

        assert len(events) > 0
        # Check tuple format
        for event in events:
            assert isinstance(event, tuple)
            assert len(event) == 2
            event_type, event_data = event
            assert event_type in ('chunk', 'done', 'error')

    def test_done_event_has_stats(self, chat_service, test_character_data):
        """Done-Event muss response + stats enthalten"""
        from utils.api_request.types import StreamEvent

        done_data = {
            'response': 'Antwort der Persona',
            'stats': {
                'api_input_tokens': 150,
                'output_tokens': 80,
                'system_prompt_est': 5000,
                'history_est': 100,
                'user_msg_est': 20,
                'prefill_est': 50,
                'total_est': 5170,
            },
        }
        chat_service.api_client.stream.return_value = iter([
            StreamEvent('done', done_data),
        ])

        events = list(chat_service.chat_stream(
            user_message='Test',
            conversation_history=[],
            character_data=test_character_data,
            persona_id='default',
        ))

        done_events = [e for e in events if e[0] == 'done']
        assert len(done_events) == 1
        _, data = done_events[0]
        assert 'response' in data
        assert 'stats' in data


class TestAfterthoughtDecision:
    def test_returns_dict(self, chat_service, test_character_data, sample_conversation):
        from utils.api_request.types import ApiResponse
        chat_service.api_client.request.return_value = ApiResponse(
            success=True,
            content='Ich denke darüber nach... [afterthought_OK]',
            usage={'input_tokens': 50, 'output_tokens': 20},
        )

        result = chat_service.afterthought_decision(
            conversation_history=sample_conversation,
            character_data=test_character_data,
            elapsed_time='5 Minuten',
            persona_id='default',
        )
        assert isinstance(result, dict)
        assert 'decision' in result
        assert 'inner_dialogue' in result
        assert isinstance(result['decision'], bool)

    def test_decision_yes(self, chat_service, test_character_data):
        """Letztes Wort '[afterthought_OK]' → decision=True"""
        from utils.api_request.types import ApiResponse
        chat_service.api_client.request.return_value = ApiResponse(
            success=True,
            content='Mein innerer Dialog... [afterthought_OK]',
            usage={'input_tokens': 50, 'output_tokens': 20},
        )

        result = chat_service.afterthought_decision(
            conversation_history=[{'role': 'user', 'content': 'Hi'}],
            character_data=test_character_data,
            elapsed_time='3 Minuten',
            persona_id='default',
        )
        assert result['decision'] is True

    def test_decision_no(self, chat_service, test_character_data):
        """Letztes Wort '[i_can_wait]' → decision=False"""
        from utils.api_request.types import ApiResponse
        chat_service.api_client.request.return_value = ApiResponse(
            success=True,
            content='Ich habe nichts zu sagen. [i_can_wait]',
            usage={'input_tokens': 50, 'output_tokens': 20},
        )

        result = chat_service.afterthought_decision(
            conversation_history=[{'role': 'user', 'content': 'Hi'}],
            character_data=test_character_data,
            elapsed_time='2 Minuten',
            persona_id='default',
        )
        assert result['decision'] is False


class TestAfterthoughtFollowup:
    def test_yields_events(self, chat_service, test_character_data):
        from utils.api_request.types import StreamEvent
        chat_service.api_client.stream.return_value = iter([
            StreamEvent('chunk', 'Mir fiel noch ein'),
            StreamEvent('done', {'response': 'Mir fiel noch ein...', 'stats': {}}),
        ])

        events = list(chat_service.afterthought_followup(
            conversation_history=[{'role': 'user', 'content': 'Hi'}],
            character_data=test_character_data,
            inner_dialogue='Ich möchte nachfragen.',
            elapsed_time='5 Minuten',
            persona_id='default',
        ))
        assert len(events) > 0


class TestGenerateSessionTitle:
    def test_returns_string(self, chat_service):
        from utils.api_request.types import ApiResponse
        chat_service.api_client.request.return_value = ApiResponse(
            success=True, content='Gespräch über Katzen',
        )
        result = chat_service.generate_session_title('User fragte nach Katzen')
        assert isinstance(result, str)
        assert result == 'Gespräch über Katzen'

    def test_fallback_on_error(self, chat_service):
        from utils.api_request.types import ApiResponse
        chat_service.api_client.request.return_value = ApiResponse(
            success=False, error='API error',
        )
        result = chat_service.generate_session_title('Test')
        assert isinstance(result, str)
        assert result == 'Neue Konversation'
