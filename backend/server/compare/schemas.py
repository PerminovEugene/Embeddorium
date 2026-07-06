"""Pydantic request models for the ``/compare`` endpoint."""

from typing import List

from pydantic import BaseModel


class TextItem(BaseModel):
    id: str
    text: str


class TextGroup(BaseModel):
    inputs: List[TextItem]


class CompareRequest(BaseModel):
    configuration: dict
    source: TextGroup
    candidates: TextGroup
