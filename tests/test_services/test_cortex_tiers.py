"""
Tests für Cortex Tier-Tracker und Tier-Checker (Schritt 3B).

Testet:
- tier_tracker: cycle_base CRUD, reset, rebuild, progress
- tier_checker: Schwellenberechnung, Trigger-Logik, Config-Loading
"""

import pytest
import os
import json
import tempfile
import threading
from unittest.mock import patch, MagicMock

# tier_tracker hat Modul-Level State → für saubere Tests müssen wir resetten
import utils.cortex.tier_tracker as tracker_module
from utils.cortex.tier_tracker import (
    get_cycle_base, set_cycle_base, reset_session, reset_all,
    rebuild_cycle_base, get_progress
)
from utils.cortex.tier_checker import (
    _calculate_threshold, _load_cortex_config, FREQUENCIES,
    DEFAULT_FREQUENCY, check_and_trigger_cortex_update
)


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_tracker_state(tmp_path):
    """
    Resettet den tier_tracker Modul-State vor jedem Test.
    Verwendet tmp_path als State-Datei-Pfad.
    """
    # State-Datei auf tmp_path umbiegen
    original_state_file = tracker_module._STATE_FILE
    tmp_state_file = str(tmp_path / 'cycle_state.json')
    tracker_module._STATE_FILE = tmp_state_file

    # In-Memory State zurücksetzen
    tracker_module._cycle_state.clear()
    tracker_module._loaded = False

    yield tmp_state_file

    # Restore
    tracker_module._STATE_FILE = original_state_file
    tracker_module._cycle_state.clear()
    tracker_module._loaded = False


# ─── Tier-Tracker Tests ─────────────────────────────────────────────────────

class TestCycleBase:
    """get_cycle_base / set_cycle_base."""

    def test_default_is_zero(self):
        """Neue Session hat cycle_base 0."""
        assert get_cycle_base('default', 1) == 0

    def test_set_and_get(self):
        """Setzen und Lesen funktioniert."""
        set_cycle_base('default', 1, 48)
        assert get_cycle_base('default', 1) == 48

    def test_different_sessions(self):
        """Verschiedene Sessions haben eigene cycle_base."""
        set_cycle_base('default', 1, 48)
        set_cycle_base('default', 2, 96)
        assert get_cycle_base('default', 1) == 48
        assert get_cycle_base('default', 2) == 96

    def test_different_personas(self):
        """Verschiedene Personas haben eigene cycle_base."""
        set_cycle_base('persona_a', 1, 30)
        set_cycle_base('persona_b', 1, 60)
        assert get_cycle_base('persona_a', 1) == 30
        assert get_cycle_base('persona_b', 1) == 60

    def test_persistence_to_disk(self, reset_tracker_state):
        """cycle_base wird auf Disk gespeichert."""
        set_cycle_base('default', 5, 100)

        # Datei sollte existieren
        assert os.path.exists(reset_tracker_state)

        with open(reset_tracker_state, 'r') as f:
            data = json.load(f)
        assert data.get('default:5') == 100

    def test_load_from_disk(self, reset_tracker_state):
        """cycle_base wird von Disk geladen nach Cache-Reset."""
        # Direkt in Datei schreiben
        os.makedirs(os.path.dirname(reset_tracker_state), exist_ok=True)
        with open(reset_tracker_state, 'w') as f:
            json.dump({"default:3": 72}, f)

        # Cache zurücksetzen
        tracker_module._cycle_state.clear()
        tracker_module._loaded = False

        assert get_cycle_base('default', 3) == 72


class TestResetSession:
    """reset_session."""

    def test_reset_removes_session(self):
        """Reset entfernt den cycle_base für eine Session."""
        set_cycle_base('default', 1, 48)
        reset_session('default', 1)
        assert get_cycle_base('default', 1) == 0

    def test_reset_nonexistent_is_noop(self):
        """Reset einer nicht-existierenden Session ist harmlos."""
        reset_session('default', 999)  # Sollte nicht crashen
        assert get_cycle_base('default', 999) == 0

    def test_reset_doesnt_affect_others(self):
        """Reset einer Session lässt andere Sessions unberührt."""
        set_cycle_base('default', 1, 48)
        set_cycle_base('default', 2, 96)
        reset_session('default', 1)
        assert get_cycle_base('default', 1) == 0
        assert get_cycle_base('default', 2) == 96


