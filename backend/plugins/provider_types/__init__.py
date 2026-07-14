"""Provider-type strategy plugins.

Every kind of model provider Embeddorium can talk to — an in-process FastEmbed
model, a mock, a local Ollama server, a remote OpenAI-compatible API — is a
small, self-contained **provider-type adapter** under
``backend/plugins/provider_types/<name>.py``. They are auto-discovered at
process start exactly like the per-actor strategy plugins (see
``docs/plugins.md``): drop a module in this directory, subclass
:class:`~backend.plugins.provider_types.base.ProviderTypeAdapter`, set a
class-level ``config``, and the new provider type shows up in the
``/provider-configs`` metadata endpoint and becomes usable by the ingestion and
compare embed paths — no registration, no editing of a dispatch table.

Each adapter owns two things:

- **What the UI needs to configure it** — a
  :class:`~backend.plugins.provider_types.base.ProviderTypeConfig` declaring the
  adapter's ``name``/``label``/``description``, whether it runs in-process
  (``type="builtin"``) or over the network (``type="remote"``), which
  ``model_type`` capabilities it supports, and a list of
  :class:`~backend.plugins._fields.FieldSpec` settings.
- **How to embed with it** — :meth:`ProviderTypeAdapter.resolve`, which turns a
  stored provider's ``config`` into a concrete
  :class:`~backend.plugins.provider_types.base.ResolvedEmbedTarget` (worker-key
  + model + endpoint + mock dimension) the embed clients dispatch on. This is
  what replaces the old hardcoded ``if provider_type == ...`` chains in the
  embed_chunks worker and the compare service.

Keep top-level imports cheap: heavy backends (fastembed/onnxruntime/openai) are
imported lazily inside the embed clients the target resolves to, never here.
"""
