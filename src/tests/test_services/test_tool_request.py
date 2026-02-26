"""
Tests für ApiClient.tool_request() — Tool-Use Loop.

Testet:
- Einzelne und mehrere Tool-Call Rounds
- Fehlerbehandlung (kein API-Key, keine Tools, Executor-Exception)
- MAX_TOOL_ROUNDS Sicherheitslimit
- Token-Usage Akkumulation
- _extract_text_from_content() Helper
"""

from unittest.mock import MagicMock, patch

from utils.api_request.client import ApiClient, MAX_TOOL_ROUNDS
from utils.api_request.types import RequestConfig


# ─── Helpers ─────────────────────────────────────────────────────────

def _make_text_block(text: str):
    """Erstellt ein Mock-TextBlock-Objekt."""
    block = MagicMock()
    block.type = 'text'
    block.text = text
    return block


def _make_tool_use_block(tool_id: str, name: str, input_data: dict):
    """Erstellt ein Mock-ToolUseBlock-Objekt (ohne .text Attribut)."""
    block = MagicMock(spec=['type', 'id', 'name', 'input'])
    block.type = 'tool_use'
    block.id = tool_id
    block.name = name
    block.input = input_data
    return block


def _make_response(stop_reason: str, content_blocks: list, input_tokens=100, output_tokens=50):
    """Erstellt eine Mock-API-Response."""
    response = MagicMock()
    response.stop_reason = stop_reason
    response.content = content_blocks
    response.usage.input_tokens = input_tokens
    response.usage.output_tokens = output_tokens
    return response


def _base_config(**overrides):
    """Erstellt eine RequestConfig mit Tools."""
    defaults = dict(
        system_prompt="Test System Prompt",
        messages=[{"role": "user", "content": "Test message"}],
        tools=[{
            "name": "read_file",
            "description": "Reads a file",
            "input_schema": {
                "type": "object",
                "properties": {"filename": {"type": "string"}},
                "required": ["filename"]
            }
        }],
        max_tokens=4096,
        temperature=0.5,
        request_type='cortex_update'
    )
    defaults.update(overrides)
    return RequestConfig(**defaults)


# ─── Tests ───────────────────────────────────────────────────────────

class TestToolRequestSingleRound:
    """Tool-Request beendet nach einer einzigen API-Antwort (end_turn)."""

    def test_end_turn_without_tools(self):
        """API antwortet sofort mit end_turn und Text (kein Tool-Call)."""
        with patch('utils.api_request.client.anthropic') as mock_anthropic:
            response = _make_response(
                'end_turn',
                [_make_text_block("Alles erledigt.")]
            )
            mock_anthropic.Anthropic.return_value.messages.create.return_value = response

            client = ApiClient(api_key='test-key')
            config = _base_config()
            executor = MagicMock(return_value=(True, "OK"))

            result = client.tool_request(config, executor)

            assert result.success is True
            assert result.content == "Alles erledigt."
            assert result.stop_reason == 'end_turn'
            assert result.tool_results is None
            executor.assert_not_called()

    def test_single_tool_round(self):
        """Ein Tool-Call, dann end_turn."""
        with patch('utils.api_request.client.anthropic') as mock_anthropic:
            # Round 1: tool_use
            tool_response = _make_response(
                'tool_use',
                [
                    _make_text_block("Ich lese die Datei..."),
                    _make_tool_use_block("toolu_123", "read_file", {"filename": "memory.md"})
                ]
            )
            # Round 2: end_turn
            final_response = _make_response(
                'end_turn',
                [_make_text_block("Fertig!")]
            )

            mock_api = mock_anthropic.Anthropic.return_value.messages.create
            mock_api.side_effect = [tool_response, final_response]

            client = ApiClient(api_key='test-key')
            config = _base_config()
            executor = MagicMock(return_value=(True, "# Erinnerungen\nTest content"))

            result = client.tool_request(config, executor)

            assert result.success is True
            assert result.content == "Fertig!"
            assert result.stop_reason == 'end_turn'
            assert len(result.tool_results) == 1
            assert result.tool_results[0]['tool_name'] == 'read_file'
            assert result.tool_results[0]['success'] is True
            executor.assert_called_once_with("read_file", {"filename": "memory.md"})


