"""
Tests für MemoryService — Summary-Erstellung + CRUD Orchestrierung.
"""
import pytest
from unittest.mock import MagicMock, patch


class TestMemoryServiceInit:
    def test_init(self, mock_api_client):
        from utils.services.memory_service import MemoryService
        service = MemoryService(mock_api_client)
        assert service.api_client is mock_api_client


class TestGetFormattedMemories:
    def test_returns_string(self, memory_service, sample_memories):
        with patch('utils.services.memory_service.get_active_memories', return_value=sample_memories):
            result = memory_service.get_formatted_memories(persona_id='default')
        assert isinstance(result, str)
        assert 'Test memory 1' in result

    def test_empty_memories(self, memory_service):
        with patch('utils.services.memory_service.get_active_memories', return_value=[]):
            result = memory_service.get_formatted_memories(persona_id='default')
        assert isinstance(result, str)
        assert result == ''


class TestCreateSummaryPreview:
    def test_returns_string_on_success(self, memory_service):
        from utils.api_request.types import ApiResponse

        mock_messages = [
            {'id': 1, 'is_user': True, 'message': 'Hallo', 'character_name': 'Test'},
            {'id': 2, 'is_user': False, 'message': 'Hi!', 'character_name': 'Test'},
            {'id': 3, 'is_user': True, 'message': 'Wie geht es?', 'character_name': 'Test'},
            {'id': 4, 'is_user': False, 'message': 'Gut, danke!', 'character_name': 'Test'},
        ]
        mock_result = {'messages': mock_messages, 'truncated': False, 'total': 4}

        memory_service.api_client.request.return_value = ApiResponse(
            success=True,
            content='Zusammenfassung des Gesprächs',
            usage={'input_tokens': 200, 'output_tokens': 100},
        )

        with patch('utils.services.memory_service.get_messages_since_marker', return_value=mock_result):
            result = memory_service.create_summary_preview(session_id=1, persona_id='default')

        assert result is not None
        assert isinstance(result, str)
        assert 'Erinnerung vom' in result

    def test_returns_none_on_no_messages(self, memory_service):
        mock_result = {'messages': [], 'truncated': False, 'total': 0}
        with patch('utils.services.memory_service.get_messages_since_marker', return_value=mock_result):
            result = memory_service.create_summary_preview(session_id=1, persona_id='default')
        assert result is None


class TestSaveSessionMemory:
    def test_returns_success_dict(self, memory_service):
        from utils.api_request.types import ApiResponse

        mock_messages = [
            {'id': 1, 'is_user': True, 'message': 'Hallo', 'character_name': 'Test'},
            {'id': 2, 'is_user': False, 'message': 'Hi!', 'character_name': 'Test'},
            {'id': 3, 'is_user': True, 'message': 'Frage', 'character_name': 'Test'},
            {'id': 4, 'is_user': False, 'message': 'Antwort', 'character_name': 'Test'},
        ]
        mock_result = {'messages': mock_messages, 'truncated': False, 'total': 4}

        memory_service.api_client.request.return_value = ApiResponse(
            success=True,
            content='Zusammenfassung',
            usage={'input_tokens': 200, 'output_tokens': 100},
        )

        with patch('utils.services.memory_service.get_messages_since_marker', return_value=mock_result), \
             patch('utils.services.memory_service.save_memory', return_value=42), \
             patch('utils.services.memory_service.set_last_memory_message_id'), \
             patch('utils.services.memory_service.get_max_message_id', return_value=4):
            result = memory_service.save_session_memory(session_id=1, persona_id='default')

        assert isinstance(result, dict)
        assert result['success'] is True
        assert result['memory_id'] == 42

    def test_returns_error_on_too_few_messages(self, memory_service):
        mock_result = {'messages': [
            {'id': 1, 'is_user': True, 'message': 'Hallo', 'character_name': 'Test'},
        ], 'truncated': False, 'total': 1}

        with patch('utils.services.memory_service.get_messages_since_marker', return_value=mock_result):
            result = memory_service.save_session_memory(session_id=1, persona_id='default')
        assert isinstance(result, dict)
        assert result['success'] is False


class TestSaveCustomMemory:
    def test_returns_success_dict(self, memory_service):
        with patch('utils.services.memory_service.save_memory', return_value=99), \
             patch('utils.services.memory_service.set_last_memory_message_id'), \
             patch('utils.services.memory_service.get_max_message_id', return_value=5), \
             patch('utils.services.memory_service.get_last_memory_message_id', return_value=0):
            result = memory_service.save_custom_memory(
                session_id=1, content='Benutzerdefinierte Erinnerung',
                persona_id='default',
            )
        assert isinstance(result, dict)
        assert result['success'] is True
        assert result['memory_id'] == 99
