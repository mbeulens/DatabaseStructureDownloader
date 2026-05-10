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
