"""
Tests for settings_defaults.py — load_model_options, get_autofill_model
"""
import json
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import utils.settings_defaults as sd


@pytest.fixture(autouse=True)
def reset_cache():
    """Clear model options cache before each test."""
    sd._MODEL_OPTIONS_CACHE = None
    yield
    sd._MODEL_OPTIONS_CACHE = None


class TestLoadModelOptions:
    def test_loads_from_file(self, tmp_path):
        options = [{"id": "model-1", "name": "Model One"}]
        file = tmp_path / "model_options.json"
        file.write_text(json.dumps(options), encoding='utf-8')

        with patch.object(sd, '_MODEL_OPTIONS_FILE', str(file)):
            result = sd.load_model_options()
        assert len(result) == 1
        assert result[0]["id"] == "model-1"

    def test_caches_result(self, tmp_path):
        options = [{"id": "cached"}]
        file = tmp_path / "model_options.json"
        file.write_text(json.dumps(options), encoding='utf-8')

        with patch.object(sd, '_MODEL_OPTIONS_FILE', str(file)):
            r1 = sd.load_model_options()
            r2 = sd.load_model_options()
        assert r1 is r2

    def test_missing_file_returns_empty(self):
        with patch.object(sd, '_MODEL_OPTIONS_FILE', "/nonexistent/path.json"):
            result = sd.load_model_options()
        assert result == []


class TestGetAutofillModel:
    def test_returns_autofill_model(self):
        with patch.object(sd, 'get_default', side_effect=lambda k, **kw: {
            'autofillModel': 'autofill-model',
            'model': 'primary-model'
        }.get(k)):
            result = sd.get_autofill_model()
        assert result == "autofill-model"

    def test_falls_back_to_primary(self):
        with patch.object(sd, 'get_default', side_effect=lambda k, **kw: {
            'autofillModel': None,
            'model': 'primary-model'
        }.get(k)):
            result = sd.get_autofill_model()
        assert result == "primary-model"
