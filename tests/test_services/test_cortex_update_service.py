"""
Tests für CortexUpdateService (Schritt 3C).

Testet:
- execute_update Flow (Success path, Error paths)
- Tool-Executor Mapping
- Rate-Limiting
- System-Prompt-Builder
- Message-Builder
"""

import pytest
import time
import threading
from unittest.mock import patch, MagicMock, PropertyMock

from utils.cortex.update_service import (
    CortexUpdateService, CORTEX_TOOLS,
    CORTEX_UPDATE_MAX_TOKENS, CORTEX_UPDATE_TEMPERATURE,
    RATE_LIMIT_SECONDS, _last_update_time, _rate_lock
)
from utils.api_request.types import ApiResponse


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_rate_limit():
    """Resettet Rate-Limit State vor jedem Test."""
    with _rate_lock:
        _last_update_time.clear()
    yield
    with _rate_lock:
        _last_update_time.clear()


@pytest.fixture
def service():
    return CortexUpdateService()


@pytest.fixture
def mock_character():
    return {
        'char_name': 'Mia',
        'identity': 'Mia, 22, weiblich',
        'core': 'Warmherzig und einfühlsam',
        'background': 'Aufgewachsen in einer kleinen Stadt'
    }


@pytest.fixture
def mock_conversation():
    return [
        {'role': 'user', 'content': 'Hallo Mia!'},
        {'role': 'assistant', 'content': 'Hey! Schön dich zu sehen!'},
        {'role': 'user', 'content': 'Wie geht es dir?'},
        {'role': 'assistant', 'content': 'Mir geht es super, danke!'},
    ]


# ─── Tool-Definitionen ──────────────────────────────────────────────────────

class TestToolDefinitions:
    """CORTEX_TOOLS Struktur."""

    def test_has_two_tools(self):
        assert len(CORTEX_TOOLS) == 2

    def test_read_file_tool(self):
        read_tool = next(t for t in CORTEX_TOOLS if t['name'] == 'read_file')
        assert 'input_schema' in read_tool
        assert read_tool['input_schema']['properties']['filename']['enum'] == [
            'memory.md', 'soul.md', 'relationship.md'
        ]

    def test_write_file_tool(self):
        write_tool = next(t for t in CORTEX_TOOLS if t['name'] == 'write_file')
        assert 'content' in write_tool['input_schema']['properties']
        assert write_tool['input_schema']['required'] == ['filename', 'content']


# ─── Rate-Limiting ──────────────────────────────────────────────────────────

class TestRateLimit:
    """Rate-Limiting pro Persona."""

    def test_first_call_allowed(self, service):
        assert service._check_rate_limit('default') is True

    def test_second_call_blocked(self, service):
        service._check_rate_limit('default')
        assert service._check_rate_limit('default') is False

    def test_different_personas_independent(self, service):
        service._check_rate_limit('persona_a')
        assert service._check_rate_limit('persona_b') is True


# ─── Tool-Executor ──────────────────────────────────────────────────────────

class TestToolExecutor:
    """_execute_tool Methode."""

    def test_read_file(self, service):
        mock_cortex = MagicMock()
        mock_cortex.read_file.return_value = '# Erinnerungen\nTest content'

        files_read, files_written = [], []
        success, result = service._execute_tool(
            mock_cortex, 'default', 'read_file', {'filename': 'memory.md'},
            files_read, files_written
        )

        assert success is True
        assert 'Erinnerungen' in result
        assert 'memory.md' in files_read
        assert files_written == []

    def test_write_file(self, service):
        mock_cortex = MagicMock()

        files_read, files_written = [], []
        success, result = service._execute_tool(
            mock_cortex, 'default', 'write_file',
            {'filename': 'memory.md', 'content': '# Neue Erinnerungen'},
            files_read, files_written
        )

        assert success is True
        assert 'successfully updated' in result
        assert 'memory.md' in files_written
        mock_cortex.write_file.assert_called_once()

    def test_unknown_tool(self, service):
        mock_cortex = MagicMock()
        files_read, files_written = [], []
        success, result = service._execute_tool(
            mock_cortex, 'default', 'delete_file', {'filename': 'x.md'},
            files_read, files_written
        )

        assert success is False
        assert 'Unknown tool' in result

    def test_value_error_caught(self, service):
        mock_cortex = MagicMock()
        mock_cortex.read_file.side_effect = ValueError("Ungültige Cortex-Datei: notes.md")

        files_read, files_written = [], []
        success, result = service._execute_tool(
            mock_cortex, 'default', 'read_file', {'filename': 'notes.md'},
            files_read, files_written
        )

        assert success is False
        assert 'notes.md' in result

    def test_no_duplicate_tracking(self, service):
        """Gleiche Datei wird nur einmal in Tracking-Liste aufgenommen."""
        mock_cortex = MagicMock()
        mock_cortex.read_file.return_value = 'Content'

        files_read, files_written = [], []
        service._execute_tool(mock_cortex, 'default', 'read_file', {'filename': 'memory.md'}, files_read, files_written)
        service._execute_tool(mock_cortex, 'default', 'read_file', {'filename': 'memory.md'}, files_read, files_written)

        assert files_read == ['memory.md']  # Nicht ['memory.md', 'memory.md']


