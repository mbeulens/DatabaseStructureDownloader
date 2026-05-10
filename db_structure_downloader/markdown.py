"""Pure markdown rendering. Takes a TableMetadata dataclass, returns a
markdown string. No I/O, no DB, no GUI dependencies."""

from __future__ import annotations

from db_structure_downloader.db import Column, Relation, TableMetadata


# Syntec-wide column conventions. Keys are matched case-insensitively.
_HARDCODED_MEANINGS: dict[str, str] = {
    "id": "Unique internal row Identifiers (Used for JOINS)",
    "guid": "Globally unique identifier (Used for record lookup)",
    "created": "Timestamp for record creation",
    "modified": "Timestamp for record last modification",
    "core_status_id": "Softdelete status ID",
}


def render(table: TableMetadata) -> str:
    parts: list[str] = []
    parts.append(f"# {table.name}")
    parts.append("")

    purpose = table.comment.strip() if table.comment else ""
    parts.append(f"**Purpose:** {purpose or _humanise_table_name(table.name)}")
    parts.append("")

    outgoing_by_column = {rel.from_column: rel for rel in table.outgoing}

    parts.append("| Column | Type | Meaning |")
    parts.append("|---|---|---|")
    for col in table.columns:
        meaning = _column_meaning(col, outgoing_by_column)
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


def _column_meaning(col: Column, outgoing_by_column: dict[str, Relation]) -> str:
    if col.comment.strip():
        return _escape_pipes(col.comment.strip())

    name_lower = col.name.lower()
    if name_lower in _HARDCODED_MEANINGS:
        return _HARDCODED_MEANINGS[name_lower]

    if name_lower.endswith("_id") and col.name in outgoing_by_column:
        return f"Foreign key {outgoing_by_column[col.name].to_table}"

    if col.is_pk:
        return "PK"

    return ""


def _format_relation(rel: Relation) -> str:
    return f"{rel.from_table}.{rel.from_column} → {rel.to_table}.{rel.to_column}"


def _escape_pipes(text: str) -> str:
    return text.replace("|", "\\|")


def _humanise_table_name(name: str) -> str:
    """`audit_logs` → `Audit logs`. Preserves case in non-leading words so
    acronyms like `CRM_users` survive as `CRM users`."""
    if not name:
        return name
    text = name.replace("_", " ")
    return text[0].upper() + text[1:]
