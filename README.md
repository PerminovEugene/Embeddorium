# Laws Agent

A Python agent for fetching, parsing, embedding, and querying legislative documents.

## Project structure

```
laws_agent/
    config.py           # env-based configuration
    parsers/
        html_parser.py      # HTML → Markdown via trafilatura
        link_extractor.py   # Markdown link extraction
        text_splitter.py    # Markdown chunking via LangChain
    clients/
        hg_client.py        # HuggingFace Hub login + model loading
        llm_client.py       # Text generation + embedding client
    storage/
        vector_store.py     # Qdrant vector store wrapper
main.py                 # Entry point
```

## Setup

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your tokens:

```sh
cp .env.example .env
```

```ini
HG_TOKEN=your_huggingface_token
```

## Run

```sh
source .venv/bin/activate
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
