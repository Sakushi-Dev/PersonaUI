"""
Tests for the file-based PromptEngine.

Tests:
- File discovery (core/, files/, internal/)
- Placeholder resolution ({{key}} → value)
- build_core_system_prompt() — core files + persona files inline + file index
- build_full_system_prompt() — all files inline
- get_chat_tools() — write_file tool definition
- read_prompt_file() — file reading + placeholder resolution
- write_prompt_file() — per-persona dynamic file writing
- read_internal() — internal prompt reading
- Variant handling (default vs experimental)
- Cache invalidation
- Backward-compat methods (resolve_prompt, get_domain_data, etc.)
"""

import os
import json
import pytest



# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def prompt_dirs(tmp_path):
    """Creates a temporary prompts directory structure with sample .md files."""
    prompts = tmp_path / 'prompts'
    for subdir in ('core', 'internal'):
        (prompts / subdir).mkdir(parents=True)

    # Per-persona cortex dir with journal files
    cortex = tmp_path / 'data' / 'default' / 'cortex'
    cortex.mkdir(parents=True)
    (cortex / 'bonding.md').write_text(
        'Bonding phases for {{char_name}} and {{user_name}}.', encoding='utf-8')
    (cortex / 'growth.md').write_text(
        '{{char_name}} evolves through interaction with {{user_name}}.', encoding='utf-8')
    # Cortex files (read-only, auto-updated)
    (cortex / 'memory.md').write_text(
        'Memories about {{user_name}} collected by {{char_name}}.', encoding='utf-8')
    (cortex / 'soul.md').write_text(
        'Soul profile of {{char_name}}.', encoding='utf-8')
    (cortex / 'relationship.md').write_text(
        'Relationship between {{char_name}} and {{user_name}}.', encoding='utf-8')

    # Core files (inline, variant-aware)
    (prompts / 'core' / 'identity.md').write_text(
        'You are {{char_name}}, age {{char_age}}.', encoding='utf-8')
    (prompts / 'core' / 'persona.md').write_text(
        '{{char_name}} is a {{persona_type}}.', encoding='utf-8')
    (prompts / 'core' / 'persona.experimental.md').write_text(
        '{{char_name}} (experimental) is a {{persona_type}}.', encoding='utf-8')
    (prompts / 'core' / 'rules.md').write_text(
        'Always respond in {{language}}.', encoding='utf-8')

    # Internal files
    (prompts / 'internal' / 'remember.md').write_text(
        'Remember: {{char_name}} speaking to {{user_name}}', encoding='utf-8')
    (prompts / 'internal' / 'afterthought_inner_dialogue.md').write_text(
        'Inner dialogue for {{char_name}}', encoding='utf-8')
    (prompts / 'internal' / 'afterthought_followup.md').write_text(
        'Followup for {{char_name}}', encoding='utf-8')
    (prompts / 'internal' / 'afterthought_system_note.md').write_text(
        'System note', encoding='utf-8')
    (prompts / 'internal' / 'cortex_update_tools.json').write_text(
        json.dumps({
            'read_file': {'tool_description': 'Reads cortex', 'filename_description': 'File name'},
            'write_file': {'tool_description': 'Writes cortex', 'filename_description': 'File name',
                           'content_description': 'Content'}
        }), encoding='utf-8')

    return tmp_path


_TEST_PLACEHOLDERS = {
    'char_name': 'Luna',
    'char_age': '22',
    'char_gender': 'weiblich',
    'persona_type': 'Companion',
    'user_name': 'Alex',
    'user_gender': 'Male',
    'language': 'english',
    'current_date': '09.03.2026',
    'current_time': '14:30',
}


