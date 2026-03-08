"""
Tests for time_context.py — get_weekday, get_time_context
"""
import os
import sys
import pytest
from unittest.mock import patch
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from utils.time_context import get_weekday, get_time_context


class TestGetWeekday:
    def test_monday_english(self):
        monday = datetime(2026, 3, 2)  # 2026-03-02 is a Monday
        assert get_weekday(monday, "english") == "Monday"

    def test_sunday_english(self):
        sunday = datetime(2026, 3, 8)  # 2026-03-08 is a Sunday
        assert get_weekday(sunday, "english") == "Sunday"

    def test_german(self):
        monday = datetime(2026, 3, 2)
        assert get_weekday(monday, "german") == "Montag"

    def test_french(self):
        monday = datetime(2026, 3, 2)
        assert get_weekday(monday, "french") == "Lundi"

    def test_japanese(self):
        monday = datetime(2026, 3, 2)
        assert get_weekday(monday, "japanese") == "月曜日"

    def test_unknown_language_falls_back_to_english(self):
        monday = datetime(2026, 3, 2)
        assert get_weekday(monday, "klingon") == "Monday"

    def test_all_weekdays_english(self):
        # March 2-8, 2026: Mon-Sun
        expected = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        for i, day_name in enumerate(expected):
            dt = datetime(2026, 3, 2 + i)
            assert get_weekday(dt, "english") == day_name


class TestGetTimeContext:
    @patch("utils.time_context._get_persona_language", return_value="english")
    def test_returns_all_fields(self, mock_lang):
        ctx = get_time_context()
        assert "current_date" in ctx
        assert "current_time" in ctx
        assert "current_weekday" in ctx

    @patch("utils.time_context._get_persona_language", return_value="english")
    def test_date_format(self, mock_lang):
        ctx = get_time_context()
        # Format: DD.MM.YYYY
        parts = ctx["current_date"].split(".")
        assert len(parts) == 3
        assert len(parts[2]) == 4

    @patch("utils.time_context._get_persona_language", return_value="english")
    def test_time_format(self, mock_lang):
        ctx = get_time_context()
        # Format: HH:MM
        assert ":" in ctx["current_time"]
        parts = ctx["current_time"].split(":")
        assert len(parts) == 2
