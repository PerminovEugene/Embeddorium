from urllib.parse import urlparse, urlunparse

from laws_agent.clients.queue.process_link_payload import ProcessLinkSourcePayload
from laws_agent.storage.sql.sql_store import SqlStore


def normalize_url(url: str) -> str:
    parsed = urlparse(url)

    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()

    if netloc.endswith(":80") and scheme == "http":
        netloc = netloc[:-3]

    if netloc.endswith(":443") and scheme == "https":
        netloc = netloc[:-4]

    path = parsed.path or "/"

    if path != "/":
        path = path.rstrip("/")

    # query and fragment are intentionally removed
    return urlunparse((scheme, netloc, path, "", "", ""))


def get_origin(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"


def is_allowed_url(
    *, payload: ProcessLinkSourcePayload, normalized_url: str, store: SqlStore
) -> bool:
    if payload.parent_document_id is None:
        return True

    parent_document = store.documents.get(payload.parent_document_id)
    if parent_document is None:
        return False

    return get_origin(parent_document.source_url) == get_origin(normalized_url)