@pytest.fixture
def engine(prompt_dirs):
    """Creates a PromptEngine with test prompts and mocked placeholders."""
    from utils.prompt_engine.engine import PromptEngine
    e = PromptEngine(instructions_dir=str(prompt_dirs))

    def mock_compute(runtime_vars=None):
        values = _TEST_PLACEHOLDERS.copy()
        if runtime_vars:
            values.update(runtime_vars)
        return values

    e._compute_placeholders = mock_compute
    # Point to test cortex dir with journal files
    cortex_dir = str(prompt_dirs / 'data' / 'default' / 'cortex')
    e._get_persona_files_dir = lambda: cortex_dir
    yield e


# ═══════════════════════════════════════════════════════════════════════════════
# Properties
# ═══════════════════════════════════════════════════════════════════════════════

class TestProperties:
    def test_is_loaded(self, engine):
        assert engine.is_loaded is True

    def test_no_load_errors(self, engine):
        assert engine.load_errors == []

    def test_missing_dir_reports_error(self, tmp_path):
        empty = tmp_path / 'empty'
        empty.mkdir()
        (empty / 'prompts').mkdir()
        # No core/internal dirs
        from utils.prompt_engine.engine import PromptEngine
        e = PromptEngine(instructions_dir=str(empty))
        assert len(e.load_errors) == 2


# ═══════════════════════════════════════════════════════════════════════════════
# Placeholder Resolution
# ═══════════════════════════════════════════════════════════════════════════════

class TestPlaceholders:
    def test_resolve_replaces_known_keys(self, engine):
        result = engine.resolve_text('Hello {{user_name}}, I am {{char_name}}.')
        assert result == 'Hello Alex, I am Luna.'

    def test_resolve_keeps_unknown_keys(self, engine):
        result = engine.resolve_text('Value: {{unknown_key}}')
        assert '{{unknown_key}}' in result

    def test_resolve_with_runtime_vars(self, engine):
        result = engine.resolve_text('Time: {{elapsed_time}}', runtime_vars={'elapsed_time': '5min'})
        assert result == 'Time: 5min'

    def test_runtime_vars_override_static(self, engine):
        result = engine.resolve_text('Name: {{char_name}}', runtime_vars={'char_name': 'Override'})
        assert result == 'Name: Override'

    def test_empty_text_returns_empty(self, engine):
        assert engine.resolve_text('') == ''
        assert engine.resolve_text(None) is None


# ═══════════════════════════════════════════════════════════════════════════════
# Core System Prompt
# ═══════════════════════════════════════════════════════════════════════════════

class TestCoreSystemPrompt:
    def test_includes_core_files(self, engine):
        prompt = engine.build_core_system_prompt()
        assert 'You are Luna, age 22.' in prompt
        assert 'Luna is a Companion' in prompt
        assert 'Always respond in english.' in prompt

    def test_persona_files_inline(self, engine):
        """All persona files (journal + cortex) must be inline in core prompt."""
        prompt = engine.build_core_system_prompt()
        # Journal files
        assert 'Bonding phases for Luna and Alex' in prompt
        assert 'Luna evolves through interaction' in prompt
        # Cortex files
        assert 'Memories about Alex collected by Luna' in prompt
        assert 'Soul profile of Luna' in prompt
        assert 'Relationship between Luna and Alex' in prompt

    def test_includes_file_index(self, engine):
        prompt = engine.build_core_system_prompt()
        assert 'YOUR JOURNAL FILES' in prompt
        assert 'bonding.md' in prompt
        assert 'growth.md' in prompt

    def test_respects_runtime_vars(self, engine):
        prompt = engine.build_core_system_prompt(runtime_vars={'char_name': 'Aria'})
        assert 'Aria' in prompt


# ═══════════════════════════════════════════════════════════════════════════════
# Full System Prompt
# ═══════════════════════════════════════════════════════════════════════════════