# ─── System-Prompt-Builder ──────────────────────────────────────────────────

class TestSystemPromptBuilder:
    """_build_cortex_system_prompt — testet den Fallback-Pfad (ohne PromptEngine)."""

    def test_contains_persona_name(self, service, mock_character):
        prompt = service._build_cortex_system_prompt_fallback('Mia', 'Alex', mock_character)
        assert 'You are Mia' in prompt

    def test_contains_user_name(self, service, mock_character):
        prompt = service._build_cortex_system_prompt_fallback('Mia', 'Alex', mock_character)
        assert 'Alex' in prompt

    def test_contains_file_descriptions(self, service, mock_character):
        prompt = service._build_cortex_system_prompt_fallback('Mia', 'Alex', mock_character)
        assert 'memory.md' in prompt
        assert 'soul.md' in prompt
        assert 'relationship.md' in prompt

    def test_contains_identity(self, service, mock_character):
        prompt = service._build_cortex_system_prompt_fallback('Mia', 'Alex', mock_character)
        assert '22, weiblich' in prompt

    def test_contains_date(self, service, mock_character):
        from datetime import datetime
        today = datetime.now().strftime('%d.%m.%Y')
        prompt = service._build_cortex_system_prompt_fallback('Mia', 'Alex', mock_character)
        assert today in prompt

    def test_minimal_character(self, service):
        """Leere Character-Daten crashen nicht."""
        prompt = service._build_cortex_system_prompt_fallback('Bot', 'User', {})
        assert 'You are Bot' in prompt


# ─── Message-Builder ────────────────────────────────────────────────────────

class TestMessageBuilder:
    """_build_messages und _format_conversation."""

    def test_builds_single_user_message(self, service, mock_conversation):
        messages = service._build_messages(mock_conversation, 'Mia', 'Alex')
        assert len(messages) == 1
        assert messages[0]['role'] == 'user'

    def test_conversation_in_message(self, service, mock_conversation):
        messages = service._build_messages(mock_conversation, 'Mia', 'Alex')
        content = messages[0]['content']
        assert 'Hallo Mia!' in content
        assert 'Schön dich zu sehen!' in content

    def test_format_conversation(self, service, mock_conversation):
        text = service._format_conversation(mock_conversation, 'Mia', 'Alex')
        assert '**Alex:** Hallo Mia!' in text
        assert '**Mia:** Hey! Schön dich zu sehen!' in text


# ─── Execute-Update Integration ─────────────────────────────────────────────

