"""Legal-structure-aware chunker for Estonian acts.

Consumes the typed tree from :mod:`backend.plugins.chunkers.legal_xml.reader` and emits
chunks whose default unit is a single ``§`` section (not an arbitrary XML block
and not raw flattened text). Key properties:

* one ``§`` -> one chunk (by default);
* a long ``§`` is split by *subsection ranges*, never mid-subsection/clause;
* every chunk repeats its legal heading path (Act / Chapter / § ...) instead of
  naive character overlap;
* chunks never span chapters, and never merge unrelated ``§§`` (only very short
  sections sharing the same immediate parent may be merged);
* the act title, publication metadata and amendment history are emitted as
  *separate* chunk types, so they never bleed into ``legal_body`` text.

See :class:`LegalChunkConfig` for the tunable limits and
:func:`build_report` / :func:`format_for_inspection` for the debug helpers.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from backend.plugins.chunkers.legal_xml.reader import (
    LegalDocument,
    Section,
    StructuralPath,
)

logger = logging.getLogger(__name__)

# Chunk types (requirement #8).
CHUNK_LEGAL_BODY = "legal_body"
CHUNK_ACT_TITLE = "act_title"
CHUNK_AMENDMENT_HISTORY = "amendment_history"
CHUNK_LEGAL_METADATA = "legal_metadata"


def _default_token_counter(text: str) -> int:
    """Cheap, deterministic token estimate (~4 chars/token).

    Deliberately dependency-free so chunking stays import-light and tests are
    reproducible; swap in a real tokenizer via ``LegalChunkConfig.token_counter``
    if exactness matters.
    """
    if not text:
        return 0
    return max(1, round(len(text) / 4))


@dataclass
class LegalChunkConfig:
    target_tokens: int = 600
    max_tokens: int = 1100
    min_tokens: int = 100
    merge_very_short_sections: bool = True
    include_heading_context: bool = True
    emit_act_title: bool = True
    emit_metadata: bool = True
    emit_amendment_history: bool = True
    token_counter: Optional[Callable[[str], int]] = None

    def count(self, text: str) -> int:
        counter = self.token_counter or _default_token_counter
        return counter(text)


@dataclass
class LegalChunk:
    text: str
    chunk_type: str
    metadata: dict = field(default_factory=dict)
    token_count: int = 0


# --- header / rendering helpers --------------------------------------------


def _labelled(kind: str, number: str, title: str) -> str:
    number = number.strip()
    title = title.strip()
    head = f"{kind} {number}".strip() if number else kind
    return f"{head}: {title}" if title else head


def _context_lines(title: str, path: StructuralPath) -> List[str]:
    """The Act/Part/Chapter/Division heading path (no § line)."""
    lines: List[str] = []
    if title:
        lines.append(f"Act: {title}")
    if path.part_number or path.part_title:
        lines.append(_labelled("Part", path.part_number, path.part_title))
    if path.chapter_number or path.chapter_title:
        lines.append(_labelled("Chapter", path.chapter_number, path.chapter_title))
    if path.division_number or path.division_title:
        lines.append(_labelled("Division", path.division_number, path.division_title))
    if path.subdivision_number or path.subdivision_title:
        lines.append(
            _labelled("Subdivision", path.subdivision_number, path.subdivision_title)
        )
    return lines


def _section_line(section: Section) -> str:
    disp = section.display.strip() or f"§ {section.section_number}."
    return f"{disp} {section.title}".strip()


def _legal_path(title: str, path: StructuralPath, section: Optional[Section]) -> str:
    bits: List[str] = []
    if title:
        bits.append(title)
    if path.chapter_number or path.chapter_title:
        bits.append(f"Chapter {path.chapter_number}".strip() or "Chapter")
    if path.division_number or path.division_title:
        bits.append(f"Division {path.division_number}".strip() or "Division")
    if section is not None:
        bits.append(
            (section.display.strip() or f"§ {section.section_number}").rstrip(".")
        )
    return " > ".join(bits)


def _section_body(section: Section, subsections=None) -> str:
    parts: List[str] = []
    if section.intro_text and subsections is None:
        parts.append(section.intro_text)
    subs = section.subsections if subsections is None else subsections
    for sub in subs:
        rendered = sub.render()
        if rendered:
            parts.append(rendered)
    if not parts and section.intro_text:
        parts.append(section.intro_text)
    return "\n".join(parts)


# --- chunker ----------------------------------------------------------------


class LegalChunker:
    def __init__(self, config: Optional[LegalChunkConfig] = None) -> None:
        self.cfg = config or LegalChunkConfig()

    def chunk(self, doc: LegalDocument) -> List[LegalChunk]:
        chunks: List[LegalChunk] = []
        chunks.extend(self._body_chunks(doc))
        if self.cfg.emit_act_title and doc.title:
            chunks.append(self._act_title_chunk(doc))
        if self.cfg.emit_metadata and doc.metadata:
            chunks.append(self._metadata_chunk(doc))
        if self.cfg.emit_amendment_history and doc.amendments:
            chunks.extend(self._amendment_chunks(doc))

        for index, chunk in enumerate(chunks):
            chunk.metadata["chunkIndex"] = index
            chunk.token_count = self.cfg.count(chunk.text)
        return chunks

    # -- legal_body --------------------------------------------------------

    def _body_chunks(self, doc: LegalDocument) -> List[LegalChunk]:
        chunks: List[LegalChunk] = []
        pending: List[Section] = []

        def flush() -> None:
            nonlocal pending
            if not pending:
                return
            if len(pending) == 1:
                chunks.append(self._single_section_chunk(doc, pending[0]))
            else:
                chunks.append(self._merged_sections_chunk(doc, pending))
            pending = []

        for section in doc.sections:
            full = self._render_single(doc, section)
            tokens = self.cfg.count(full)

            if tokens > self.cfg.max_tokens:
                flush()
                chunks.extend(self._split_section_chunks(doc, section))
                continue

            if self.cfg.merge_very_short_sections and tokens < self.cfg.min_tokens:
                if pending and (
                    pending[-1].path.parent_key() != section.path.parent_key()
                ):
                    flush()
                pending.append(section)
                merged = self._render_merged(doc, pending)
                if self.cfg.count(merged) >= self.cfg.target_tokens:
                    flush()
                continue

            flush()
            chunks.append(self._single_section_chunk(doc, section))

        flush()
        return chunks

    def _render_single(self, doc: LegalDocument, section: Section) -> str:
        body = _section_body(section)
        if not self.cfg.include_heading_context:
            return body
        header = "\n".join(
            _context_lines(doc.title, section.path) + [_section_line(section)]
        )
        return f"{header}\n\n{body}" if body else header

    def _single_section_chunk(self, doc: LegalDocument, section: Section) -> LegalChunk:
        return LegalChunk(
            text=self._render_single(doc, section),
            chunk_type=CHUNK_LEGAL_BODY,
            metadata=self._section_metadata(doc, section),
        )

    def _section_metadata(
        self, doc: LegalDocument, section: Section, subsection_range: str = ""
    ) -> dict:
        path = section.path
        meta = {
            "actTitle": doc.title,
            "sourceUrl": doc.source_url,
            "language": doc.language,
            "chunkType": CHUNK_LEGAL_BODY,
            "partNumber": path.part_number,
            "partTitle": path.part_title,
            "chapterNumber": path.chapter_number,
            "chapterTitle": path.chapter_title,
            "divisionTitle": path.division_title,
            "subdivisionTitle": path.subdivision_title,
            "sectionNumber": section.section_number,
            "sectionTitle": section.title,
            "subsectionRange": subsection_range,
            "legalPath": _legal_path(doc.title, path, section),
            "documentId": doc.document_id,
        }
        return {k: v for k, v in meta.items() if v != ""}

    # -- merged very-short sections ----------------------------------------

    def _render_merged(self, doc: LegalDocument, sections: List[Section]) -> str:
        path = sections[0].path
        lines = _context_lines(doc.title, path)
        if not self.cfg.include_heading_context:
            lines = []
        blocks: List[str] = []
        for section in sections:
            body = _section_body(section)
            block = _section_line(section)
            if body:
                block = f"{block}\n{body}"
            blocks.append(block)
        joined = "\n\n".join(blocks)
        if lines:
            return "\n".join(lines) + "\n\n" + joined
        return joined

    def _merged_sections_chunk(
        self, doc: LegalDocument, sections: List[Section]
    ) -> LegalChunk:
        path = sections[0].path
        numbers = ", ".join(s.section_number for s in sections)
        meta = {
            "actTitle": doc.title,
            "sourceUrl": doc.source_url,
            "language": doc.language,
            "chunkType": CHUNK_LEGAL_BODY,
            "partNumber": path.part_number,
            "partTitle": path.part_title,
            "chapterNumber": path.chapter_number,
            "chapterTitle": path.chapter_title,
            "divisionTitle": path.division_title,
            "subdivisionTitle": path.subdivision_title,
            "sectionNumber": numbers,
            "sectionTitle": "; ".join(s.title for s in sections if s.title),
            "subsectionRange": "",
            "legalPath": _legal_path(doc.title, path, None) + " > §§ " + numbers,
            "documentId": doc.document_id,
            "merged": True,
        }
        return LegalChunk(
            text=self._render_merged(doc, sections),
            chunk_type=CHUNK_LEGAL_BODY,
            metadata={k: v for k, v in meta.items() if v != ""},
        )

    # -- long-section splitting --------------------------------------------

    def _split_section_chunks(
        self, doc: LegalDocument, section: Section
    ) -> List[LegalChunk]:
        subs = section.subsections
        if not subs:
            # No subsections to split on: emit whole (unavoidably large).
            return [self._single_section_chunk(doc, section)]

        header_tokens = self.cfg.count(
            "\n".join(
                _context_lines(doc.title, section.path) + [_section_line(section)]
            )
        )
        chunks: List[LegalChunk] = []
        current: list = []
        current_tokens = 0

        def flush_group() -> None:
            nonlocal current, current_tokens
            if not current:
                return
            sub_range = (
                current[0].label
                if len(current) == 1
                else f"{current[0].label}-{current[-1].label}"
            )
            body = _section_body(section, subsections=current)
            chunks.append(
                self._make_split_chunk(
                    doc, section, body, sub_range, f"Subsections: {sub_range}"
                )
            )
            current = []
            current_tokens = 0

        for sub in subs:
            sub_tokens = self.cfg.count(sub.render())
            # A single subsection that alone exceeds the ceiling is split by its
            # clauses (clauses are sub-units, not "mid-subsection" splits).
            if sub_tokens > self.cfg.max_tokens and sub.clauses:
                flush_group()
                chunks.extend(
                    self._split_subsection_by_clauses(doc, section, sub, header_tokens)
                )
                continue
            if (
                current
                and header_tokens + current_tokens + sub_tokens > self.cfg.target_tokens
            ):
                flush_group()
            current.append(sub)
            current_tokens += sub_tokens
        flush_group()
        return chunks

    def _make_split_chunk(
        self,
        doc: LegalDocument,
        section: Section,
        body: str,
        sub_range: str,
        header_extra: str,
    ) -> LegalChunk:
        header = "\n".join(
            _context_lines(doc.title, section.path)
            + [_section_line(section), header_extra]
        )
        text = f"{header}\n\n{body}" if self.cfg.include_heading_context else body
        return LegalChunk(
            text=text,
            chunk_type=CHUNK_LEGAL_BODY,
            metadata=self._section_metadata(doc, section, sub_range),
        )

    def _split_subsection_by_clauses(
        self, doc: LegalDocument, section: Section, sub, header_tokens: int
    ) -> List[LegalChunk]:
        lead_in = (
            sub.text
        )  # e.g. "Within the meaning of this Act:" — repeated for context
        lead_tokens = self.cfg.count(lead_in)
        chunks: List[LegalChunk] = []
        current: list = []
        current_tokens = 0

        def clause_label(clause) -> str:
            disp = clause.display.strip()
            return disp or f"{clause.number})"

        def flush() -> None:
            nonlocal current, current_tokens
            if not current:
                return
            first, last = clause_label(current[0]), clause_label(current[-1])
            clause_range = first if len(current) == 1 else f"{first}-{last}"
            sub_range = f"{sub.label} {clause_range}"
            body_lines = [lead_in] if lead_in else []
            body_lines.extend(c.render() for c in current)
            body = "\n".join(body_lines)
            chunks.append(
                self._make_split_chunk(
                    doc,
                    section,
                    body,
                    sub_range,
                    f"Subsection {sub.label}, clauses {clause_range}",
                )
            )
            current = []
            current_tokens = 0

        for clause in sub.clauses:
            c_tokens = self.cfg.count(clause.render())
            if current and (
                header_tokens + lead_tokens + current_tokens + c_tokens
                > self.cfg.target_tokens
            ):
                flush()
            current.append(clause)
            current_tokens += c_tokens
        flush()
        return chunks

    # -- non-body chunk types ----------------------------------------------

    def _act_title_chunk(self, doc: LegalDocument) -> LegalChunk:
        lines = [f"Act: {doc.title}"]
        kind = doc.metadata.get("documentKind")
        if kind:
            lines.append(f"Document type: {kind}")
        return LegalChunk(
            text="\n".join(lines),
            chunk_type=CHUNK_ACT_TITLE,
            metadata={
                "actTitle": doc.title,
                "sourceUrl": doc.source_url,
                "language": doc.language,
                "chunkType": CHUNK_ACT_TITLE,
                "documentId": doc.document_id,
                "legalPath": doc.title,
            },
        )

    def _metadata_chunk(self, doc: LegalDocument) -> LegalChunk:
        lines = [f"Act: {doc.title}", "Publication metadata:"]
        for key, value in doc.metadata.items():
            lines.append(f"{key}: {value}")
        return LegalChunk(
            text="\n".join(lines),
            chunk_type=CHUNK_LEGAL_METADATA,
            metadata={
                "actTitle": doc.title,
                "sourceUrl": doc.source_url,
                "language": doc.language,
                "chunkType": CHUNK_LEGAL_METADATA,
                "documentId": doc.document_id,
                "legalPath": f"{doc.title} > Publication metadata",
                "fields": dict(doc.metadata),
            },
        )

    def _amendment_chunks(self, doc: LegalDocument) -> List[LegalChunk]:
        rendered = [a.render() for a in doc.amendments]
        rendered = [r for r in rendered if r]
        if not rendered:
            return []
        header = f"Act: {doc.title}\nAmendment history:"
        chunks: List[LegalChunk] = []
        current: List[str] = []
        current_tokens = self.cfg.count(header)

        def flush() -> None:
            if not current:
                return
            text = header + "\n" + "\n".join(current)
            chunks.append(
                LegalChunk(
                    text=text,
                    chunk_type=CHUNK_AMENDMENT_HISTORY,
                    metadata={
                        "actTitle": doc.title,
                        "sourceUrl": doc.source_url,
                        "language": doc.language,
                        "chunkType": CHUNK_AMENDMENT_HISTORY,
                        "documentId": doc.document_id,
                        "legalPath": f"{doc.title} > Amendment history",
                        "entryCount": len(current),
                    },
                )
            )

        for line in rendered:
            line_tokens = self.cfg.count(line)
            if current and current_tokens + line_tokens > self.cfg.max_tokens:
                flush()
                current = []
                current_tokens = self.cfg.count(header)
            current.append(line)
            current_tokens += line_tokens
        flush()
        return chunks


# --- debug / validation (requirement #11) ----------------------------------

_METADATA_PREFIX_RE = re.compile(r"^\s*(RT\s+[IVX]|avaldatud|Riigi\s+Teataja)", re.I)


@dataclass
class ChunkReport:
    total: int
    by_type: dict
    min_tokens: int
    avg_tokens: float
    max_tokens: int
    largest: List[tuple]  # (tokens, legalPath)
    below_min: List[tuple]
    multi_chapter: List[tuple]
    metadata_leak: List[tuple]


def build_report(chunks: List[LegalChunk], min_tokens: int = 100) -> ChunkReport:
    by_type: dict = {}
    for c in chunks:
        by_type[c.chunk_type] = by_type.get(c.chunk_type, 0) + 1

    body = [c for c in chunks if c.chunk_type == CHUNK_LEGAL_BODY]
    token_counts = [c.token_count for c in chunks] or [0]
    largest = sorted(
        ((c.token_count, c.metadata.get("legalPath", "?")) for c in chunks),
        reverse=True,
    )[:10]
    below_min = [
        (c.token_count, c.metadata.get("legalPath", "?"))
        for c in body
        if c.token_count < min_tokens
    ]
    multi_chapter = [
        (c.token_count, c.metadata.get("legalPath", "?"))
        for c in body
        if "," in str(c.metadata.get("chapterNumber", ""))
    ]
    metadata_leak = [
        (c.token_count, c.metadata.get("legalPath", "?"))
        for c in body
        if _starts_with_metadata(c.text)
    ]
    return ChunkReport(
        total=len(chunks),
        by_type=by_type,
        min_tokens=min(token_counts),
        avg_tokens=round(sum(token_counts) / len(token_counts), 1),
        max_tokens=max(token_counts),
        largest=largest,
        below_min=below_min,
        multi_chapter=multi_chapter,
        metadata_leak=metadata_leak,
    )


def _starts_with_metadata(text: str) -> bool:
    # Strip the heading context we add ourselves before checking the body.
    body = text
    if "\n\n" in text:
        body = text.split("\n\n", 1)[1]
    first_line = body.strip().splitlines()[0] if body.strip() else ""
    return bool(_METADATA_PREFIX_RE.match(first_line))


def log_report(report: ChunkReport, *, log=logger) -> None:
    log.info(
        "legal_chunker: %d chunks (%s); tokens min/avg/max=%d/%.1f/%d",
        report.total,
        ", ".join(f"{k}={v}" for k, v in sorted(report.by_type.items())),
        report.min_tokens,
        report.avg_tokens,
        report.max_tokens,
    )
    for tokens, path in report.largest:
        log.debug("legal_chunker: largest chunk %d tok @ %s", tokens, path)
    if report.below_min:
        log.warning(
            "legal_chunker: %d legal_body chunk(s) below min size: %s",
            len(report.below_min),
            report.below_min[:5],
        )
    if report.multi_chapter:
        log.warning(
            "legal_chunker: %d chunk(s) appear to span multiple chapters: %s",
            len(report.multi_chapter),
            report.multi_chapter,
        )
    if report.metadata_leak:
        log.warning(
            "legal_chunker: %d legal_body chunk(s) start with raw publication "
            "metadata: %s",
            len(report.metadata_leak),
            report.metadata_leak,
        )


def format_for_inspection(chunks: List[LegalChunk], preview: int = 300) -> str:
    """Human-readable dump for the local inspection helper (requirement #12)."""
    out: List[str] = []
    for chunk in chunks:
        index = chunk.metadata.get("chunkIndex", "?")
        path = chunk.metadata.get("legalPath", "")
        snippet = " ".join(chunk.text.split())[:preview]
        out.append(
            f"[{index}] type={chunk.chunk_type} tokens={chunk.token_count} "
            f"path={path}\n    {snippet}"
        )
    return "\n".join(out)