class TestResetAll:
    """reset_all."""

    def test_clears_everything(self, reset_tracker_state):
        """Reset löscht alle Sessions und die Datei."""
        set_cycle_base('default', 1, 48)
        set_cycle_base('persona_x', 2, 100)
        reset_all()

        assert get_cycle_base('default', 1) == 0
        assert get_cycle_base('persona_x', 2) == 0
        assert not os.path.exists(reset_tracker_state)


class TestRebuildCycleBase:
    """rebuild_cycle_base."""

    def test_basic_rebuild(self):
        """Rebuild berechnet korrekte cycle_base."""
        # 100 Nachrichten, Schwelle 48 → 2 Zyklen → cycle_base = 96
        result = rebuild_cycle_base('default', 1, message_count=100, threshold=48)
        assert result == 96
        assert get_cycle_base('default', 1) == 96

    def test_exact_multiple(self):
        """Rebuild bei exaktem Vielfachen."""
        result = rebuild_cycle_base('default', 1, message_count=96, threshold=48)
        assert result == 96

    def test_threshold_zero_fallback(self):
        """Threshold 0 wird auf 1 gesetzt."""
        result = rebuild_cycle_base('default', 1, message_count=50, threshold=0)
        assert result == 50  # 50 // 1 * 1 = 50


class TestGetProgress:
    """get_progress."""

    def test_basic_progress(self):
        """Fortschrittsberechnung."""
        set_cycle_base('default', 1, 0)
        progress = get_progress('default', 1, message_count=25, threshold=48)

        assert progress['messages_since_reset'] == 25
        assert progress['threshold'] == 48
        assert progress['progress_percent'] == 52.1
        assert progress['cycle_number'] == 1

    def test_progress_after_reset(self):
        """Progress nach Zyklus-Reset."""
        set_cycle_base('default', 1, 48)
        progress = get_progress('default', 1, message_count=60, threshold=48)

        assert progress['messages_since_reset'] == 12
        assert progress['progress_percent'] == 25.0
        assert progress['cycle_number'] == 2

    def test_progress_at_threshold(self):
        """Progress bei 100%."""
        set_cycle_base('default', 1, 0)
        progress = get_progress('default', 1, message_count=48, threshold=48)

        assert progress['progress_percent'] == 100.0

    def test_progress_capped_at_100(self):
        """Progress wird bei 100% gedeckelt."""
        set_cycle_base('default', 1, 0)
        progress = get_progress('default', 1, message_count=60, threshold=48)

        assert progress['progress_percent'] == 100.0


# ─── Tier-Checker Tests ─────────────────────────────────────────────────────

class TestCalculateThreshold:
    """_calculate_threshold."""

    def test_medium_65(self):
        """Mittel bei contextLimit=65 → 48."""
        assert _calculate_threshold(65, "medium") == 48

    def test_frequent_65(self):
        """Häufig bei contextLimit=65 → 32."""
        assert _calculate_threshold(65, "frequent") == 32

    def test_rare_65(self):
        """Selten bei contextLimit=65 → 61."""
        assert _calculate_threshold(65, "rare") == 61

    def test_medium_200(self):
        """Mittel bei contextLimit=200 → 150."""
        assert _calculate_threshold(200, "medium") == 150

    def test_minimum_context(self):
        """Mittel bei contextLimit=10 → 7."""
        assert _calculate_threshold(10, "medium") == 7

    def test_unknown_frequency_fallback(self):
        """Unbekannte Frequenz → Fallback auf medium."""
        assert _calculate_threshold(65, "unknown") == 48


