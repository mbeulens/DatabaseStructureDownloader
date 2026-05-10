# Database Structure Downloader Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a desktop Python utility (Tkinter GUI) that connects to a MySQL server, lets the user select tables, and writes one markdown-per-table to a chosen folder for ingestion into a RAG knowledgebase.

**Architecture:** Small Python package. Five modules with single responsibilities: dataclasses + DB queries (`db.py`), pure markdown rendering (`markdown.py`), Tkinter GUI orchestration (`gui.py`), config persistence (`config.py`), entry point (`__main__.py`). The pure module is unit-tested; DB and GUI are manually tested against a Docker MySQL.

**Tech Stack:** Python 3.10+, PyMySQL (DB driver), Tkinter (stdlib GUI), pytest (tests).

---

## File structure

```
DatabaseStructureDownloader/
├── db_structure_downloader/
│   ├── __init__.py
│   ├── __main__.py        # entry point: python -m db_structure_downloader
│   ├── db.py              # dataclasses + MySQL queries
│   ├── markdown.py        # render(TableMetadata) -> str
│   ├── gui.py             # Tkinter App with ConnectionFrame + ExportFrame
│   └── config.py          # load/save last-connection JSON
├── tests/
│   ├── __init__.py
│   ├── test_markdown.py
│   └── test_config.py
├── docs/
│   └── superpowers/...    # already exists
├── requirements.txt       # runtime + dev deps
├── README.md
└── .gitignore
```

Each file's responsibility:

| File | Knows about | Does not know about |
|---|---|---|
| `db.py` | PyMySQL, INFORMATION_SCHEMA, dataclasses | Tkinter, file I/O for output |
| `markdown.py` | Dataclasses from `db.py` | PyMySQL, Tkinter, file I/O |
| `config.py` | JSON, `~/.config/...` path | DB, GUI |
| `gui.py` | Tkinter, calls into the other three | SQL, markdown layout details |
| `__main__.py` | `gui.py` only | everything else |

---

## Task 0: Project scaffolding

**Files:**
- Create: `.gitignore`
- Create: `requirements.txt`
- Create: `README.md`
- Create: `db_structure_downloader/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Initialize git repo**

Run:
```bash
git init
git config user.email "m.beulens@syntec-it.nl"
git config user.name "Marcel Beulens"
```

- [ ] **Step 2: Write `.gitignore`**

```gitignore
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/
.pytest_cache/
.idea/
.vscode/
*.swp
```

- [ ] **Step 3: Write `requirements.txt`**

```
# runtime
PyMySQL==1.1.1

# dev
pytest==8.3.3
```

- [ ] **Step 4: Write `README.md`**

```markdown
# Database Structure Downloader

A desktop utility that connects to a MySQL server, lets you pick tables from a
GUI, and exports each table's structure as a separate markdown file. The output
is shaped for ingestion into a RAG knowledgebase.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python -m db_structure_downloader
```

## Test

```bash
pytest
```
```

- [ ] **Step 5: Create empty package files**

```bash
mkdir -p db_structure_downloader tests
touch db_structure_downloader/__init__.py tests/__init__.py
```

- [ ] **Step 6: Verify Python and create venv**

