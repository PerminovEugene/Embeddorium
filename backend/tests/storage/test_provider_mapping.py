"""ORM -> domain mapping for generic providers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from backend.shared.models import Provider
from backend.shared.storage.sql.model_to_dto import _to_provider
from backend.shared.storage.sql.models.provider import ProviderORM


def test_to_provider_maps_jsonb_config() -> None:
    orm = ProviderORM(
        id=uuid.uuid4(),
        name="ol",
        provider_type="ollama",
        model_type="embedding",
        config={"model_name": "nomic-embed-text"},
        created_at=datetime.now(UTC),
    )

    provider = _to_provider(orm)

    assert isinstance(provider, Provider)
    assert provider.provider_type == "ollama"
    assert provider.config == {"model_name": "nomic-embed-text"}
    assert provider.id == orm.id
