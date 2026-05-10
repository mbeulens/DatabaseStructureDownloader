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
