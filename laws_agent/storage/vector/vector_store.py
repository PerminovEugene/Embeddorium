import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from laws_agent import config

VECTOR_SIZE = 1536  # change to match your embedding model output dimension


class VectorStore:
    def __init__(self, collection: str, url: str = config.QDRANT_URL) -> None:
        self.client = QdrantClient(url=url)
        self.collection = collection

    def create_collection(self, vector_size: int = VECTOR_SIZE) -> None:
        existing = [c.name for c in self.client.get_collections().collections]
        if self.collection not in existing:
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
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

    def search(self, query_vector: list[float], top_k: int = 5) -> list[dict]:
        results = self.client.query_points(
            collection_name=self.collection,
            query=query_vector,
            limit=top_k,
        )
        return [
            {"score": hit.score, **hit.payload}
            for hit in results.points
        ]

    def delete_collection(self) -> None:
        self.client.delete_collection(self.collection)