class TestToolRequestMultiRound:
    """Mehrere Tool-Call Rounds (read → write → end_turn)."""

    def test_read_then_write(self):
        """Typischer Cortex-Flow: read_file → write_file → end_turn."""
        with patch('utils.api_request.client.anthropic') as mock_anthropic:
            # Round 1: read_file
            r1 = _make_response(
                'tool_use',
                [_make_tool_use_block("toolu_r1", "read_file", {"filename": "memory.md"})]
            )
            # Round 2: write_file
            r2 = _make_response(
                'tool_use',
                [_make_tool_use_block("toolu_w1", "write_file", {"filename": "memory.md", "content": "Updated"})]
            )
            # Round 3: end_turn
            r3 = _make_response(
                'end_turn',
                [_make_text_block("Aktualisierung abgeschlossen.")]
            )

            mock_api = mock_anthropic.Anthropic.return_value.messages.create
            mock_api.side_effect = [r1, r2, r3]

            client = ApiClient(api_key='test-key')
            config = _base_config()

            call_count = 0
            def mock_executor(name, inp):
                nonlocal call_count
                call_count += 1
                if name == "read_file":
                    return True, "Old content"
                elif name == "write_file":
                    return True, "Datei erfolgreich geschrieben."
                return False, "Unknown"

            result = client.tool_request(config, mock_executor)

            assert result.success is True
            assert call_count == 2
            assert len(result.tool_results) == 2
            assert result.tool_results[0]['tool_name'] == 'read_file'
            assert result.tool_results[1]['tool_name'] == 'write_file'

    def test_multiple_tools_in_single_round(self):
        """API gibt mehrere ToolUseBlocks in einer Antwort zurück."""
        with patch('utils.api_request.client.anthropic') as mock_anthropic:
            # Round 1: two tool calls at once
            r1 = _make_response(
                'tool_use',
                [
                    _make_tool_use_block("toolu_a", "read_file", {"filename": "memory.md"}),
                    _make_tool_use_block("toolu_b", "read_file", {"filename": "soul.md"})
                ]
            )
            r2 = _make_response('end_turn', [_make_text_block("Done")])

            mock_api = mock_anthropic.Anthropic.return_value.messages.create
            mock_api.side_effect = [r1, r2]

            client = ApiClient(api_key='test-key')
            config = _base_config()
            executor = MagicMock(return_value=(True, "Content"))

            result = client.tool_request(config, executor)

            assert result.success is True
            assert len(result.tool_results) == 2
            assert executor.call_count == 2


