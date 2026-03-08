"""
Tests for JSONL Sessions Module (jsonl_sessions.py)

Verifies: create_session, get_all_sessions, get_session,
          update_session_title, delete_session, get_current_session_id,
          get_persona_session_summary
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from utils.database import jsonl_sessions, jsonl_store


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """Redirect DATA_DIR to a temp directory."""
    monkeypatch.setattr("utils.database.connection.DATA_DIR", str(tmp_path))
    monkeypatch.setattr("utils.database.jsonl_sessions.DATA_DIR", str(tmp_path))
    return tmp_path


class TestCreateSession:
    def test_creates_with_default_title(self, data_dir):
        sid = jsonl_sessions.create_session(persona_id="default")
        assert sid == 1
        session = jsonl_sessions.get_session(sid, persona_id="default")
        assert session["title"] == "Neue Konversation"

    def test_creates_with_custom_title(self, data_dir):
        sid = jsonl_sessions.create_session(title="Mein Chat", persona_id="default")
        session = jsonl_sessions.get_session(sid, persona_id="default")
        assert session["title"] == "Mein Chat"

    def test_increments_ids(self, data_dir):
        id1 = jsonl_sessions.create_session(persona_id="default")
        id2 = jsonl_sessions.create_session(persona_id="default")
        assert id2 == id1 + 1

    def test_different_personas(self, data_dir):
        sid_a = jsonl_sessions.create_session(persona_id="persona_a")
        sid_b = jsonl_sessions.create_session(persona_id="persona_b")
        assert sid_a == 1
        assert sid_b == 1


class TestGetAllSessions:
    def test_returns_all_for_persona(self, data_dir):
        jsonl_sessions.create_session(title="S1", persona_id="default")
        jsonl_sessions.create_session(title="S2", persona_id="default")
        sessions = jsonl_sessions.get_all_sessions(persona_id="default")
        assert len(sessions) == 2

    def test_sorted_newest_first(self, data_dir):
        jsonl_sessions.create_session(title="Old", persona_id="default")
        jsonl_sessions.create_session(title="New", persona_id="default")
        sessions = jsonl_sessions.get_all_sessions(persona_id="default")
        assert sessions[0]["title"] == "New"

    def test_aggregates_all_personas(self, data_dir):
        jsonl_sessions.create_session(persona_id="default")
        jsonl_sessions.create_session(persona_id="persona_x")
        all_sessions = jsonl_sessions.get_all_sessions(persona_id=None)
        assert len(all_sessions) == 2

    def test_empty_persona(self, data_dir):
        assert jsonl_sessions.get_all_sessions(persona_id="default") == []


class TestGetSession:
    def test_finds_session(self, data_dir):
        sid = jsonl_sessions.create_session(title="Test", persona_id="default")
        session = jsonl_sessions.get_session(sid, persona_id="default")
        assert session is not None
        assert session["id"] == sid

    def test_returns_none_for_missing(self, data_dir):
        assert jsonl_sessions.get_session(999, persona_id="default") is None


class TestUpdateSessionTitle:
    def test_updates_title(self, data_dir):
        sid = jsonl_sessions.create_session(title="Old", persona_id="default")
        result = jsonl_sessions.update_session_title(sid, "New Title", persona_id="default")
        assert result is True
        session = jsonl_sessions.get_session(sid, persona_id="default")
        assert session["title"] == "New Title"

    def test_missing_session(self, data_dir):
        assert jsonl_sessions.update_session_title(999, "X", persona_id="default") is False


class TestDeleteSession:
    def test_deletes_session(self, data_dir):
        sid = jsonl_sessions.create_session(persona_id="default")
        result = jsonl_sessions.delete_session(sid, persona_id="default")
        assert result is True
        assert jsonl_sessions.get_session(sid, persona_id="default") is None

    def test_delete_nonexistent(self, data_dir):
        result = jsonl_sessions.delete_session(999, persona_id="default")
        assert result is True  # rewrite succeeds even with no match


class TestGetCurrentSessionId:
    def test_returns_latest(self, data_dir):
        jsonl_sessions.create_session(title="First", persona_id="default")
        sid2 = jsonl_sessions.create_session(title="Second", persona_id="default")
        current = jsonl_sessions.get_current_session_id(persona_id="default")
        assert current == sid2

    def test_no_sessions(self, data_dir):
        assert jsonl_sessions.get_current_session_id(persona_id="default") is None


class TestGetPersonaSessionSummary:
    def test_summary_counts(self, data_dir):
        jsonl_sessions.create_session(persona_id="default")
        jsonl_sessions.create_session(persona_id="default")
        jsonl_sessions.create_session(persona_id="persona_x")
        summary = jsonl_sessions.get_persona_session_summary()
        ids = {s["persona_id"]: s["session_count"] for s in summary}
        assert ids["default"] == 2
        assert ids["persona_x"] == 1


class TestGetSessionPersonaId:
    def test_returns_persona_id(self, data_dir):
        sid = jsonl_sessions.create_session(persona_id="my_persona")
        pid = jsonl_sessions.get_session_persona_id(sid, persona_id="my_persona")
        assert pid == "my_persona"

    def test_fallback_for_missing(self, data_dir):
        pid = jsonl_sessions.get_session_persona_id(999, persona_id="fallback")
        assert pid == "fallback"
