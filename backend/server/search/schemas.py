"""Pydantic models for the ``/search`` and ``/searches`` endpoints."""

import uuid
from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class TextItem(BaseModel):
    id: str
    text: str


class TextGroup(BaseModel):
    inputs: List[TextItem]


class SearchRequest(BaseModel):
    # configuration carries: runId (the pipeline run to search — its saved
    # config supplies the Qdrant collection and the embedding provider/model),
    # topK (how many results to return per query; defaults server-side when
    # omitted), and searchMethod — the retrieval strategy: "semantic" (dense
    # vectors, the
    # default and legacy behaviour; "embedding" is accepted as an alias),
    # "keyword" (BM25 sparse), or "hybrid" (dense + BM25 fused via Reciprocal
    # Rank Fusion). Absent falls back to "semantic".
    configuration: dict
    source: TextGroup


class _CamelModel(BaseModel):
    """Base for API schemas: camelCase on the wire, snake_case in Python."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class SearchSummaryOut(_CamelModel):
    """One persisted search launch, without its result hits.

    ``run_name``/``dataset_name`` are joined in from the pipeline run the
    search was executed against; the comparison UI uses them (together with
    ``input_text``) to decide which searches are comparable — only searches
    over the same dataset with the same input text line up meaningfully.
    """

    id: uuid.UUID
    pipeline_id: uuid.UUID
    run_name: str
    dataset_name: str
    input_text: str
    top_k: int | None = None
    search_method: str = ""
    result_count: int
    created_at: datetime | None = None


class SearchDetailOut(SearchSummaryOut):
    """A persisted search including its stored result hits.

    ``results`` is the JSONB list saved by ``_persist_search`` — hits keep the
    order they were returned in (sorted by score at search time), so a hit's
    list index is its rank.
    """

    results: list[dict]