class TestToolRequestErrors:
    """Fehlerbehandlung in tool_request()."""

    def test_no_api_key(self):
        """Kein API-Key → sofortiger Fehler."""
        with patch('utils.api_request.client.anthropic') as mock_anthropic:
            mock_anthropic.Anthropic.return_value = None
            client = ApiClient(api_key='')
            config = _base_config()
            executor = MagicMock()

            result = client.tool_request(config, executor)

            assert result.success is False
            assert 'nicht initialisiert' in result.error
            executor.assert_not_called()

    def test_no_tools_in_config(self):
        """Keine Tools in config → sofortiger Fehler."""
        with patch('utils.api_request.client.anthropic') as mock_anthropic:
            mock_anthropic.Anthropic.return_value.messages.create.return_value = MagicMock()

            client = ApiClient(api_key='test-key')
            config = _base_config(tools=None)
            executor = MagicMock()

            result = client.tool_request(config, executor)

            assert result.success is False
            assert 'tool_request()' in result.error
            executor.assert_not_called()

    def test_empty_tools_list(self):
        """Leere Tools-Liste → sofortiger Fehler."""
        with patch('utils.api_request.client.anthropic') as mock_anthropic:
            mock_anthropic.Anthropic.return_value.messages.create.return_value = MagicMock()

            client = ApiClient(api_key='test-key')
            config = _base_config(tools=[])
            executor = MagicMock()

            result = client.tool_request(config, executor)

            assert result.success is False
            assert 'tool_request()' in result.error

    def test_executor_exception(self):
        """Executor wirft Exception → is_error=True, Loop geht weiter."""
        with patch('utils.api_request.client.anthropic') as mock_anthropic:
            r1 = _make_response(
                'tool_use',
                [_make_tool_use_block("toolu_err", "read_file", {"filename": "bad.md"})]
            )
            r2 = _make_response('end_turn', [_make_text_block("Recovered")])

            mock_api = mock_anthropic.Anthropic.return_value.messages.create
            mock_api.side_effect = [r1, r2]

            client = ApiClient(api_key='test-key')
            config = _base_config()
            executor = MagicMock(side_effect=ValueError("File not found"))

            result = client.tool_request(config, executor)

            assert result.success is True
            assert result.content == "Recovered"
            assert len(result.tool_results) == 1
            assert result.tool_results[0]['success'] is False
            assert "File not found" in result.tool_results[0]['result']

    def test_executor_returns_failure(self):
        """Executor gibt (False, msg) zurück → is_error=True."""
        with patch('utils.api_request.client.anthropic') as mock_anthropic:
            r1 = _make_response(
                'tool_use',
                [_make_tool_use_block("toolu_fail", "read_file", {"filename": "notes.md"})]
            )
            r2 = _make_response('end_turn', [_make_text_block("OK")])

            mock_api = mock_anthropic.Anthropic.return_value.messages.create
            mock_api.side_effect = [r1, r2]

            client = ApiClient(api_key='test-key')
            config = _base_config()
            executor = MagicMock(return_value=(False, "Ungültige Datei: notes.md"))

            result = client.tool_request(config, executor)

            assert result.success is True
            assert result.tool_results[0]['success'] is False
            assert "notes.md" in result.tool_results[0]['result']

    def test_api_error(self):
        """API-Fehler → ApiResponse(success=False)."""
        import anthropic as real_anthropic

        with patch('utils.api_request.client.anthropic') as mock_anthropic:
            mock_anthropic.APIError = real_anthropic.APIError
            mock_api = mock_anthropic.Anthropic.return_value.messages.create
            mock_api.side_effect = real_anthropic.APIError(
                message="Server error",
                request=MagicMock(),
                body=None
            )

            client = ApiClient(api_key='test-key')
            config = _base_config()
            executor = MagicMock()

            result = client.tool_request(config, executor)

            assert result.success is False
            assert result.error is not None
            executor.assert_not_called()

    def test_credit_balance_exhausted(self):
        """Credit-Balance-Fehler wird erkannt."""
        import anthropic as real_anthropic

        with patch('utils.api_request.client.anthropic') as mock_anthropic:
            mock_anthropic.APIError = real_anthropic.APIError
            mock_api = mock_anthropic.Anthropic.return_value.messages.create
            mock_api.side_effect = real_anthropic.APIError(
                message="Your credit balance is too low",
                request=MagicMock(),
                body=None
            )

            client = ApiClient(api_key='test-key')
            config = _base_config()
            executor = MagicMock()

            result = client.tool_request(config, executor)

            assert result.success is False
            assert result.error == 'credit_balance_exhausted'


class TestToolRequestMaxRounds:
    """Sicherheitslimit MAX_TOOL_ROUNDS."""

    def test_max_rounds_reached(self):
        """Loop bricht nach MAX_TOOL_ROUNDS ab."""
        import anthropic as real_anthropic

        with patch('utils.api_request.client.anthropic') as mock_anthropic:
            mock_anthropic.APIError = real_anthropic.APIError

            # Endlos tool_use Responses
            endless_response = _make_response(
                'tool_use',
                [_make_tool_use_block("toolu_loop", "read_file", {"filename": "memory.md"})]
            )

            mock_api = mock_anthropic.Anthropic.return_value.messages.create
            mock_api.return_value = endless_response

            client = ApiClient(api_key='test-key')
            config = _base_config()
            executor = MagicMock(return_value=(True, "Content"))

            result = client.tool_request(config, executor)

            assert result.success is True
            assert result.stop_reason == 'max_tool_rounds'
            assert len(result.tool_results) == MAX_TOOL_ROUNDS
            assert mock_api.call_count == MAX_TOOL_ROUNDS


