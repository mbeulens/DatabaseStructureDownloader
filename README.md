# Database Structure Downloader

A desktop utility that connects to a MySQL server, lets you pick tables from a
GUI, and exports each table's structure as a separate markdown file. The output
is shaped for ingestion into a RAG knowledgebase: chunks split cleanly per
table, business meaning sits next to structure, and foreign-key relationships
are written as plain English so embeddings retrieve them on questions about
the underlying concepts.

## Setup

```bash
sudo apt install python3-tk    # Linux only — Tkinter is shipped separately on Debian/Ubuntu
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

```markdown
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
```

`Purpose` and `Meaning` come from MySQL `TABLE_COMMENT` and `COLUMN_COMMENT`
where present; otherwise they are emitted as `_TODO_` placeholders so the gap
is obvious in the editor. Relations are inferred from `INFORMATION_SCHEMA`
foreign-key rows; outgoing FKs are listed first, then incoming.

## Test

```bash
pytest
```
