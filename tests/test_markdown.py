from db_structure_downloader.db import Column, Relation, TableMetadata
from db_structure_downloader.markdown import render, render_overview


ID_MEANING = "Unique internal row Identifiers (Used for JOINS)"
GUID_MEANING = "Globally unique identifier (Used for record lookup)"
CREATED_MEANING = "Timestamp for record creation"
MODIFIED_MEANING = "Timestamp for record last modification"
CORE_STATUS_MEANING = "Softdelete status ID"


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
        f"| id | char(36) | {ID_MEANING} |\n"
        "| name | varchar(200) | Legal name |\n"
        "| kvk_number | varchar(8) |  |\n"
        "\n"
        "**Relations:**\n"
        "- `contacts.customer_id → customers.id`\n"
        "- `engagements.customer_id → customers.id`\n"
    )

    assert render(table) == expected


def test_empty_table_comment_falls_back_to_humanised_table_name():
    table = TableMetadata(
        name="orders",
        comment="",
        columns=[Column(name="id", type="bigint", comment="", is_pk=True)],
        outgoing=[],
        incoming=[],
    )

    assert "**Purpose:** Orders" in render(table)


def test_snake_case_table_name_becomes_normal_text_for_purpose():
    table = TableMetadata(
        name="audit_logs",
        comment="",
        columns=[Column(name="id", type="bigint", comment="", is_pk=True)],
        outgoing=[],
        incoming=[],
    )

    assert "**Purpose:** Audit logs" in render(table)


def test_multi_word_snake_case_table_name_for_purpose():
    table = TableMetadata(
        name="customer_engagement_history",
        comment="",
        columns=[Column(name="id", type="bigint", comment="", is_pk=True)],
        outgoing=[],
        incoming=[],
    )

    assert "**Purpose:** Customer engagement history" in render(table)


def test_table_comment_still_wins_over_humanised_name():
    table = TableMetadata(
        name="audit_logs",
        comment="Append-only audit trail for compliance.",
        columns=[Column(name="id", type="bigint", comment="", is_pk=True)],
        outgoing=[],
        incoming=[],
    )

    assert "**Purpose:** Append-only audit trail for compliance." in render(table)
    assert "Audit logs" not in render(table)


def test_column_with_comment_uses_comment_verbatim():
    table = TableMetadata(
        name="customers",
        comment="",
        columns=[
            Column(name="id", type="char(36)", comment="My PK comment", is_pk=True),
            Column(name="created", type="timestamp", comment="Set in app code", is_pk=False),
        ],
        outgoing=[],
        incoming=[],
    )

    result = render(table)
    # COLUMN_COMMENT wins over hardcoded meanings.
    assert "| id | char(36) | My PK comment |" in result
    assert "| created | timestamp | Set in app code |" in result
    assert ID_MEANING not in result
    assert CREATED_MEANING not in result


def test_hardcoded_column_names_get_canonical_meanings():
    table = TableMetadata(
        name="anything",
        comment="",
        columns=[
            Column(name="id", type="bigint", comment="", is_pk=True),
            Column(name="guid", type="char(36)", comment="", is_pk=False),
            Column(name="created", type="timestamp", comment="", is_pk=False),
            Column(name="modified", type="timestamp", comment="", is_pk=False),
            Column(name="core_status_id", type="int", comment="", is_pk=False),
        ],
        outgoing=[],
        incoming=[],
    )

    result = render(table)
    assert f"| id | bigint | {ID_MEANING} |" in result
    assert f"| guid | char(36) | {GUID_MEANING} |" in result
    assert f"| created | timestamp | {CREATED_MEANING} |" in result
    assert f"| modified | timestamp | {MODIFIED_MEANING} |" in result
    assert f"| core_status_id | int | {CORE_STATUS_MEANING} |" in result


def test_hardcoded_match_is_case_insensitive():
    table = TableMetadata(
        name="anything",
        comment="",
        columns=[
            Column(name="ID", type="bigint", comment="", is_pk=True),
            Column(name="Created", type="timestamp", comment="", is_pk=False),
        ],
        outgoing=[],
        incoming=[],
    )

    result = render(table)
    assert f"| ID | bigint | {ID_MEANING} |" in result
    assert f"| Created | timestamp | {CREATED_MEANING} |" in result


def test_id_suffix_with_outgoing_fk_renders_as_foreign_key():
    table = TableMetadata(
        name="engagements",
        comment="",
        columns=[
            Column(name="id", type="char(36)", comment="", is_pk=True),
            Column(name="customer_id", type="char(36)", comment="", is_pk=False),
        ],
        outgoing=[
            Relation(from_table="engagements", from_column="customer_id",
                     to_table="customers", to_column="id"),
        ],
        incoming=[],
    )

    result = render(table)
    assert "| customer_id | char(36) | Foreign key customers |" in result


