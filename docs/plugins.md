# Plugins

The `chunk_document` pipeline stage is pluggable: chunking strategies live as
small, self-contained plugins under `backend/plugins/chunkers/` and are
auto-discovered at process start — no registration step, no editing of the
actor. Drop a file (or a subpackage) in that directory, implement one class,
and it shows up in `GET /chunkers` and becomes selectable for any run.

This is currently the only plugin kind, but the surrounding
`backend/plugins/` package is deliberately generic so other plugin kinds
(parsers, filters, ...) have an obvious place to land later.

## The mental model

A chunker plugin is a **near-pure function**: given a document's text (and,
optionally, its raw fetched content), return a list of chunks. Everything
else — reading the parsed text and raw content off disk, extracting markdown
links out of each chunk, building and upserting `DocumentChunk` rows,
advancing the crawl target's status, publishing the outbox event that
triggers embedding — is boilerplate the `chunk_document` actor handles for
every chunker, so plugin authors never touch it.

```
ChunkInput  ──►  YourChunker.chunk(ctx)  ──►  list[Chunk]  ──►  (actor persists + extracts links)
```

## The interface

Everything a plugin needs is in
[`backend/plugins/chunkers/base.py`](../backend/plugins/chunkers/base.py):

```python
@dataclass
class ChunkInput:
    text: str                          # parsed markdown/plain text
    raw_content: Optional[str] = None  # raw fetched content (e.g. XML), if any
    source_url: str = ""
    language: str = "en"
    content_type: Optional[str] = None


@dataclass
class Chunk:
    text: str
    chunk_type: str = "passage"        # "passage" unless your chunker has real types
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChunkerField:
    key: str            # snake_case; this is the exact key used in `settings`
    label: str           # UI label
    type: str            # "text" | "number" | "checkbox" | "select"
    default: Any
    min: Optional[int] = None
    max: Optional[int] = None
    options: Optional[List[Dict[str, Any]]] = None   # for type="select"
    placeholder: Optional[str] = None


@dataclass
class ChunkerConfig:
    name: str             # unique, snake_case id — e.g. "text_markdown"
    label: str            # UI display name
    description: str
    restrictions: str = ""            # free text, e.g. "Requires raw XML content"
    fields: List[ChunkerField] = field(default_factory=list)


class Chunker(ABC):
    config: ClassVar[ChunkerConfig]

    def __init__(self, settings: Dict[str, Any]) -> None: ...   # resolves settings vs. field defaults

    @abstractmethod
    def chunk(self, ctx: ChunkInput) -> List[Chunk]: ...
```

`Chunk` here intentionally has **no `links` field** — link extraction is not
a chunker's job. The actor runs `LinkExtractor` over each returned chunk's
text after your `chunk()` call returns, so you don't need to think about
links at all.

## Writing a chunker

1. Create a module (or subpackage) under `backend/plugins/chunkers/`, e.g.
   `backend/plugins/chunkers/my_chunker.py`.
2. Subclass `Chunker`, set a class-level `config`, and implement `chunk()`.

```python
# backend/plugins/chunkers/my_chunker.py
from __future__ import annotations

from typing import List

from backend.plugins.chunkers.base import Chunk, Chunker, ChunkerConfig, ChunkerField, ChunkInput


class DoubleNewlineChunker(Chunker):
    """Splits on blank lines; merges paragraphs shorter than `min_chars`."""

    config = ChunkerConfig(
        name="double_newline",
        label="Double newline",
        description="Splits on blank lines, merging short paragraphs together.",
        fields=[
            ChunkerField(
                key="min_chars", label="Minimum chunk length",
                type="number", default=200, min=0,
            ),
        ],
    )

    def chunk(self, ctx: ChunkInput) -> List[Chunk]:
        if not ctx.text:
            return []

        min_chars = int(self._get("min_chars"))
        paragraphs = [p.strip() for p in ctx.text.split("\n\n") if p.strip()]

        chunks: List[Chunk] = []
        buffer = ""
        for paragraph in paragraphs:
            buffer = f"{buffer}\n\n{paragraph}" if buffer else paragraph
            if len(buffer) >= min_chars:
                chunks.append(Chunk(text=buffer))
                buffer = ""
        if buffer:
            chunks.append(Chunk(text=buffer))
        return chunks
```

That's it — no registration. The next time the process (or worker) starts,
`GET /chunkers` includes `double_newline`, and any pipeline run can select it
via `actorSettings.chunk_document = {"chunker": "double_newline", "settings":
{"min_chars": 400}}`.

### Rules of thumb

