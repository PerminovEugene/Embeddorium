import dramatiq

from laws_agent.clients.hg_client import HgClient
from laws_agent.storage.sql.sql_store import SqlStore
from laws_agent.storage.vector.vector_store import VectorStore
from laws_agent.clients.queue.queue_client import QueueClient
from laws_agent.clients.queue.embed_chunks_payload import EmbedChunksPayload
from laws_agent.clients.queue.queue_names import EMBED_CHUNKS_ACTOR, EMBED_CHUNKS_QUEUE

COLLECTION_BASE = "LAWS"
MODEL_NAME = "Qwen/Qwen3-Embedding-8B"
MODEL_COLLECTION_POSTFIX = "qwen_embed_8b"
BATCH_SIZE = 32

# Lazy singletons — initialized on first actor invocation, not at import time
_rabbitmq_broker = None
_model = None
_model_size: int | None = None


def _get_broker():
    global _rabbitmq_broker
    if _rabbitmq_broker is None:
        _rabbitmq_broker = QueueClient().create("embed_chunks")
        dramatiq.set_broker(_rabbitmq_broker)
    return _rabbitmq_broker


def _get_model_and_size():
    global _model, _model_size
    if _model is None:
        hg_client = HgClient()
        _model = hg_client.get_model(MODEL_NAME)
        _model_size = hg_client.get_model_size(MODEL_NAME)
    return _model, _model_size


def _embed_chunks(
    *,
    document_id: str,
    chunk_ids: list[str],
    group: str,
    store: SqlStore,
    vector_store: VectorStore,
    model,
    model_size: int,
) -> None:
    payload = EmbedChunksPayload.from_actor_kwargs(
        document_id=document_id,
        chunk_ids=chunk_ids,
        group=group,
    )

    vector_store.create_collection(model_size)

    chunks = store.chunks.get_many(payload.chunk_ids)

    for start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[start: start + BATCH_SIZE]

        embeddings = model.encode(
            [chunk.text for chunk in batch],
            batch_size=BATCH_SIZE,
            show_progress_bar=False,
            normalize_embeddings=True,
        )

        vector_store.upsert(
            vectors=[embedding.tolist() for embedding in embeddings],
            payloads=[
                {
                    "chunk_id": str(chunk.id),
                    "document_id": str(payload.document_id),
                    "chunk_index": chunk.chunk_index,
                    "language": payload.group,
                }
                for chunk in batch
            ],
        )


@dramatiq.actor(
    queue_name=EMBED_CHUNKS_QUEUE,
    actor_name=EMBED_CHUNKS_ACTOR,
    max_retries=3,
)
def embed_chunks(*, document_id: str, chunk_ids: list[str], group: str) -> None:
    model, model_size = _get_model_and_size()
    collection = f"{COLLECTION_BASE}_{group}_{MODEL_COLLECTION_POSTFIX}"

    with SqlStore() as store:
        _embed_chunks(
            document_id=document_id,
            chunk_ids=chunk_ids,
            group=group,
            store=store,
            vector_store=VectorStore(collection),
            model=model,
            model_size=model_size,
        )
