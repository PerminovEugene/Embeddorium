"""_load_embed_config() resolves a run's embed config from its snapshot only.

The provider a run embeds with must be the one it recorded: a vector produced by
a different provider than the query side uses is silently wrong, so every
unresolvable case raises EmbedConfigError rather than falling back to a global
default. These tests pin that contract, including the caching that keeps the run
row a once-per-pipeline read.
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest

import backend.actors.embed_chunks_actor.launcher as launcher
from backend.actors.embed_chunks_actor.launcher import (
    EmbedConfigError,
    _load_embed_config,
)


def _run_with(provider: dict, collection: str = "kb_docs") -> MagicMock:
    run = MagicMock()
    run.actor_configs = {
        # chunk_document is required by PipelineActorConfigs but its own fields
        # all default, so an empty block is the minimal valid snapshot.
        "chunk_document": {},
        "embed_chunks": {"provider": provider},
        "vector_store": {"collection": collection, "similarity": "cosine"},
    }
    return run


@pytest.fixture(autouse=True)
def _reset_cache():
    launcher._embed_config.clear()
    yield
    launcher._embed_config.clear()


def test_reads_provider_and_collection_from_the_run_snapshot() -> None:
    pipeline_id = str(uuid.uuid4())
    run = _run_with(
        {
            "provider_type": "ollama",
            "model_type": "embedding",
            "config": {"model_name": "qwen3-embedding"},
        }
    )

    with patch.object(launcher, "sql_store") as store:
        store.pipeline_runs.get.return_value = run
        provider_type, model_type, provider_config, collection, _ = _load_embed_config(
            pipeline_id
        )

    assert provider_type == "ollama"
    assert model_type == "embedding"
    assert provider_config == {"model_name": "qwen3-embedding"}
    assert collection == "kb_docs"


def test_flat_legacy_snapshot_without_a_config_key_is_accepted() -> None:
    pipeline_id = str(uuid.uuid4())
    run = _run_with({"provider_type": "mock", "mock_dim": 8})

    with patch.object(launcher, "sql_store") as store:
        store.pipeline_runs.get.return_value = run
        provider_type, _, provider_config, _, _ = _load_embed_config(pipeline_id)

    assert provider_type == "mock"
    # No nested "config": type-specific settings stay at the top level.
    assert provider_config == {"provider_type": "mock", "mock_dim": 8}


def test_model_type_defaults_to_embedding_when_absent() -> None:
    pipeline_id = str(uuid.uuid4())

    with patch.object(launcher, "sql_store") as store:
        store.pipeline_runs.get.return_value = _run_with({"provider_type": "mock"})
        _, model_type, _, _, _ = _load_embed_config(pipeline_id)

    assert model_type == "embedding"


def test_the_run_row_is_read_once_per_pipeline() -> None:
    pipeline_id = str(uuid.uuid4())

    with patch.object(launcher, "sql_store") as store:
        store.pipeline_runs.get.return_value = _run_with({"provider_type": "mock"})
        first = _load_embed_config(pipeline_id)
        second = _load_embed_config(pipeline_id)

    store.pipeline_runs.get.assert_called_once()
    assert first == second


def test_missing_pipeline_id_raises() -> None:
    with pytest.raises(EmbedConfigError, match="requires a pipeline_id"):
        _load_embed_config(None)


def test_unparseable_pipeline_id_raises() -> None:
    with pytest.raises(EmbedConfigError, match="Invalid pipeline_id"):
        _load_embed_config("not-a-uuid")


def test_missing_run_row_raises() -> None:
    pipeline_id = str(uuid.uuid4())

    with patch.object(launcher, "sql_store") as store:
        store.pipeline_runs.get.return_value = None
        with pytest.raises(EmbedConfigError, match="No pipeline run found"):
            _load_embed_config(pipeline_id)


def test_unparseable_actor_configs_raises() -> None:
    pipeline_id = str(uuid.uuid4())
    run = MagicMock()
    run.actor_configs = {"vector_store": "not-an-object"}

    with patch.object(launcher, "sql_store") as store:
        store.pipeline_runs.get.return_value = run
        with pytest.raises(EmbedConfigError, match="Could not parse actor_configs"):
            _load_embed_config(pipeline_id)


@pytest.mark.parametrize(
    "provider", [{}, {"provider_type": ""}, {"model_type": "embedding"}]
)
def test_snapshot_without_a_provider_raises_instead_of_guessing(provider) -> None:
    pipeline_id = str(uuid.uuid4())

    with patch.object(launcher, "sql_store") as store:
        store.pipeline_runs.get.return_value = _run_with(provider)
        with pytest.raises(EmbedConfigError, match="No embedding provider recorded"):
            _load_embed_config(pipeline_id)


def test_a_failed_load_is_not_cached() -> None:
    """A transient miss must not poison the cache for later messages."""
    pipeline_id = str(uuid.uuid4())

    with patch.object(launcher, "sql_store") as store:
        store.pipeline_runs.get.return_value = None
        with pytest.raises(EmbedConfigError):
            _load_embed_config(pipeline_id)

        store.pipeline_runs.get.return_value = _run_with({"provider_type": "mock"})
        provider_type, _, _, _, _ = _load_embed_config(pipeline_id)

    assert provider_type == "mock"
