from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field

ModelType = Literal["embedding", "text", "long-text", "reranker"]


class OllamaProvider(BaseModel):
    """A provider backed by a local Ollama instance."""

    id: Optional[uuid.UUID] = None
    name: str
    model_type: ModelType

    provider_type: Literal["ollama"] = "ollama"

    # Port the local Ollama server listens on.
    port: int
    # Name of the model to pull/run, e.g. "nomic-embed-text".
    model_name: str

    created_at: Optional[datetime] = None


class RemoteProvider(BaseModel):
    """A provider backed by a remote OpenAI-compatible endpoint."""

    id: Optional[uuid.UUID] = None
    name: str
    model_type: ModelType

    provider_type: Literal["remote"] = "remote"

    # Base URL of the OpenAI-compatible endpoint.
    base_url: str
    # API key used for authentication.
    api_key: str
    # Optional organization id (OpenAI-specific).
    organization: str
    # Name of the remote model, e.g. "text-embedding-3-small".
    model_name: str

    created_at: Optional[datetime] = None


class MockProvider(BaseModel):
    """A mock provider used for testing, with no extra configuration."""

    id: Optional[uuid.UUID] = None
    name: str
    model_type: ModelType

    provider_type: Literal["mock"] = "mock"

    created_at: Optional[datetime] = None


Provider = Annotated[
    Union[OllamaProvider, RemoteProvider, MockProvider],
    Field(discriminator="provider_type"),
]
