# Qdrant infra

Qdrant has no standalone config file today — it runs from the stock
`qdrant/qdrant:latest` image, configured through environment variables in
`docker-compose.yml` (e.g. `QDRANT__SERVICE__GRPC_PORT`) with data persisted in
the `qdrant_data` volume.

Put any future Qdrant config (`config.yaml`, etc.) here and mount it from the
`qdrant` service in `docker-compose.yml`.
