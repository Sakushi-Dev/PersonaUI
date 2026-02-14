"""
Integration Test: Memory Create+Save E2E Flow (Mock-API).
Testet Preview → Save Ablauf.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestMemoryFlowE2E:
    def test_preview_then_save(self, mock_api_client):
        """Kompletter Memory-Flow: Preview → Save"""
        from utils.services.memory_service import MemoryService
        from utils.api_request.types import ApiResponse

        service = MemoryService(mock_api_client)

        mock_messages = [
            {'id': 1, 'is_user': True, 'message': 'Ich mag Katzen', 'character_name': 'TestPersona'},
            {'id': 2, 'is_user': False, 'message': 'Das ist schön!', 'character_name': 'TestPersona'},
            {'id': 3, 'is_user': True, 'message': 'Besonders Perserkatzen', 'character_name': 'TestPersona'},
            {'id': 4, 'is_user': False, 'message': 'Die sind wirklich elegant.', 'character_name': 'TestPersona'},
        ]
        mock_result = {'messages': mock_messages, 'truncated': False, 'total': 4}

        mock_api_client.request.return_value = ApiResponse(
            success=True,
            content='Der User mag Katzen, besonders Perserkatzen.',
            usage={'input_tokens': 300, 'output_tokens': 50},
        )

        # Step 1: Preview
        with patch('utils.services.memory_service.get_messages_since_marker', return_value=mock_result):
            preview = service.create_summary_preview(session_id=1, persona_id='default')

        assert preview is not None
        assert 'Erinnerung vom' in preview
        assert 'Katzen' in preview

        # Step 2: Save
        with patch('utils.services.memory_service.get_messages_since_marker', return_value=mock_result), \
             patch('utils.services.memory_service.save_memory', return_value=1), \
             patch('utils.services.memory_service.set_last_memory_message_id'), \
             patch('utils.services.memory_service.get_max_message_id', return_value=4):
            result = service.save_session_memory(session_id=1, persona_id='default')

        assert result['success'] is True
        assert result['memory_id'] == 1

    def test_custom_memory_save(self, mock_api_client):
        """Custom Memory speichern (ohne API-Call)"""
        from utils.services.memory_service import MemoryService

        service = MemoryService(mock_api_client)

        with patch('utils.services.memory_service.save_memory', return_value=42), \
             patch('utils.services.memory_service.set_last_memory_message_id'), \
             patch('utils.services.memory_service.get_max_message_id', return_value=10), \
             patch('utils.services.memory_service.get_last_memory_message_id', return_value=0):
            result = service.save_custom_memory(
                session_id=1, content='Benutzerdefinierte Erinnerung',
                persona_id='default',
            )

        assert result['success'] is True
        assert result['memory_id'] == 42
        # Kein API-Call nötig
        mock_api_client.request.assert_not_called()

    def test_save_with_no_messages_fails(self, mock_api_client):
        """Save ohne Nachrichten → Fehler"""
        from utils.services.memory_service import MemoryService

        service = MemoryService(mock_api_client)
        mock_result = {'messages': [], 'truncated': False, 'total': 0}

        with patch('utils.services.memory_service.get_messages_since_marker', return_value=mock_result):
            result = service.save_session_memory(session_id=1, persona_id='default')

        assert result['success'] is False
