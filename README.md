# Database Structure Downloader

A desktop utility that connects to a MySQL server, lets you pick tables from a
GUI, and exports each table's structure as a separate markdown file. The output
is shaped for ingestion into a RAG knowledgebase.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python -m db_structure_downloader
```

## Test

```bash
pytest
```
