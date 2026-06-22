-- Transactional outbox: rows are written in the same transaction as domain
-- changes, then published to RabbitMQ by the outbox dispatcher.
CREATE TABLE IF NOT EXISTS outbox_events (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    queue_name  TEXT NOT NULL,
    actor_name  TEXT NOT NULL,
    payload     JSONB NOT NULL DEFAULT '{}',
    dedup_key   TEXT NOT NULL,
    status      VARCHAR(16) NOT NULL DEFAULT 'pending',
    attempts    INTEGER NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    sent_at     TIMESTAMPTZ
);

-- A given logical event is enqueued at most once even across retries.
CREATE UNIQUE INDEX IF NOT EXISTS outbox_events_dedup_key_key
    ON outbox_events (dedup_key);

CREATE INDEX IF NOT EXISTS outbox_events_status_created_idx
    ON outbox_events (status, created_at);
