"""
Tests for JSONL Storage Engine (jsonl_store.py)

Verifies: append, read_all, read_filtered, read_paginated,
          read_last_n, count_lines, next_id, rewrite, delete_file
"""
import json
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from utils.database import jsonl_store


@pytest.fixture
def jsonl_file(tmp_path):
    """Returns a path to a JSONL file inside a temp directory."""
    return str(tmp_path / "test.jsonl")


@pytest.fixture
def populated_file(jsonl_file):
    """Creates a JSONL file with 5 sample records."""
    for i in range(1, 6):
        jsonl_store.append(jsonl_file, {"id": i, "text": f"msg_{i}"})
    return jsonl_file


class TestAppend:
    def test_creates_file_and_writes(self, jsonl_file):
        result = jsonl_store.append(jsonl_file, {"id": 1, "name": "test"})
        assert os.path.exists(jsonl_file)
        assert result["id"] == 1

    def test_returns_copy(self, jsonl_file):
        original = {"id": 1}
        result = jsonl_store.append(jsonl_file, original)
        result["id"] = 999
        assert original["id"] == 1

    def test_appends_multiple(self, jsonl_file):
        jsonl_store.append(jsonl_file, {"id": 1})
        jsonl_store.append(jsonl_file, {"id": 2})
        records = jsonl_store.read_all(jsonl_file)
        assert len(records) == 2
        assert records[0]["id"] == 1
        assert records[1]["id"] == 2

    def test_creates_parent_directories(self, tmp_path):
        deep_path = str(tmp_path / "a" / "b" / "c" / "data.jsonl")
        jsonl_store.append(deep_path, {"id": 1})
        assert os.path.exists(deep_path)

    def test_unicode_content(self, jsonl_file):
        jsonl_store.append(jsonl_file, {"text": "日本語テスト 🎉"})
        records = jsonl_store.read_all(jsonl_file)
        assert records[0]["text"] == "日本語テスト 🎉"


class TestReadAll:
    def test_empty_file(self, jsonl_file):
        with open(jsonl_file, 'w') as f:
            f.write("")
        assert jsonl_store.read_all(jsonl_file) == []

    def test_nonexistent_file(self, tmp_path):
        assert jsonl_store.read_all(str(tmp_path / "nope.jsonl")) == []

    def test_reads_all_records(self, populated_file):
        records = jsonl_store.read_all(populated_file)
        assert len(records) == 5
        assert [r["id"] for r in records] == [1, 2, 3, 4, 5]

    def test_skips_corrupt_lines(self, jsonl_file):
        with open(jsonl_file, 'w', encoding='utf-8') as f:
            f.write('{"id":1}\n')
            f.write('CORRUPT LINE\n')
            f.write('{"id":2}\n')
        records = jsonl_store.read_all(jsonl_file)
        assert len(records) == 2
        assert records[0]["id"] == 1
        assert records[1]["id"] == 2

    def test_skips_blank_lines(self, jsonl_file):
        with open(jsonl_file, 'w', encoding='utf-8') as f:
            f.write('{"id":1}\n\n\n{"id":2}\n')
        records = jsonl_store.read_all(jsonl_file)
        assert len(records) == 2


class TestReadFiltered:
    def test_filter_by_field(self, populated_file):
        results = jsonl_store.read_filtered(populated_file, lambda r: r["id"] > 3)
        assert len(results) == 2
        assert results[0]["id"] == 4

    def test_no_matches(self, populated_file):
        results = jsonl_store.read_filtered(populated_file, lambda r: r["id"] > 100)
        assert results == []

    def test_nonexistent_file(self, tmp_path):
        results = jsonl_store.read_filtered(str(tmp_path / "nope.jsonl"), lambda r: True)
        assert results == []


class TestReadPaginated:
    def test_first_page(self, populated_file):
        records = jsonl_store.read_paginated(populated_file, limit=2, offset=0)
        assert len(records) == 2
        assert records[0]["id"] == 1

    def test_second_page(self, populated_file):
        records = jsonl_store.read_paginated(populated_file, limit=2, offset=2)
        assert len(records) == 2
        assert records[0]["id"] == 3

    def test_reverse_mode(self, populated_file):
        records = jsonl_store.read_paginated(populated_file, limit=2, offset=0, reverse=True)
        assert len(records) == 2
        assert records[0]["id"] == 5
        assert records[1]["id"] == 4

    def test_offset_beyond_end(self, populated_file):
        records = jsonl_store.read_paginated(populated_file, limit=10, offset=100)
        assert records == []

    def test_nonexistent_file(self, tmp_path):
        records = jsonl_store.read_paginated(str(tmp_path / "x.jsonl"), limit=5, offset=0)
        assert records == []


class TestReadLastN:
    def test_last_2(self, populated_file):
        records = jsonl_store.read_last_n(populated_file, n=2)
        assert len(records) == 2
        assert records[0]["id"] == 4
        assert records[1]["id"] == 5

    def test_last_more_than_total(self, populated_file):
        records = jsonl_store.read_last_n(populated_file, n=100)
        assert len(records) == 5

    def test_n_zero(self, populated_file):
        assert jsonl_store.read_last_n(populated_file, n=0) == []

    def test_nonexistent_file(self, tmp_path):
        assert jsonl_store.read_last_n(str(tmp_path / "x.jsonl"), n=5) == []


class TestCountLines:
    def test_counts_records(self, populated_file):
        assert jsonl_store.count_lines(populated_file) == 5

    def test_empty_file(self, jsonl_file):
        with open(jsonl_file, 'w') as f:
            f.write("\n\n")
        assert jsonl_store.count_lines(jsonl_file) == 0

    def test_nonexistent_file(self, tmp_path):
        assert jsonl_store.count_lines(str(tmp_path / "nope.jsonl")) == 0


class TestNextId:
    def test_first_id(self, tmp_path):
        assert jsonl_store.next_id(str(tmp_path / "new.jsonl")) == 1

    def test_increments(self, populated_file):
        assert jsonl_store.next_id(populated_file) == 6

    def test_after_gap(self, jsonl_file):
        jsonl_store.append(jsonl_file, {"id": 1})
        jsonl_store.append(jsonl_file, {"id": 10})
        assert jsonl_store.next_id(jsonl_file) == 11


class TestRewrite:
    def test_replaces_content(self, populated_file):
        new_records = [{"id": 100, "text": "replaced"}]
        jsonl_store.rewrite(populated_file, new_records)
        records = jsonl_store.read_all(populated_file)
        assert len(records) == 1
        assert records[0]["id"] == 100

    def test_empty_rewrite(self, populated_file):
        jsonl_store.rewrite(populated_file, [])
        records = jsonl_store.read_all(populated_file)
        assert records == []


class TestDeleteFile:
    def test_deletes_existing(self, populated_file):
        jsonl_store.delete_file(populated_file)
        assert not os.path.exists(populated_file)

    def test_no_error_on_missing(self, tmp_path):
        jsonl_store.delete_file(str(tmp_path / "nope.jsonl"))


class TestEnsureDir:
    def test_creates_nested_dirs(self, tmp_path):
        target = str(tmp_path / "a" / "b" / "c")
        jsonl_store.ensure_dir(target)
        assert os.path.isdir(target)

    def test_existing_dir_no_error(self, tmp_path):
        jsonl_store.ensure_dir(str(tmp_path))
