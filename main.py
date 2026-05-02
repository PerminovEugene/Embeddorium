import requests

from laws_agent.clients.hg_client import HgClient
from laws_agent.models import Document, DocumentChunk
from laws_agent.parsers.html_parser import HtmlParser
from laws_agent.parsers.text_splitter import TextSplitter
from laws_agent.storage.sql.sql_store import SqlStore
from laws_agent.storage.vector.vector_store import VectorStore
from laws_agent.parsers.config_parser import parse_sources_config
import os

URL = "https://www.evgeniiperminov.dev/"
LANGUAGE = "ES"
BATCH_SIZE = 32
COLLECTION_BASE = "LAWS"
MODEL_NAME = "Qwen/Qwen3-Embedding-8B"
MODEL_COLLECTION_POSTFIX = "qwen_embed_8b"

config = parse_sources_config(os.getenv("CONFIG_PATH"))

hg_client = HgClient()
model = hg_client.get_model(MODEL_NAME)
model_size = hg_client.get_model_size(MODEL_NAME)

print("pulling from", url)
response = requests.get(URL, timeout=10, verify=False)
print("got url", response)

parser = HtmlParser()
text = parser.parse(response.text, URL)
print("parsed", text)

splitter = TextSplitter()
chunks = splitter.split(text)
print("chunks amount", len(chunks))

COLLECTION = COLLECTION_BASE + "_" + LANGUAGE + "_" + MODEL_COLLECTION_POSTFIX

vector_store = VectorStore(collection=COLLECTION)

vector_store.create_collection(model_size)

with SqlStore() as sql_store:
    document = sql_store.documents.save(Document(source_url=URL, language=LANGUAGE))
    print(f"saved document id={document.id}")

    for start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[start : start + BATCH_SIZE]

        embeddings = model.encode(
            [chunk.text for chunk in batch],
            batch_size=BATCH_SIZE,
            show_progress_bar=False,
            normalize_embeddings=True,
        )

        saved_chunks = sql_store.chunks.save_many([
            DocumentChunk(
                document_id=document.id,
                text=chunk.text,
                links=chunk.links,
                chunk_index=start + i,
            )
            for i, chunk in enumerate(batch)
        ])

        vector_store.upsert(
            vectors=[embedding.tolist() for embedding in embeddings],
            payloads=[
                {
                    "chunk_id": str(chunk.id),
                    "document_id": str(document.id),
                    "chunk_index": chunk.chunk_index,
                    "language": LANGUAGE,
                }
                for chunk in saved_chunks
            ],
        )

    print(f"done: {len(chunks)} chunks indexed")
