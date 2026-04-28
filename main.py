import requests

from laws_agent.clients.hg_client import HgClient
from laws_agent.models import Document, DocumentChunk
from laws_agent.parsers.html_parser import HtmlParser
from laws_agent.parsers.text_splitter import TextSplitter
from laws_agent.storage.sql_store import SqlStore
from laws_agent.storage.vector_store import VectorStore

URL = "https://www.evgeniiperminov.dev/"
LANGUAGE = "ES"
BATCH_SIZE = 32
COLLECTION = "laws"

hg_client = HgClient()
model = hg_client.get_model("Qwen/Qwen3-Embedding-8B")

response = requests.get(URL, timeout=10, verify=False)
print("got url", response)

parser = HtmlParser()
text = parser.parse(response.text, URL)
print("parsed", text)

splitter = TextSplitter()
chunks = splitter.split(text)
print("chunks amount", len(chunks))

vector_store = VectorStore(collection=COLLECTION)

vector_store.create

with SqlStore() as sql_store:
    document = sql_store.save_document(Document(source_url=URL, language=LANGUAGE))
    print(f"saved document id={document.id}")

    for start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[start : start + BATCH_SIZE]

        embeddings = model.encode(
            [chunk.text for chunk in batch],
            batch_size=BATCH_SIZE,
            show_progress_bar=False,
            normalize_embeddings=True,
        )

        saved_chunks = sql_store.save_chunks([
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
                    "chunk_id": str(saved.id),
                    "document_id": str(saved.document_id),
                    "chunk_index": saved.chunk_index,
                    "language": LANGUAGE,
                }
                for saved in saved_chunks
            ],
        )

    print(f"done: {len(chunks)} chunks indexed")