def test_id_suffix_without_relation_falls_through_to_blank():
    # An *_id column that is NOT a real FK (no INFORMATION_SCHEMA row) must
    # not be labelled as a foreign key. With nothing else to say, the Meaning
    # cell is left blank rather than echoing the column name.
    table = TableMetadata(
        name="webhook_events",
        comment="",
        columns=[
            Column(name="id", type="bigint", comment="", is_pk=True),
            Column(name="external_id", type="varchar(64)", comment="", is_pk=False),
        ],
        outgoing=[],
        incoming=[],
    )

    result = render(table)
    assert "| external_id | varchar(64) |  |" in result


def test_core_status_id_hardcoded_meaning_beats_fk_meaning():
    # core_status_id is in the hardcoded list AND ends in _id and may have an
    # FK; the hardcoded meaning is more specific and must win.
    table = TableMetadata(
        name="customers",
        comment="",
        columns=[
            Column(name="id", type="bigint", comment="", is_pk=True),
            Column(name="core_status_id", type="int", comment="", is_pk=False),
        ],
        outgoing=[
            Relation(from_table="customers", from_column="core_status_id",
                     to_table="core_status", to_column="id"),
        ],
        incoming=[],
    )

    result = render(table)
    assert f"| core_status_id | int | {CORE_STATUS_MEANING} |" in result
    assert "Foreign key core_status" not in result


def test_default_fallback_leaves_meaning_blank():
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
    assert "| message | text |  |" in result


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
    assert result.endswith("| message | text |  |\n")


def test_override_takes_precedence_over_column_comment():
    table = TableMetadata(
        name="core_user",
        comment="",
        columns=[
            Column(name="id", type="bigint", comment="", is_pk=True),
            Column(name="login_name", type="varchar(200)",
                   comment="raw DB comment", is_pk=False),
        ],
        outgoing=[],
        incoming=[],
    )

    overrides = {"login_name": "User's unique login (display name in UI)"}
    result = render(table, overrides=overrides)
    assert "| login_name | varchar(200) | User's unique login (display name in UI) |" in result
    assert "raw DB comment" not in result


def test_override_applied_when_no_other_rule_matches():
    table = TableMetadata(
        name="core_role",
        comment="",
        columns=[
            Column(name="id", type="bigint", comment="", is_pk=True),
            Column(name="scope", type="text", comment="", is_pk=False),
        ],
        outgoing=[],
        incoming=[],
    )

    overrides = {"scope": "JSON map of permissions granted by this role"}
    result = render(table, overrides=overrides)
    assert "| scope | text | JSON map of permissions granted by this role |" in result


def test_no_overrides_argument_keeps_existing_behaviour():
    # Backwards-compatible: callers that don't pass overrides see no change.
    table = TableMetadata(
        name="logs",
        comment="",
        columns=[Column(name="message", type="text", comment="", is_pk=False)],
        outgoing=[],
        incoming=[],
    )

    assert "| message | text |  |" in render(table)
    assert "| message | text |  |" in render(table, overrides=None)
    assert "| message | text |  |" in render(table, overrides={})


def test_override_with_pipe_is_escaped():
    table = TableMetadata(
        name="settings",
        comment="",
        columns=[Column(name="mode", type="varchar(8)", comment="", is_pk=False)],
        outgoing=[],
        incoming=[],
    )

    overrides = {"mode": "Either 'on' | 'off'"}
    result = render(table, overrides=overrides)
    assert "| mode | varchar(8) | Either 'on' \\| 'off' |" in result


def test_incoming_relations_under_cap_are_all_shown():
    table = TableMetadata(
        name="core_status",
        comment="",
        columns=[Column(name="id", type="int", comment="", is_pk=True)],
        outgoing=[],
        incoming=[
            Relation(from_table=f"t{i:02d}", from_column="core_status_id",
                     to_table="core_status", to_column="id")
            for i in range(25)
        ],
    )

    result = render(table)
    assert "more inbound foreign keys" not in result
    # All 25 rows present.
    for i in range(25):
        assert f"`t{i:02d}.core_status_id" in result


