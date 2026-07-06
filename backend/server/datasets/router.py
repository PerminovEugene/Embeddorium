"""CRUD endpoints for ``Dataset`` rows (``/datasets``).

A dataset describes where ingestion content comes from (web crawl vs. local
files). Request/response bodies use camelCase to match the UI's
``Dataset`` union (``ui/src/components/datasets/types.ts``); see
``datasets/schemas.py`` for the camelCase<->domain mapping.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException

from backend.server.datasets.schemas import (
    DatasetIn,
    DatasetOut,
    dataset_in_to_domain,
    dataset_to_out,
)
from backend.shared.storage.sql.sql_store import SqlStore

router = APIRouter(prefix="/datasets", tags=["datasets"])


def _parse_id(dataset_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(dataset_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=404, detail="Dataset not found")


@router.get("", response_model=list[DatasetOut], response_model_by_alias=True)
async def list_datasets() -> list[DatasetOut]:
    """List every dataset, newest first."""
    store = SqlStore(application_name="embeddorium-datasets")
    try:
        return [dataset_to_out(d) for d in store.datasets.list_recent()]
    finally:
        store.close()


@router.post("", response_model=DatasetOut, response_model_by_alias=True)
async def create_dataset(payload: DatasetIn) -> DatasetOut:
    """Create a dataset and return it with its generated id."""
    store = SqlStore(application_name="embeddorium-datasets")
    try:
        created = store.datasets.create(dataset_in_to_domain(payload))
        return dataset_to_out(created)
    finally:
        store.close()


@router.get("/{dataset_id}", response_model=DatasetOut, response_model_by_alias=True)
async def get_dataset(dataset_id: str) -> DatasetOut:
    """Fetch a single dataset by id, or 404 if it doesn't exist."""
    parsed = _parse_id(dataset_id)
    store = SqlStore(application_name="embeddorium-datasets")
    try:
        dataset = store.datasets.get(parsed)
        if dataset is None:
            raise HTTPException(status_code=404, detail="Dataset not found")
        return dataset_to_out(dataset)
    finally:
        store.close()


@router.put("/{dataset_id}", response_model=DatasetOut, response_model_by_alias=True)
async def update_dataset(dataset_id: str, payload: DatasetIn) -> DatasetOut:
    """Replace a dataset's fields, or 404 if it doesn't exist."""
    parsed = _parse_id(dataset_id)
    store = SqlStore(application_name="embeddorium-datasets")
    try:
        updated = store.datasets.update(parsed, dataset_in_to_domain(payload))
        if updated is None:
            raise HTTPException(status_code=404, detail="Dataset not found")
        return dataset_to_out(updated)
    finally:
        store.close()


@router.delete("/{dataset_id}")
async def delete_dataset(dataset_id: str) -> dict:
    """Delete a dataset, or 404 if it doesn't exist."""
    parsed = _parse_id(dataset_id)
    store = SqlStore(application_name="embeddorium-datasets")
    try:
        deleted = store.datasets.delete(parsed)
        if not deleted:
            raise HTTPException(status_code=404, detail="Dataset not found")
        return {"status": "deleted"}
    finally:
        store.close()
