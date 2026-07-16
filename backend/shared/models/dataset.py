from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field


class WebDataset(BaseModel):
    """A dataset sourced from a single URL.

    Crawl scope (whether to follow child links, cross-domain, and how deep)
    is configured on the ingestion pipeline's ``schedule_discovered_links``
    actor config — the single source of truth the crawl actually reads — not
    on the dataset.
    """

    id: Optional[uuid.UUID] = None
    name: str

    source_type: Literal["web"] = "web"

    url: str

    created_at: Optional[datetime] = None


class LocalDataset(BaseModel):
    """A dataset sourced from local filesystem files/folders."""

    id: Optional[uuid.UUID] = None
    name: str

    source_type: Literal["local"] = "local"

    # Selected file/folder paths.
    paths: list[str]

    created_at: Optional[datetime] = None


Dataset = Annotated[Union[WebDataset, LocalDataset], Field(discriminator="source_type")]