Run:
```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
Expected: Python 3.10+, no install errors.

- [ ] **Step 7: Commit**

```bash
git add .gitignore requirements.txt README.md db_structure_downloader/__init__.py tests/__init__.py
git commit -m "chore: scaffold project structure"
```

---

## Task 1: Dataclasses in `db.py`

**Files:**
- Create: `db_structure_downloader/db.py`

- [ ] **Step 1: Write the dataclasses**

```python
"""MySQL introspection. Connects to a database and returns table metadata
as plain dataclasses. No knowledge of the GUI or markdown layout."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Column:
    name: str
    type: str
    comment: str
    is_pk: bool


@dataclass
class Relation:
    from_table: str
    from_column: str
    to_table: str
    to_column: str


@dataclass
class TableMetadata:
    name: str
    comment: str
    columns: list[Column] = field(default_factory=list)
    outgoing: list[Relation] = field(default_factory=list)
    incoming: list[Relation] = field(default_factory=list)
```

- [ ] **Step 2: Verify the module imports**

Run:
```bash
source .venv/bin/activate
python -c "from db_structure_downloader.db import Column, Relation, TableMetadata; print('ok')"
```
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add db_structure_downloader/db.py
git commit -m "feat(db): add Column/Relation/TableMetadata dataclasses"
```

---

## Task 2: Markdown rendering — happy path (TDD)

**Files:**
- Create: `tests/test_markdown.py`
- Create: `db_structure_downloader/markdown.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_markdown.py
from db_structure_downloader.db import Column, Relation, TableMetadata
from db_structure_downloader.markdown import render


def test_full_table_renders_all_sections():
    table = TableMetadata(
        name="customers",
        comment="The master list of companies we do business with.",
        columns=[
            Column(name="id", type="char(36)", comment="", is_pk=True),
            Column(name="name", type="varchar(200)", comment="Legal name", is_pk=False),
            Column(name="kvk_number", type="varchar(8)", comment="", is_pk=False),
        ],
        outgoing=[],
        incoming=[
            Relation(from_table="engagements", from_column="customer_id",
                     to_table="customers", to_column="id"),
            Relation(from_table="contacts", from_column="customer_id",
                     to_table="customers", to_column="id"),
        ],
    )

    expected = (
        "# customers\n"
        "\n"
        "**Purpose:** The master list of companies we do business with.\n"
        "\n"
        "| Column | Type | Meaning |\n"
        "|---|---|---|\n"
        "| id | char(36) | PK |\n"
        "| name | varchar(200) | Legal name |\n"
        "| kvk_number | varchar(8) | _TODO_ |\n"
        "\n"
        "**Relations:**\n"
        "- `contacts.customer_id → customers.id`\n"
        "- `engagements.customer_id → customers.id`\n"
    )

    assert render(table) == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
source .venv/bin/activate
pytest tests/test_markdown.py::test_full_table_renders_all_sections -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'db_structure_downloader.markdown'`

- [ ] **Step 3: Implement `render`**

```python
# db_structure_downloader/markdown.py
"""Pure markdown rendering. Takes a TableMetadata dataclass, returns a
markdown string. No I/O, no DB, no GUI dependencies."""

from __future__ import annotations

from db_structure_downloader.db import Column, Relation, TableMetadata


_TODO_PURPOSE = "_TODO: describe purpose_"
_TODO_MEANING = "_TODO_"


def render(table: TableMetadata) -> str:
    parts: list[str] = []
    parts.append(f"# {table.name}")
    parts.append("")

    purpose = table.comment.strip() if table.comment else ""
    parts.append(f"**Purpose:** {purpose or _TODO_PURPOSE}")
    parts.append("")

    parts.append("| Column | Type | Meaning |")
    parts.append("|---|---|---|")
    for col in table.columns:
        meaning = _column_meaning(col)
        parts.append(f"| {col.name} | {col.type} | {meaning} |")

    has_relations = bool(table.outgoing) or bool(table.incoming)
    if has_relations:
        parts.append("")
        parts.append("**Relations:**")
        for rel in sorted(table.outgoing, key=lambda r: r.from_column):
            parts.append(f"- `{_format_relation(rel)}`")
        for rel in sorted(table.incoming, key=lambda r: (r.from_table, r.from_column)):
            parts.append(f"- `{_format_relation(rel)}`")

    return "\n".join(parts) + "\n"


def _column_meaning(col: Column) -> str:
    if col.comment.strip():
        return _escape_pipes(col.comment.strip())
    if col.is_pk:
        return "PK"
    return _TODO_MEANING


def _format_relation(rel: Relation) -> str:
    return f"{rel.from_table}.{rel.from_column} → {rel.to_table}.{rel.to_column}"


def _escape_pipes(text: str) -> str:
    return text.replace("|", "\\|")
```

- [ ] **Step 4: Run the test**

Run:
```bash
pytest tests/test_markdown.py::test_full_table_renders_all_sections -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_markdown.py db_structure_downloader/markdown.py
git commit -m "feat(markdown): render full table with purpose, columns, relations"
```

---

## Task 3: Markdown rendering — TODO placeholders for empty comments

**Files:**
- Modify: `tests/test_markdown.py`

- [ ] **Step 1: Add the failing test**

Append to `tests/test_markdown.py`:
```python
def test_empty_comments_emit_todo_placeholders():
    table = TableMetadata(
        name="orders",
        comment="",
        columns=[
            Column(name="id", type="bigint", comment="", is_pk=True),
            Column(name="amount", type="decimal(10,2)", comment="", is_pk=False),
        ],
        outgoing=[],
        incoming=[],
    )

    result = render(table)

    assert "**Purpose:** _TODO: describe purpose_" in result
    assert "| amount | decimal(10,2) | _TODO_ |" in result
    # PK column with no comment still gets "PK" not "_TODO_"
    assert "| id | bigint | PK |" in result
```

Add the import at the top of the file if not already present:
```python
from db_structure_downloader.markdown import render
from db_structure_downloader.db import Column, Relation, TableMetadata
```

- [ ] **Step 2: Run the test**

Run:
```bash
pytest tests/test_markdown.py::test_empty_comments_emit_todo_placeholders -v
```
Expected: PASS (the existing implementation already handles this).

- [ ] **Step 3: Commit**

```bash
git add tests/test_markdown.py
git commit -m "test(markdown): cover TODO placeholders for empty comments"
```

---

## Task 4: Markdown rendering — omit `**Relations:**` section when no FKs

**Files:**
- Modify: `tests/test_markdown.py`

- [ ] **Step 1: Add the failing test**

Append to `tests/test_markdown.py`:
```python
def test_no_relations_section_when_no_fks():
    table = TableMetadata(
        name="logs",
        comment="Append-only audit log.",
        columns=[
            Column(name="id", type="bigint", comment="", is_pk=True),
            Column(name="message", type="text", comment="", is_pk=False),
        ],
        outgoing=[],
        incoming=[],
    )

    result = render(table)

    assert "**Relations:**" not in result
    # Last line is still the columns table row, plus a single trailing newline.
    assert result.endswith("| message | text | _TODO_ |\n")
```

- [ ] **Step 2: Run the test**

Run:
```bash
pytest tests/test_markdown.py::test_no_relations_section_when_no_fks -v
```
Expected: PASS (the `if has_relations:` guard already handles this).

- [ ] **Step 3: Commit**

```bash
git add tests/test_markdown.py
git commit -m "test(markdown): cover omission of relations section"
```

---

## Task 5: Markdown rendering — escape pipes in column comments

**Files:**
- Modify: `tests/test_markdown.py`

- [ ] **Step 1: Add the failing test**

Append to `tests/test_markdown.py`:
```python
def test_pipe_in_column_comment_is_escaped():
    table = TableMetadata(
        name="settings",
        comment="",
        columns=[
            Column(name="value", type="varchar(255)",
                   comment="Either 'on' | 'off'", is_pk=False),
        ],
        outgoing=[],
        incoming=[],
    )

    result = render(table)

    assert "| value | varchar(255) | Either 'on' \\| 'off' |" in result
```

- [ ] **Step 2: Run the test**

Run:
```bash
pytest tests/test_markdown.py::test_pipe_in_column_comment_is_escaped -v
```
Expected: PASS (the `_escape_pipes` helper already handles this).

- [ ] **Step 3: Run the full markdown test file**

Run:
```bash
pytest tests/test_markdown.py -v
```
Expected: 4 tests pass.

- [ ] **Step 4: Commit**

```bash
git add tests/test_markdown.py
git commit -m "test(markdown): cover pipe escaping in column comments"
```

---

## Task 6: Database — connect and list tables

**Files:**
- Modify: `db_structure_downloader/db.py`

- [ ] **Step 1: Add `connect` and `list_tables`**

First, modify the imports at the top of `db_structure_downloader/db.py` to add the PyMySQL imports under the stdlib block. The top of the file should now read:
```python
from __future__ import annotations

from dataclasses import dataclass, field

import pymysql
from pymysql.connections import Connection
```

Then append to the bottom of `db_structure_downloader/db.py`:
```python
def connect(host: str, port: int, user: str, password: str, database: str) -> Connection:
    """Open a MySQL connection. Raises pymysql.Error on failure."""
    return pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        charset="utf8mb4",
    )


def list_tables(conn: Connection) -> list[str]:
    """Return all table names in the connected database, alphabetically sorted."""
    with conn.cursor() as cur:
        cur.execute("SHOW TABLES")
        rows = cur.fetchall()
    return sorted(row[0] for row in rows)
```

- [ ] **Step 2: Manually verify with a Docker MySQL**

Start a throwaway MySQL container:
```bash
docker run --rm -d --name testmysql \
  -e MYSQL_ROOT_PASSWORD=test \
  -e MYSQL_DATABASE=testdb \
  -p 3306:3306 \
  mysql:8
sleep 15  # wait for MySQL to be ready
```

Seed it:
```bash
docker exec -i testmysql mysql -uroot -ptest testdb <<'SQL'
CREATE TABLE customers (
    id CHAR(36) PRIMARY KEY,
    name VARCHAR(200) COMMENT 'Legal name',
    kvk_number VARCHAR(8)
) COMMENT='The master list of companies we do business with.';

CREATE TABLE engagements (
    id CHAR(36) PRIMARY KEY,
    customer_id CHAR(36) NOT NULL,
    title VARCHAR(200),
    CONSTRAINT fk_engagements_customer
        FOREIGN KEY (customer_id) REFERENCES customers(id)
);
SQL
```

Probe from Python:
```bash
source .venv/bin/activate
python -c "
from db_structure_downloader.db import connect, list_tables
conn = connect('127.0.0.1', 3306, 'root', 'test', 'testdb')
print(list_tables(conn))
conn.close()
"
```
Expected: `['customers', 'engagements']`

Leave the container running — Tasks 7 and later use it.

- [ ] **Step 3: Commit**

```bash
git add db_structure_downloader/db.py
git commit -m "feat(db): add connect() and list_tables()"
```

---

## Task 7: Database — fetch table metadata

**Files:**
- Modify: `db_structure_downloader/db.py`

- [ ] **Step 1: Add `fetch_table_metadata`**

Append to `db_structure_downloader/db.py`:
```python
def fetch_table_metadata(conn: Connection, database: str, table: str) -> TableMetadata:
    """Pull comment, columns, and FK relations for one table."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT TABLE_COMMENT FROM INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s",
            (database, table),
        )
        row = cur.fetchone()
        table_comment = row[0] if row and row[0] else ""

        cur.execute(
            "SELECT COLUMN_NAME, COLUMN_TYPE, COLUMN_COMMENT, COLUMN_KEY "
            "FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s "
            "ORDER BY ORDINAL_POSITION",
            (database, table),
        )
        columns = [
            Column(
                name=name,
                type=col_type,
                comment=comment or "",
                is_pk=(key == "PRI"),
            )
            for (name, col_type, comment, key) in cur.fetchall()
        ]

        cur.execute(
            "SELECT COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME "
            "FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE "
            "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s "
            "  AND REFERENCED_TABLE_NAME IS NOT NULL",
            (database, table),
        )
        outgoing = [
            Relation(
                from_table=table,
                from_column=col,
                to_table=ref_table,
                to_column=ref_col,
            )
            for (col, ref_table, ref_col) in cur.fetchall()
        ]

        cur.execute(
            "SELECT TABLE_NAME, COLUMN_NAME, REFERENCED_COLUMN_NAME "
            "FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE "
            "WHERE TABLE_SCHEMA = %s AND REFERENCED_TABLE_NAME = %s "
            "  AND REFERENCED_TABLE_NAME IS NOT NULL",
            (database, table),
        )
        incoming = [
            Relation(
                from_table=other_table,
                from_column=other_col,
                to_table=table,
                to_column=ref_col,
            )
            for (other_table, other_col, ref_col) in cur.fetchall()
        ]

    return TableMetadata(
        name=table,
        comment=table_comment,
        columns=columns,
        outgoing=outgoing,
        incoming=incoming,
    )
