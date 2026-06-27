from pydantic import BaseModel
from typing import List

class TextItem(BaseModel):
    id: str
    text: str

class TextGroup(BaseModel):
    inputs: List[TextItem]

class CompareRequest(BaseModel):
    configuration: dict
    source: TextGroup
    candidates: TextGroup
