"""
Tests for JSONL Chat Module (jsonl_chat.py)

Verifies: save_message, get_chat_history, get_message_count,
          get_conversation_context, clear_chat_history,
          get_last_message, delete_last_message, update_last_message_text
"""
import os
import sys
import pytest
from unittest.mock import patch
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from utils.database import jsonl_store, jsonl_chat, jsonl_sessions


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """Redirect DATA_DIR to a temp directory."""
    monkeypatch.setattr("utils.database.connection.DATA_DIR", str(tmp_path))
    monkeypatch.setattr("utils.database.jsonl_chat.DATA_DIR", str(tmp_path))
    monkeypatch.setattr("utils.database.jsonl_sessions.DATA_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def session_with_messages(data_dir):
    """Creates a default persona with one session and some messages."""
    session_id = jsonl_sessions.create_session(title="Test", persona_id="default")
    jsonl_chat.save_message("Hello", is_user=True, session_id=session_id, persona_id="default")
    jsonl_chat.save_message("Hi there!", is_user=False, character_name="Bot", session_id=session_id, persona_id="default")
    jsonl_chat.save_message("How are you?", is_user=True, session_id=session_id, persona_id="default")
    return session_id


class TestSaveMessage:
    def test_save_and_retrieve(self, data_dir):
        sid = jsonl_sessions.create_session(persona_id="default")
        msg_id = jsonl_chat.save_message("Hallo!", is_user=True, session_id=sid, persona_id="default")
        assert msg_id == 1
        history = jsonl_chat.get_chat_history(session_id=sid, persona_id="default")
        assert len(history) == 1
        assert history[0]["message"] == "Hallo!"
        assert history[0]["is_user"] is True

    def test_auto_increment_id(self, data_dir):
        sid = jsonl_sessions.create_session(persona_id="default")
        id1 = jsonl_chat.save_message("A", is_user=True, session_id=sid, persona_id="default")
        id2 = jsonl_chat.save_message("B", is_user=False, session_id=sid, persona_id="default")
        assert id2 == id1 + 1

    def test_creates_session_if_none(self, data_dir):
        msg_id = jsonl_chat.save_message("orphan", is_user=True, persona_id="default")
        assert msg_id >= 1


class TestGetChatHistory:
    def test_returns_messages_oldest_first(self, session_with_messages):
        history = jsonl_chat.get_chat_history(session_id=session_with_messages, persona_id="default")
        assert history[0]["message"] == "Hello"
        assert history[-1]["message"] == "How are you?"

    def test_limit(self, session_with_messages):
        history = jsonl_chat.get_chat_history(limit=2, session_id=session_with_messages, persona_id="default")
        assert len(history) == 2

    def test_empty_session(self, data_dir):
        sid = jsonl_sessions.create_session(persona_id="default")
        history = jsonl_chat.get_chat_history(session_id=sid, persona_id="default")
        assert history == []

    def test_no_session_returns_empty(self, data_dir):
        history = jsonl_chat.get_chat_history(session_id=9999, persona_id="default")
        assert history == []


class TestGetMessageCount:
    def test_counts_messages(self, session_with_messages):
        count = jsonl_chat.get_message_count(session_id=session_with_messages, persona_id="default")
        assert count == 3

    def test_empty_session(self, data_dir):
        sid = jsonl_sessions.create_session(persona_id="default")
        assert jsonl_chat.get_message_count(session_id=sid, persona_id="default") == 0


class TestGetConversationContext:
    def test_returns_api_format(self, session_with_messages):
        ctx = jsonl_chat.get_conversation_context(limit=10, session_id=session_with_messages, persona_id="default")
        assert all("role" in m and "content" in m for m in ctx)
        assert ctx[0]["role"] == "user"
        assert ctx[1]["role"] == "assistant"

    def test_merges_consecutive_same_role(self, data_dir):
        sid = jsonl_sessions.create_session(persona_id="default")
        jsonl_chat.save_message("A", is_user=True, session_id=sid, persona_id="default")
        jsonl_chat.save_message("B", is_user=True, session_id=sid, persona_id="default")
        jsonl_chat.save_message("C", is_user=False, session_id=sid, persona_id="default")
        ctx = jsonl_chat.get_conversation_context(limit=10, session_id=sid, persona_id="default")
        assert len(ctx) == 2
        assert "A" in ctx[0]["content"]
        assert "B" in ctx[0]["content"]

    def test_limit_respected(self, session_with_messages):
        ctx = jsonl_chat.get_conversation_context(limit=1, session_id=session_with_messages, persona_id="default")
        assert len(ctx) <= 1


class TestClearChatHistory:
    def test_clears_all(self, session_with_messages):
        jsonl_chat.clear_chat_history(persona_id="default")
        assert jsonl_chat.get_message_count(session_id=session_with_messages, persona_id="default") == 0


class TestGetLastMessage:
    def test_returns_last(self, session_with_messages):
        last = jsonl_chat.get_last_message(session_id=session_with_messages, persona_id="default")
        assert last["message"] == "How are you?"
        assert last["is_user"] is True

    def test_empty_session(self, data_dir):
        sid = jsonl_sessions.create_session(persona_id="default")
        assert jsonl_chat.get_last_message(session_id=sid, persona_id="default") is None


class TestDeleteLastMessage:
    def test_deletes_and_returns(self, session_with_messages):
        deleted = jsonl_chat.delete_last_message(session_id=session_with_messages, persona_id="default")
        assert deleted["message"] == "How are you?"
        assert jsonl_chat.get_message_count(session_id=session_with_messages, persona_id="default") == 2

    def test_empty_session(self, data_dir):
        sid = jsonl_sessions.create_session(persona_id="default")
        assert jsonl_chat.delete_last_message(session_id=sid, persona_id="default") is None


class TestUpdateLastMessageText:
    def test_updates_text(self, session_with_messages):
        result = jsonl_chat.update_last_message_text(
            session_id=session_with_messages, new_text="EDITED", persona_id="default"
        )
        assert result is True
        last = jsonl_chat.get_last_message(session_id=session_with_messages, persona_id="default")
        assert last["message"] == "EDITED"

    def test_empty_session(self, data_dir):
        sid = jsonl_sessions.create_session(persona_id="default")
        assert jsonl_chat.update_last_message_text(session_id=sid, new_text="X", persona_id="default") is False
