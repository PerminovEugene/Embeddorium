# Laws Agent

A Python agent for fetching, parsing, embedding, and querying legislative documents.

## Project structure

```
laws_agent/
    config.py               # env-based configuration (single source of truth)
    parsers/
        html_parser.py      # HTML → Markdown via trafilatura
        link_extractor.py   # Markdown link extraction
        text_splitter.py    # Markdown chunking via LangChain
    clients/
        hg_client.py        # HuggingFace Hub login + model loading
        llm_client.py       # Text generation + embedding client
    models/
        document.py         # Document Pydantic model
        document_chunk.py   # DocumentChunk Pydantic model
    storage/
        sql_store.py        # PostgreSQL ORM models + repository (SQLAlchemy)
        vector_store.py     # Qdrant vector store wrapper
        migrations/
            001_create_documents.sql
            002_create_document_chunks.sql
main.py                     # Indexing entry point
migrate.py                  # Migration runner
```

## Setup

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your values:

```sh
cp .env.example .env
```

| Variable            | Required | Default                 | Description              |
| ------------------- | -------- | ----------------------- | ------------------------ |
| `HG_TOKEN`          | yes      | —                       | HuggingFace API token    |
| `POSTGRES_USER`     | yes      | —                       | PostgreSQL user          |
| `POSTGRES_PASSWORD` | yes      | —                       | PostgreSQL password      |
| `POSTGRES_DB`       | yes      | —                       | PostgreSQL database name |
| `POSTGRES_HOST`     | no       | `localhost`             | PostgreSQL host          |
| `POSTGRES_PORT`     | no       | `5432`                  | PostgreSQL port          |
| `QDRANT_URL`        | no       | `http://localhost:6333` | Qdrant instance URL      |

## Run

Apply migrations first, then run the indexer:

```sh
python migrate.py
python main.py
```

## Dependency management

```sh
# Add a package
pip install <package>
pip freeze > requirements.txt

# Remove a package
pip uninstall <package>
pip freeze > requirements.txt
```

---

## Code style & best practices

This project follows [PEP 8](https://peps.python.org/pep-0008/) and standard Python conventions.

### Formatting & linting

Use [Ruff](https://docs.astral.sh/ruff/) as a single tool for both linting and formatting:

```sh
pip install ruff
ruff check .          # lint
ruff format .         # format (replaces Black)
```

### PEP 8 compliance check

```sh
pip install pycodestyle
pycodestyle .
```

## Local dev

1. for management qdarnt - http://0.0.0.0:6333/dashboard
2. for management psql -
