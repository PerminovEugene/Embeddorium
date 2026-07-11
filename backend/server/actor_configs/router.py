"""Read-only metadata endpoint for actor strategy plugins (``/actor-configs``).

Lists, per plugin-backed actor, every strategy discovered under
``backend/plugins/<actor>`` so the UI can render each actor's strategy picker
and the selected strategy's settings form in one fetch. No DB access — it only
reads the in-process plugin registries.

Generalises the existing ``/chunkers`` endpoint to every actor; ``/chunkers``
stays for the chunk_document-only consumer, and ``chunk_document`` is also
included here (its "strategies" are the discovered chunkers) so the pipeline
form has a single source of truth.

GET /actor-configs — list every plugin-backed actor's strategy configs.
"""

from __future__ import annotations

from typing import Callable, List

from fastapi import APIRouter

from backend.plugins.chunkers.registry import list_chunker_configs
from backend.plugins.embed_chunks.registry import list_embed_strategy_configs
from backend.plugins.fetch_source.registry import list_fetch_strategy_configs
from backend.plugins.filter_documents.registry import list_filter_strategy_configs
from backend.plugins.parse_source.registry import list_parse_strategy_configs
from backend.plugins.validate_source.registry import list_validation_strategy_configs
from backend.server.actor_configs.schemas import (
    ActorConfigOut,
    strategy_config_to_out,
)

router = APIRouter(prefix="/actor-configs", tags=["actor-configs"])

# Actor key -> its strategy-config lister, in pipeline order. The actor keys
# match the ``PipelineActorConfigs`` snapshot keys the create endpoint reads,
# so the UI can send each actor's settings straight back under the same key.
_ACTOR_LISTERS: list[tuple[str, Callable[[], list]]] = [
    ("validate_source", list_validation_strategy_configs),
    ("fetch_source", list_fetch_strategy_configs),
    ("parse_source", list_parse_strategy_configs),
    ("filter_documents", list_filter_strategy_configs),
    ("chunk_document", list_chunker_configs),
    ("embed_chunks", list_embed_strategy_configs),
]


@router.get("", response_model=List[ActorConfigOut], response_model_by_alias=True)
async def list_actor_configs() -> List[ActorConfigOut]:
    """List every plugin-backed actor's discovered strategy configs."""
    return [
        ActorConfigOut(
            actor=actor,
            strategies=[strategy_config_to_out(cfg) for cfg in lister()],
        )
        for actor, lister in _ACTOR_LISTERS
    ]
