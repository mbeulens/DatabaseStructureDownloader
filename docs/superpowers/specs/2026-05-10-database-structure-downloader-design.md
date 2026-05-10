# Database Structure Downloader — design

## Purpose

A desktop utility that connects to a MySQL server (native or Docker), lets the user
pick which tables to export, and writes one markdown file per table to a chosen
folder. The output is shaped for ingestion into a Retrieval-Augmented Generation
(RAG) knowledgebase: chunks split cleanly per table, business meaning sits next
to structure, and foreign-key relationships are written as plain English so
embeddings retrieve them on questions about the underlying concepts.

## Non-goals

- Exporting data rows. Schema only.
- Running migrations or modifying the database in any way. The connection is
  read-only in spirit (no enforcement at the driver level, but no `INSERT` /
  `UPDATE` / `DDL` is ever issued).
- Supporting databases other than MySQL.
- Producing JSON, raw SQL dumps, or ER diagrams. Markdown only.
- Multi-user or networked deployment. Single-user desktop tool.

## Architecture

A small Python package:

```
db_structure_downloader/
├── __main__.py    # entry point: `python -m db_structure_downloader`
├── db.py          # MySQL connection + INFORMATION_SCHEMA queries
├── markdown.py    # pure: takes table metadata, returns markdown string
├── gui.py         # Tkinter window + event wiring
└── config.py      # load/save last-connection JSON
requirements.txt   # PyMySQL only; Tkinter is stdlib
```

Boundaries:

- `markdown.py` is a pure function over data — testable without a database or GUI.
- `db.py` knows nothing about Tk; it returns plain dicts/dataclasses.
- `gui.py` writes no SQL and produces no markdown; it orchestrates.
- `config.py` is a tiny module that reads/writes one JSON file.

## Dependencies

- Python 3.10+
- `PyMySQL` (pure Python, easy install — no system MySQL client libs needed).
- `tkinter` from the standard library.

No other runtime dependencies.

## GUI flow

1. **Connection screen** (the only thing visible on launch):
   - Fields: host, port (default `3306`), user, password, database.
   - On launch, `config.py` pre-fills host/port/user/database from the saved
     last-connection JSON if it exists. Password is never persisted.
   - **Connect** button. On failure: a red error label appears below the form
     with the driver's error message. The form stays open.
   - On success: the GUI transitions to the export screen.
2. **Export screen**:
   - Scrollable list of tables in the connected database, each with a checkbox.
     Tables are listed alphabetically.
   - **Select all** / **Deselect all** buttons above the list.
   - **Output folder** field with a **Browse...** button (uses
     `tkinter.filedialog.askdirectory`).
   - **Export** button (disabled until at least one table is selected and a
     folder is chosen).
   - Status area below: a read-only multi-line text widget where progress
     messages are appended live during export.
3. **During export**:
   - For each selected table, fetch metadata, render markdown, write
     `{output_folder}/{table_name}.md`. Update the status area:
     `Exported customers (3 / 47)`.
   - If a single table fails, log the error to the status area and continue.
4. **End of export**:
   - Final status line: `Done. Exported 46 / 47 tables. 1 failed: orders (see
     above).` if there were failures, otherwise `Done. Exported 47 / 47
     tables.`.
   - On full success, `config.py` writes the last-connection JSON
     (host/port/user/database — no password).

The export screen does not need a "back to connection" button in v1; closing
and relaunching the app is fine.

## Database introspection

All queries hit `INFORMATION_SCHEMA`. Per table being exported, four queries
run, each parameterized on the database name and table name:

1. **Table comment**:

   ```sql
   SELECT TABLE_COMMENT
   FROM INFORMATION_SCHEMA.TABLES
   WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s;
   ```

2. **Columns**:

   ```sql
   SELECT COLUMN_NAME, COLUMN_TYPE, COLUMN_COMMENT, COLUMN_KEY
   FROM INFORMATION_SCHEMA.COLUMNS
   WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
   ORDER BY ORDINAL_POSITION;
   ```

   `COLUMN_KEY = 'PRI'` identifies primary-key columns.

3. **Outgoing foreign keys** (this table → others):

   ```sql
   SELECT COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
   FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
   WHERE TABLE_SCHEMA = %s
     AND TABLE_NAME = %s
     AND REFERENCED_TABLE_NAME IS NOT NULL;
   ```

