from __future__ import annotations

from typing import Any, Dict, List, Optional

from typing_extensions import TypedDict


class AgentState(TypedDict):
    # Input
    country: str
    year: int
    target_schema: Dict[str, Any]

    # Search
    search_queries: List[str]
    chunks: List[dict]
    search_count: int

    # Coverage
    coverage_ok: bool
    missing_fields: Optional[List[str]]

    # Config
    config: Optional[Dict[str, Any]]
    validation_errors: List[str]
    is_partial: bool
    warnings: List[str]
    repair_attempts: int
