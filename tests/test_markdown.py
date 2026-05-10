from db_structure_downloader.db import Column, Relation, TableMetadata
from db_structure_downloader.markdown import render


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
        "| kvk_number | varchar(8) | kvk_number |\n"
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


def test_id_suffix_without_relation_falls_back_to_column_name():
    # An *_id column that is NOT a real FK (no INFORMATION_SCHEMA row) must
    # not be labelled as a foreign key — fall through to the column name.
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
    assert "| external_id | varchar(64) | external_id |" in result


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


def test_default_fallback_uses_column_name():
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
    assert "| message | text | message |" in result


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
    assert result.endswith("| message | text | message |\n")


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
