# Plugins

Every **configurable** pipeline stage in Embeddorium is pluggable. The
per-stage behaviour a user can pick and tune — how a source is validated, how
it's fetched, how it's parsed, how documents are filtered, how text is chunked,
how chunks are embedded — lives as small, self-contained **strategy plugins**
under `backend/plugins/<actor>/`. They are auto-discovered at process start:
drop a module in the right directory, implement one class, and it shows up in
the API and becomes selectable for any run — no registration, no editing of the
actor.

The plugin surface exists so that (a) the web UI can render each stage's
options and settings form entirely from backend metadata, and (b) new
strategies can be added without touching the pipeline plumbing.

## The mental model

An actor is split in two:

- **The actor** (`backend/actors/<actor>/`) owns all the plumbing that's the
  same for every strategy: acquiring and locking the crawl target, reading and
  writing artefacts on disk, status transitions, persisting rows, and
  publishing the outbox event that triggers the next stage.
- **The strategy plugin** (`backend/plugins/<actor>/`) owns only the part that
  varies — ideally a **near-pure function**. The actor calls it and does
  everything else.

```
raw input ──►  strategy.<method>(...)  ──►  result  ──►  (actor persists + advances the pipeline)
```

### Which actors are plugin-backed

| Actor              | Plugin package                    | Strategy contract (near-pure function) |
| ------------------ | --------------------------------- | -------------------------------------- |
| `validate_source`  | `backend/plugins/validate_source` | seed value → canonical identity + admissibility |
| `fetch_source`     | `backend/plugins/fetch_source`    | target → raw fetched content + next-stage routing |
| `parse_source`     | `backend/plugins/parse_source`    | `(raw, content_type)` → normalized text |
| `filter_documents` | `backend/plugins/filter_documents`| `(title, text)` → keep/skip predicate |
| `chunk_document`   | `backend/plugins/chunkers`        | document text → `list[Chunk]` |
| `embed_chunks`     | `backend/plugins/embed_chunks`    | provider snapshot → concrete embed target |

The remaining actors (`schedule_embeddings`, `schedule_discovered_links`,
`track_pipeline_status`) are pure plumbing with nothing for a user to
configure, so they are intentionally **not** pluggable.

## Anatomy of a plugin package

Every package follows the same layout (`chunkers` is the historical outlier —
same shape, slightly different names):

```
backend/plugins/<actor>/
  __init__.py     # package docstring; explains the plugin surface
  base.py         # the ABC + its *StrategyConfig + any typed context/result/error types
  registry.py     # discovery + lookup: list_*_configs / get_*_class / build_*
  <strategy>.py   # one concrete strategy per module (e.g. web.py, local_file.py)
```

Two shared building blocks live one level up, in `backend/plugins/`:

- **`_fields.py` — `FieldSpec`**: the single field-descriptor dataclass every
  plugin kind reuses to declare a configurable setting for the UI.
- **`_strategy_discovery.py` — `discover_strategies()`**: the shared discovery
  walker used by every registry.

### `base.py` — the interface

Each `base.py` defines an abstract base class and a frozen `*StrategyConfig`
dataclass. Every config has the **same shape** — this is what lets one API
schema serve all of them:

```python
@dataclass(frozen=True)
class ParseStrategyConfig:          # …FetchStrategyConfig, EmbedStrategyConfig, etc.
    name: str                       # unique, stable id — the registry key + stored run value
    label: str                      # UI display name
    description: str                # UI help text
    fields: list[FieldSpec] = field(default_factory=list)   # the settings form


class ParseStrategy(ABC):
    config: ClassVar[ParseStrategyConfig]

    @abstractmethod
    def parse(self, *, raw: str, content_type: str | None, final_url: str) -> str | None:
        ...
```

`ChunkerConfig` additionally carries a free-text `restrictions` field; the API
treats it as optional so the shared schema still fits.

### How settings reach a strategy

There are two flavours, and the difference is worth understanding:

