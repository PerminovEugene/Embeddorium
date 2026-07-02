"""The chunker plugin interface.

A "chunker" turns one document's text (and, for structure-aware chunkers,
its raw fetched content) into a list of :class:`Chunk` objects. All the
boilerplate a naive implementation would otherwise duplicate — loading the
source text off disk, extracting markdown links, building/upserting
``DocumentChunk`` rows, publishing the outbox event — lives in the
``chunk_document`` actor instead, so a chunker plugin is a near-pure
function: ``ChunkInput -> list[Chunk]``.

Link extraction in particular is *not* a chunker concern: the actor runs
:class:`~backend.shared.parsers.link_extractor.LinkExtractor` over each
returned chunk's text after the fact. That is why :class:`Chunk` here has no
``links`` field, unlike the older
:class:`backend.shared.parsers.text_splitter.Chunk` it superficially
resembles — the two are intentionally kept separate (see that module's
docstring) rather than unified, so the legacy ``TextSplitter``/
``LegalXmlChunker`` stack and its existing tests are untouched.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, List, Optional


@dataclass
class Chunk:
    """One chunk of a document, as produced by a chunker plugin.

    ``chunk_type`` defaults to the generic searchable "passage" type; a
    structure-aware chunker (e.g. ``legal_xml``) may emit other types
    (``legal_body``, ``act_title``, ...) via ``metadata``/``chunk_type`` so
    downstream retrieval can distinguish them.
    """

    text: str
    chunk_type: str = "passage"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChunkInput:
    """Everything a chunker needs to split one document.

    ``text`` is the normalised, already-parsed markdown text (what most
    chunkers operate on). ``raw_content`` is the original fetched content as
    text (e.g. raw XML) for chunkers that need the un-flattened structure;
    it is ``None`` when unavailable, and structure-aware chunkers must fall
    back to ``text`` in that case rather than erroring.
    """

    text: str
    raw_content: Optional[str] = None
    source_url: str = ""
    language: str = "en"
    content_type: Optional[str] = None


@dataclass
class ChunkerField:
    """One UI-configurable setting exposed by a chunker plugin.

    ``key`` is the exact snake_case key the value is stored/read under in
    ``ChunkDocumentSettings.settings`` — it is never transformed, even
    though the API layer camelCases every other JSON object key when
    serving :class:`ChunkerConfig` to the frontend.
    """

    key: str
    label: str
    # One of "text" | "number" | "checkbox" | "select".
    type: str
    default: Any
    min: Optional[int] = None
    max: Optional[int] = None
    options: Optional[List[Dict[str, Any]]] = None
    placeholder: Optional[str] = None


@dataclass
class ChunkerConfig:
    """Static, UI-facing description of a chunker plugin.

    Discovered once per process and served verbatim (camelCased) by
    ``GET /chunkers``; ``name`` is the stable id stored in
    ``ChunkDocumentSettings.chunker`` and used to look the class up again via
    :func:`backend.plugins.chunkers.registry.get_chunker_class`.
    """

    name: str
    label: str
    description: str
    restrictions: str = ""
    fields: List[ChunkerField] = field(default_factory=list)


class Chunker(ABC):
    """Base class every chunker plugin subclasses.

    Subclasses set a class-level ``config`` (a :class:`ChunkerConfig`) and
    implement :meth:`chunk`. ``__init__`` resolves the raw ``settings`` dict
    (as stored in ``ChunkDocumentSettings.settings``) against ``config
    .fields``, falling back to each field's declared default for any key the
    caller omitted — subclasses read resolved values via :meth:`_get` (or
    ``self.settings`` directly) instead of re-implementing default handling.
    """

    config: ClassVar[ChunkerConfig]

    def __init__(self, settings: Dict[str, Any]) -> None:
        settings = settings or {}
        self.settings: Dict[str, Any] = {
            f.key: settings.get(f.key, f.default) for f in self.config.fields
        }

    def _get(self, key: str) -> Any:
        """Return the resolved value for a declared field key."""
        return self.settings[key]

    @abstractmethod
    def chunk(self, ctx: ChunkInput) -> List[Chunk]:
        """Split *ctx* into chunks. Must not raise on empty/whitespace text —
        return ``[]`` instead."""
        raise NotImplementedError
