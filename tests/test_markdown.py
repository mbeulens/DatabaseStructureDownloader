from db_structure_downloader.db import Column, Relation, TableMetadata
from db_structure_downloader.markdown import render


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
        "| id | char(36) | PK |\n"
        "| name | varchar(200) | Legal name |\n"
        "| kvk_number | varchar(8) | _TODO_ |\n"
        "\n"
        "**Relations:**\n"
        "- `contacts.customer_id → customers.id`\n"
        "- `engagements.customer_id → customers.id`\n"
    )

    assert render(table) == expected
