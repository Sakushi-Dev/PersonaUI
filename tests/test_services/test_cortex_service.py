"""
Tests für CortexService.
Unit-Tests für Dateiverwaltung, Pfadauflösung, Prompt-Integration und tool_use Handling.
"""
import os
import shutil
import pytest
from unittest.mock import MagicMock, patch

import utils.cortex_service as cortex_module
from utils.cortex_service import (
    CortexService,
    CORTEX_FILES,
    TEMPLATES,
    CORTEX_BASE_DIR,
    CORTEX_DEFAULT_DIR,
    CORTEX_CUSTOM_DIR,
    MEMORY_TEMPLATE,
    SOUL_TEMPLATE,
    RELATIONSHIP_TEMPLATE,
    get_cortex_dir,
    ensure_cortex_dir,
    create_cortex_dir,
    delete_cortex_dir,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def mock_api_client():
    """Gemockter ApiClient für CortexService"""
    client = MagicMock()
    client.is_ready = True
    return client


@pytest.fixture
def cortex_service(mock_api_client):
    """CortexService-Instanz mit Mock-ApiClient"""
    return CortexService(mock_api_client)


@pytest.fixture
def temp_cortex_dir(tmp_path):
    """Temporäres Cortex-Verzeichnis für isolierte Tests."""
    original_base = cortex_module.CORTEX_BASE_DIR
    original_default = cortex_module.CORTEX_DEFAULT_DIR
    original_custom = cortex_module.CORTEX_CUSTOM_DIR

    test_base = str(tmp_path / 'cortex')
    test_default = str(tmp_path / 'cortex' / 'default')
    test_custom = str(tmp_path / 'cortex' / 'custom')

    cortex_module.CORTEX_BASE_DIR = test_base
    cortex_module.CORTEX_DEFAULT_DIR = test_default
    cortex_module.CORTEX_CUSTOM_DIR = test_custom

    yield tmp_path / 'cortex'

    cortex_module.CORTEX_BASE_DIR = original_base
    cortex_module.CORTEX_DEFAULT_DIR = original_default
    cortex_module.CORTEX_CUSTOM_DIR = original_custom


# ============================================================
# Standalone-Funktionen Tests
# ============================================================

class TestGetCortexDir:
    def test_default_persona(self):
        result = get_cortex_dir('default')
        assert result == CORTEX_DEFAULT_DIR

    def test_empty_persona_id(self):
        result = get_cortex_dir('')
        assert result == CORTEX_DEFAULT_DIR

    def test_none_persona_id(self):
        result = get_cortex_dir(None)
        assert result == CORTEX_DEFAULT_DIR

    def test_custom_persona(self):
        result = get_cortex_dir('a1b2c3d4')
        assert result == os.path.join(CORTEX_CUSTOM_DIR, 'a1b2c3d4')


class TestEnsureCortexDir:
    def test_creates_default_dir_and_files(self, temp_cortex_dir):
        ensure_cortex_dir('default')
        default_dir = temp_cortex_dir / 'default'
        assert default_dir.exists()
        for fname in CORTEX_FILES:
            assert (default_dir / fname).exists()

    def test_creates_custom_dir_and_files(self, temp_cortex_dir):
        ensure_cortex_dir('test123')
        custom_dir = temp_cortex_dir / 'custom' / 'test123'
        assert custom_dir.exists()
        for fname in CORTEX_FILES:
            assert (custom_dir / fname).exists()

    def test_does_not_overwrite_existing_files(self, temp_cortex_dir):
        ensure_cortex_dir('default')
        memory_file = temp_cortex_dir / 'default' / 'memory.md'
        memory_file.write_text('Custom content', encoding='utf-8')

        # Erneuter Aufruf darf nicht überschreiben
        ensure_cortex_dir('default')
        assert memory_file.read_text(encoding='utf-8') == 'Custom content'

    def test_template_content_is_correct(self, temp_cortex_dir):
        ensure_cortex_dir('default')
        default_dir = temp_cortex_dir / 'default'
        assert (default_dir / 'memory.md').read_text(encoding='utf-8') == MEMORY_TEMPLATE
        assert (default_dir / 'soul.md').read_text(encoding='utf-8') == SOUL_TEMPLATE
        assert (default_dir / 'relationship.md').read_text(encoding='utf-8') == RELATIONSHIP_TEMPLATE


class TestCreateCortexDir:
    def test_success(self, temp_cortex_dir):
        result = create_cortex_dir('new_persona')
        assert result is True
        assert (temp_cortex_dir / 'custom' / 'new_persona').exists()

    def test_returns_true_for_default(self, temp_cortex_dir):
        result = create_cortex_dir('default')
        assert result is True


class TestDeleteCortexDir:
    def test_delete_custom_persona(self, temp_cortex_dir):
        ensure_cortex_dir('abc123')
        assert (temp_cortex_dir / 'custom' / 'abc123').exists()

        result = delete_cortex_dir('abc123')
        assert result is True
        assert not (temp_cortex_dir / 'custom' / 'abc123').exists()

    def test_cannot_delete_default(self, temp_cortex_dir):
        ensure_cortex_dir('default')
        result = delete_cortex_dir('default')
        assert result is False
        assert (temp_cortex_dir / 'default').exists()

    def test_delete_nonexistent_returns_false(self, temp_cortex_dir):
        result = delete_cortex_dir('nonexistent')
        assert result is False


# ============================================================
# CortexService Method Tests
# ============================================================

class TestCortexServicePathResolution:
    def test_get_cortex_path_default(self, cortex_service):
        path = cortex_service.get_cortex_path('default')
        assert path == CORTEX_DEFAULT_DIR

    def test_get_cortex_path_custom(self, cortex_service):
        path = cortex_service.get_cortex_path('xyz789')
        assert path.endswith(os.path.join('custom', 'xyz789'))


class TestCortexServiceReadFile:
    def test_read_existing_file(self, cortex_service, temp_cortex_dir):
        ensure_cortex_dir('default')
        content = cortex_service.read_file('default', 'memory.md')
        assert '# Memories' in content

    def test_read_invalid_filename_raises(self, cortex_service):
        with pytest.raises(ValueError, match="Ungültige Cortex-Datei"):
            cortex_service.read_file('default', 'invalid.md')

    def test_read_all_returns_three_keys(self, cortex_service, temp_cortex_dir):
        ensure_cortex_dir('default')
        result = cortex_service.read_all('default')
        assert set(result.keys()) == {'memory', 'soul', 'relationship'}
        assert '# Memories' in result['memory']
        assert '# Soul Development' in result['soul']
        assert '# Relationship Dynamics' in result['relationship']


class TestCortexServiceWriteFile:
    def test_write_and_read_back(self, cortex_service, temp_cortex_dir):
        ensure_cortex_dir('default')
        cortex_service.write_file('default', 'memory.md', '# Custom Memory')
        content = cortex_service.read_file('default', 'memory.md')
        assert content == '# Custom Memory'

    def test_write_invalid_filename_raises(self, cortex_service):
        with pytest.raises(ValueError, match="Ungültige Cortex-Datei"):
            cortex_service.write_file('default', 'hack.txt', 'evil')


class TestCortexServicePromptIntegration:
    def test_get_cortex_for_prompt_keys(self, cortex_service, temp_cortex_dir):
        ensure_cortex_dir('default')
        result = cortex_service.get_cortex_for_prompt('default')
        assert set(result.keys()) == {'cortex_memory', 'cortex_soul', 'cortex_relationship'}

    def test_get_cortex_for_prompt_content(self, cortex_service, temp_cortex_dir):
        ensure_cortex_dir('default')
        cortex_service.write_file('default', 'memory.md', '# Test Memory Content')
        result = cortex_service.get_cortex_for_prompt('default')
        assert result['cortex_memory'] == '### Memories & Knowledge\n\n# Test Memory Content'


class TestCortexServiceFilenameValidation:
    """Alle drei erlaubten Dateinamen werden akzeptiert, andere abgelehnt."""

    def test_valid_filenames(self, cortex_service, temp_cortex_dir):
        ensure_cortex_dir('default')
        for fname in CORTEX_FILES:
            content = cortex_service.read_file('default', fname)
            assert isinstance(content, str)

    @pytest.mark.parametrize("bad_name", [
        'notes.md', '../secret.txt', 'memory', 'MEMORY.MD',
        '../../etc/passwd', '', 'soul.txt'
    ])
    def test_invalid_filenames(self, cortex_service, bad_name):
        with pytest.raises(ValueError):
            cortex_service.read_file('default', bad_name)


class TestCortexServiceToolCallHandler:
    def test_handle_read_tool_call(self, cortex_service, temp_cortex_dir):
        ensure_cortex_dir('default')
        result = cortex_service._handle_tool_call(
            'default', 'cortex_read_file', {'filename': 'memory.md'}
        )
        assert '# Memories' in result

    def test_handle_write_tool_call(self, cortex_service, temp_cortex_dir):
        ensure_cortex_dir('default')
        result = cortex_service._handle_tool_call(
            'default', 'cortex_write_file',
            {'filename': 'soul.md', 'content': '# Updated Soul'}
        )
        assert 'erfolgreich aktualisiert' in result

        # Verify it was written
        content = cortex_service.read_file('default', 'soul.md')
        assert content == '# Updated Soul'

    def test_handle_invalid_tool_name(self, cortex_service):
        result = cortex_service._handle_tool_call(
            'default', 'unknown_tool', {}
        )
        assert 'Unbekanntes Tool' in result

    def test_handle_invalid_filename_in_read(self, cortex_service):
        result = cortex_service._handle_tool_call(
            'default', 'cortex_read_file', {'filename': 'hack.md'}
        )
        assert 'Fehler' in result


class TestCortexServiceFormatHistory:
    def test_formats_history(self, cortex_service):
        history = [
            {'role': 'user', 'content': 'Hallo!'},
            {'role': 'assistant', 'content': 'Hi, wie gehts?'},
            {'role': 'user', 'content': 'Gut, danke!'},
        ]
        result = cortex_service._format_history_for_update(history, 'Mia')
        assert 'User: Hallo!' in result
        assert 'Mia: Hi, wie gehts?' in result
        assert 'User: Gut, danke!' in result


class TestCortexServiceExecuteUpdate:
    def test_returns_error_when_api_not_ready(self, cortex_service, mock_api_client):
        mock_api_client.is_ready = False
        result = cortex_service.execute_cortex_update(
            'default', [{'role': 'user', 'content': 'hi'}], {'char_name': 'Mia'}
        )
        assert result['success'] is False
        assert 'nicht initialisiert' in result['error']

    def test_returns_error_without_history(self, cortex_service):
        result = cortex_service.execute_cortex_update(
            'default', [], {'char_name': 'Mia'}
        )
        assert result['success'] is False
        assert 'Kein Gesprächsverlauf' in result['error']
