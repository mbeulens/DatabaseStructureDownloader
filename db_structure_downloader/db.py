"""MySQL introspection. Connects to a database and returns table metadata
as plain dataclasses. No knowledge of the GUI or markdown layout."""

from __future__ import annotations

from dataclasses import dataclass, field

import pymysql
from pymysql.connections import Connection


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