def test_incoming_relations_over_cap_are_truncated_with_summary():
    table = TableMetadata(
        name="core_status",
        comment="",
        columns=[Column(name="id", type="int", comment="", is_pk=True)],
        outgoing=[],
        incoming=[
            Relation(from_table=f"t{i:03d}", from_column="core_status_id",
                     to_table="core_status", to_column="id")
            for i in range(212)
        ],
    )

    result = render(table)
    # First 25 (sorted alphabetically) are present.
    for i in range(25):
        assert f"`t{i:03d}.core_status_id" in result
    # The 26th onwards are NOT individually present.
    assert "`t025.core_status_id" not in result
    assert "`t211.core_status_id" not in result
    # Summary line with the overflow count and the noise-warning.
    assert "…and 187 more inbound foreign keys" in result
    assert "system-wide marker" in result


def test_outgoing_relations_are_never_capped():
    # We don't cap outgoing — they're nearly always small in count and
    # represent the table's own structural dependencies.
    table = TableMetadata(
        name="busy_join",
        comment="",
        columns=[Column(name="id", type="int", comment="", is_pk=True)],
        outgoing=[
            Relation(from_table="busy_join", from_column=f"col_{i:02d}_id",
                     to_table=f"target_{i:02d}", to_column="id")
            for i in range(50)
        ],
        incoming=[],
    )

    result = render(table)
    assert "more inbound foreign keys" not in result
    # All 50 outgoing rows present.
    for i in range(50):
        assert f"`busy_join.col_{i:02d}_id" in result


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


# --- render_overview ----------------------------------------------------------


def _meta(name: str, *targets: str) -> TableMetadata:
    """Convenience: build a stub TableMetadata with the given outgoing FKs."""
    return TableMetadata(
        name=name,
        comment="",
        columns=[Column(name="id", type="int", comment="", is_pk=True)],
        outgoing=[
            Relation(from_table=name, from_column=f"{t}_id",
                     to_table=t, to_column="id")
            for t in targets
        ],
        incoming=[],
    )


def test_overview_header_frames_relationships_not_schema():
    # The header is tuned to retrieve well on conceptual "how does X work"
    # questions in RAG — "relationships" and "how tables connect" are the
    # semantic hooks, "schema overview" is jargon that doesn't.
    out = render_overview("syntec", [_meta("customers")])
    assert out.startswith("# Syntec database — relationships and how tables connect")


def test_overview_humanises_underscored_database_name():
    out = render_overview("syntec_crm", [_meta("customers")])
    assert out.startswith("# Syntec crm database — relationships and how tables connect")


def test_overview_groups_tables_by_name_prefix():
    tables = [
        _meta("core_role"),
        _meta("core_user"),
        _meta("crm_lead", "core_user"),
        _meta("customers"),
    ]
    out = render_overview("syntec", tables)
    assert "## core" in out
    assert "## crm" in out
    # No `_` → goes into (misc).
    assert "## (misc)" in out
    # core section lists both core_* tables, crm section lists crm_* table.
    core_idx = out.index("## core")
    crm_idx = out.index("## crm")
    misc_idx = out.index("## (misc)")
    assert core_idx < crm_idx < misc_idx
    core_block = out[core_idx:crm_idx]
    assert "- core_role" in core_block
    assert "- core_user" in core_block


def test_overview_renders_outgoing_arrow():
    tables = [
        _meta("core_user_role", "core_role", "core_user"),
        _meta("core_role"),
        _meta("core_user"),
    ]
    out = render_overview("db", tables)
    # The composite table has outgoing FKs shown after an arrow.
    assert "- core_user_role → core_role, core_user" in out
    # The leaf tables have no arrow.
    assert "- core_role\n" in out
    assert "- core_user\n" in out


def test_overview_deduplicates_outgoing_targets():
    # A multi-column FK to the same table should appear once.
    t = TableMetadata(
        name="join_table",
        comment="",
        columns=[Column(name="id", type="int", comment="", is_pk=True)],
        outgoing=[
            Relation(from_table="join_table", from_column="a_id",
                     to_table="parent", to_column="id"),
            Relation(from_table="join_table", from_column="b_id",
                     to_table="parent", to_column="id"),
        ],
        incoming=[],
    )
    out = render_overview("db", [t])
    assert "- join_table → parent\n" in out
    # parent appears once in the arrow list.
    assert out.count("parent") == 1


def test_overview_misc_group_is_last():
    tables = [_meta("customers"), _meta("audit_logs"), _meta("crm_lead")]
    out = render_overview("db", tables)
    # Both prefixed groups come before (misc).
    assert out.index("## audit") < out.index("## (misc)")
    assert out.index("## crm") < out.index("## (misc)")


def test_overview_with_no_tables():
    out = render_overview("db", [])
    # Still emits the header and a hint, but no group sections.
    assert "# Db database — relationships and how tables connect" in out
    assert "##" not in out
