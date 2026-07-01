"""Local inspection helper for the legal XML chunker (requirement #12).

Usage::

    python -m backend.shared.parsers.legal_inspect path/to/act.xml
    python -m backend.shared.parsers.legal_inspect path/to/act.xml --preview 500

Prints, for one XML file: a validation report (counts, token stats, warnings)
followed by every chunk's index, type, token count, legal path and a text
preview. Read-only; touches no database or queue.
"""

from __future__ import annotations

import argparse
import sys

from backend.shared.parsers.legal_chunker import (
    LegalChunkConfig,
    LegalChunker,
    build_report,
    format_for_inspection,
)
from backend.shared.parsers.legal_xml import LegalXmlReader


def inspect_file(path: str, *, preview: int = 300) -> int:
    try:
        content = open(path, encoding="utf-8").read()
    except OSError as exc:
        print(f"error: cannot read {path}: {exc}", file=sys.stderr)
        return 2

    doc = LegalXmlReader().parse(content, source_url=path)
    if doc is None:
        print(f"error: {path} is not a parseable Juurakt XML document", file=sys.stderr)
        return 1

    cfg = LegalChunkConfig()
    chunks = LegalChunker(cfg).chunk(doc)
    report = build_report(chunks, min_tokens=cfg.min_tokens)

    print(f"Act:        {doc.title}")
    print(f"Document id:{doc.document_id}")
    print(f"Sections:   {len(doc.sections)}    Amendments: {len(doc.amendments)}")
    print("-" * 70)
    print(f"Chunks:     {report.total}")
    for chunk_type, count in sorted(report.by_type.items()):
        print(f"  {chunk_type:20} {count}")
    print(
        f"Tokens:     min={report.min_tokens} avg={report.avg_tokens} "
        f"max={report.max_tokens}"
    )
    if report.below_min:
        print(f"WARNING: {len(report.below_min)} legal_body chunk(s) below min size")
    if report.multi_chapter:
        print(f"WARNING: {len(report.multi_chapter)} chunk(s) span multiple chapters")
    if report.metadata_leak:
        print(
            f"WARNING: {len(report.metadata_leak)} legal_body chunk(s) start with "
            "raw publication metadata"
        )
    print("Top largest chunks:")
    for tokens, legal_path in report.largest:
        print(f"  {tokens:5} tok  {legal_path}")
    print("=" * 70)
    print(format_for_inspection(chunks, preview=preview))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Inspect legal XML chunking")
    parser.add_argument("path", help="Path to a Juurakt legal-act XML file")
    parser.add_argument(
        "--preview", type=int, default=300, help="Characters of text to preview per chunk"
    )
    args = parser.parse_args(argv)
    return inspect_file(args.path, preview=args.preview)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
