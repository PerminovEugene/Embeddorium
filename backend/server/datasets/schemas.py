"""camelCase API schemas for the ``/datasets`` endpoints.

Mirrors the UI's discriminated ``Dataset`` union (``ui/src/components/
datasets/types.ts``) field-for-field, so request/response bodies need no
reshaping on the frontend. These are pure API-layer models: route handlers
translate to/from the snake_case domain models in ``backend.shared.models``.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from backend.shared.models import Dataset, LocalDataset, WebDataset


class _CamelModel(BaseModel):
    """Base for API schemas: camelCase on the wire, snake_case in Python."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class WebDatasetIn(_CamelModel):
    """Request body for creating/updating a web dataset."""

    name: str
    source_type: Literal["web"] = "web"
    url: str


class LocalDatasetIn(_CamelModel):
    """Request body for creating/updating a local dataset."""

    name: str
    source_type: Literal["local"] = "local"
    paths: List[str]


DatasetIn = Annotated[
    Union[WebDatasetIn, LocalDatasetIn], Field(discriminator="source_type")
]


class WebDatasetOut(_CamelModel):
    """Response body for a web dataset."""

    id: uuid.UUID
    name: str
    source_type: Literal["web"] = "web"
    url: str
    created_at: Optional[datetime] = None


class LocalDatasetOut(_CamelModel):
    """Response body for a local dataset."""

    id: uuid.UUID
    name: str
    source_type: Literal["local"] = "local"
    paths: List[str]
    created_at: Optional[datetime] = None


DatasetOut = Union[WebDatasetOut, LocalDatasetOut]


def dataset_in_to_domain(payload: DatasetIn) -> Dataset:
    """Map a validated camelCase request body to its snake_case domain model."""
    if payload.source_type == "web":
        return WebDataset(name=payload.name, url=payload.url)
    return LocalDataset(name=payload.name, paths=payload.paths)


def dataset_to_out(dataset: Dataset) -> DatasetOut:
    """Map a snake_case domain model to its camelCase response schema."""
    if isinstance(dataset, WebDataset):
        return WebDatasetOut(
            id=dataset.id,
            name=dataset.name,
            url=dataset.url,
            created_at=dataset.created_at,
        )
    return LocalDatasetOut(
        id=dataset.id,
        name=dataset.name,
        paths=dataset.paths,
        created_at=dataset.created_at,
    )
