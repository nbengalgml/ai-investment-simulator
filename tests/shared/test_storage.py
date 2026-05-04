import json
import pytest
from pathlib import Path

from storage import read_json, write_json, append_json_list


def test_write_and_read_json(tmp_path):
    path = tmp_path / "test.json"
    data = {"key": "value", "number": 42, "nested": {"x": True}}
    write_json(path, data)
    loaded = read_json(path)
    assert loaded == data


def test_write_creates_parent_dirs(tmp_path):
    path = tmp_path / "a" / "b" / "c" / "file.json"
    write_json(path, {"created": True})
    assert path.exists()
    assert read_json(path) == {"created": True}


def test_write_overwrites_existing(tmp_path):
    path = tmp_path / "file.json"
    write_json(path, {"v": 1})
    write_json(path, {"v": 2})
    assert read_json(path) == {"v": 2}


def test_append_json_list_creates_file(tmp_path):
    path = tmp_path / "log.json"
    assert not path.exists()
    append_json_list(path, {"id": 1})
    assert path.exists()
    assert read_json(path) == [{"id": 1}]


def test_append_json_list_accumulates(tmp_path):
    path = tmp_path / "log.json"
    for i in range(5):
        append_json_list(path, {"id": i})
    loaded = read_json(path)
    assert len(loaded) == 5
    assert [entry["id"] for entry in loaded] == list(range(5))


def test_read_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_json(tmp_path / "nonexistent.json")


def test_json_serializes_dates(tmp_path):
    from datetime import date, datetime
    path = tmp_path / "dates.json"
    data = {"d": date(2026, 5, 3), "dt": datetime(2026, 5, 3, 9, 30)}
    write_json(path, data)
    loaded = read_json(path)
    # Dates serialized to strings via default=str
    assert loaded["d"] == "2026-05-03"
    assert "2026-05-03" in loaded["dt"]
