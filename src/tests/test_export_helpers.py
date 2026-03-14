"""
Tests for export_helpers.py — format_messages_as_txt, format_messages_as_json, make_export_filename
"""
import json
import os
import sys
import pytest
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from utils.export_helpers import format_messages_as_txt, format_messages_as_json, make_export_filename


@pytest.fixture
def sample_messages():
    return [
        {"timestamp": "2026-03-08T14:30:00", "is_user": True, "message": "Hello!", "character_name": "Bot"},
        {"timestamp": "2026-03-08T14:30:05", "is_user": False, "message": "Hi there!", "character_name": "Bot"},
    ]


class TestFormatMessagesAsTxt:
    def test_formats_correctly(self, sample_messages):
        result = format_messages_as_txt(sample_messages)
        assert "[2026-03-08 14:30] User: Hello!" in result
        assert "[2026-03-08 14:30] Bot: Hi there!" in result

    def test_empty_list(self):
        assert format_messages_as_txt([]) == ""

    def test_invalid_timestamp(self):
        msgs = [{"timestamp": "INVALID", "is_user": True, "message": "test"}]
        result = format_messages_as_txt(msgs)
        assert "[Unknown] User: test" in result

    def test_missing_fields(self):
        msgs = [{"timestamp": "", "message": "orphan"}]
        result = format_messages_as_txt(msgs)
        assert "Assistant: orphan" in result


class TestFormatMessagesAsJson:
    def test_valid_json(self, sample_messages):
        result = format_messages_as_json(sample_messages)
        parsed = json.loads(result)
        assert len(parsed) == 2
        assert parsed[0]["role"] == "user"
        assert parsed[1]["role"] == "assistant"

    def test_empty_list(self):
        assert format_messages_as_json([]) == "[]"

    def test_content_preserved(self, sample_messages):
        result = json.loads(format_messages_as_json(sample_messages))
        assert result[0]["content"] == "Hello!"


class TestMakeExportFilename:
    def test_txt_format(self):
        filename = make_export_filename(42, "txt")
        assert filename.startswith("chat_export_42_")
        assert filename.endswith(".txt")

    def test_json_format(self):
        filename = make_export_filename(1, "json")
        assert filename.endswith(".json")

    def test_contains_date(self):
        filename = make_export_filename(1, "txt")
        today = datetime.now().strftime('%Y-%m-%d')
        assert today in filename
