import json
from pathlib import Path

from db_structure_downloader.config import load_last_connection, save_last_connection


def test_save_then_load_roundtrip(tmp_path):
    path = tmp_path / "last-connection.json"

    save_last_connection(
        path,
        host="db.internal",
        port=3307,
        user="reader",
        database="syntec_crm",
    )

    loaded = load_last_connection(path)

    assert loaded == {
        "host": "db.internal",
        "port": 3307,
        "user": "reader",
        "database": "syntec_crm",
    }


def test_load_returns_none_when_file_missing(tmp_path):
    path = tmp_path / "does-not-exist.json"
    assert load_last_connection(path) is None


def test_load_returns_none_when_file_corrupt(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("{not valid json")
    assert load_last_connection(path) is None


def test_save_creates_parent_directory(tmp_path):
    path = tmp_path / "nested" / "dir" / "last.json"
    save_last_connection(path, host="h", port=3306, user="u", database="d")
    assert json.loads(path.read_text())["host"] == "h"