4. **Incoming foreign keys** (other tables → this one):

   ```sql
   SELECT TABLE_NAME, COLUMN_NAME, REFERENCED_COLUMN_NAME
   FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
   WHERE TABLE_SCHEMA = %s
     AND REFERENCED_TABLE_NAME = %s
     AND REFERENCED_TABLE_NAME IS NOT NULL;
   ```

   `REFERENCED_TABLE_NAME` isn't in the `SELECT` because it's the table being
   exported — `db.py` fills `to_table` on the resulting `Relation` from the
   table name it was given.

The list of all tables (for the GUI checkbox list) comes from a single
`SHOW TABLES` after connecting.

`db.py` exposes a small typed surface:

```python
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
    columns: list[Column]
    outgoing: list[Relation]   # this table's FKs pointing out
    incoming: list[Relation]   # other tables' FKs pointing in
```

## Markdown output

One file per table, named `{table_name}.md`. The template:

```markdown
# {table_name}

**Purpose:** {table_comment_or_TODO}

| Column | Type | Meaning |
|---|---|---|
| {col} | {type} | {meaning} |
| ...   | ...    | ...       |

**Relations:**
- `{outgoing.from_table}.{outgoing.from_column} → {outgoing.to_table}.{outgoing.to_column}`
- `{incoming.from_table}.{incoming.from_column} → {incoming.to_table}.{incoming.to_column}`
```

Field rules:

- **Purpose**: `TABLE_COMMENT` if non-empty, otherwise the literal string
  `_TODO: describe purpose_`.
- **Meaning** column: `COLUMN_COMMENT` if non-empty; else `PK` if `COLUMN_KEY =
  'PRI'`; else `_TODO_`.
- **Relations** section: outgoing FKs are listed first (sorted alphabetically
  by `from_column`), then incoming FKs (sorted alphabetically by
  `from_table`, then `from_column`). If a table has no FKs in either
  direction, the entire `**Relations:**` section is omitted — no empty
  heading.
- Pipe characters in column comments are escaped as `\|` so they don't break
  the markdown table.
- Trailing newline at end of file.

## Configuration persistence

`config.py` reads and writes a single JSON file:

```
~/.config/db-structure-downloader/last-connection.json
```

Contents:

```json
{
  "host": "localhost",
  "port": 3306,
  "user": "root",
  "database": "syntec_crm"
}
```

Behavior:

- On app launch: if the file exists and parses, pre-fill those fields.
  Otherwise leave them blank (port defaults to `3306`).
- On successful export: write the current connection's host/port/user/database
  to the file (creating the directory if needed). Never write the password.
- Read or write failures of this file are non-fatal — log a warning to stderr
  and continue. The file is convenience, not state.

## Error handling

- **Connection failure**: red error label below the form with the driver's
  message. Form stays open. No dialog popup.
- **`SHOW TABLES` failure** after a successful connect: error dialog, stay on
  connection screen.
- **Output folder missing or not writable**: error dialog when **Export** is
  clicked, before any export starts. Stay on export screen.
- **Per-table introspection or write failure** during export: append the error
  to the status area (`Failed: orders — <reason>`), continue with the next
  table. Final summary reports the count of failures.
- **Unexpected exception** anywhere: the GUI must not silently die. A
  top-level handler in `gui.py` shows a dialog with the exception message and
  keeps the app running.

## Testing

- Unit tests on `markdown.render(table_metadata) -> str` covering:
  - Table with comment + column comments + PK + outgoing + incoming FKs.
  - Table with no comments anywhere (everything becomes `_TODO_` / `_TODO:
    describe purpose_`).
  - Table with no FKs in either direction (no `**Relations:**` section).
  - Pipe character in a column comment is escaped.
- No automated tests for `db.py` or `gui.py` in v1. Both are tested manually
  against a Docker MySQL.

## Out-of-scope but worth noting

- A future version could split the output by logical domain (`crm.md`,
  `billing.md`) when a schema has >50 tables, as your knowledgebase guidance
  suggests. v1 is one-file-per-table only.
- A future version could read the column-and-table comments and seed a
  hand-edited glossary file. v1 leaves the glossary as a manual,
  cross-cutting document.