class TestFullSystemPrompt:
    def test_includes_core_and_all_persona_files(self, engine):
        prompt = engine.build_full_system_prompt()
        # Core content
        assert 'You are Luna' in prompt
        assert 'Luna is a Companion' in prompt
        # Journal files
        assert 'Bonding phases for Luna and Alex' in prompt
        assert 'Luna evolves through interaction' in prompt
        # Cortex files
        assert 'Memories about Alex collected by Luna' in prompt
        assert 'Soul profile of Luna' in prompt
        assert 'Relationship between Luna and Alex' in prompt

    def test_default_variant_skips_experimental(self, engine):
        prompt = engine.build_full_system_prompt(variant='default')
        assert '(experimental)' not in prompt

    def test_experimental_variant_uses_experimental_files(self, engine):
        prompt = engine.build_full_system_prompt(variant='experimental')
        assert '(experimental)' in prompt


# ═══════════════════════════════════════════════════════════════════════════════
# Chat Tools
# ═══════════════════════════════════════════════════════════════════════════════

class TestChatTools:
    def test_returns_only_write_tool(self, engine):
        tools = engine.get_chat_tools()
        names = [t['name'] for t in tools]
        assert 'write_file' in names
        assert 'read_file' not in names
        assert len(tools) == 1

    def test_write_tool_has_journal_files(self, engine):
        tools = engine.get_chat_tools()
        write_tool = tools[0]
        writable = write_tool['input_schema']['properties']['filename']['enum']
        assert 'bonding.md' in writable
        assert 'growth.md' in writable
        assert len(writable) == 2

    def test_write_tool_requires_content(self, engine):
        tools = engine.get_chat_tools()
        write_tool = tools[0]
        assert 'content' in write_tool['input_schema']['required']


# ═══════════════════════════════════════════════════════════════════════════════
# read_prompt_file (Tool Executor)
# ═══════════════════════════════════════════════════════════════════════════════

class TestReadPromptFile:
    def test_reads_and_resolves(self, engine):
        content = engine.read_prompt_file('bonding.md')
        assert 'Luna' in content
        assert 'Alex' in content

    def test_unknown_file_returns_error(self, engine):
        content = engine.read_prompt_file('nonexistent.md')
        assert 'not found' in content.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# write_prompt_file (Dynamic File Writing)
# ═══════════════════════════════════════════════════════════════════════════════

class TestWritePromptFile:
    def test_write_creates_per_persona_file(self, engine, prompt_dirs):
        persona_dir = prompt_dirs / 'data' / 'default' / 'cortex'
        engine._get_persona_files_dir = lambda: str(persona_dir)

        result = engine.write_prompt_file('bonding.md', '# Updated bonding content')
        assert 'Successfully' in result
        assert (persona_dir / 'bonding.md').exists()
        assert (persona_dir / 'bonding.md').read_text(encoding='utf-8') == '# Updated bonding content'

    def test_write_rejects_unknown_file(self, engine):
        engine._get_persona_files_dir = lambda: '/tmp/test'
        result = engine.write_prompt_file('nonexistent.md', 'content')
        assert 'Unknown file' in result

    def test_write_rejects_cortex_files(self, engine):
        result = engine.write_prompt_file('cortex_memory.md', 'content')
        assert 'Cannot write cortex' in result

    def test_write_rejects_oversized_content(self, engine, prompt_dirs):
        from utils.cortex import MAX_CORTEX_FILE_SIZE
        persona_dir = prompt_dirs / 'data' / 'default' / 'cortex'
        engine._get_persona_files_dir = lambda: str(persona_dir)
        big = 'x' * (MAX_CORTEX_FILE_SIZE + 1)
        result = engine.write_prompt_file('bonding.md', big)
        assert 'too long' in result.lower()

    def test_write_fails_without_persona_context(self, engine):
        engine._get_persona_files_dir = lambda: None
        result = engine.write_prompt_file('bonding.md', 'content')
        assert 'Cannot determine' in result

    def test_read_prefers_per_persona_over_template(self, engine, prompt_dirs):
        """After writing, read should return per-persona content, not template."""
        persona_dir = prompt_dirs / 'data' / 'default' / 'cortex'
        engine._get_persona_files_dir = lambda: str(persona_dir)

        engine.write_prompt_file('growth.md', '# My personal growth journal')

        content = engine.read_prompt_file('growth.md')
        assert '# My personal growth journal' in content

    def test_read_returns_not_found_without_file(self, engine, prompt_dirs):
        """Without per-persona file, read returns not-found message."""
        empty_dir = prompt_dirs / 'data' / 'empty_persona' / 'cortex'
        empty_dir.mkdir(parents=True)
        engine._get_persona_files_dir = lambda: str(empty_dir)
        content = engine.read_prompt_file('bonding.md')
        assert 'not found' in content.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# Internal Prompts