```

- [ ] **Step 2: Manually verify against the Docker MySQL**

Run:
```bash
source .venv/bin/activate
python -c "
from db_structure_downloader.db import connect, fetch_table_metadata
from db_structure_downloader.markdown import render
conn = connect('127.0.0.1', 3306, 'root', 'test', 'testdb')
print(render(fetch_table_metadata(conn, 'testdb', 'customers')))
print('---')
print(render(fetch_table_metadata(conn, 'testdb', 'engagements')))
conn.close()
"
```
Expected output for `customers`:
- `# customers`
- `**Purpose:** The master list of companies we do business with.`
- A column row for `id` with `PK`, for `name` with `Legal name`, for `kvk_number` with `_TODO_`.
- A `**Relations:**` section listing `engagements.customer_id → customers.id`.

Expected for `engagements`:
- `**Purpose:** _TODO: describe purpose_`
- Outgoing relation `engagements.customer_id → customers.id`.

- [ ] **Step 3: Commit**

```bash
git add db_structure_downloader/db.py
git commit -m "feat(db): add fetch_table_metadata() with FK introspection"
```

---

## Task 8: Config — load and save last connection

**Files:**
- Create: `db_structure_downloader/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
pytest tests/test_config.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'db_structure_downloader.config'`.

- [ ] **Step 3: Implement `config.py`**

