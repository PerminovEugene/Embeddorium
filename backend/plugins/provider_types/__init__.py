"""Provider-type / model-type strategy plugins.

Embedding and reranking are described by two auto-discovered layers:

- A **provider type** — the runtime/API Embeddorium talks to (a mock, a local
  Ollama server, a remote OpenAI-compatible API) — is a self-contained folder
  ``backend/plugins/provider_types/<name>/`` whose ``base.py`` holds a
  :class:`~backend.plugins.provider_types.base.ProviderTypeAdapter` subclass. It
  owns the *connection* (``url``/``port``/``api_key``) and whether it runs
  in-process (``type="builtin"``) or over the network (``type="remote"``).
- A **model type** — the capability a model serves under a provider
  (``embedding``, ``cross-encoder`` reranking, …) — is a module in that
  provider's ``model_types/`` subpackage holding a
  :class:`~backend.plugins.provider_types.base.ModelTypeHandler` subclass. It owns
  the capability-specific settings (``model_name``, ``mock_dim``,
  ``rerank_path``) and turns the provider's connection plus those settings into a
  concrete :class:`~backend.plugins.provider_types.base.ResolvedEmbedTarget` /
  :class:`~backend.plugins.provider_types.base.ResolvedRerankTarget` (and, for
  embedding, an :class:`~backend.shared.clients.embed_client.EmbedClient`).

A provider's supported model types are *derived* from the handlers it ships —
adding a capability to a provider is dropping one module in its ``model_types/``
folder, and the UI picks it up automatically from ``/provider-configs``. A
cross-encoder reranker is thus a model type under ``ollama``, not a provider type.

Discovery (see :mod:`backend.plugins.provider_types.registry`) walks the whole
package once at process start: no registration, no editing of a dispatch table.
Keep top-level imports cheap — heavy backends (the openai/ollama clients) are
imported lazily inside :meth:`ModelTypeHandler.build_embed_client`, never here.
"""
