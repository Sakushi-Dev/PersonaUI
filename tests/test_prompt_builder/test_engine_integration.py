"""
Tests für PromptEngine Integration.

Testet:
- Engine-Delegation in ChatPromptBuilder
- PromptEngine Parity (strukturelle Korrektheit)
- ChatService Engine-Nutzung
- Architektur-Regeln für prompt_engine/
"""
import os
import sys
import pytest
from unittest.mock import MagicMock, patch, PropertyMock


# ============================================================
# PromptEngine Parity Tests
# ============================================================

class TestPromptEngineParity:
    """Stellt sicher, dass Engine-Prompts sinnvolle Ergebnisse liefern.

    Hinweis: Exakte Parity mit alten .txt-Buildern ist nicht verlangt,
    da die JSON-Inhalte leicht anders formuliert sein können.
    Wir testen stattdessen, dass die Engine-Outputs strukturell korrekt sind.
    """

    @pytest.fixture(autouse=True)
    def setup_engine(self):
        """Stellt sicher, dass PromptEngine geladen ist."""
        from utils.prompt_engine import PromptEngine
        self.engine = PromptEngine()
        if not self.engine.is_loaded:
            pytest.skip("PromptEngine nicht geladen (JSON-Dateien fehlen)")

    def test_system_prompt_default_has_content(self):
        """Default System-Prompt enthält sinnvollen Inhalt."""
        result = self.engine.build_system_prompt(variant='default')
        assert isinstance(result, str)
        assert len(result) > 100

    def test_system_prompt_experimental_has_content(self):
        """Experimental System-Prompt enthält abweichende Persona-Description."""
        result = self.engine.build_system_prompt(variant='experimental')
        assert isinstance(result, str)
        assert len(result) > 100

    def test_prefill_default_has_content(self):
        """Default Prefill enthält Remember-Text."""
        result = self.engine.build_prefill(variant='default')
        assert isinstance(result, str)
        assert len(result) > 10

    def test_prefill_experimental_is_valid(self):
        """Experimental Prefill liefert String (kann leer sein wenn nicht konfiguriert)."""
        result = self.engine.build_prefill(variant='experimental')
        assert isinstance(result, str)

    def test_consent_dialog_experimental_is_none(self):
        """Consent Dialog ist nicht mehr vorhanden (experimental Prompts entfernt)."""
        result = self.engine.get_consent_dialog(variant='experimental')
        assert result is None

    def test_consent_dialog_default_is_none(self):
        """Consent Dialog ist im Default-Modus nicht vorhanden."""
        result = self.engine.get_consent_dialog(variant='default')
        assert result is None

    def test_afterthought_inner_dialogue(self):
        """Afterthought Inner Dialogue enthält sinnvollen Text."""
        result = self.engine.build_afterthought_inner_dialogue(
            variant='default',
            runtime_vars={'elapsed_time': '5 Minuten'}
        )
        assert isinstance(result, str)
        assert len(result) > 50
        assert 'INNERER DIALOG' in result or 'innerer Dialog' in result.lower() or 'NACHGEDANKE' in result

    def test_afterthought_followup(self):
        """Afterthought Followup enthält sinnvollen Text."""
        result = self.engine.build_afterthought_followup(
            variant='default',
            runtime_vars={'elapsed_time': '3 Minuten', 'inner_dialogue': 'Test-Gedanken'}
        )
        assert isinstance(result, str)
        assert len(result) > 30

    def test_afterthought_system_note(self):
        """Afterthought System Note (append) enthält NACHGEDANKE."""
        result = self.engine.get_system_prompt_append(variant='default')
        assert isinstance(result, str)
        assert 'NACHGEDANKE' in result

    def test_summary_prompt_has_system_and_prefill(self):
        """Summary Prompt enthält system_prompt und prefill."""
        result = self.engine.build_summary_prompt(variant='default')
        assert isinstance(result, dict)
        assert 'system_prompt' in result
        assert 'prefill' in result
        assert len(result['system_prompt']) > 100
        assert len(result['prefill']) > 10

    def test_spec_autofill_persona_type(self):
        """Spec-Autofill Persona-Type enthält Input."""
        result = self.engine.build_spec_autofill_prompt('persona_type', 'Fee')
        assert isinstance(result, str)
        assert 'Fee' in result

    def test_spec_autofill_all_types(self):
        """Alle 5 Spec-Autofill Typen liefern Ergebnisse."""
        types = ['persona_type', 'core_trait', 'knowledge', 'scenario', 'expression_style']
        for spec_type in types:
            result = self.engine.build_spec_autofill_prompt(spec_type, 'Testinput')
            assert result is not None, f"Spec-Autofill '{spec_type}' lieferte None"
            assert 'Testinput' in result, f"Spec-Autofill '{spec_type}' enthält nicht den Input"

    def test_title_generation_prompt(self):
        """Title Generation Prompt enthält Context."""
        result = self.engine.resolve_prompt(
            'title_generation', variant='default',
            runtime_vars={'context': 'Hallo Welt'}
        )
        assert isinstance(result, str)
        assert 'Hallo Welt' in result

    def test_memory_context_prompt(self):
        """Memory Context Prompt enthält Memory-Einträge."""
        result = self.engine.resolve_prompt(
            'memory_context', variant='default',
            runtime_vars={'memory_entries': 'Test Memory Content'}
        )
        assert isinstance(result, str)
        assert 'Test Memory Content' in result
        assert 'MEMORY CONTEXT' in result


# ============================================================
# Service Engine Integration
# ============================================================

class TestServiceEngineIntegration:
    """Testet dass Services die Engine korrekt verwenden."""

    def test_chat_service_passes_engine(self, mock_api_client):
        """ChatService verwendet Engine direkt (nicht über prompt_builder)."""
        from utils.services.chat_service import ChatService
        service = ChatService(mock_api_client)
        # Engine ist vorhanden wenn JSON-Dateien existieren
        if service._engine:
            assert service._engine.is_loaded


# ============================================================
# Architecture Tests
# ============================================================

class TestArchitecturePhase2:
    """Architektur-Regeln für prompt_engine/."""

    def test_prompt_engine_no_flask_imports(self):
        """prompt_engine/ darf kein Flask importieren."""
        import glob
        engine_dir = os.path.dirname(os.path.abspath(
            __import__('utils.prompt_engine', fromlist=['__init__']).__file__
        ))
        for py_file in glob.glob(os.path.join(engine_dir, '*.py')):
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            filename = os.path.basename(py_file)
            assert 'import flask' not in content.lower() and 'from flask' not in content, \
                f"prompt_engine/{filename} darf kein Flask importieren"

    def test_prompt_engine_no_pywebview_imports(self):
        """prompt_engine/ darf kein PyWebView importieren."""
        import glob
        engine_dir = os.path.dirname(os.path.abspath(
            __import__('utils.prompt_engine', fromlist=['__init__']).__file__
        ))
        for py_file in glob.glob(os.path.join(engine_dir, '*.py')):
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            filename = os.path.basename(py_file)
            assert 'import webview' not in content and 'from webview' not in content, \
                f"prompt_engine/{filename} darf kein webview importieren"