```python
# db_structure_downloader/config.py
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
```

- [ ] **Step 4: Run the tests**

Run:
```bash
pytest tests/test_config.py -v
```
Expected: 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add db_structure_downloader/config.py tests/test_config.py
git commit -m "feat(config): add load/save last-connection JSON"
```

---

## Task 9: GUI — connection screen

**Files:**
- Create: `db_structure_downloader/gui.py`

- [ ] **Step 1: Implement the App skeleton + ConnectionFrame**

```python
# db_structure_downloader/gui.py
"""Tkinter GUI. Two screens (connection, export) presented as frames swapped
inside a single Tk root window. Knows nothing about SQL or markdown layout."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import pymysql

from db_structure_downloader import config, db
from db_structure_downloader.markdown import render


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Database Structure Downloader")
        self.geometry("600x500")
        self._container = ttk.Frame(self, padding=12)
        self._container.pack(fill="both", expand=True)
        self._show_connection_screen()

    def _show_connection_screen(self) -> None:
        for child in self._container.winfo_children():
            child.destroy()
        ConnectionFrame(self._container, on_connected=self._show_export_screen).pack(
            fill="both", expand=True
        )

    def _show_export_screen(self, conn, database: str, conn_args: dict) -> None:
        # Filled in in Task 10.
        raise NotImplementedError


class ConnectionFrame(ttk.Frame):
    def __init__(self, master, on_connected) -> None:
        super().__init__(master)
        self._on_connected = on_connected

        self._host = tk.StringVar(value="localhost")
        self._port = tk.StringVar(value="3306")
        self._user = tk.StringVar(value="root")
        self._password = tk.StringVar()
        self._database = tk.StringVar()

        saved = config.load_last_connection()
        if saved:
            self._host.set(saved.get("host", "localhost"))
            self._port.set(str(saved.get("port", 3306)))
            self._user.set(saved.get("user", "root"))
            self._database.set(saved.get("database", ""))

        self._build()

    def _build(self) -> None:
        ttk.Label(self, text="Connect to MySQL", font=("", 14, "bold")).grid(
            row=0, column=0, columnspan=2, pady=(0, 12), sticky="w"
        )

        rows = [
            ("Host", self._host, False),
            ("Port", self._port, False),
            ("User", self._user, False),
            ("Password", self._password, True),
            ("Database", self._database, False),
        ]
        for i, (label, var, is_secret) in enumerate(rows, start=1):
            ttk.Label(self, text=label).grid(row=i, column=0, sticky="w", pady=4)
            entry = ttk.Entry(self, textvariable=var, show="*" if is_secret else "")
            entry.grid(row=i, column=1, sticky="ew", pady=4)

        self.columnconfigure(1, weight=1)

        self._error = ttk.Label(self, foreground="red", wraplength=500)
        self._error.grid(row=len(rows) + 1, column=0, columnspan=2, sticky="w", pady=(8, 4))

        ttk.Button(self, text="Connect", command=self._on_connect_click).grid(
            row=len(rows) + 2, column=0, columnspan=2, pady=(8, 0)
        )

    def _on_connect_click(self) -> None:
        self._error.config(text="")
        try:
            port = int(self._port.get())
        except ValueError:
            self._error.config(text="Port must be a number.")
            return

        conn_args = dict(
            host=self._host.get().strip(),
            port=port,
            user=self._user.get().strip(),
            password=self._password.get(),
            database=self._database.get().strip(),
        )
        try:
            conn = db.connect(**conn_args)
        except pymysql.Error as e:
            self._error.config(text=f"Connection failed: {e}")
            return

        self._on_connected(conn, conn_args["database"], conn_args)
```

- [ ] **Step 2: Manually smoke-test the connection screen**

Run:
```bash
source .venv/bin/activate
python -c "from db_structure_downloader.gui import App; App().mainloop()"
```
Expected: a window appears with a connection form; clicking **Connect** with bad credentials shows a red error; with the Docker MySQL credentials from Task 6 it raises `NotImplementedError` (the export screen isn't built yet) — that's fine, close the window.

- [ ] **Step 3: Commit**

```bash
git add db_structure_downloader/gui.py
git commit -m "feat(gui): add App skeleton and connection screen"
```

---

## Task 10: GUI — export screen

**Files:**
- Modify: `db_structure_downloader/gui.py`

- [ ] **Step 1: Replace the `_show_export_screen` stub with a real method**

In `db_structure_downloader/gui.py`, find:
```python
    def _show_export_screen(self, conn, database: str, conn_args: dict) -> None:
        # Filled in in Task 10.
        raise NotImplementedError
```
Replace it with:
```python
    def _show_export_screen(self, conn, database: str, conn_args: dict) -> None:
        for child in self._container.winfo_children():
            child.destroy()
        ExportFrame(
            self._container,
            conn=conn,
            database=database,
            conn_args=conn_args,
        ).pack(fill="both", expand=True)
```

- [ ] **Step 2: Append `ExportFrame` to the same file**

First, add two imports to the top of `db_structure_downloader/gui.py` (in the stdlib group, before the `import tkinter as tk` line):
```python
import os
from pathlib import Path
```

Then append at the bottom of `db_structure_downloader/gui.py`:
```python
class ExportFrame(ttk.Frame):
    def __init__(self, master, conn, database: str, conn_args: dict) -> None:
        super().__init__(master)
        self._conn = conn
        self._database = database
        self._conn_args = conn_args

        self._output_folder = tk.StringVar()
        self._table_vars: dict[str, tk.BooleanVar] = {}

        self._build()
        self._load_tables()

    def _build(self) -> None:
        ttk.Label(self, text=f"Tables in `{self._database}`",
                  font=("", 14, "bold")).pack(anchor="w", pady=(0, 8))

        button_row = ttk.Frame(self)
        button_row.pack(fill="x")
        ttk.Button(button_row, text="Select all",
                   command=self._select_all).pack(side="left")
        ttk.Button(button_row, text="Deselect all",
                   command=self._deselect_all).pack(side="left", padx=(8, 0))

        # Scrollable checkbox list
        list_frame = ttk.Frame(self)
        list_frame.pack(fill="both", expand=True, pady=(8, 8))

        canvas = tk.Canvas(list_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        self._inner = ttk.Frame(canvas)

        self._inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=self._inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Output folder row
        folder_row = ttk.Frame(self)
        folder_row.pack(fill="x", pady=(0, 8))
        ttk.Label(folder_row, text="Output folder:").pack(side="left")
        ttk.Entry(folder_row, textvariable=self._output_folder).pack(
            side="left", fill="x", expand=True, padx=8
        )
        ttk.Button(folder_row, text="Browse...",
                   command=self._pick_folder).pack(side="left")

        ttk.Button(self, text="Export", command=self._on_export_click).pack(
            anchor="e", pady=(0, 8)
        )

        self._status = tk.Text(self, height=8, state="disabled", wrap="word")
        self._status.pack(fill="both", expand=False)

    def _load_tables(self) -> None:
        try:
            tables = db.list_tables(self._conn)
        except pymysql.Error as e:
            messagebox.showerror("Failed to list tables", str(e))
            return
        for t in tables:
            var = tk.BooleanVar(value=False)
            self._table_vars[t] = var
            ttk.Checkbutton(self._inner, text=t, variable=var).pack(anchor="w")

    def _select_all(self) -> None:
        for v in self._table_vars.values():
            v.set(True)

    def _deselect_all(self) -> None:
        for v in self._table_vars.values():
            v.set(False)

    def _pick_folder(self) -> None:
        chosen = filedialog.askdirectory(title="Choose output folder")
        if chosen:
            self._output_folder.set(chosen)

    def _append_status(self, line: str) -> None:
        self._status.configure(state="normal")
        self._status.insert("end", line + "\n")
        self._status.see("end")
        self._status.configure(state="disabled")
        self.update_idletasks()

    def _on_export_click(self) -> None:
        selected = [t for t, v in self._table_vars.items() if v.get()]
        if not selected:
            messagebox.showwarning("No tables selected",
                                   "Pick at least one table to export.")
            return
        folder = self._output_folder.get().strip()
        if not folder:
            messagebox.showwarning("No output folder",
                                   "Pick an output folder.")
            return
        out_path = Path(folder)
        if not out_path.is_dir() or not os.access(out_path, os.W_OK):
            messagebox.showerror("Folder not writable",
                                 f"Cannot write to {out_path}.")
            return

        exported = 0
        failed: list[tuple[str, str]] = []
        total = len(selected)

        for i, table in enumerate(selected, start=1):
            try:
                meta = db.fetch_table_metadata(self._conn, self._database, table)
                content = render(meta)
                (out_path / f"{table}.md").write_text(content, encoding="utf-8")
                exported += 1
                self._append_status(f"Exported {table} ({i} / {total})")
            except (pymysql.Error, OSError) as e:
                failed.append((table, str(e)))
                self._append_status(f"Failed: {table} — {e}")

        if failed:
            self._append_status(
                f"Done. Exported {exported} / {total} tables. "
                f"{len(failed)} failed: {', '.join(t for t, _ in failed)} "
                f"(see above)."
            )
        else:
            self._append_status(f"Done. Exported {exported} / {total} tables.")
            config.save_last_connection(
                host=self._conn_args["host"],
                port=self._conn_args["port"],
                user=self._conn_args["user"],
                database=self._conn_args["database"],
            )
```

- [ ] **Step 3: Manual smoke test against the Docker MySQL**

Run:
```bash
source .venv/bin/activate
mkdir -p /tmp/dbsd-out
python -c "from db_structure_downloader.gui import App; App().mainloop()"
```

In the app:
1. Connection screen pre-fills with whatever was saved (or defaults). Enter host=`127.0.0.1`, port=`3306`, user=`root`, password=`test`, database=`testdb`. Click **Connect**.
2. Export screen lists `customers` and `engagements`. Click **Select all**.
3. **Browse...** → pick `/tmp/dbsd-out`.
4. Click **Export**. Status area shows two `Exported ... (n / 2)` lines, then `Done.`.
5. Close the window.

Then check the output:
```bash
ls /tmp/dbsd-out/
cat /tmp/dbsd-out/customers.md
cat /tmp/dbsd-out/engagements.md
```
Expected: two `.md` files, content matches what `render` produced in Task 7.

Also check the saved config:
```bash
cat ~/.config/db-structure-downloader/last-connection.json
```
Expected: JSON with host/port/user/database, no password.

- [ ] **Step 4: Commit**

```bash
git add db_structure_downloader/gui.py
git commit -m "feat(gui): add export screen with table selection and writeout"
```

---

## Task 11: Top-level error guard and `__main__.py`

**Files:**
- Create: `db_structure_downloader/__main__.py`
- Modify: `db_structure_downloader/gui.py`

- [ ] **Step 1: Add top-level exception reporter to `App`**

In `db_structure_downloader/gui.py`, modify the `App.__init__` method to register a handler. Replace:
```python
    def __init__(self) -> None:
        super().__init__()
        self.title("Database Structure Downloader")
        self.geometry("600x500")
        self._container = ttk.Frame(self, padding=12)
        self._container.pack(fill="both", expand=True)
        self._show_connection_screen()
```
with:
```python
    def __init__(self) -> None:
        super().__init__()
        self.title("Database Structure Downloader")
        self.geometry("600x500")
        self.report_callback_exception = self._on_unhandled_exception
        self._container = ttk.Frame(self, padding=12)
        self._container.pack(fill="both", expand=True)
        self._show_connection_screen()

    def _on_unhandled_exception(self, exc_type, exc_value, exc_tb) -> None:
        import traceback
        traceback.print_exception(exc_type, exc_value, exc_tb)
        messagebox.showerror(
            "Unexpected error",
            f"{exc_type.__name__}: {exc_value}\n\nThe app will keep running.",
        )
```

- [ ] **Step 2: Write `__main__.py`**

```python
# db_structure_downloader/__main__.py
"""Entry point: `python -m db_structure_downloader`."""

from db_structure_downloader.gui import App


def main() -> None:
    App().mainloop()


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Manual end-to-end smoke test**

Run:
```bash
source .venv/bin/activate
python -m db_structure_downloader
```
Expected: window opens, full flow from Task 10 still works.

Test the error guard: with the app running, force an exception by entering an invalid port like `abc` — that's already caught; instead try connecting with database name `bogus_does_not_exist` then clicking Connect — pymysql raises an error, which is caught by `ConnectionFrame` and shown as a red label (not the dialog). To verify the top-level guard works, temporarily edit `_on_export_click` to add `raise RuntimeError("test")` at the top, run again, click Export — a dialog should appear and the app should keep running. Revert the test change.

- [ ] **Step 4: Run the full test suite**

Run:
```bash
pytest -v
```
Expected: all tests in `test_markdown.py` and `test_config.py` pass.

- [ ] **Step 5: Tear down the Docker MySQL**

```bash
docker stop testmysql
```

- [ ] **Step 6: Commit**

```bash
git add db_structure_downloader/__main__.py db_structure_downloader/gui.py
git commit -m "feat: add __main__ entry point and top-level error guard"
```

---

## Task 12: Final polish — README usage section + version tag

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Expand `README.md` with a usage section**

Replace `README.md` with:
```markdown
# Database Structure Downloader

A desktop utility that connects to a MySQL server, lets you pick tables from a
GUI, and exports each table's structure as a separate markdown file. The output
is shaped for ingestion into a RAG knowledgebase: chunks split cleanly per
table, business meaning sits next to structure, and foreign-key relationships
are written as plain English so embeddings retrieve them on questions about
the underlying concepts.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python -m db_structure_downloader
```

1. Enter MySQL host, port, user, password, database. Click **Connect**.
2. Tick the tables you want to export (or click **Select all**).
3. Click **Browse...** and pick an output folder.
4. Click **Export**. One `<table>.md` is written per selected table.

The host/port/user/database (no password) are remembered between runs in
`~/.config/db-structure-downloader/last-connection.json`.

## Output format

Each markdown file looks like:

````markdown
# customers

**Purpose:** The master list of companies we do business with.

| Column | Type | Meaning |
|---|---|---|
| id | char(36) | PK |
| name | varchar(200) | Legal name |
| kvk_number | varchar(8) | _TODO_ |

**Relations:**
- `engagements.customer_id → customers.id`
- `contacts.customer_id → customers.id`
````

`Purpose` and `Meaning` come from MySQL `TABLE_COMMENT` and `COLUMN_COMMENT`
where present; otherwise they are emitted as `_TODO_` placeholders so the gap
is obvious in the editor. Relations are inferred from `INFORMATION_SCHEMA`
foreign-key rows; outgoing FKs are listed first, then incoming.

## Test

```bash
pytest
```
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: expand README with usage and output format"
```

- [ ] **Step 3: Tag v0.1.0**

```bash
git tag v0.1.0
git log --oneline
```
Expected: a clean linear history of ~12 commits.

---

## Self-review checklist (already run by author)

- ✓ Spec coverage: every section of the design has at least one task that
  implements it (purpose → Task 2; columns → Task 2; relations rules → Tasks
  2 + 4; pipe escape → Task 5; introspection queries → Tasks 6–7; config
  persistence → Task 8; connection screen → Task 9; export screen → Task 10;
  per-table failure handling → Task 10; top-level error guard → Task 11; test
  list → Tasks 2–5 + 8).
- ✓ No placeholders ("TBD", "implement appropriate ...", etc.) — every step
  contains exact code or commands.
- ✓ Type consistency: dataclass field names (`from_table`, `from_column`,
  `to_table`, `to_column`, `is_pk`) are identical across `db.py`,
  `markdown.py`, and the test files. Function names used in `gui.py` (`db.connect`,
  `db.list_tables`, `db.fetch_table_metadata`, `markdown.render`,
  `config.load_last_connection`, `config.save_last_connection`) match their
  definitions.
