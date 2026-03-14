"""
Tests for last_encounter.py — humanize_time_delta, compute_last_encounter
"""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from utils.last_encounter import humanize_time_delta, compute_last_encounter


class TestHumanizeTimeDelta:
    """Test all time threshold boundaries."""

    def test_negative_seconds(self):
        assert humanize_time_delta(-10) == "a few seconds ago"

    def test_zero_seconds(self):
        assert humanize_time_delta(0) == "a few seconds ago"

    def test_30_seconds(self):
        assert humanize_time_delta(30) == "a few seconds ago"

    def test_45_seconds_boundary(self):
        assert humanize_time_delta(45) == "a few seconds ago"

    def test_46_seconds_about_a_minute(self):
        assert humanize_time_delta(46) == "about a minute ago"

    def test_90_seconds_still_about_a_minute(self):
        assert humanize_time_delta(90) == "about a minute ago"

    def test_91_seconds_minutes(self):
        result = humanize_time_delta(91)
        assert "minutes ago" in result

    def test_5_minutes(self):
        assert humanize_time_delta(5 * 60) == "5 minutes ago"

    def test_45_minutes(self):
        assert humanize_time_delta(45 * 60) == "45 minutes ago"

    def test_46_minutes_about_an_hour(self):
        assert humanize_time_delta(46 * 60) == "about an hour ago"

    def test_90_minutes_about_an_hour(self):
        assert humanize_time_delta(90 * 60) == "about an hour ago"

    def test_91_minutes_hours(self):
        result = humanize_time_delta(91 * 60)
        assert "hours ago" in result

    def test_12_hours(self):
        assert humanize_time_delta(12 * 3600) == "12 hours ago"

    def test_22_hours(self):
        assert humanize_time_delta(22 * 3600) == "22 hours ago"

    def test_23_hours_about_a_day(self):
        result = humanize_time_delta(23 * 3600)
        assert "about a day ago" in result

    def test_36_hours_about_a_day(self):
        assert humanize_time_delta(36 * 3600) == "about a day ago"

    def test_37_hours_days(self):
        result = humanize_time_delta(37 * 3600)
        assert "days ago" in result

    def test_10_days(self):
        assert humanize_time_delta(10 * 86400) == "10 days ago"

    def test_25_days(self):
        assert humanize_time_delta(25 * 86400) == "25 days ago"

    def test_30_days_about_a_month(self):
        result = humanize_time_delta(30 * 86400)
        assert "about a month ago" in result

    def test_3_months(self):
        result = humanize_time_delta(90 * 86400)
        assert "months ago" in result

    def test_12_months_about_a_year(self):
        result = humanize_time_delta(365 * 86400)
        assert "about a year ago" in result

    def test_2_years(self):
        result = humanize_time_delta(730 * 86400)
        assert "years ago" in result


class TestComputeLastEncounter:
    """Test the 3 encounter cases."""

    def test_no_session_first_encounter(self):
        with patch("utils.last_encounter.get_current_session_id", return_value=None):
            result = compute_last_encounter(None, "default")
        assert "first encounter" in result

    def test_single_session_no_user_messages(self):
        with patch("utils.last_encounter.get_current_session_id", return_value=1), \
             patch("utils.last_encounter.get_all_sessions", return_value=[{"id": 1}]), \
             patch("utils.last_encounter.jsonl_store.read_filtered", return_value=[]):
            result = compute_last_encounter(1, "default")
        assert "first encounter" in result

    def test_active_session_with_user_messages(self):
        now = datetime.now(timezone.utc)
        ts = now.isoformat()
        user_msgs = [{"is_user": True, "timestamp": ts}]

        with patch("utils.last_encounter.get_current_session_id", return_value=1), \
             patch("utils.last_encounter.get_all_sessions", return_value=[{"id": 1}]), \
             patch("utils.last_encounter.jsonl_store.read_filtered", return_value=user_msgs):
            result = compute_last_encounter(1, "default")
        assert "user last wrote" in result
