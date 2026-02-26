"""
Integration Test: Afterthought E2E Flow (Mock-API).
Tests decision → followup workflow.
"""
from unittest.mock import patch


def _make_chat_service(mock_api_client, mock_engine):
    """Creates a ChatService with mocked API client and engine."""
    from utils.services.chat_service import ChatService
    with patch('utils.services.chat_service.ChatService.__init__', lambda self, api_client: None):
        service = ChatService.__new__(ChatService)
    service.api_client = mock_api_client
    service._engine = mock_engine
    return service


class TestAfterthoughtFlowE2E:
    def test_decision_then_followup(self, mock_api_client, test_character_data, sample_conversation, mock_engine):
        """Kompletter Afterthought-Ablauf: Decision=[afterthought_OK] → Followup-Stream"""
        from utils.api_request.types import ApiResponse, StreamEvent

        service = _make_chat_service(mock_api_client, mock_engine)

        # Step 1: Decision (letztes Wort = "[afterthought_OK]")
        mock_api_client.request.return_value = ApiResponse(
            success=True,
            content='Ich möchte noch etwas sagen über Katzen. [afterthought_OK]',
            usage={'input_tokens': 100, 'output_tokens': 30},
        )

        decision = service.afterthought_decision(
            conversation_history=sample_conversation,
            character_data=test_character_data,
            elapsed_time='5 Minuten',
            persona_id='default',
        )
        assert decision['decision'] is True
        assert len(decision['inner_dialogue']) > 0

        # Step 2: Followup (stream with inner dialogue)
        mock_api_client.stream.return_value = iter([
            StreamEvent('chunk', 'Übrigens, '),
            StreamEvent('chunk', 'magst du Katzen?'),
            StreamEvent('done', {
                'response': 'Übrigens, magst du Katzen?',
                'stats': {'api_input_tokens': 150, 'output_tokens': 20},
            }),
        ])

        events = list(service.afterthought_followup(
            conversation_history=sample_conversation,
            character_data=test_character_data,
            inner_dialogue=decision['inner_dialogue'],
            elapsed_time='5 Minuten',
            persona_id='default',
        ))

        chunks = [e for e in events if e[0] == 'chunk']
        dones = [e for e in events if e[0] == 'done']
        assert len(chunks) >= 1
        assert len(dones) == 1

    def test_decision_no_skips_followup(self, mock_api_client, test_character_data, sample_conversation, mock_engine):
        """Decision=[i_can_wait] → kein Followup nötig"""
        from utils.api_request.types import ApiResponse

        service = _make_chat_service(mock_api_client, mock_engine)
        mock_api_client.request.return_value = ApiResponse(
            success=True,
            content='Nein, ich habe nichts hinzuzufügen. [i_can_wait]',
            usage={'input_tokens': 100, 'output_tokens': 30},
        )

        decision = service.afterthought_decision(
            conversation_history=sample_conversation,
            character_data=test_character_data,
            elapsed_time='2 Minuten',
            persona_id='default',
        )
        assert decision['decision'] is False
