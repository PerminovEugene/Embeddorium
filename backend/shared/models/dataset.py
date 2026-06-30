from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field


class WebDataset(BaseModel):
    """A dataset sourced from a single URL, optionally crawling its links."""

    id: Optional[uuid.UUID] = None
    name: str

    source_type: Literal["web"] = "web"

    url: str
    # Follow links found on the page.
    process_child_links: bool
    # Only meaningful when process_child_links is true.
    process_cross_domain_links: bool
    # How many link levels deep to crawl. Only meaningful when
    # process_child_links is true.
    depth: int

    created_at: Optional[datetime] = None


class LocalDataset(BaseModel):
    """A dataset sourced from local filesystem files/folders."""

    id: Optional[uuid.UUID] = None
    name: str

    source_type: Literal["local"] = "local"

    # Selected file/folder paths.
    paths: list[str]

    created_at: Optional[datetime] = None


Dataset = Annotated[
    Union[WebDataset, LocalDataset], Field(discriminator="source_type")
]
