"""Structured parser for the Estonian legal-act XML format (``Juurakt`` schema).

Where ``xml_parser.XmlParser`` flattens the whole tree into one blob with
``itertext()`` (which is what produced the "title-only" and "everything in one
giant chunk" problems), this module preserves the legal hierarchy:

    oigusakt
      metaandmed / kehtivus / vastuvoetud        -> document metadata
      aktinimi/nimi/pealkiri                      -> act title
      sisu
        osa            (Part)
          peatykk      (Chapter)
            jagu       (Division)
              jaotis   (Subdivision)
                paragrahv   (§ Section)
                  loige     (subsection, e.g. "(1)")
                    alampunkt  (clause, e.g. "1)")
      muutmismarge / avaldamismarge (scattered)   -> amendment history

The parser walks the tree recursively, snapshotting the structural path at each
``paragrahv`` so a § always knows its chapter/division. Amendment markers
(``muutmismarge``) are *removed* from legal body text and collected separately,
so publication/RT references never bleed into the searchable legal text.

This module produces a typed tree only. Turning the tree into chunks is the job
of :mod:`backend.plugins.chunkers.legal_xml.chunker`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional
from xml.etree import ElementTree

# --- tag names (namespace-stripped) ----------------------------------------

TAG_TITLE = "pealkiri"
TAG_PART = "osa"
TAG_CHAPTER = "peatykk"
TAG_DIVISION = "jagu"
TAG_SUBDIVISION = "jaotis"
TAG_SECTION = "paragrahv"
TAG_SUBSECTION = "loige"
TAG_CLAUSE = "alampunkt"
TAG_CONTENT = "sisuTekst"
TAG_AMENDMENT = "muutmismarge"
TAG_PUBLICATION = "avaldamismarge"
TAG_SUP = "sup"
TAG_METADATA = "metaandmed"

_NUMBER_SUFFIX = {
    TAG_PART: "Nr",
    TAG_CHAPTER: "Nr",
    TAG_DIVISION: "Nr",
    TAG_SUBDIVISION: "Nr",
}
_TITLE_SUFFIX = {
    TAG_PART: "Pealkiri",
    TAG_CHAPTER: "Pealkiri",
    TAG_DIVISION: "Pealkiri",
    TAG_SUBDIVISION: "Pealkiri",
}

# Text inside these subtrees is metadata, never legal body text.
_BODY_EXCLUDE = (TAG_AMENDMENT,)

_SUP_CHARS = "⁰¹²³⁴⁵⁶⁷⁸⁹"
_SUPERSCRIPT = str.maketrans("0123456789", _SUP_CHARS)
# Numbering can carry a superscript either as a real ``<sup>`` element or, more
# commonly, as literal ``<sup>..</sup>`` markup inside a CDATA section (e.g.
# ``(2<sup>1</sup>)``); both are normalized to Unicode superscript digits.
_SUP_MARKUP_RE = re.compile(r"<sup>(.*?)</sup>", re.IGNORECASE | re.DOTALL)
_SECTION_NUM_RE = re.compile(rf"§\s*([0-9{_SUP_CHARS}]+)")


def _strip_ns(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _normalize_sup(text: str) -> str:
    return _SUP_MARKUP_RE.sub(lambda m: m.group(1).translate(_SUPERSCRIPT), text)


def _collapse(text: str) -> str:
    return _normalize_sup(" ".join(text.split()))


def _node_text(elem: ElementTree.Element, exclude=_BODY_EXCLUDE) -> str:
    """Concatenate an element's text, skipping ``exclude`` subtrees.

    ``sup`` children are rendered as Unicode superscripts so that ``§ 3<sup>1</sup>``
    becomes ``§ 3¹`` instead of the misleading ``§ 31``.
    """
    parts: List[str] = []

    def rec(node: ElementTree.Element, is_root: bool) -> None:
        tag = _strip_ns(node.tag)
        if tag in exclude:
            if not is_root and node.tail:
                parts.append(node.tail)
            return
        if tag == TAG_SUP:
            parts.append("".join(node.itertext()).translate(_SUPERSCRIPT))
            if node.tail:
                parts.append(node.tail)
            return
        if node.text:
            parts.append(node.text)
        for child in node:
            rec(child, False)
        if not is_root and node.tail:
            parts.append(node.tail)

    rec(elem, True)
    return _collapse("".join(parts))


def _direct_child_text(elem: ElementTree.Element, tag: str) -> str:
    for child in elem:
        if _strip_ns(child.tag) == tag:
            return _node_text(child)
    return ""


# --- typed tree ------------------------------------------------------------


@dataclass
class StructuralPath:
    """The structural ancestry of a § (everything above ``paragrahv``)."""

    part_number: str = ""
    part_title: str = ""
    chapter_number: str = ""
    chapter_title: str = ""
    division_number: str = ""
    division_title: str = ""
    subdivision_number: str = ""
    subdivision_title: str = ""

    def with_part(self, number: str, title: str) -> "StructuralPath":
        # A new Part resets everything below it.
        return StructuralPath(part_number=number, part_title=title)

    def with_chapter(self, number: str, title: str) -> "StructuralPath":
        return StructuralPath(
            part_number=self.part_number,
            part_title=self.part_title,
            chapter_number=number,
            chapter_title=title,
        )

    def with_division(self, number: str, title: str) -> "StructuralPath":
        return StructuralPath(
            part_number=self.part_number,
            part_title=self.part_title,
            chapter_number=self.chapter_number,
            chapter_title=self.chapter_title,
            division_number=number,
            division_title=title,
        )

    def with_subdivision(self, number: str, title: str) -> "StructuralPath":
        return StructuralPath(
            part_number=self.part_number,
            part_title=self.part_title,
            chapter_number=self.chapter_number,
            chapter_title=self.chapter_title,
            division_number=self.division_number,
            division_title=self.division_title,
            subdivision_number=number,
            subdivision_title=title,
        )

    def chapter_key(self) -> str:
        """Identity used to forbid chunks from spanning chapters."""
        return f"{self.part_number}|{self.chapter_number}"

    def parent_key(self) -> str:
        """Immediate-parent identity used when merging very short sections."""
        return (
            f"{self.part_number}|{self.chapter_number}|"
            f"{self.division_number}|{self.subdivision_number}"
        )


@dataclass
class Clause:
    """``alampunkt`` — e.g. ``1) enabling berthing of water craft;``."""

    number: str
    display: str
    text: str

    def render(self) -> str:
        prefix = self.display.strip()
        if prefix:
            return f"{prefix} {self.text}".strip()
        return self.text


@dataclass
class Subsection:
    """``loige`` — e.g. ``(1) ...`` optionally with nested clauses."""

    number: str
    display: str
    text: str
    clauses: List[Clause] = field(default_factory=list)
    index: int = 0  # 1-based position within the section, for range splitting

    @property
    def label(self) -> str:
        """Human label for subsection-range headers, e.g. ``(1)``."""
        disp = self.display.strip()
        if disp:
            return disp
        if self.number:
            return f"({self.number})"
        return f"({self.index})"

    def render(self) -> str:
        head = self.display.strip()
        body = self.text
        lines: List[str] = []
        if head and body:
            lines.append(f"{head} {body}")
        elif head:
            lines.append(head)
        elif body:
            lines.append(body)
        for clause in self.clauses:
            lines.append(clause.render())
        return "\n".join(line for line in lines if line)


@dataclass
class Section:
    """``paragrahv`` — a single § section, the default chunk unit."""

    path: StructuralPath
    number: str
    display: str
    title: str
    subsections: List[Subsection] = field(default_factory=list)
    intro_text: str = ""

    @property
    def section_number(self) -> str:
        """Logical number such as ``4`` or ``25`` or ``3¹`` (from display)."""
        m = _SECTION_NUM_RE.search(self.display.strip())
        if m:
            return m.group(1)
        return self.number


@dataclass
class AmendmentMark:
    """A single ``muutmismarge`` / ``avaldamismarge`` entry."""

    rt_part: str = ""
    published: str = ""
    article: str = ""
    act_reference: str = ""
    in_force: str = ""
    context: str = ""  # legal path where the amendment was attached

    def render(self) -> str:
        ref = ", ".join(p for p in (self.rt_part, self.published, self.article) if p)
        bits = []
        if ref:
            bits.append(f"RT {ref}" if not ref.startswith("RT") else ref)
        if self.in_force:
            bits.append(f"in force {self.in_force}")
        if self.context:
            bits.append(f"[{self.context}]")
        return " - ".join(bits)


@dataclass
class LegalDocument:
    title: str
    source_url: str = ""
    language: str = "en"
    document_id: str = ""
    sections: List[Section] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    amendments: List[AmendmentMark] = field(default_factory=list)


# --- parsing ---------------------------------------------------------------


def _parse_publication(elem: ElementTree.Element, context: str = "") -> AmendmentMark:
    return AmendmentMark(
        rt_part=_direct_child_text(elem, "RTosa"),
        published=_direct_child_text(elem, "avaldamineKuupaev"),
        article=_direct_child_text(elem, "RTartikkel"),
        act_reference=_direct_child_text(elem, "aktViide"),
        context=context,
    )


def _build_clause(elem: ElementTree.Element) -> Clause:
    return Clause(
        number=_direct_child_text(elem, "alampunktNr"),
        display=_direct_child_text(elem, "kuvatavNr"),
        text=_subtree_content_text(elem),
    )


def _subtree_content_text(elem: ElementTree.Element) -> str:
    """Text of the *direct* ``sisuTekst`` children of ``elem`` (no nested clauses)."""
    parts: List[str] = []
    for child in elem:
        if _strip_ns(child.tag) == TAG_CONTENT:
            parts.append(_node_text(child))
    return _collapse(" ".join(p for p in parts if p))


def _build_subsection(elem: ElementTree.Element, index: int) -> Subsection:
    clauses = [
        _build_clause(child) for child in elem if _strip_ns(child.tag) == TAG_CLAUSE
    ]
    return Subsection(
        number=_direct_child_text(elem, "loigeNr"),
        display=_direct_child_text(elem, "kuvatavNr"),
        text=_subtree_content_text(elem),
        clauses=clauses,
        index=index,
    )


def _build_section(elem: ElementTree.Element, path: StructuralPath) -> Section:
    subsections: List[Subsection] = []
    for child in elem:
        if _strip_ns(child.tag) == TAG_SUBSECTION:
            subsections.append(_build_subsection(child, index=len(subsections) + 1))
    return Section(
        path=path,
        number=_direct_child_text(elem, "paragrahvNr"),
        display=_direct_child_text(elem, "kuvatavNr"),
        title=_direct_child_text(elem, "paragrahvPealkiri"),
        subsections=subsections,
        intro_text=_subtree_content_text(elem),
    )


def _legal_path_str(path: StructuralPath, title: str) -> str:
    bits = [title] if title else []
    if path.part_number or path.part_title:
        bits.append(f"Part {path.part_number}".strip())
    if path.chapter_number or path.chapter_title:
        bits.append(f"Chapter {path.chapter_number}".strip())
    if path.division_number or path.division_title:
        bits.append(f"Division {path.division_number}".strip())
    return " > ".join(bits)


class LegalXmlReader:
    """Parses Estonian act XML into a :class:`LegalDocument` tree."""

    def parse(
        self, content: str, source_url: str = "", language: str = "en"
    ) -> Optional[LegalDocument]:
        try:
            root = ElementTree.fromstring(content)
        except ElementTree.ParseError:
            return None
        if _strip_ns(root.tag) != "oigusakt":
            return None

        title = self._extract_title(root)
        doc = LegalDocument(
            title=title,
            source_url=source_url,
            language=language,
            metadata=self._extract_metadata(root),
        )
        doc.document_id = str(doc.metadata.get("globalId") or "")

        sections: List[Section] = []
        amendments: List[AmendmentMark] = []
        self._walk(root, StructuralPath(), title, sections, amendments, in_body=False)
        doc.sections = sections
        doc.amendments = amendments
        return doc

    # -- helpers ------------------------------------------------------------

    def _extract_title(self, root: ElementTree.Element) -> str:
        for elem in root.iter():
            if _strip_ns(elem.tag) == TAG_TITLE:
                return _node_text(elem)
        return ""

    def _extract_metadata(self, root: ElementTree.Element) -> dict:
        meta: dict = {}
        simple = {
            "valjaandja": "publisher",
            "dokumentLiik": "documentKind",
            "globaalID": "globalId",
            "skeemiNimi": "schemaName",
            "tekstiliik": "textKind",
            "dokumentStaatus": "documentStatus",
            "kehtivuseAlgus": "validFrom",
            "kehtivuseLopp": "validUntil",
            "metaandmedVersioonKuupaev": "metadataVersionDate",
        }
        for elem in root.iter():
            tag = _strip_ns(elem.tag)
            if tag in simple and simple[tag] not in meta:
                value = _node_text(elem)
                if value:
                    meta[simple[tag]] = value
        schema_loc = root.attrib.get(
            "{http://www.w3.org/2001/XMLSchema-instance}schemaLocation"
        )
        if schema_loc:
            meta["schemaLocation"] = schema_loc
        if root.attrib.get("id"):
            meta["xmlId"] = root.attrib["id"]
        return meta

    def _walk(
        self,
        elem: ElementTree.Element,
        path: StructuralPath,
        title: str,
        sections: List[Section],
        amendments: List[AmendmentMark],
        in_body: bool,
    ) -> None:
        tag = _strip_ns(elem.tag)

        if tag == TAG_AMENDMENT:
            context = _legal_path_str(path, title) if in_body else ""
            for pub in elem:
                if _strip_ns(pub.tag) == TAG_PUBLICATION:
                    mark = _parse_publication(pub, context)
                    mark.in_force = _direct_child_text(elem, "joustumine")
                    amendments.append(mark)
            return

        if tag == TAG_SECTION:
            sections.append(_build_section(elem, path))
            # Amendment marks attached anywhere inside the § are still collected.
            for child in elem:
                self._walk(child, path, title, sections, amendments, in_body=True)
            return

        new_path = path
        if tag == TAG_PART:
            new_path = path.with_part(
                _direct_child_text(elem, "osaNr"),
                _direct_child_text(elem, "osaPealkiri"),
            )
            in_body = True
        elif tag == TAG_CHAPTER:
            new_path = path.with_chapter(
                _direct_child_text(elem, "peatykkNr"),
                _direct_child_text(elem, "peatykkPealkiri"),
            )
            in_body = True
        elif tag == TAG_DIVISION:
            new_path = path.with_division(
                _direct_child_text(elem, "jaguNr"),
                _direct_child_text(elem, "jaguPealkiri"),
            )
        elif tag == TAG_SUBDIVISION:
            new_path = path.with_subdivision(
                _direct_child_text(elem, "jaotisNr"),
                _direct_child_text(elem, "jaotisPealkiri"),
            )

        for child in elem:
            self._walk(child, new_path, title, sections, amendments, in_body)