- **Settings-resolved strategies** (`chunkers`, `parse_source`,
  `filter_documents`, `embed_chunks`). The base class `__init__(settings)`
  resolves the raw `settings` dict against `config.fields`, filling in each
  field's `default` for any missing key. Subclasses read values via
  `self._get(key)` and never touch the raw dict. The registry's `build_*(name,
  settings)` instantiates with settings.

- **Context-passed strategies** (`fetch_source`, `validate_source`). These are
  **stateless** — `build_*(name)` takes no settings. The typed settings model
  (`FetchSourceSettings`, `ValidateSourceSettings`) is handed to the strategy
  per call via a context object or keyword argument (`ctx.settings`,
  `settings=`). Their `config.fields` still exist, but purely to describe the
  form to the UI; the actor reads the values off the typed model itself.

Either way, `fields` is the single source of truth for **what** is
configurable; the two flavours only differ in **how** the resolved values are
delivered to the code.

### How a strategy is selected

The actor decides which strategy name to build:

- `fetch_source` / `validate_source` select by the dataset's **`source_type`**
  (`"web"` or `"local"`) — the strategy's `config.name` *is* the source type.
- `parse_source` / `filter_documents` / `embed_chunks` have a single built-in
  strategy, selected by a module-level `DEFAULT_*_STRATEGY` constant.
- `chunk_document` is the only stage where the **user** picks the strategy from
  many (the chunker picker); the choice is stored on the run.

## FieldSpec and the UI

`FieldSpec` (`backend/plugins/_fields.py`) describes one configurable setting:

```python
@dataclass
class FieldSpec:
    key: str                 # exact snake_case storage key — never transformed
    label: str
    type: str                # "text" | "number" | "checkbox" | "select" | "provider_id"
    default: Any
    min: Optional[int] = None
    max: Optional[int] = None
    options: Optional[List[Dict[str, Any]]] = None   # for type="select"
    placeholder: Optional[str] = None
    required: bool = False
```

Two endpoints expose these configs to the frontend:

- **`GET /actor-configs`** (`backend/server/actor_configs/router.py`) — the
  single source of truth. Returns, per plugin-backed actor, every discovered
  strategy plus its `fields`, camelCased for the UI. The ingestion-pipeline
  form builds each stage's strategy picker and settings form entirely from this
  response.
- **`GET /chunkers`** (`backend/server/chunkers/router.py`) — the original
  chunker-only endpoint, kept for backward compatibility. The UI no longer
  calls it (chunkers now arrive via `/actor-configs` as `chunk_document`'s
  strategies).

Two rules make the round trip work:

- **Object keys are camelCased on the wire, but a field's `key` *value* stays
  snake_case.** The UI sends the value straight back under that exact key, so
  it lands verbatim in the stored settings (e.g. `chunk_size`, `verify_tls`).
- **`type="provider_id"`** tells the UI to render a picker over the configured
  embedding providers; run-creation materialises the picked id into the stored
  provider snapshot. This is how `embed_chunks` gets its required `provider`
  field.

## Discovery and registries

### Libraries

Discovery uses the **Python standard library only** — no third-party plugin
framework (no setuptools entry points, no `pluggy`):

- `pkgutil.walk_packages` — enumerate every module *and* subpackage under the
  plugin package.
- `importlib.import_module` — import each one.
- `inspect` — find concrete (non-abstract) subclasses of the package's base
  class that declare a `config`.
- `dataclasses`, `abc`, `logging` — the config/interface types and warnings.

`backend/plugins/_strategy_discovery.py` implements this once as
`discover_strategies(package, base_cls) -> {config.name: strategy_class}`, and
every registry calls it. (`chunkers/registry.py` predates the shared helper and
carries an equivalent private `_discover`.)

### Why a registry at all

The registry is the thin indirection layer between "a class in a file" and
"the actor / API". It buys:

- **Zero-registration discovery** — no hand-maintained list to keep in sync.
- **A shared entry point** — the actor and the API both go through
  `list_*_configs()` / `get_*_class(name)` / `build_*(...)`, so there's one
  place that knows how to find and instantiate a strategy.
- **Caching** — discovery runs once per process and is memoised in a module
  `_cache`; lookups afterward are dict hits.
- **Graceful degradation** — a plugin that fails to import (bad dependency,
  syntax error) is logged and skipped, not fatal. One broken plugin never
  takes down the endpoint or the worker for the others.
- **Stable string ids** — runs store a strategy by `config.name`, decoupling
  persisted config from where the class actually lives, so internals can be
  refactored freely.

If two strategies claim the same `name`, the first one discovered wins and a
warning is logged.

## End to end: how a run uses a plugin

1. **Configure.** The UI reads `/actor-configs`, renders the form, and submits
   per-actor settings. Run-creation
   (`backend/server/pipeline/router.py`) resolves them into the typed
   `PipelineActorConfigs` snapshot stored on the run (see
   `backend/shared/models/pipeline_run.py`). `chunk_document` is stored as
   `{"chunker": "<name>", "settings": {...}}`; `embed_chunks` stores the picked
   provider's full snapshot under `provider`.
2. **Run.** When the stage's actor processes a message, it loads its settings
   block from the run, asks the registry to `build_*` the right strategy, calls
   the strategy's one method, and handles the result — persisting output and
   publishing the next outbox event. For example
   `fetch_source_actor/handler.py` does `build_fetch_strategy(source_type)` →
   `strategy.fetch(...)` → `strategy.next_outbox_event(...)`, and
   `chunk_document_actor/launcher.py` caches the built chunker per
   `(name, settings)` so it isn't rebuilt on every message.

## Adding a strategy to an existing actor

The worked example below is a chunker (the richest, user-selectable case); the
other actors follow the same three steps against their own base class.

1. Create a module (or subpackage) under the actor's plugin directory, e.g.
   `backend/plugins/chunkers/double_newline.py`.
2. Subclass the base class, set a class-level `config`, implement the abstract
   method.
3. Restart the server/worker — discovery picks it up.

```python
# backend/plugins/chunkers/double_newline.py
from __future__ import annotations

