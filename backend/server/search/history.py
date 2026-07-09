"""Read API over persisted searches (search history).

Every ``/search`` launch is saved to Postgres by ``_persist_search`` (one
``searches`` row per query, referencing its ``search_inputs`` row). This module
exposes that history so the UI's search-comparison page can list past searches
and load the stored results of the ones the user selects.

The searches table stores only ``pipeline_id``/``user_input_id`` foreign keys,
so summaries join in the input text and the run's name/dataset here. Lookups
are cached per request: many searches share the same run and input.
"""

from __future__ import annotations

import uuid

from backend.server.search.schemas import SearchDetailOut, SearchSummaryOut
from backend.shared.models import PipelineRun, Search
from backend.shared.storage.sql.sql_store import SqlStore


def list_searches(limit: int = 100) -> list[SearchSummaryOut]:
    """Return persisted searches, newest first, with run/input info joined in."""
    store = SqlStore(application_name="embeddorium-search-history")
    try:
        searches = store.searches.list_recent(limit=limit)
        input_texts: dict[uuid.UUID, str] = {}
        runs: dict[uuid.UUID, PipelineRun | None] = {}

        summaries: list[SearchSummaryOut] = []
        for search in searches:
            if search.user_input_id not in input_texts:
                search_input = store.search_inputs.get(search.user_input_id)
                input_texts[search.user_input_id] = (
                    search_input.text if search_input else ""
                )
            if search.pipeline_id not in runs:
                runs[search.pipeline_id] = store.pipeline_runs.get(search.pipeline_id)
            summaries.append(
                _summarize(
                    search,
                    input_texts[search.user_input_id],
                    runs[search.pipeline_id],
                )
            )
        return summaries
    finally:
        store.close()


def get_search(search_id: uuid.UUID) -> SearchDetailOut | None:
    """Load one persisted search with its stored results, or ``None``."""
    store = SqlStore(application_name="embeddorium-search-history")
    try:
        search = store.searches.get(search_id)
        if search is None:
            return None
        search_input = store.search_inputs.get(search.user_input_id)
        run = store.pipeline_runs.get(search.pipeline_id)
        summary = _summarize(search, search_input.text if search_input else "", run)
        return SearchDetailOut(
            **summary.model_dump(by_alias=False),
            results=_results_list(search),
        )
    finally:
        store.close()


def _summarize(
    search: Search, input_text: str, run: PipelineRun | None
) -> SearchSummaryOut:
    top_k = search.search_config.get("top_n")
    return SearchSummaryOut(
        id=search.id,
        pipeline_id=search.pipeline_id,
        run_name=(run.name if run else None) or "",
        dataset_name=run.dataset.get("name", "") if run else "",
        input_text=input_text,
        top_k=top_k if isinstance(top_k, int) else None,
        search_method=str(search.search_config.get("search_method", "")),
        result_count=len(_results_list(search)),
        created_at=search.created_at,
    )


def _results_list(search: Search) -> list[dict]:
    """The stored hits as a list (the JSONB column also admits a dict)."""
    return search.results if isinstance(search.results, list) else []
