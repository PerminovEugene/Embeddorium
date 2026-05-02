import requests
import dramatiq

from laws_agent.models import Document, DocumentChunk
from laws_agent.models.crawl_target import CrawlTargetStatus
from laws_agent.parsers.html_parser import HtmlParser
from laws_agent.parsers.text_splitter import TextSplitter
from laws_agent.storage.sql.sql_store import SqlStore
from laws_agent.clients.queue.queue_client import QueueClient
from laws_agent.clients.queue.process_web_source_payload import ProcessWebSourcePayload
from laws_agent.clients.queue.embed_chunks_payload import EmbedChunksPayload
from laws_agent.clients.queue.queue_names import (
    FETCH_SOURCE_ACTOR,
    FETCH_SOURCE_QUEUE,
    EMBED_CHUNKS_QUEUE,
    EMBED_CHUNKS_ACTOR,
    LINK_PROCESSOR_QUEUE,
    LINK_PROCESSOR_ACTOR,
)

BATCH_SIZE = 32

rabbitmq_broker = QueueClient().create("web_source")
dramatiq.set_broker(rabbitmq_broker)

sql_store = SqlStore()
sql_store.run_migrations()


def _process_web_source(
    *,
    crawl_target_id: str,
    group: str,
    store: SqlStore,
    broker,
    http_get,
) -> None:
    payload = ProcessWebSourcePayload.from_actor_kwargs(
        crawl_target_id=crawl_target_id,
        group=group,
    )

    crawl_target = store.crawl_targets.get(payload.crawl_target_id)
    if crawl_target is None:
        return

    store.crawl_targets.update_status(
        target_id=payload.crawl_target_id,
        status=CrawlTargetStatus.PROCESSING,
    )

    try:
        response = http_get(crawl_target.original_url, timeout=10, verify=False)
        response.raise_for_status()
    except Exception as exc:
        store.crawl_targets.update_status(
            target_id=payload.crawl_target_id,
            status=CrawlTargetStatus.FAILED,
            error=str(exc),
        )
        raise

    parser = HtmlParser()
    text = parser.parse(response.text, crawl_target.original_url)

    splitter = TextSplitter()
    chunks = splitter.split(text)

    document = store.documents.save(
        Document(source_url=crawl_target.original_url, language=payload.group)
    )

    store.crawl_targets.update_status(
        target_id=payload.crawl_target_id,
        status=CrawlTargetStatus.PROCESSED,
        document_id=document.id,
    )

    for start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[start: start + BATCH_SIZE]

        saved_chunks = store.chunks.save_many([
            DocumentChunk(
                document_id=document.id,
                text=chunk.text,
                chunk_index=start + i,
            )
            for i, chunk in enumerate(batch)
        ])

        embed_payload = EmbedChunksPayload(
            document_id=document.id,
            chunk_ids=[chunk.id for chunk in saved_chunks],
            group=payload.group,
        )
        broker.enqueue(
            dramatiq.Message(
                queue_name=EMBED_CHUNKS_QUEUE,
                actor_name=EMBED_CHUNKS_ACTOR,
                args=[],
                kwargs=embed_payload.to_actor_kwargs(),
                options={},
            )
        )

        for saved_chunk, raw_chunk in zip(saved_chunks, batch):
            for link in raw_chunk.links:
                broker.enqueue(
                    dramatiq.Message(
                        queue_name=LINK_PROCESSOR_QUEUE,
                        actor_name=LINK_PROCESSOR_ACTOR,
                        args=[],
                        kwargs={
                            "url": link["url"],
                            "group": payload.group,
                            "parent_document_id": str(document.id),
                            "parent_chunk_id": str(saved_chunk.id),
                        },
                        options={},
                    )
                )


@dramatiq.actor(
    queue_name=FETCH_SOURCE_QUEUE,
    actor_name=FETCH_SOURCE_ACTOR,
    max_retries=3,
)
def process_web_source(*, crawl_target_id: str, group: str) -> None:
    _process_web_source(
        crawl_target_id=crawl_target_id,
        group=group,
        store=sql_store,
        broker=rabbitmq_broker,
        http_get=requests.get,
    )