from typing import List

from backend.plugins._fields import FieldSpec
from backend.plugins.chunkers.base import Chunk, Chunker, ChunkerConfig, ChunkInput


class DoubleNewlineChunker(Chunker):
    """Splits on blank lines; merges paragraphs shorter than `min_chars`."""

    config = ChunkerConfig(
        name="double_newline",
        label="Double newline",
        description="Splits on blank lines, merging short paragraphs together.",
        fields=[
            FieldSpec(key="min_chars", label="Minimum chunk length",
                      type="number", default=200, min=0),
        ],
    )

    def chunk(self, ctx: ChunkInput) -> List[Chunk]:
        if not ctx.text:
            return []                       # return [] for empty input; never raise

        min_chars = int(self._get("min_chars"))     # read settings via _get
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

That's it — no registration. On the next process start, `/actor-configs`
includes `double_newline` under `chunk_document`, and a run can select it via
`actorSettings.chunk_document = {"chunker": "double_newline", "settings":
{"min_chars": 400}}`.

### Rules of thumb

- **Keep the strategy near-pure.** No DB writes, no broker, no disk I/O the
  actor already does. If you find yourself needing those, it probably belongs
  in the actor.
- **Read settings only via `self._get(key)`** (settings-resolved strategies) —
  never re-read the raw dict; `__init__` already applied field defaults.
- **Fail soft where the contract says so.** Chunkers return `[]` for empty
  input; `parse_source` returns `None` when nothing supports the content
  (the actor then marks the target `SKIPPED_UNSUPPORTED`).
- **Keep top-level imports cheap.** Discovery imports every plugin at startup;
  a heavy import slows the whole process. Import optional/heavy dependencies
  lazily inside the method.
- **`ctx.raw_content` may be `None`** (chunkers). Only structure-aware chunkers
  need it; fall back to `ctx.text` rather than raising — see `legal_xml.py`.

### Subpackages

For a strategy with real internals (multiple files, fixtures), use a subpackage
instead of a single module. `pkgutil.walk_packages` descends into it, so
`my_strategy/impl.py` is discovered exactly like a flat module:

```
backend/plugins/chunkers/my_chunker/
  __init__.py
  chunker.py     # defines MyChunker(Chunker)
  helpers.py
```

## Adding a brand-new pluggable actor

To make a *new* stage pluggable, mirror an existing package (`fetch_source` is
a good template):

1. **`base.py`** — an ABC with a `config: ClassVar[<Name>StrategyConfig]` and
   one abstract method that captures the varying behaviour. Choose the settings
   flavour (resolved-dict `__init__` vs. context-passed) to match how the actor
   already carries config.
