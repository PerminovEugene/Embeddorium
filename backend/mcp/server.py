from fastmcp import FastMCP
from backend.shared.storage.sql.sql_store import SqlStore
from backend.shared.storage.vector.vector_store import VectorStore

mcp = FastMCP("Demo 🚀")

sql_store = SqlStore()
vector_store = VectorStore()

@mcp.tool()
def search_knowledge_base(query: str, limit: int = 5) -> list[dict]:
    """
    Search documents in vector DB + PostgreSQL.
    """
    # Replace this with your real retrieval service:
    # return retrieval_service.search(query=query, limit=limit)
    embedding = 
    vector_store.search(embedding, 10)
    return [
        {
            "document_id": "doc_1",
            "chunk_id": "chunk_1",
            "title": "Example document",
            "source_url": "https://example.com/source",
            "text": f"Fake retrieved chunk for query: {query}",
            "score": 0.91,
        }
    ]


@mcp.resource("kb://schema")
def knowledge_base_schema() -> str:
    """
    Static readable info about your KB.
    """
    return """
    Tables:
    - documents(id, title, source_url, group, country)
    - chunks(id, document_id, text, chunk_index)
    - embeddings(chunk_id, vector)
    """


@mcp.prompt()
def answer_with_sources(question: str) -> str:
    """
    Prompt template for grounded answers.
    """
    return f"""
    Answer the question using only retrieved knowledge-base chunks.
    Cite document_id and source_url.

    Question: {question}
    """

if __name__ == "__main__":
    mcp.run()