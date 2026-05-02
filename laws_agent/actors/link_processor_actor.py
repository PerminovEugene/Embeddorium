import dramatiq

from laws_agent.models import CrawlTarget, CrawlTargetStatus
from laws_agent.storage.sql.sql_store import SqlStore
from laws_agent.clients.queue.queue_client import QueueClient
from laws_agent.clients.queue.process_link_payload import ProcessLinkSourcePayload
from laws_agent.clients.queue.queue_names import (
    FETCH_SOURCE_ACTOR,
    FETCH_SOURCE_QUEUE,
    LINK_PROCESSOR_ACTOR,
    LINK_PROCESSOR_QUEUE,
)
from laws_agent.actors.url_helper import normalize_url, get_origin


rabbitmq_broker = QueueClient().create("link_processor")
dramatiq.set_broker(rabbitmq_broker)

sql_store = SqlStore()
sql_store.run_migrations()


def _is_allowed_url(
    *, payload: ProcessLinkSourcePayload, normalized_url: str, store: SqlStore
) -> bool:
    if payload.parent_document_id is None:
        return True

    parent_document = store.documents.get(payload.parent_document_id)
    if parent_document is None:
        return False

    return get_origin(parent_document.source_url) == get_origin(normalized_url)


def process_link(
    *,
    url: str,
    group: str,
    parent_document_id: str | None = None,
    parent_chunk_id: str | None = None,
    store: SqlStore,
    broker,
) -> None:
    print('got message', url)
    payload = ProcessLinkSourcePayload.from_actor_kwargs(
        url=url,
        group=group,
        parent_document_id=parent_document_id,
        parent_chunk_id=parent_chunk_id,
    )

    clean_url = normalize_url(payload.url)

    existing_target = store.crawl_targets.find_active_by_normalized_url(
        group=payload.group,
        normalized_url=clean_url,
    )
    if existing_target is not None:
        return

    if not _is_allowed_url(payload=payload, normalized_url=clean_url, store=store):
        return

    target = store.crawl_targets.save(
        CrawlTarget(
            group=payload.group,
            original_url=payload.url,
            normalized_url=clean_url,
            status=CrawlTargetStatus.QUEUED,
            parent_document_id=payload.parent_document_id,
            parent_chunk_id=payload.parent_chunk_id,
        )
    )

    broker.enqueue(
        dramatiq.Message(
            queue_name=FETCH_SOURCE_QUEUE,
            actor_name=FETCH_SOURCE_ACTOR,
            args=[],
            kwargs={
                "crawl_target_id": str(target.id),
                "group": payload.group,
            },
            options={},
        )
    )


@dramatiq.actor(
    queue_name=LINK_PROCESSOR_QUEUE,
    actor_name=LINK_PROCESSOR_ACTOR,
    max_retries=3,
)
def link_processor(
    *,
    url: str,
    group: str,
    parent_document_id: str | None = None,
    parent_chunk_id: str | None = None,
) -> None:
    process_link(
        url=url,
        group=group,
        parent_document_id=parent_document_id,
        parent_chunk_id=parent_chunk_id,
        store=sql_store,
        broker=rabbitmq_broker,
    )
