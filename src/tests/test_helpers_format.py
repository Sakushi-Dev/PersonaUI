"""
Tests for helpers.py — format_message, _extract_code_blocks, _insert_code_blocks_html
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from utils.helpers import format_message, _extract_code_blocks, _insert_code_blocks_html


class TestFormatMessage:
    def test_none_input(self):
        assert format_message(None) is None

    def test_empty_string(self):
        assert format_message("") == ""

    def test_nonverbal_stars(self):
        result = format_message("Hello *smiles* world")
        assert '<span class="non_verbal">smiles</span>' in result

    def test_line_breaks_to_br(self):
        result = format_message("line1\nline2")
        assert "<br>" in result

    def test_already_processed_html(self):
        html = '<div class="code-block">code</div> *waves*'
        result = format_message(html)
        assert '<span class="non_verbal">waves</span>' in result
        assert '<div class="code-block">' in result


class TestExtractCodeBlocks:
    def test_no_code_blocks(self):
        text, blocks = _extract_code_blocks("Hello world")
        assert blocks == []
        assert text == "Hello world"

    def test_single_code_block(self):
        text, blocks = _extract_code_blocks("before ```print('hi')``` after")
        assert len(blocks) == 1
        assert "print('hi')" in blocks[0]
        assert "###CODE_BLOCK_0###" in text

    def test_multiple_code_blocks(self):
        text, blocks = _extract_code_blocks("```a``` text ```b```")
        assert len(blocks) == 2
        assert "###CODE_BLOCK_0###" in text
        assert "###CODE_BLOCK_1###" in text

    def test_python_language_tag(self):
        text, blocks = _extract_code_blocks("```python\nx = 1\n```")
        assert len(blocks) == 1
        assert "x = 1" in blocks[0]


class TestInsertCodeBlocksHtml:
    def test_replaces_placeholder(self):
        result = _insert_code_blocks_html("###CODE_BLOCK_0###", ["print('hi')"])
        assert '<div class="code-block">' in result
        assert "print(&#x27;hi&#x27;)" in result  # HTML escaped

    def test_html_escaping_xss(self):
        result = _insert_code_blocks_html("###CODE_BLOCK_0###", ["<script>alert('xss')</script>"])
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_no_blocks(self):
        result = _insert_code_blocks_html("plain text", [])
        assert result == "plain text"
