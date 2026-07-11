"""Web validation strategy: URL normalization + same-origin gate.

This is the behavior of the old crawl_frontier_manager actor: normalize the
URL (unless the run disables it) and reject a discovered child link whose
origin differs from its parent document's origin (or whose parent document no
longer exists). Root seeds (no parent) are always allowed.
"""

from __future__ import annotations

from backend.plugins._fields import FieldSpec
from backend.plugins.validate_source.base import (
    NormalizedSource,
    SourceValidationError,
    SourceValidationStrategy,
    ValidationStrategyConfig,
)
from backend.shared.clients.queue.validate_source_payload import ValidateSourcePayload
from backend.shared.models import ValidateSourceSettings
from backend.shared.pipeline.url_helper import is_allowed_url, normalize_url
from backend.shared.storage.sql.sql_store import SqlStore


class WebSourceValidation(SourceValidationStrategy):
    config = ValidationStrategyConfig(
        name="web",
        label="Web URL",
        description=(
            "Normalizes the URL and rejects discovered links whose origin "
            "differs from their parent document's origin."
        ),
        # normalize_urls is web-only; dedup is the shared already-queued gate
        # the actor applies for every strategy. Keys/defaults mirror
        # ValidateSourceSettings exactly.
        fields=[
            FieldSpec(
                key="normalize_urls",
                label="Normalize URLs before dedup",
                type="checkbox",
                default=True,
            ),
            FieldSpec(
                key="dedup",
                label="Skip already-queued sources",
                type="checkbox",
                default=True,
            ),
        ],
    )

    def normalize(
        self, *, payload: ValidateSourcePayload, settings: ValidateSourceSettings
    ) -> NormalizedSource:
        normalized = (
            normalize_url(payload.url) if settings.normalize_urls else payload.url
        )
        return NormalizedSource(original_url=payload.url, normalized_url=normalized)

    def validate(
        self,
        *,
        payload: ValidateSourcePayload,
        source: NormalizedSource,
        store: SqlStore,
    ) -> None:
        if not is_allowed_url(
            payload=payload, normalized_url=source.normalized_url, store=store
        ):
            raise SourceValidationError(
                "url_not_allowed",
                f"url {source.normalized_url} rejected by the origin gate",
            )
