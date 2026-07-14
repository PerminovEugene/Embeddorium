"""Single source of truth for the document chunking parameters.

Kept in its own dependency-free module (no langchain import) so the values can
be read both by the chunker plugins' size-field defaults and by the
pipeline-run recorder without pulling any text-splitting stack into actors that
only need to snapshot config.
"""

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 150

# Parsing provenance version, recorded on each run by ``parse_source_actor``.
# Bump when the format-parser output/algorithm changes.
PARSER_VERSION = "1"

# Chunking provenance version, recorded on each run by ``parse_source_actor``.
# Bump when chunking parameters/algorithm change.
CHUNKER_VERSION = "3"
