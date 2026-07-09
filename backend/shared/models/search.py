from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field


class Search(BaseModel):
    """One search query launch against a pipeline run's collection, plus the
    results it returned.

    Fields
    ------
    id
        Auto-assigned UUID primary key; ``None`` before the row is persisted.
    pipeline_id
        The ``PipelineRun.id`` whose collection/embedding model this query
        was run against.
    user_input_id
        The ``SearchInput.id`` this search was launched with.
    search_config
        Opaque snapshot of the search parameters used (e.g. ``top_n`` and
        ``search_method``), stored as JSONB.
    results
        The list of result hits returned for this query, stored as JSONB.
    created_at
        Set by the database server on insert.
    """

    id: Optional[uuid.UUID] = None
    pipeline_id: uuid.UUID
    user_input_id: uuid.UUID
    search_config: Dict = Field(default_factory=dict)
    results: Union[List[Dict], Dict] = Field(default_factory=list)
    created_at: Optional[datetime] = None
