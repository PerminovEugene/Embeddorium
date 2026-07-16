from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

# The capability a provider's model serves. A provider is not always an
# embedder: ``text``/``long-text`` are chat/completion models, ``reranker`` and
# ``cross-encoder`` re-score candidate pairs. The embed_chunks actor requires an
# ``embedding`` provider; other consumers pick by the capability they need.
ModelType = Literal["embedding", "text", "long-text", "reranker", "cross-encoder"]


class Provider(BaseModel):
    """A configured model provider (Ollama, OpenAI, mock, ...).

    The provider is a single, flat record: ``provider_type`` is the name of the
    provider-type *adapter* (``backend/plugins/provider_types/<name>.py``) that
    knows how to talk to it, ``model_type`` is the capability the model serves,
    and every type-specific setting (port, url, api_key, model_name, ...) lives
    in the ``config`` jsonb blob, validated against the selected adapter's
    declared ``fields``. This replaces the former discriminated union of one
    Pydantic subclass per provider type — adding a new provider type is now a
    new adapter module, with no change to this model.
    """

    id: uuid.UUID | None = None
    name: str
    # Adapter name (registry key): "ollama" | "mock" | "openai" | ...
    provider_type: str
    model_type: ModelType
    # Type-specific settings, resolved against the adapter's field defaults.
    config: dict[str, Any] = Field(default_factory=dict)

    created_at: datetime | None = None
