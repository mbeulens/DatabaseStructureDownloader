"""Pure markdown rendering. Takes a TableMetadata dataclass, returns a
markdown string. No I/O, no DB, no GUI dependencies."""

from __future__ import annotations

from db_structure_downloader.db import Column, Relation, TableMetadata


# When a table is referenced by more than this many other tables, the
# remaining incoming-FK rows are collapsed into a single summary line.
# Soft-delete / status / audit reference tables would otherwise emit 200+
# near-identical lines that drown out useful chunks during RAG retrieval.
_MAX_INCOMING_RELATIONS = 25

# Syntec-wide column conventions. Keys are matched case-insensitively.
_HARDCODED_MEANINGS: dict[str, str] = {
    "id": "Unique internal row Identifiers (Used for JOINS)",
    "guid": "Globally unique identifier (Used for record lookup)",
    "created": "Timestamp for record creation",
    "modified": "Timestamp for record last modification",
    "core_status_id": "Softdelete status ID",
}


def render(table: TableMetadata, overrides: dict[str, str] | None = None) -> str:
    overrides = overrides or {}
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
        meaning = _column_meaning(col, outgoing_by_column, overrides)
        parts.append(f"| {col.name} | {col.type} | {meaning} |")

    has_relations = bool(table.outgoing) or bool(table.incoming)
    if has_relations:
        parts.append("")
        parts.append("**Relations:**")
        for rel in sorted(table.outgoing, key=lambda r: r.from_column):
            parts.append(f"- `{_format_relation(rel)}`")
        sorted_incoming = sorted(
            table.incoming, key=lambda r: (r.from_table, r.from_column)
        )
        for rel in sorted_incoming[:_MAX_INCOMING_RELATIONS]:
            parts.append(f"- `{_format_relation(rel)}`")
        overflow = len(sorted_incoming) - _MAX_INCOMING_RELATIONS
        if overflow > 0:
            parts.append(
                f"- …and {overflow} more inbound foreign keys "
                "(likely a system-wide marker like a status/audit reference "
                "— don't reason about ownership from this list)."
            )

    return "\n".join(parts) + "\n"


def _column_meaning(
    col: Column,
    outgoing_by_column: dict[str, Relation],
    overrides: dict[str, str],
) -> str:
    # Manual override file wins over everything else.
    if col.name in overrides and overrides[col.name].strip():
        return _escape_pipes(overrides[col.name].strip())

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


_MISC_GROUP = "(misc)"


def render_overview(database: str, tables: list[TableMetadata]) -> str:
    """Render a single-file overview that groups tables by name prefix.

    One chunk in RAG terms — gives the model a "system shape" view it can
    retrieve when asked questions like "how does the role system fit
    together" that span multiple tables. Each table is listed with its
    outgoing foreign keys so subsystem boundaries are visible at a glance.
    """
    parts: list[str] = []
    parts.append(
        f"# {_humanise_table_name(database)} database — "
        "relationships and how tables connect"
    )
    parts.append("")
    parts.append(
        "This file describes how the tables in the database connect to each "
        "other. Tables are grouped by name prefix, which usually marks a "
        "subsystem (for example all `core_*` tables form the core subsystem). "
        "The arrow `→` shows which other tables a given table references "
        "through a foreign key; the target may belong to a different group, "
        "which makes cross-subsystem dependencies easy to spot."
    )

    groups: dict[str, list[TableMetadata]] = {}
    for table in tables:
        prefix = table.name.split("_", 1)[0] if "_" in table.name else _MISC_GROUP
        groups.setdefault(prefix, []).append(table)

    def group_sort_key(name: str) -> tuple[int, str]:
        # (misc) always last; everything else alphabetical.
        return (1 if name == _MISC_GROUP else 0, name)

    for group_name in sorted(groups, key=group_sort_key):
        parts.append("")
        parts.append(f"## {group_name}")
        for table in sorted(groups[group_name], key=lambda t: t.name):
            targets = sorted({rel.to_table for rel in table.outgoing})
            if targets:
                parts.append(f"- {table.name} → {', '.join(targets)}")
            else:
                parts.append(f"- {table.name}")

    return "\n".join(parts) + "\n"