- **Return `[]` for empty/whitespace input** — don't raise.
- **Read settings via `self._get(key)`** (or `self.settings[key]`) — never
  read the raw `settings` dict passed to `__init__` yourself; `Chunker
  .__init__` already resolves it against `config.fields`, filling in each
  field's `default` for any key the caller omitted.
- **`ctx.raw_content` may be `None`.** Only structure-aware chunkers (parsing
  XML/HTML, say) need it; if yours does and the content isn't there or
  doesn't parse, fall back to splitting `ctx.text` instead of raising — see
  `legal_xml.py` for the reference pattern (it falls back to the markdown
  chunker).
- **`chunk_type`/`metadata` are optional.** Leave them at their defaults
  (`"passage"` / `{}`) unless your chunker has genuinely distinct chunk
  kinds worth surfacing to retrieval (the way `legal_xml` emits
  `legal_body`/`act_title`/`amendment_history`/`legal_metadata`).
- **A plugin that fails to import doesn't take down the others.** Discovery
  logs a warning and skips it, so a bad dependency or syntax error in your
  plugin degrades gracefully rather than breaking `GET /chunkers` or the
  worker for everyone else.

### Subpackages

For a chunker with real internals (multiple files, its own tests fixtures,
etc.), use a subpackage instead of a single module:

```
backend/plugins/chunkers/my_chunker/
  __init__.py
  chunker.py     # defines MyChunker(Chunker)
  helpers.py
```

Discovery (`backend.plugins.chunkers.registry`) walks every module *and*
subpackage under `backend/plugins/chunkers/` (`pkgutil.walk_packages`), so
`my_chunker/chunker.py` is found the same way a flat module would be —
nothing extra to wire up.

## How it's used end to end

- `GET /chunkers` (`backend/server/chunkers_routes.py`) lists every
  discovered chunker's `ChunkerConfig`, camelCased for the UI — this is what
  powers the chunker picker and its settings form.
- A pipeline run's `actor_configs.chunk_document` stores the choice as
  `{"chunker": "<name>", "settings": {...}}` (see `ChunkDocumentSettings` in
  `backend/shared/models/pipeline_run.py`); `settings` is stored **verbatim**
  — its keys are exactly the `ChunkerField.key`s your plugin declared.
- The `chunk_document` actor's launcher
  (`backend/actors/chunk_document_actor/launcher.py`) reads that block from
  the run, builds your chunker once via `registry.build_chunker(name,
  settings)`, and caches the instance per `(name, settings)` so it isn't
  rebuilt on every message.
- `chunk_document`'s handler (`backend/actors/chunk_document_actor/handler.py`)
  builds the `ChunkInput`, calls `chunker.chunk(ctx)`, extracts links from
  each returned chunk's text, and persists everything.

## Testing a plugin

Chunkers are plain Python objects — instantiate and call `chunk()` directly,
no DB or broker needed:

```python
from backend.plugins.chunkers.my_chunker import DoubleNewlineChunker
from backend.plugins.chunkers.base import ChunkInput

def test_splits_on_blank_lines():
    chunker = DoubleNewlineChunker({"min_chars": 10})
    chunks = chunker.chunk(ChunkInput(text="Short.\n\nAlso short.\n\nLong enough now."))
    assert len(chunks) >= 1
```

See `backend/tests/plugins/chunkers/` for the tests covering the built-in
chunkers, and `backend/tests/server/test_chunkers_routes.py` for the
`GET /chunkers` contract.

## Built-in chunkers

| Name                  | What it does                                                              | Configurable fields                     |
| --------------------- | -------------------------------------------------------------------------- | ---------------------------------------- |
| `text_markdown`       | Size-based split along markdown-aware boundaries. **Default.**             | `chunk_size`, `chunk_overlap`            |
| `text_section`        | Splits on `#`/`##`/`###` headers; falls back to paragraphs if none exist.  | — |
| `text_recursive`      | Recursively tries paragraph/line/word/character separators to hit a size target. | `chunk_size`, `chunk_overlap`      |
| `text_fixed`          | Fixed-size character chunks, no structure awareness.                       | `chunk_size`, `chunk_overlap`            |
| `text_sentence`       | Packs whole sentences into chunks up to the target size — never cuts a sentence in half. | `chunk_size`, `chunk_overlap` |
| `text_sliding_window` | Overlapping windows of whole words; the window advances by `step_size` words. | `window_size`, `step_size`            |
| `legal_xml`           | One chunk per `§` for Estonian Juurakt-format act XML; falls back to `text_markdown` for non-act content. | `target_tokens`, `max_tokens`, `min_tokens` |
