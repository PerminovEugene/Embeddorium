# Add custom provider configuration

A provider plugin has a connection adapter and one handler per capability.
Discovery associates handlers with the provider package that contains them.

## Package layout

```text
backend/plugins/provider_types/acme/
  __init__.py
  base.py
  model_types/
    __init__.py
    embedding.py
```

## Connection adapter

```python
# backend/plugins/provider_types/acme/base.py
from backend.plugins.provider_types._remote import api_key_field, build_base_url, url_field
from backend.plugins.provider_types.base import (
    ProviderTypeAdapter,
    ProviderTypeConfig,
    ResolvedConnection,
)


class AcmeProviderType(ProviderTypeAdapter):
    config = ProviderTypeConfig(
        name="acme",
        label="Acme",
        description="An OpenAI-compatible embedding endpoint.",
        type="remote",
        fields=[url_field("https://api.example.invalid/v1"), api_key_field()],
    )

    def resolve_connection(self) -> ResolvedConnection:
        return ResolvedConnection(
            base_url=build_base_url(self._get("url"), None),
            api_key=self._get("api_key") or None,
        )
```

## Embedding capability

```python
# backend/plugins/provider_types/acme/model_types/embedding.py
from backend.plugins.provider_types._remote import model_name_field
from backend.plugins.provider_types.base import (
    ModelTypeConfig,
    ModelTypeHandler,
    ResolvedEmbedTarget,
)


class AcmeEmbedding(ModelTypeHandler):
    config = ModelTypeConfig(
        model_type="embedding",
        label="Embedding",
        fields=[model_name_field("acme-embed")],
    )

    def resolve(self) -> ResolvedEmbedTarget:
        return ResolvedEmbedTarget(
            provider="openai",
            model=self._get("model_name"),
            base_url=self.connection.base_url,
            api_key=self.connection.api_key,
        )

    def build_embed_client(self):
        from backend.shared.clients.openai_embed_client import OpenAIEmbedClient

        target = self.resolve()
        if not target.base_url or not target.model:
            raise ValueError("acme embedding provider requires URL and model")
        return OpenAIEmbedClient(
            model=target.model,
            base_url=target.base_url,
            api_key=target.api_key,
        )
```

Keep SDK or client imports inside `build_embed_client` so discovery remains
cheap and one missing optional dependency does not break unrelated providers.

## Verify discovery

Restart the server and embedding worker, then inspect:

```sh
curl -sS http://localhost:8000/providers/configs
.venv/bin/python -m pytest backend/tests/plugins/provider_types -q
```

No central registration edit is required. A provider package that fails to
import is logged and skipped.