class TestToolRequestUsage:
    """Token-Usage Akkumulation über mehrere Rounds."""

    def test_usage_accumulation(self):
        """Token-Usage wird über alle Rounds korrekt akkumuliert."""
        with patch('utils.api_request.client.anthropic') as mock_anthropic:
            r1 = _make_response('tool_use',
                [_make_tool_use_block("t1", "read_file", {"filename": "memory.md"})],
                input_tokens=200, output_tokens=100
            )
            r2 = _make_response('end_turn',
                [_make_text_block("Done")],
                input_tokens=300, output_tokens=150
            )

            mock_api = mock_anthropic.Anthropic.return_value.messages.create
            mock_api.side_effect = [r1, r2]

            client = ApiClient(api_key='test-key')
            config = _base_config()
            executor = MagicMock(return_value=(True, "Content"))

            result = client.tool_request(config, executor)

            assert result.usage == {'input_tokens': 500, 'output_tokens': 250}


class TestExtractTextFromContent:
    """_extract_text_from_content() Static Method."""

    def test_empty_content(self):
        """Leeres content → leerer String."""
        assert ApiClient._extract_text_from_content(None) == ''
        assert ApiClient._extract_text_from_content([]) == ''

    def test_text_only(self):
        """Nur TextBlocks → Text zusammengefügt."""
        content = [_make_text_block("Hello"), _make_text_block("World")]
        assert ApiClient._extract_text_from_content(content) == "Hello\nWorld"

    def test_mixed_content(self):
        """Mix aus TextBlock und ToolUseBlock → nur Text extrahiert."""
        content = [
            _make_text_block("Ich aktualisiere..."),
            _make_tool_use_block("t1", "write_file", {"filename": "memory.md", "content": "..."}),
            _make_text_block("Done")
        ]
        result = ApiClient._extract_text_from_content(content)
        assert "Ich aktualisiere..." in result
        assert "Done" in result
        # Tool-Input should not appear
        assert "memory.md" not in result

    def test_tool_blocks_only(self):
        """Nur ToolUseBlocks → leerer String."""
        content = [
            _make_tool_use_block("t1", "read_file", {"filename": "memory.md"})
        ]
        assert ApiClient._extract_text_from_content(content) == ''


class TestToolRequestMessageBuilding:
    """Prüft ob Messages korrekt aufgebaut werden (assistant + tool_result)."""

    def test_messages_include_tool_results(self):
        """Nach Tool-Call: assistant-content + user-tool_result werden angehängt."""
        with patch('utils.api_request.client.anthropic') as mock_anthropic:
            r1 = _make_response(
                'tool_use',
                [_make_tool_use_block("toolu_abc", "read_file", {"filename": "soul.md"})]
            )
            r2 = _make_response('end_turn', [_make_text_block("OK")])

            mock_api = mock_anthropic.Anthropic.return_value.messages.create
            mock_api.side_effect = [r1, r2]

            client = ApiClient(api_key='test-key')
            config = _base_config()
            executor = MagicMock(return_value=(True, "Soul content"))

            client.tool_request(config, executor)

            # Verify the second API call had the right messages
            second_call_kwargs = mock_api.call_args_list[1]
            messages = second_call_kwargs.kwargs.get('messages') or second_call_kwargs[1].get('messages')

            # Should have: original user msg + assistant (tool_use) + user (tool_result)
            assert len(messages) == 3
            assert messages[1]['role'] == 'assistant'
            assert messages[2]['role'] == 'user'
            assert messages[2]['content'][0]['type'] == 'tool_result'
            assert messages[2]['content'][0]['tool_use_id'] == 'toolu_abc'
            assert messages[2]['content'][0]['content'] == 'Soul content'