class TestExecuteUpdate:
    """execute_update — Vollständiger Flow."""

    @patch.object(CortexUpdateService, '_get_cortex_service')
    @patch.object(CortexUpdateService, '_get_api_client')
    @patch.object(CortexUpdateService, '_load_character')
    @patch.object(CortexUpdateService, '_load_user_profile')
    @patch.object(CortexUpdateService, '_load_conversation')
    def test_success_flow(self, mock_conv, mock_profile, mock_char,
                          mock_api, mock_cortex, service, mock_character, mock_conversation):
        """Erfolgreicher Update-Flow."""
        mock_char.return_value = mock_character
        mock_profile.return_value = {'user_name': 'Alex'}
        mock_conv.return_value = mock_conversation

        # Mock CortexService
        mock_cortex_svc = MagicMock()
        mock_cortex_svc.read_file.return_value = '# Erinnerungen'
        mock_cortex.return_value = mock_cortex_svc

        # Mock ApiClient
        mock_api_client = MagicMock()
        mock_api_client.is_ready = True
        mock_api_client.tool_request.return_value = ApiResponse(
            success=True,
            content='Update fertig.',
            stop_reason='end_turn',
            tool_results=[
                {'tool_name': 'read_file', 'success': True, 'result': '...'},
                {'tool_name': 'write_file', 'success': True, 'result': '...'}
            ],
            usage={'input_tokens': 3000, 'output_tokens': 1500}
        )
        mock_api.return_value = mock_api_client

        result = service.execute_update('default', 1)

        assert result['success'] is True
        assert result['tool_calls_count'] == 2
        assert result['error'] is None
        assert result['usage'] == {'input_tokens': 3000, 'output_tokens': 1500}

    @patch.object(CortexUpdateService, '_get_api_client')
    def test_no_api_key(self, mock_api, service):
        """Kein API-Key → Fehler."""
        mock_api_client = MagicMock()
        mock_api_client.is_ready = False
        mock_api.return_value = mock_api_client

        result = service.execute_update('default', 1)

        assert result['success'] is False
        assert 'API-Client' in result['error']

    @patch.object(CortexUpdateService, '_get_cortex_service')
    @patch.object(CortexUpdateService, '_get_api_client')
    @patch.object(CortexUpdateService, '_load_character')
    @patch.object(CortexUpdateService, '_load_user_profile')
    @patch.object(CortexUpdateService, '_load_conversation')
    def test_too_few_messages(self, mock_conv, mock_profile, mock_char,
                              mock_api, mock_cortex, service, mock_character):
        """Zu wenig Nachrichten → Abbruch."""
        mock_char.return_value = mock_character
        mock_profile.return_value = {'user_name': 'Alex'}
        mock_conv.return_value = [
            {'role': 'user', 'content': 'Hi'},
            {'role': 'assistant', 'content': 'Hello'}
        ]

        mock_api_client = MagicMock()
        mock_api_client.is_ready = True
        mock_api.return_value = mock_api_client
        mock_cortex.return_value = MagicMock()

        result = service.execute_update('default', 1)

        assert result['success'] is False
        assert 'Zu wenig' in result['error']

    def test_rate_limit_blocks(self, service):
        """Zweiter Aufruf innerhalb von 30s → Rate-Limit."""
        # Ersten Call simulieren (Rate-Limit State setzen)
        service._check_rate_limit('default')

        # Zweiter Call → Rate-Limit
        result = service.execute_update('default', 1)
        assert result['success'] is False
        assert 'Rate-Limit' in result['error']

    @patch.object(CortexUpdateService, '_get_cortex_service')
    @patch.object(CortexUpdateService, '_get_api_client')
    @patch.object(CortexUpdateService, '_load_character')
    @patch.object(CortexUpdateService, '_load_user_profile')
    @patch.object(CortexUpdateService, '_load_conversation')
    def test_api_failure(self, mock_conv, mock_profile, mock_char,
                         mock_api, mock_cortex, service, mock_character, mock_conversation):
        """API-Fehler → Fehlerergebnis."""
        mock_char.return_value = mock_character
        mock_profile.return_value = {'user_name': 'Alex'}
        mock_conv.return_value = mock_conversation

        mock_cortex.return_value = MagicMock()

        mock_api_client = MagicMock()
        mock_api_client.is_ready = True
        mock_api_client.tool_request.return_value = ApiResponse(
            success=False,
            error='credit_balance_exhausted'
        )
        mock_api.return_value = mock_api_client

        result = service.execute_update('default', 1)

        assert result['success'] is False
        assert result['error'] == 'credit_balance_exhausted'


# ─── Konstanten ──────────────────────────────────────────────────────────────

class TestConstants:
    """Konfigurationskonstanten."""

    def test_max_tokens(self):
        assert CORTEX_UPDATE_MAX_TOKENS == 8192

    def test_temperature(self):
        assert CORTEX_UPDATE_TEMPERATURE == 0.4

    def test_rate_limit(self):
        assert RATE_LIMIT_SECONDS == 30
