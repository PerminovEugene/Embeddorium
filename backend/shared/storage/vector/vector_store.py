import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from backend.shared import config

VECTOR_SIZE = 1536  # change to match your embedding model output dimension

# Maps the persisted similarity name (see VectorStoreSettings) to a Qdrant
# distance, so a run's recorded similarity drives how its collection is created.
_SIMILARITY_TO_DISTANCE = {
    "cosine": Distance.COSINE,
    "dot": Distance.DOT,
    "euclid": Distance.EUCLID,
}


def similarity_to_distance(similarity: str) -> Distance:
    """Resolve a stored similarity name to a Qdrant ``Distance`` (default cosine)."""
    return _SIMILARITY_TO_DISTANCE.get(similarity, Distance.COSINE)


class VectorStore:
    def __init__(
        self,
        collection: str,
        url: str = config.QDRANT_URL,
        client: QdrantClient | None = None,
    ) -> None:
        # A ``QdrantClient`` owns an HTTP connection pool and is safe to share
        # process-wide, so callers that already hold one (e.g. the API server,
        # via ``Depends(get_qdrant_client)``) pass it in rather than opening a
        # fresh client per request. When omitted, one is created from ``url``.
        self.client = client or QdrantClient(url=url)
        self.collection = collection

    def create_collection(
        self, vector_size: int = VECTOR_SIZE, distance: Distance = Distance.COSINE
    ) -> None:
        existing = [c.name for c in self.client.get_collections().collections]
        if self.collection not in existing:
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=vector_size, distance=distance),
            )

    def upsert(
        self,
        vectors: list[list[float]],
        payloads: list[dict],
        ids: list[str] | None = None,
    ) -> None:
        # Deterministic ids (e.g. chunk_id) make re-embedding idempotent: the
        # same point is overwritten instead of duplicated. Falls back to random
        # ids when the caller has no stable key.
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in vectors]
        points = [
            PointStruct(
                id=point_id,
                vector=vector,
                payload=payload,
            )
            for point_id, vector, payload in zip(ids, vectors, payloads)
        ]
        self.client.upsert(collection_name=self.collection, points=points)

    def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        pipeline_id: str | None = None,
    ) -> list[dict]:
        # When a pipeline_id is supplied, restrict hits to vectors whose payload
        # ``pipeline_run_id`` field matches exactly.  A single collection can
        # hold vectors from several pipeline runs, so without this filter a query
        # returns results from every run that ever wrote to the collection.
        query_filter = (
            Filter(
                must=[
                    FieldCondition(
                        key="pipeline_run_id",
                        match=MatchValue(value=str(pipeline_id)),
                    )
                ]
            )
            if pipeline_id
            else None
        )
        results = self.client.query_points(
            collection_name=self.collection,
            query=query_vector,
            limit=top_k,
            query_filter=query_filter,
        )
        return [{"score": hit.score, **hit.payload} for hit in results.points]

    def delete_collection(self) -> None:
        self.client.delete_collection(self.collection)