# ═══════════════════════════════════════════════════════════════════════════════

class TestInternalPrompts:
    def test_read_internal(self, engine):
        result = engine.read_internal('remember')
        assert 'Luna' in result
        assert 'Alex' in result

    def test_read_internal_missing(self, engine):
        result = engine.read_internal('nonexistent')
        assert result == ''

    def test_read_internal_json(self, engine):
        data = engine.read_internal_json('cortex_update_tools')
        assert 'read_file' in data
        assert 'write_file' in data


# ═══════════════════════════════════════════════════════════════════════════════
# Convenience Methods
# ═══════════════════════════════════════════════════════════════════════════════

class TestConvenienceMethods:
    def test_build_prefill(self, engine):
        result = engine.build_prefill()
        assert 'Luna' in result

    def test_build_afterthought_inner_dialogue(self, engine):
        result = engine.build_afterthought_inner_dialogue()
        assert 'Luna' in result

    def test_build_afterthought_followup(self, engine):
        result = engine.build_afterthought_followup()
        assert 'Luna' in result

    def test_get_system_prompt_append(self, engine):
        result = engine.get_system_prompt_append()
        assert 'System note' in result


# ═══════════════════════════════════════════════════════════════════════════════
# Backward Compat
# ═══════════════════════════════════════════════════════════════════════════════

class TestBackwardCompat:
    def test_resolve_prompt_finds_internal(self, engine):
        result = engine.resolve_prompt('remember')
        assert result is not None
        assert 'Luna' in result

    def test_resolve_prompt_returns_none_for_unknown(self, engine):
        result = engine.resolve_prompt('user_info')
        assert result is None

    def test_resolve_prompt_by_id_raises_on_missing(self, engine):
        with pytest.raises(KeyError):
            engine.resolve_prompt_by_id('nonexistent_prompt')

    def test_get_domain_data(self, engine):
        data = engine.get_domain_data('cortex_update_tools')
        assert 'read_file' in data

    def test_get_dialog_injections_returns_empty(self, engine):
        assert engine.get_dialog_injections() == []

    def test_build_system_prompt_alias(self, engine):
        """build_system_prompt should work as alias for build_full_system_prompt."""
        full = engine.build_full_system_prompt()
        alias = engine.build_system_prompt()
        assert alias == full


# ═══════════════════════════════════════════════════════════════════════════════
# Cache
# ═══════════════════════════════════════════════════════════════════════════════

class TestCache:
    def test_invalidate_cache_clears(self, engine):
        # Fill cache
        engine._static_cache = {'char_name': 'cached'}
        engine.invalidate_cache()
        assert engine._static_cache == {}

    def test_reload_clears_errors(self, engine):
        engine._load_errors = ['some error']
        engine.reload()
        assert engine._load_errors == []


# ═══════════════════════════════════════════════════════════════════════════════
# Cortex Tools
# ═══════════════════════════════════════════════════════════════════════════════

class TestCortexTools:
    def test_get_cortex_tools_from_json(self, engine):
        tools = engine.get_cortex_tools()
        assert len(tools) == 2
        assert tools[0]['name'] == 'read_file'
        assert tools[1]['name'] == 'write_file'

    def test_cortex_tools_have_enum(self, engine):
        tools = engine.get_cortex_tools()
        filenames = tools[0]['input_schema']['properties']['filename']['enum']
        assert 'memory.md' in filenames
        assert 'soul.md' in filenames
        assert 'relationship.md' in filenames