class TestCheckAndTrigger:
    """check_and_trigger_cortex_update — Integrationstest."""

    @patch('utils.cortex.tier_checker._load_cortex_config')
    @patch('utils.cortex.tier_checker._get_context_limit')
    @patch('utils.cortex.tier_checker.get_message_count')
    @patch('utils.cortex.tier_checker._start_background_cortex_update')
    def test_disabled_returns_none(self, mock_bg, mock_count, mock_limit, mock_config):
        """Cortex deaktiviert → None."""
        mock_config.return_value = {"enabled": False, "frequency": "medium"}

        result = check_and_trigger_cortex_update('default', 1)
        assert result is None
        mock_bg.assert_not_called()

    @patch('utils.cortex.tier_checker._load_cortex_config')
    @patch('utils.cortex.tier_checker._get_context_limit')
    @patch('utils.cortex.tier_checker.get_message_count')
    @patch('utils.cortex.tier_checker._start_background_cortex_update')
    def test_no_messages_returns_none(self, mock_bg, mock_count, mock_limit, mock_config):
        """Keine Nachrichten → None."""
        mock_config.return_value = {"enabled": True, "frequency": "medium"}
        mock_limit.return_value = 65
        mock_count.return_value = 0

        result = check_and_trigger_cortex_update('default', 1)
        assert result is None
        mock_bg.assert_not_called()

    @patch('utils.cortex.tier_checker._load_cortex_config')
    @patch('utils.cortex.tier_checker._get_context_limit')
    @patch('utils.cortex.tier_checker.get_message_count')
    @patch('utils.cortex.tier_checker._start_background_cortex_update')
    def test_below_threshold_no_trigger(self, mock_bg, mock_count, mock_limit, mock_config):
        """Unter Schwelle → kein Trigger."""
        mock_config.return_value = {"enabled": True, "frequency": "medium"}
        mock_limit.return_value = 65
        mock_count.return_value = 30  # 30 < 48

        result = check_and_trigger_cortex_update('default', 1)
        assert result is not None
        assert result['triggered'] is False
        assert result['progress']['messages_since_reset'] == 30
        mock_bg.assert_not_called()

    @patch('utils.cortex.tier_checker._load_cortex_config')
    @patch('utils.cortex.tier_checker._get_context_limit')
    @patch('utils.cortex.tier_checker.get_message_count')
    @patch('utils.cortex.tier_checker._start_background_cortex_update')
    def test_at_threshold_triggers(self, mock_bg, mock_count, mock_limit, mock_config):
        """Exakt an Schwelle → Trigger!"""
        mock_config.return_value = {"enabled": True, "frequency": "medium"}
        mock_limit.return_value = 65
        mock_count.return_value = 48  # 48 >= 48

        result = check_and_trigger_cortex_update('default', 1)
        assert result is not None
        assert result['triggered'] is True
        assert result['frequency'] == 'medium'
        mock_bg.assert_called_once_with('default', 1)

    @patch('utils.cortex.tier_checker._load_cortex_config')
    @patch('utils.cortex.tier_checker._get_context_limit')
    @patch('utils.cortex.tier_checker.get_message_count')
    @patch('utils.cortex.tier_checker._start_background_cortex_update')
    def test_second_cycle_trigger(self, mock_bg, mock_count, mock_limit, mock_config):
        """Zweiter Zyklus triggert korrekt."""
        mock_config.return_value = {"enabled": True, "frequency": "medium"}
        mock_limit.return_value = 65
        mock_count.return_value = 48

        # Erster Trigger
        result1 = check_and_trigger_cortex_update('default', 1)
        assert result1['triggered'] is True

        # Zweiter Check: 60 Nachrichten, cycle_base ist jetzt 48 → seit Reset: 12 < 48
        mock_count.return_value = 60
        result2 = check_and_trigger_cortex_update('default', 1)
        assert result2['triggered'] is False
        assert result2['progress']['messages_since_reset'] == 12

        # Dritter Check: 96 Nachrichten → seit Reset: 48 >= 48 → Trigger!
        mock_count.return_value = 96
        result3 = check_and_trigger_cortex_update('default', 1)
        assert result3['triggered'] is True

    @patch('utils.cortex.tier_checker._load_cortex_config')
    @patch('utils.cortex.tier_checker._get_context_limit')
    @patch('utils.cortex.tier_checker.get_message_count')
    @patch('utils.cortex.tier_checker._start_background_cortex_update')
    def test_frequent_triggers_earlier(self, mock_bg, mock_count, mock_limit, mock_config):
        """Häufig (50%) triggert früher als Mittel (75%)."""
        mock_config.return_value = {"enabled": True, "frequency": "frequent"}
        mock_limit.return_value = 65
        mock_count.return_value = 32  # 32 >= floor(65 * 0.50) = 32

        result = check_and_trigger_cortex_update('default', 1)
        assert result['triggered'] is True
