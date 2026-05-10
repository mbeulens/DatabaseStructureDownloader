"""Persist the last MySQL connection's non-secret fields. Password is never
persisted. All errors are non-fatal — caller treats None / no-op as 'no
saved state'."""

from __future__ import annotations

import json
import sys
from pathlib import Path


DEFAULT_CONFIG_PATH = Path.home() / ".config" / "db-structure-downloader" / "last-connection.json"


def load_last_connection(path: Path = DEFAULT_CONFIG_PATH) -> dict | None:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError) as e:
        print(f"warning: could not read {path}: {e}", file=sys.stderr)
        return None


def save_last_connection(
    path: Path = DEFAULT_CONFIG_PATH,
    *,
    host: str,
    port: int,
    user: str,
    database: str,
) -> None:
    data = {"host": host, "port": port, "user": user, "database": database}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2))
    except OSError as e:
        print(f"warning: could not write {path}: {e}", file=sys.stderr)
