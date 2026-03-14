"""
Tests für CortexService.
Unit-Tests für Dateiverwaltung, Pfadauflösung, Prompt-Integration und tool_use Handling.
"""
import os
import pytest
from unittest.mock import MagicMock

import utils.cortex as cortex_module
import utils.cortex.constants as cortex_constants
from utils.cortex import (
    CortexService,
    CORTEX_FILES,
    DATA_DIR,
    MEMORY_TEMPLATE,
    SOUL_TEMPLATE,
    RELATIONSHIP_TEMPLATE,
    BONDING_TEMPLATE,
    GROWTH_TEMPLATE,
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
    """Temporäres Data-Verzeichnis für isolierte Cortex-Tests."""
    original_data_dir = cortex_constants.DATA_DIR

    test_data_dir = str(tmp_path / 'data')

    cortex_constants.DATA_DIR = test_data_dir

    yield tmp_path / 'data'

    cortex_constants.DATA_DIR = original_data_dir


# ============================================================
# Standalone-Funktionen Tests
# ============================================================

class TestGetCortexDir:
    def test_default_persona(self):
        result = get_cortex_dir('default')
        assert result == os.path.join(DATA_DIR, 'default', 'cortex')

    def test_empty_persona_id(self):
        result = get_cortex_dir('')
        assert result == os.path.join(DATA_DIR, 'default', 'cortex')

    def test_none_persona_id(self):
        result = get_cortex_dir(None)
        assert result == os.path.join(DATA_DIR, 'default', 'cortex')

    def test_custom_persona(self):
        result = get_cortex_dir('a1b2c3d4')
        assert result == os.path.join(DATA_DIR, 'a1b2c3d4', 'cortex')


class TestEnsureCortexDir:
    def test_creates_default_dir_and_files(self, temp_cortex_dir):
        ensure_cortex_dir('default')
        default_dir = temp_cortex_dir / 'default' / 'cortex'
        assert default_dir.exists()
        for fname in CORTEX_FILES:
            assert (default_dir / fname).exists()

    def test_creates_custom_dir_and_files(self, temp_cortex_dir):
        ensure_cortex_dir('test123')
        custom_dir = temp_cortex_dir / 'test123' / 'cortex'
        assert custom_dir.exists()
        for fname in CORTEX_FILES:
            assert (custom_dir / fname).exists()

    def test_does_not_overwrite_existing_files(self, temp_cortex_dir):
        ensure_cortex_dir('default')
        memory_file = temp_cortex_dir / 'default' / 'cortex' / 'memory.md'
        memory_file.write_text('Custom content', encoding='utf-8')

        # Erneuter Aufruf darf nicht überschreiben
        ensure_cortex_dir('default')
        assert memory_file.read_text(encoding='utf-8') == 'Custom content'

    def test_template_content_is_correct(self, temp_cortex_dir):
        ensure_cortex_dir('default')
        default_dir = temp_cortex_dir / 'default' / 'cortex'
        assert (default_dir / 'memory.md').read_text(encoding='utf-8') == MEMORY_TEMPLATE
        assert (default_dir / 'soul.md').read_text(encoding='utf-8') == SOUL_TEMPLATE
        assert (default_dir / 'relationship.md').read_text(encoding='utf-8') == RELATIONSHIP_TEMPLATE
        assert (default_dir / 'bonding.md').read_text(encoding='utf-8') == BONDING_TEMPLATE
        assert (default_dir / 'growth.md').read_text(encoding='utf-8') == GROWTH_TEMPLATE


class TestCreateCortexDir:
    def test_success(self, temp_cortex_dir):
        result = create_cortex_dir('new_persona')
        assert result is True
        assert (temp_cortex_dir / 'new_persona' / 'cortex').exists()

    def test_returns_true_for_default(self, temp_cortex_dir):
        result = create_cortex_dir('default')
        assert result is True


class TestDeleteCortexDir:
    def test_delete_custom_persona(self, temp_cortex_dir):
        ensure_cortex_dir('abc123')
        assert (temp_cortex_dir / 'abc123' / 'cortex').exists()

        result = delete_cortex_dir('abc123')
        assert result is True
        assert not (temp_cortex_dir / 'abc123' / 'cortex').exists()

    def test_cannot_delete_default(self, temp_cortex_dir):
        ensure_cortex_dir('default')
        result = delete_cortex_dir('default')
        assert result is False
        assert (temp_cortex_dir / 'default' / 'cortex').exists()

    def test_delete_nonexistent_returns_false(self, temp_cortex_dir):
        result = delete_cortex_dir('nonexistent')
        assert result is False


# ============================================================
# CortexService Method Tests
# ============================================================

class TestCortexServicePathResolution:
    def test_get_cortex_path_default(self, cortex_service):
        path = cortex_service.get_cortex_path('default')
        assert path == os.path.join(DATA_DIR, 'default', 'cortex')

    def test_get_cortex_path_custom(self, cortex_service):
        path = cortex_service.get_cortex_path('xyz789')
        assert path.endswith(os.path.join('xyz789', 'cortex'))


class TestCortexServiceReadFile:
    def test_read_existing_file(self, cortex_service, temp_cortex_dir):
        ensure_cortex_dir('default')
        content = cortex_service.read_file('default', 'memory.md')
        assert '# Memory' in content

    def test_read_invalid_filename_raises(self, cortex_service):
        with pytest.raises(ValueError, match="Ungültige Cortex-Datei"):
            cortex_service.read_file('default', 'invalid.md')

    def test_read_all_returns_three_keys(self, cortex_service, temp_cortex_dir):
        ensure_cortex_dir('default')
        result = cortex_service.read_all('default')
        assert set(result.keys()) == {'memory', 'soul', 'relationship'}
        assert '# Memory' in result['memory']
        assert '# Soul' in result['soul']
        assert '# Relationship' in result['relationship']


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
