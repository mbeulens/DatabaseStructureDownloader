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
