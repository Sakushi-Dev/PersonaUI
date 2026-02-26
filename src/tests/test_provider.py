"""
Tests für provider.py — Zentrales Instance-Management.
"""
import pytest
from unittest.mock import patch


class TestInitServices:
    def test_init_creates_instances(self):
        from utils import provider
        with patch('utils.api_request.ApiClient') as MockClient, \
             patch('utils.services.ChatService') as MockChat:
            provider.init_services(api_key='test-key')

            MockClient.assert_called_once_with(api_key='test-key')
            MockChat.assert_called_once()

    def test_init_without_key(self):
        from utils import provider
        with patch('utils.api_request.ApiClient') as MockClient, \
             patch('utils.services.ChatService'):
            provider.init_services()
            MockClient.assert_called_once_with(api_key=None)


class TestGetters:
    def test_get_api_client_after_init(self):
        from utils import provider
        with patch('utils.api_request.ApiClient') as MockClient, \
             patch('utils.services.ChatService'):
            provider.init_services(api_key='test')
            client = provider.get_api_client()
            assert client is not None
            assert client is MockClient.return_value

    def test_get_chat_service_after_init(self):
        from utils import provider
        with patch('utils.api_request.ApiClient'), \
             patch('utils.services.ChatService') as MockChat:
            provider.init_services()
            service = provider.get_chat_service()
            assert service is not None
            assert service is MockChat.return_value

    def test_get_api_client_before_init_raises(self):
        from utils import provider
        # Reset state
        provider._api_client = None
        with pytest.raises(RuntimeError):
            provider.get_api_client()

    def test_get_chat_service_before_init_raises(self):
        from utils import provider
        provider._chat_service = None
        with pytest.raises(RuntimeError):
            provider.get_chat_service()
