# Add custom actor configuration

The safest complete example is a custom `chunk_document` strategy because the
pipeline form exposes chunkers as a user-selectable plugin list. Other
plugin-backed actors publish field metadata too, but their strategy choice is
currently fixed by source type or actor in the frontend.

## 1. Add a chunker module

Create `backend/plugins/chunkers/double_newline.py`:

```python
from backend.plugins._fields import FieldSpec
from backend.plugins.chunkers.base import Chunk, Chunker, ChunkerConfig, ChunkInput


class DoubleNewlineChunker(Chunker):
    config = ChunkerConfig(
        name="double_newline",
        label="Double newline",
        description="Splits text at blank lines.",
        fields=[
            FieldSpec(
                key="min_chars",
                label="Minimum characters",
                type="number",
                default=200,
                min=1,
            )
        ],
    )

    def chunk(self, ctx: ChunkInput) -> list[Chunk]:
        if not ctx.text.strip():
            return []
        minimum = int(self._get("min_chars"))
        output: list[Chunk] = []
        buffer = ""
        for paragraph in ctx.text.split("\n\n"):
            buffer = f"{buffer}\n\n{paragraph}" if buffer else paragraph
            if len(buffer) >= minimum:
                output.append(Chunk(text=buffer))
                buffer = ""
        if buffer:
            output.append(Chunk(text=buffer))
        return output
```

The `FieldSpec.key` is stored verbatim under
`actor_configs.chunk_document.settings`; use snake_case and read the resolved
value through `self._get`.

## 2. Restart discovery consumers

Restart `server` and `worker-chunk-document`. Registries cache discovery for the
life of each process.

## 3. Verify metadata and behavior

```sh
curl -sS http://localhost:8000/chunkers
.venv/bin/python -m pytest backend/tests/plugins/chunkers -q
```

Add a focused test that instantiates the class and calls `chunk(ChunkInput(...))`.
No DB or broker is required for that unit test.

Chunkers must return `[]` for empty input. They should not persist data, publish
messages, or extract links; the actor owns those operations.
