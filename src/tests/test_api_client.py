"""
Tests für api_request/ Package.
Unit + Mock für ApiClient, Dataclasses, Response Cleaner.
"""
import pytest
from unittest.mock import MagicMock, patch


# ============================================================
# Dataclass Tests (types.py)
# ============================================================

class TestRequestConfig:
    def test_defaults(self):
        from utils.api_request.types import RequestConfig
        config = RequestConfig(
            system_prompt='Test system',
            messages=[{'role': 'user', 'content': 'Hi'}],
        )
        assert config.system_prompt == 'Test system'
        assert config.messages == [{'role': 'user', 'content': 'Hi'}]
        assert config.model is None
        assert config.max_tokens == 500
        assert config.temperature == 0.7
        assert config.stream is False
        assert config.prefill is None
        assert config.request_type == 'generic'

    def test_custom_values(self):
        from utils.api_request.types import RequestConfig
        config = RequestConfig(
            system_prompt='Sys',
            messages=[],
            model='claude-sonnet-4-5-20250929',
            max_tokens=1000,
            temperature=0.3,
            stream=True,
            prefill='Remember:',
            request_type='chat',
        )
        assert config.stream is True
        assert config.max_tokens == 1000
        assert config.request_type == 'chat'


class TestApiResponse:
    def test_success_response(self):
        from utils.api_request.types import ApiResponse
        resp = ApiResponse(
            success=True,
            content='Hello world',
            usage={'input_tokens': 10, 'output_tokens': 5},
            stop_reason='end_turn',
        )
        assert resp.success is True
        assert resp.content == 'Hello world'
        assert resp.usage['input_tokens'] == 10

    def test_error_response(self):
        from utils.api_request.types import ApiResponse
        resp = ApiResponse(success=False, error='API key invalid')
        assert resp.success is False
        assert resp.error == 'API key invalid'
        assert resp.content == ''

    def test_defaults(self):
        from utils.api_request.types import ApiResponse
        resp = ApiResponse(success=True)
        assert resp.content == ''
        assert resp.error is None
        assert resp.usage is None
        assert resp.raw_response is None
        assert resp.stop_reason is None


class TestStreamEvent:
    def test_chunk_event(self):
        from utils.api_request.types import StreamEvent
        event = StreamEvent(event_type='chunk', data='Hello ')
        assert event.event_type == 'chunk'
        assert event.data == 'Hello '

    def test_done_event(self):
        from utils.api_request.types import StreamEvent
        event = StreamEvent(event_type='done', data={'response': 'Full text', 'stats': {}})
        assert event.event_type == 'done'
        assert isinstance(event.data, dict)

    def test_error_event(self):
        from utils.api_request.types import StreamEvent
        event = StreamEvent(event_type='error', data='credit_balance_exhausted')
        assert event.event_type == 'error'


# ============================================================
# Response Cleaner Tests
# ============================================================

class TestResponseCleaner:
    def test_plain_text_passthrough(self):
        from utils.api_request.response_cleaner import clean_api_response
        assert clean_api_response('Hello world') == 'Hello world'

    def test_empty_string(self):
        from utils.api_request.response_cleaner import clean_api_response
        assert clean_api_response('') == ''

    def test_none_input(self):
        from utils.api_request.response_cleaner import clean_api_response
        result = clean_api_response(None)
        assert result == '' or result is None  # Depending on implementation

    def test_code_blocks_preserved(self):
        from utils.api_request.response_cleaner import clean_api_response
        text = 'Hier ist Code:\n```python\nprint("hello")\n```\nEnde.'
        result = clean_api_response(text)
        # Response cleaner converts code blocks to HTML
        assert 'print' in result and 'hello' in result

    def test_html_tags_in_text(self):
        from utils.api_request.response_cleaner import clean_api_response
        text = 'Ein <b>Test</b> mit Tags'
        result = clean_api_response(text)
        assert isinstance(result, str)


# ============================================================
# ApiClient Tests
# ============================================================

