"""
Tests for Phase 5 – Export, Import, Factory Reset, Integrity.

Tests:
- export_prompt_set (ZIP export)
- import_prompt_set (Replace, Merge, Overwrite)
- factory_reset (restoration from _defaults)
- validate_integrity (corruption detection + recovery)
"""

import os
import json
import shutil
import zipfile
import pytest

# ===== Shared Fixture =====

@pytest.fixture
def engine_dir(tmp_path):
    """Creates a temporary instructions/ setup with _defaults/ for tests."""
    instructions_dir = tmp_path / 'instructions'
    instructions_dir.mkdir()
    prompts_dir = instructions_dir / 'prompts'
    prompts_dir.mkdir()
    defaults_dir = prompts_dir / '_defaults'
    defaults_dir.mkdir()

    # Manifest
    manifest = {
        "version": "2.0",
        "prompts": {
            "test_prompt": {
                "name": "Test",
                "description": "Ein Test-Prompt",
                "category": "system",
                "type": "text",
                "target": "system_prompt",
                "position": "system_prompt",
                "order": 100,
                "enabled": True,
                "domain_file": "test.json",
                "tags": ["test"]
            }
        }
    }
    meta_dir = prompts_dir / '_meta'
    meta_dir.mkdir()
    (meta_dir / 'prompt_manifest.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8'
    )

    # Registry
    registry = {
        "version": "2.0",
        "placeholders": {
            "char_name": {
                "name": "Persona-Name",
                "source": "persona_config",
                "source_path": "persona_settings.name",
                "type": "string",
                "default": "Assistant",
                "category": "persona",
                "resolve_phase": "static"
            }
        }
    }
    (meta_dir / 'placeholder_registry.json').write_text(
        json.dumps(registry, ensure_ascii=False, indent=2), encoding='utf-8'
    )

    # Domain-Datei
    domain = {
        "test_prompt": {
            "variants": {
                "default": {"content": "Original content."}
            },
            "placeholders_used": []
        }
    }
    (prompts_dir / 'test.json').write_text(
        json.dumps(domain, ensure_ascii=False, indent=2), encoding='utf-8'
    )

    # _defaults: Kopien
    defaults_meta_dir = defaults_dir / '_meta'
    defaults_meta_dir.mkdir()
    for filename in ('prompt_manifest.json', 'placeholder_registry.json'):
        src = meta_dir / filename
        shutil.copy2(str(src), str(defaults_meta_dir / filename))
    shutil.copy2(str(prompts_dir / 'test.json'), str(defaults_dir / 'test.json'))

    # Persona config (for resolver)
    personas_dir = instructions_dir / 'personas' / 'active'
    personas_dir.mkdir(parents=True)
    persona_config = {
        "active_persona_id": "test",
        "persona_settings": {"name": "TestPersona"}
    }
    (personas_dir / 'persona_config.json').write_text(
        json.dumps(persona_config, ensure_ascii=False, indent=2), encoding='utf-8'
    )

    # Settings (for user_name)
    settings_dir = tmp_path / 'settings'
    settings_dir.mkdir(parents=True, exist_ok=True)
    (settings_dir / 'user_profile.json').write_text(
        json.dumps({"user_name": "TestUser"}, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )

    return str(instructions_dir)


def _make_engine(instructions_dir):
    """Creates a PromptEngine without real compute functions."""
    from src.utils.prompt_engine import PromptEngine
    engine = PromptEngine(instructions_dir)
    if engine._resolver:
        engine._resolver._compute_functions = {}
    return engine


# ===== Export Tests =====

class TestExportPromptSet:
    """Tests for export_prompt_set()."""

    def test_export_creates_zip(self, engine_dir, tmp_path):
        """Export creates a ZIP file."""
        engine = _make_engine(engine_dir)
        output = str(tmp_path / 'export' / 'test_export.zip')

        result = engine.export_prompt_set(output)
        assert os.path.exists(result)
        assert result == output

    def test_export_zip_contents(self, engine_dir, tmp_path):
        """ZIP contains manifest, registry, domain files and metadata."""
        engine = _make_engine(engine_dir)
        output = str(tmp_path / 'export.zip')
        engine.export_prompt_set(output)

        with zipfile.ZipFile(output, 'r') as zf:
            names = zf.namelist()
            assert '_meta/prompt_manifest.json' in names
            assert '_meta/placeholder_registry.json' in names
            assert 'prompts/test.json' in names
            assert 'metadata.json' in names

    def test_export_metadata_content(self, engine_dir, tmp_path):
        """Metadata contains expected fields."""
        engine = _make_engine(engine_dir)
        output = str(tmp_path / 'export.zip')
        engine.export_prompt_set(output)

        with zipfile.ZipFile(output, 'r') as zf:
            metadata = json.loads(zf.read('metadata.json'))
            assert 'export_date' in metadata
            assert metadata['version'] == '2.0'
            assert metadata['prompt_count'] == 1
            assert 'test.json' in metadata['domain_files']

    def test_export_excludes_defaults(self, engine_dir, tmp_path):
        """_defaults/ is not exported."""
        engine = _make_engine(engine_dir)
        output = str(tmp_path / 'export.zip')
        engine.export_prompt_set(output)

        with zipfile.ZipFile(output, 'r') as zf:
            names = zf.namelist()
            assert not any('_defaults' in n for n in names)


# ===== Import Tests =====

class TestImportPromptSet:
    """Tests for import_prompt_set()."""

    def _create_import_zip(self, tmp_path, domain_content="Imported content."):
        """Creates an import ZIP."""
        zip_path = str(tmp_path / 'import.zip')
        manifest = {
            "version": "3.0",
            "prompts": {
                "test_prompt": {
                    "name": "Imported Test",
                    "type": "text",
                    "target": "system_prompt",
                    "position": "system_prompt",
                    "order": 100,
                    "enabled": True,
                    "domain_file": "test.json"
                },
                "new_prompt": {
                    "name": "New",
                    "type": "text",
                    "target": "system_prompt",
                    "position": "system_prompt",
                    "order": 200,
                    "enabled": True,
                    "domain_file": "new.json"
                }
            }
        }
        domain = {
            "test_prompt": {
                "variants": {"default": {"content": domain_content}},
                "placeholders_used": []
            }
        }
        new_domain = {
            "new_prompt": {
                "variants": {"default": {"content": "Brand new prompt."}},
                "placeholders_used": []
            }
        }

        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr('_meta/prompt_manifest.json', json.dumps(manifest, indent=2))
            zf.writestr('prompts/test.json', json.dumps(domain, indent=2))
            zf.writestr('prompts/new.json', json.dumps(new_domain, indent=2))
            zf.writestr('metadata.json', json.dumps({"export_date": "2026-01-01"}))

        return zip_path

    def test_import_replace(self, engine_dir, tmp_path):
        """Import mode 'replace' replaces everything."""
        engine = _make_engine(engine_dir)
        zip_path = self._create_import_zip(tmp_path)

        result = engine.import_prompt_set(zip_path, merge_mode='replace')
        assert result['imported'] >= 2  # manifest + domain
        assert len(result['errors']) == 0

        # Manifest version should now be 3.0
        manifest = engine._loader.load_manifest()
        assert manifest['version'] == '3.0'

    def test_import_merge_skips_existing(self, engine_dir, tmp_path):
        """Import mode 'merge' skips existing files."""
        engine = _make_engine(engine_dir)
        zip_path = self._create_import_zip(tmp_path)

        result = engine.import_prompt_set(zip_path, merge_mode='merge')
        assert result['skipped'] >= 1  # manifest + test.json exist
        # new.json should have been imported
        new_path = os.path.join(engine_dir, 'prompts', 'new.json')
        assert os.path.exists(new_path)

    def test_import_overwrite_replaces_existing(self, engine_dir, tmp_path):
        """Import mode 'overwrite' overwrites existing files."""
        engine = _make_engine(engine_dir)
        zip_path = self._create_import_zip(tmp_path, domain_content="Overwritten!")

        result = engine.import_prompt_set(zip_path, merge_mode='overwrite')
        assert result['imported'] >= 2
        assert result['skipped'] == 0

    def test_import_invalid_mode_raises(self, engine_dir, tmp_path):
        """Invalid merge_mode raises ValueError."""
        engine = _make_engine(engine_dir)
        zip_path = self._create_import_zip(tmp_path)

        with pytest.raises(ValueError, match='invalid'):
            engine.import_prompt_set(zip_path, merge_mode='invalid')

    def test_import_missing_zip_raises(self, engine_dir):
        """Missing ZIP file raises FileNotFoundError."""
        engine = _make_engine(engine_dir)

        with pytest.raises(FileNotFoundError):
            engine.import_prompt_set('/nonexistent/file.zip')

    def test_import_invalid_zip_returns_error(self, engine_dir, tmp_path):
        """Invalid ZIP file returns error."""
        bad_path = str(tmp_path / 'bad.zip')
        with open(bad_path, 'w') as f:
            f.write("not a zip file")

        engine = _make_engine(engine_dir)
        result = engine.import_prompt_set(bad_path)
        assert len(result['errors']) > 0

    def test_import_zip_without_manifest_returns_error(self, engine_dir, tmp_path):
        """ZIP without manifest returns error."""
        zip_path = str(tmp_path / 'no_manifest.zip')
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr('prompts/test.json', '{}')

        engine = _make_engine(engine_dir)
        result = engine.import_prompt_set(zip_path)
        assert len(result['errors']) > 0
        assert 'manifest' in result['errors'][0].lower()

    def test_roundtrip_export_import(self, engine_dir, tmp_path):
        """Export → Import roundtrip preserves data."""
        engine = _make_engine(engine_dir)

        # Export
        export_path = str(tmp_path / 'roundtrip.zip')
        engine.export_prompt_set(export_path)

        # Modify domain file
        prompts_dir = os.path.join(engine_dir, 'prompts')
        modified = {"test_prompt": {"variants": {"default": {"content": "Modified!"}}, "placeholders_used": []}}
        with open(os.path.join(prompts_dir, 'test.json'), 'w', encoding='utf-8') as f:
            json.dump(modified, f)

        # Import (replace)
        result = engine.import_prompt_set(export_path, merge_mode='replace')
        assert len(result['errors']) == 0

        # Check: original restored
        domain = engine._loader.load_domain_file('test.json')
        assert domain['test_prompt']['variants']['default']['content'] == 'Original content.'


# ===== Factory Reset Tests =====

class TestFactoryReset:
    """Tests for factory_reset()."""

    def test_factory_reset_restores_files(self, engine_dir):
        """Factory reset restores files from _defaults/."""
        engine = _make_engine(engine_dir)

        # Modify domain file
        prompts_dir = os.path.join(engine_dir, 'prompts')
        modified = {"test_prompt": {"variants": {"default": {"content": "Modified!"}}, "placeholders_used": []}}
        with open(os.path.join(prompts_dir, 'test.json'), 'w', encoding='utf-8') as f:
            json.dump(modified, f)

        # Reset
        result = engine.factory_reset()
        assert result['restored'] >= 1
        assert len(result['errors']) == 0

        # Check: original restored
        domain = engine._loader.load_domain_file('test.json')
        assert domain['test_prompt']['variants']['default']['content'] == 'Original content.'

    def test_factory_reset_restores_manifest(self, engine_dir):
        """Factory reset also restores manifest."""
        engine = _make_engine(engine_dir)

        # Modify manifest
        manifest = engine._loader.load_manifest()
        manifest['version'] = '999.0'
        engine._loader.save_manifest(manifest)

        result = engine.factory_reset()
        assert result['restored'] >= 1

        # Manifest should be restored to original
        manifest = engine._loader.load_manifest()
        assert manifest['version'] == '2.0'

    def test_factory_reset_no_defaults_dir(self, tmp_path):
        """Factory reset without _defaults/ directory returns error."""
        instructions_dir = tmp_path / 'instructions'
        instructions_dir.mkdir()
        prompts_dir = instructions_dir / 'prompts'
        prompts_dir.mkdir()

        # Minimal-Manifest zum Laden
        meta_dir = prompts_dir / '_meta'
        meta_dir.mkdir()
        manifest = {"version": "1.0", "prompts": {}}
        (meta_dir / 'prompt_manifest.json').write_text(
            json.dumps(manifest), encoding='utf-8'
        )
        registry = {"version": "1.0", "placeholders": {}}
        (meta_dir / 'placeholder_registry.json').write_text(
            json.dumps(registry), encoding='utf-8'
        )

        engine = _make_engine(str(instructions_dir))
        result = engine.factory_reset()
        assert len(result['errors']) > 0
        assert 'nicht gefunden' in result['errors'][0] or '_defaults' in result['errors'][0]


# ===== Validate Integrity Tests =====

class TestValidateIntegrity:
    """Tests for validate_integrity()."""

    def test_all_valid(self, engine_dir):
        """All files valid → valid=True."""
        engine = _make_engine(engine_dir)
        result = engine.validate_integrity()

        assert result['valid'] is True
        assert result['checked'] >= 3  # manifest + registry + domain
        assert result['recovered'] == 0
        assert len(result['errors']) == 0

    def test_corrupt_file_recovery_from_defaults(self, engine_dir):
        """Corrupted file is restored from _defaults/."""
        prompts_dir = os.path.join(engine_dir, 'prompts')
        domain_path = os.path.join(prompts_dir, 'test.json')

        # Corrupt file (no .bak available)
        with open(domain_path, 'w') as f:
            f.write("NOT VALID JSON!!!")

        engine = _make_engine(engine_dir)
        result = engine.validate_integrity()

        assert result['recovered'] >= 1

    def test_missing_file_recovery_from_defaults(self, engine_dir):
        """Missing domain file is restored from _defaults/."""
        prompts_dir = os.path.join(engine_dir, 'prompts')
        domain_path = os.path.join(prompts_dir, 'test.json')

        # Delete file
        os.remove(domain_path)

        engine = _make_engine(engine_dir)
        result = engine.validate_integrity()

        assert result['recovered'] >= 1
        assert os.path.exists(domain_path)

    def test_unrecoverable_corruption(self, tmp_path):
        """Unrecoverable corruption → valid=False."""
        instructions_dir = tmp_path / 'instructions'
        instructions_dir.mkdir()
        prompts_dir = instructions_dir / 'prompts'
        prompts_dir.mkdir()

        # Corrupted manifest (without _defaults and without .bak)
        meta_dir = prompts_dir / '_meta'
        meta_dir.mkdir()
        (meta_dir / 'prompt_manifest.json').write_text("{CORRUPT", encoding='utf-8')
        (meta_dir / 'placeholder_registry.json').write_text(
            json.dumps({"version": "1.0", "placeholders": {}}), encoding='utf-8'
        )

        engine = _make_engine(str(instructions_dir))
        result = engine.validate_integrity()

        assert result['valid'] is False
        assert len(result['errors']) > 0
