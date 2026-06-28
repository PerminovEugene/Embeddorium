"""Single source of truth for the document chunking parameters.

Kept in its own dependency-free module (no langchain import) so the values can
be read both by ``TextSplitter`` and by the pipeline-run recorder without
pulling the text-splitting stack into actors that only need to snapshot config.
"""

CHUNK_STRATEGY = "markdown"
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 150