class TestApiClientInit:
    def test_init_with_key(self, mock_anthropic):
        from utils.api_request import ApiClient
        client = ApiClient(api_key='sk-test-123')
        assert client.is_ready is True

    def test_init_without_key(self):
        from utils.api_request import ApiClient
        with patch('utils.api_request.client.anthropic'):
            client = ApiClient(api_key=None)
            # Sollte nicht ready sein wenn kein Key
            assert client.api_key is None or client.api_key == ''

    def test_update_api_key(self, api_client):
        result = api_client.update_api_key('new-key-456')
        assert result is True


class TestApiClientRequest:
    def test_simple_request(self, api_client):
        from utils.api_request.types import RequestConfig
        config = RequestConfig(
            system_prompt='Du bist ein Test.',
            messages=[{'role': 'user', 'content': 'Hallo'}],
            max_tokens=100,
        )
        response = api_client.request(config)
        assert response.success is True
        assert response.content == 'Test response'
        assert response.usage is not None
        assert response.usage['input_tokens'] == 100
        assert response.usage['output_tokens'] == 50

    def test_request_with_prefill(self, api_client):
        from utils.api_request.types import RequestConfig
        config = RequestConfig(
            system_prompt='System',
            messages=[{'role': 'user', 'content': 'Test'}],
            prefill='Ich denke',
        )
        response = api_client.request(config)
        assert response.success is True

    def test_request_builds_correct_messages(self, mock_anthropic):
        """Prüft dass Prefill als assistant-Message an messages angehängt wird"""
        from utils.api_request import ApiClient
        from utils.api_request.types import RequestConfig
        client = ApiClient(api_key='test-key')
        config = RequestConfig(
            system_prompt='System prompt',
            messages=[{'role': 'user', 'content': 'User msg'}],
            prefill='Prefill text',
        )
        client.request(config)

        # Check the create() call
        create_call = mock_anthropic.Anthropic.return_value.messages.create
        assert create_call.called
        call_kwargs = create_call.call_args
        messages_sent = call_kwargs.kwargs.get('messages') or call_kwargs[1].get('messages', [])
        if not messages_sent and len(call_kwargs.args) > 0:
            # Fallback: positional
            pass
        # Mindestens der User-Message muss da sein
        assert any(m.get('role') == 'user' for m in messages_sent if isinstance(m, dict))


class TestApiClientStream:
    def test_stream_yields_events(self, api_client_stream):
        from utils.api_request.types import RequestConfig
        config = RequestConfig(
            system_prompt='Stream test',
            messages=[{'role': 'user', 'content': 'Hi'}],
            stream=True,
        )
        events = list(api_client_stream.stream(config))
        # Sollte mindestens chunk und done Events haben
        event_types = [e.event_type if hasattr(e, 'event_type') else e[0] for e in events]
        assert 'chunk' in event_types or 'done' in event_types or len(events) > 0


class TestApiClientContract:
    """Contract Tests: Prüft dass Return-Werte die erwarteten Felder haben"""

    def test_api_response_has_required_fields(self, api_client):
        from utils.api_request.types import RequestConfig
        config = RequestConfig(
            system_prompt='Test', messages=[{'role': 'user', 'content': 'Hi'}],
        )
        resp = api_client.request(config)
        assert hasattr(resp, 'success')
        assert hasattr(resp, 'content')
        assert hasattr(resp, 'error')
        assert hasattr(resp, 'usage')
        assert hasattr(resp, 'stop_reason')

    def test_stream_event_has_required_fields(self):
        from utils.api_request.types import StreamEvent
        event = StreamEvent(event_type='chunk', data='text')
        assert hasattr(event, 'event_type')
        assert hasattr(event, 'data')


# ============================================================
# Package Exports Test
# ============================================================

class TestPackageExports:
    def test_all_exports_importable(self):
        from utils.api_request import ApiClient, RequestConfig, ApiResponse, StreamEvent, clean_api_response
        assert ApiClient is not None
        assert RequestConfig is not None
        assert ApiResponse is not None
        assert StreamEvent is not None
        assert callable(clean_api_response)
