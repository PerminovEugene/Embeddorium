from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SearchInput(BaseModel):
    """The raw user-supplied text a search query was launched with.

    Stored separately from ``Search`` so the same input text is not
    duplicated inline on every search row and can be inspected/reused on its
    own (e.g. for search-history features).
    """

    id: Optional[uuid.UUID] = None
    text: str
    created_at: Optional[datetime] = None
