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


class SearchRequest(BaseModel):
    # configuration carries: runId (the pipeline run to search — its saved
    # config supplies the Qdrant collection and the embedding provider/model)
    # and ollamaPort (where to reach Ollama for embedding the query).
    configuration: dict
    source: TextGroup
