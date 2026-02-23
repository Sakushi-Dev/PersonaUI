"""
Shared Fixtures für alle Tests.
Mock-API, Test-Personas, Sample-Data.
"""
import sys
import os
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from dataclasses import dataclass

# Projektpfad einrichten
SRC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src')
sys.path.insert(0, SRC_DIR)

# Working directory auf src/ setzen (Templates erwarten relative Pfade)
os.chdir(SRC_DIR)


# ============================================================
# Character Data / Persona Fixtures
# ============================================================

@pytest.fixture
def test_character_data():
    """Standard Persona für Tests"""
    return {
        'char_name': 'TestPersona',
        'desc': 'Eine Test-Persona für Unit-Tests.',
        'start_msg_enabled': True,
        'background': 'TestPersona wurde in einer kleinen Stadt geboren.',
        'identity': 'TestPersona, 25, weiblich',
        'core': 'Freundlich und hilfsbereit',
        'behavior': 'Antwortet stets höflich',
        'comms': 'Spricht deutsch',
        'voice': 'Ruhig und freundlich',
    }


@pytest.fixture
def minimal_character_data():
    """Minimale Persona — nur Pflichtfelder"""
    return {
        'char_name': 'Mini',
        'desc': '',
        'start_msg_enabled': False,
        'background': '',
        'identity': '',
        'core': '',
        'behavior': '',
        'comms': '',
        'voice': '',
    }


# ============================================================
# Conversation Fixtures
# ============================================================

@pytest.fixture
def sample_conversation():
    """Beispiel-Konversation (user/assistant abwechselnd)"""
    return [
        {'role': 'user', 'content': 'Hallo, wie geht es dir?'},
        {'role': 'assistant', 'content': 'Mir geht es gut, danke der Nachfrage!'},
        {'role': 'user', 'content': 'Was machst du gerne?'},
        {'role': 'assistant', 'content': 'Ich unterhalte mich gerne mit dir!'},
    ]


@pytest.fixture
def empty_conversation():
    """Leere Konversation"""
    return []


# ============================================================
# Mock API Fixtures
# ============================================================

@pytest.fixture
def mock_anthropic():
    """Mock anthropic-Modul — kein echter API-Call"""
    with patch('utils.api_request.client.anthropic') as mock_mod:
        # Standard-Response
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='Test response')]
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50
        mock_response.stop_reason = 'end_turn'
        mock_mod.Anthropic.return_value.messages.create.return_value = mock_response
        yield mock_mod


@pytest.fixture
def mock_anthropic_stream():
    """Mock anthropic-Modul für Streaming"""
    with patch('utils.api_request.client.anthropic') as mock_mod:
        # Stream-Response simulieren
        mock_stream_ctx = MagicMock()

        # ContentBlockDelta Events
        delta1 = MagicMock()
        delta1.type = 'content_block_delta'
        delta1.delta.text = 'Hello '

        delta2 = MagicMock()
        delta2.type = 'content_block_delta'
        delta2.delta.text = 'World'

        # MessageStop Event
        stop_event = MagicMock()
        stop_event.type = 'message_stop'

        # Message am Ende
        final_message = MagicMock()
        final_message.usage.input_tokens = 80
        final_message.usage.output_tokens = 20

        mock_stream_ctx.__enter__ = MagicMock(return_value=mock_stream_ctx)
        mock_stream_ctx.__exit__ = MagicMock(return_value=False)
        mock_stream_ctx.__iter__ = MagicMock(return_value=iter([delta1, delta2, stop_event]))
        mock_stream_ctx.get_final_message.return_value = final_message

        mock_mod.Anthropic.return_value.messages.stream.return_value = mock_stream_ctx
        yield mock_mod


@pytest.fixture
def api_client(mock_anthropic):
    """Initialisierter ApiClient mit Mock"""
    from utils.api_request import ApiClient
    client = ApiClient(api_key='test-key-123')
    return client


@pytest.fixture
def api_client_stream(mock_anthropic_stream):
    """Initialisierter ApiClient mit Stream-Mock"""
    from utils.api_request import ApiClient
    client = ApiClient(api_key='test-key-123')
    return client


# ============================================================
# Service Fixtures
# ============================================================

@pytest.fixture
def mock_api_client():
    """Komplett gemockter ApiClient (ohne anthropic)"""
    from utils.api_request.types import ApiResponse, StreamEvent
    client = MagicMock()
    client.is_ready = True
    client.request.return_value = ApiResponse(
        success=True,
        content='Mocked response',
        usage={'input_tokens': 100, 'output_tokens': 50},
        stop_reason='end_turn',
    )
    return client


@pytest.fixture
def mock_engine():
    """Gemockte PromptEngine für ChatService"""
    engine = MagicMock()
    engine.is_loaded = True
    engine.build_system_prompt.return_value = (
        'Du bist TestPersona. Eine Test-Persona für Unit-Tests.\n\n'
        'Antworte immer auf Deutsch. Bleibe stets in deiner Rolle als TestPersona.'
    )
    engine.build_prefill.return_value = 'Ich antworte als TestPersona:'
    engine.resolve_prompt.return_value = 'Ich bin TestPersona und bleibe in meiner Rolle.'
    engine.get_dialog_injections.return_value = []
    engine.get_system_prompt_append.return_value = ''
    engine.build_afterthought_inner_dialogue.return_value = 'Innerer Dialog Anweisung'
    engine.build_afterthought_followup.return_value = 'Followup Anweisung'
    engine.get_chat_message_sequence.return_value = [
        {'id': 'memory_context', 'position': 'first_assistant', 'order': 100},
        {'id': 'conversation_history', 'position': 'history', 'order': 200},
        {'id': 'remember', 'position': 'prefill', 'order': 300},
    ]
    return engine


@pytest.fixture
def chat_service(mock_api_client, mock_engine):
    """ChatService mit gemocktem API-Client und gemockter Engine"""
    from utils.services.chat_service import ChatService
    with patch('utils.services.chat_service.ChatService.__init__', lambda self, api_client: None):
        service = ChatService.__new__(ChatService)
    service.api_client = mock_api_client
    service._engine = mock_engine
    return service