2. **`registry.py`** — a module `_cache`, a `_registry()` that calls
   `discover_strategies(pkg, <Base>)`, and `list_*_configs()` /
   `get_*_class(name)` / `build_*(...)`.
3. **Wire the actor** — have the handler/launcher pick a strategy name, call
   `build_*`, and invoke the method instead of doing the work inline.
4. **Expose it** — add the actor + its `list_*_configs` to the `_ACTOR_LISTERS`
   table in `backend/server/actor_configs/router.py` so the UI can see it.

## Pros and cons

**Pros**

- **Zero-registration extensibility** — a new strategy is one file; it appears
  in the API and the pipeline on restart.
- **Thin, uniform actors** — the same split across six stages lowers cognitive
  load, and strategy logic is isolated.
- **Automatic UI** — add a `FieldSpec` and the settings form renders it with no
  frontend change.
- **Fault isolation** — a broken plugin is logged and skipped, not fatal.
- **Refactor-safe persistence** — runs reference strategies by stable string
  id, not by class path.

**Cons / trade-offs**

- **Restart to pick up changes** — discovery is import-time and cached per
  process; adding/removing a plugin needs a server/worker restart.
- **Import side effects at startup** — every plugin is imported during
  discovery, so a heavy top-level import taxes everyone.
- **Loosely-typed settings** — values are dicts resolved against `fields`; a
  typo'd field `key` silently falls back to the default instead of erroring.
- **Flat, unversioned names** — names are a global namespace per actor; a
  collision is resolved by "first wins" with a warning.
- **Only fits function-shaped variability** — plumbing-heavy stages don't fit
  the model and shouldn't be forced into it.

## Testing a plugin

Strategies are plain Python objects — instantiate and call the method directly,
no DB or broker:

```python
from backend.plugins.chunkers.double_newline import DoubleNewlineChunker
from backend.plugins.chunkers.base import ChunkInput

def test_splits_on_blank_lines():
    chunker = DoubleNewlineChunker({"min_chars": 10})
    chunks = chunker.chunk(ChunkInput(text="Short.\n\nAlso short.\n\nLong enough now."))
    assert len(chunks) >= 1
```

See `backend/tests/plugins/` for per-plugin tests (including registry
discovery), and `backend/tests/server/test_actor_configs_routes.py` /
`test_chunkers_routes.py` for the endpoint contracts.

## Reference: built-in strategies

| Actor              | Strategy       | Selected by       | Configurable fields |
| ------------------ | -------------- | ----------------- | ------------------- |
| `validate_source`  | `web`          | source type       | `normalize_urls`, `dedup` |
|                    | `local`        | source type       | `dedup` |
| `fetch_source`     | `web`          | source type       | `verify_tls`, `timeout_seconds`, `allowed_content_types` |
|                    | `local`        | source type       | `file_glob` |
| `parse_source`     | `content_type` | default           | `parser` (`auto`/`html`/`xml`/`plain`/`pdf`) |
| `filter_documents` | `keyword`      | default           | `enabled`, `keywords` |
| `embed_chunks`     | `standard`     | default           | `provider` (`provider_id`, required) |
| `chunk_document`   | *(see below)*  | **user pick**     | *(per chunker)* |

### Built-in chunkers

| Name                  | What it does                                                              | Configurable fields                     |
| --------------------- | -------------------------------------------------------------------------- | ---------------------------------------- |
| `text_markdown`       | Size-based split along markdown-aware boundaries. **Default.**             | `chunk_size`, `chunk_overlap`            |
| `text_section`        | Splits on `#`/`##`/`###` headers; falls back to paragraphs if none exist.  | — |
| `text_recursive`      | Recursively tries paragraph/line/word/character separators to hit a size target. | `chunk_size`, `chunk_overlap`      |
| `text_fixed`          | Fixed-size character chunks, no structure awareness.                       | `chunk_size`, `chunk_overlap`            |
| `text_sentence`       | Packs whole sentences into chunks up to the target size — never cuts a sentence in half. | `chunk_size`, `chunk_overlap` |
| `text_sliding_window` | Overlapping windows of whole words; the window advances by `step_size` words. | `window_size`, `step_size`            |
| `legal_xml`           | One chunk per `§` for Estonian Juurakt-format act XML; falls back to `text_markdown` for non-act content. | `target_tokens`, `max_tokens`, `min_tokens` |
