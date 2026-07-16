# Limitations

The following constraints are visible in the current implementation.

- Local ingestion enumerates only `*.xml`; the source browser also exposes only
  directories and XML files.
- Built-in web parsing supports HTML/XHTML, plain text, and XML. The parser
  selector displays `pdf`, but no PDF parser plugin exists.
- `follow_child_links` works, while `max_depth` and `follow_cross_domain` are
  stored but not enforced. The validation strategy always rejects discovered
  cross-origin URLs.
- Every web and local source passes through the keyword filter. With empty
  include/exclude lists the filter passes all content.
- Collections are named per dataset, not per run. If a collection already
  exists, `VectorStore.create_collection` does not recreate it with a new
  dimension or distance; incompatible runs therefore require a distinct
  dataset name or collection cleanup.
- Workers ship as one process and one thread per actor. There is no
  application-level embedding concurrency limiter or ingestion backpressure.
- The OpenAI embedding client does not configure an explicit HTTP timeout. The
  Ollama embedding client relies on its underlying library's timeout behavior.
- Search persistence is best-effort: a search can succeed even if saving its
  history fails.
- Search Lab compares returned ranks and scores but provides no relevance
  labels, Recall@k, MRR, nDCG, or regression evaluation.
- The API and infrastructure ports are unauthenticated or use local default
  credentials. The Compose stack is not hardened for untrusted networks.
- `backend/mcp/server.py` is incomplete, so the MCP-dependent agent is not a
  supported working flow.
- There is no documented backup, upgrade, compatibility, or data-retention
  policy: {MISSED_INFO}
