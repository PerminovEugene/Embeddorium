# Postgres infra

Postgres has no standalone config file today — it runs from the stock
`postgres:16` image and is configured entirely through environment variables in
`docker-compose.yml` (`POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB`) with
data persisted in the `postgres_data` volume.

Put any future Postgres config (custom `postgresql.conf`, init SQL, etc.) here and
mount it from the `postgres` service in `docker-compose.yml`.
