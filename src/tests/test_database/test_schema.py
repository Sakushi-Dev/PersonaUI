"""
Tests for Database Schema Module (schema.py)

Verifies: init_persona_db, create_persona_db, delete_persona_db,
          init_all_dbs, find_session_persona
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from utils.database import schema, jsonl_store, jsonl_sessions
from utils.database.connection import DATA_DIR


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """Redirect DATA_DIR to a temp directory."""
    monkeypatch.setattr("utils.database.connection.DATA_DIR", str(tmp_path))
    monkeypatch.setattr("utils.database.schema.DATA_DIR", str(tmp_path))
    monkeypatch.setattr("utils.database.jsonl_sessions.DATA_DIR", str(tmp_path))
    return tmp_path


class TestInitPersonaDb:
    def test_creates_directory(self, data_dir):
        schema.init_persona_db("test_persona")
        assert os.path.isdir(os.path.join(str(data_dir), "test_persona"))

    def test_default_persona(self, data_dir):
        schema.init_persona_db()
        assert os.path.isdir(os.path.join(str(data_dir), "default"))


class TestCreatePersonaDb:
    def test_returns_true(self, data_dir):
        assert schema.create_persona_db("new_persona") is True
        assert os.path.isdir(os.path.join(str(data_dir), "new_persona"))


class TestDeletePersonaDb:
    def test_deletes_existing(self, data_dir):
        schema.create_persona_db("to_delete")
        assert schema.delete_persona_db("to_delete") is True
        assert not os.path.exists(os.path.join(str(data_dir), "to_delete"))

    def test_cannot_delete_default(self, data_dir):
        schema.init_persona_db("default")
        assert schema.delete_persona_db("default") is False

    def test_nonexistent_returns_false(self, data_dir):
        assert schema.delete_persona_db("nonexistent") is False


class TestInitAllDbs:
    def test_creates_default_dir(self, data_dir):
        schema.init_all_dbs()
        assert os.path.isdir(os.path.join(str(data_dir), "default"))


class TestFindSessionPersona:
    def test_finds_correct_persona(self, data_dir):
        sid = jsonl_sessions.create_session(title="Test", persona_id="persona_abc")
        result = schema.find_session_persona(sid)
        assert result == "persona_abc"

    def test_returns_none_for_missing(self, data_dir):
        assert schema.find_session_persona(9999) is None
