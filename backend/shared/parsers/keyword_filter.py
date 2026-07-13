"""Generic keyword relevance filter for the document ingestion pipeline.

``filter_documents`` uses this to gate which documents advance through the
pipeline based on a caller-supplied keyword list. When no keywords are provided
the filter is a pass-through — every document is considered relevant.

For the *include* gate (:func:`matches_keywords`) the title is authoritative:
any keyword match there is sufficient. If the title is empty (or matches
nothing), the raw text is consulted as a fallback so that untitled documents
are not silently dropped.

For the *exclude* gate (:func:`matches_any`) the title and body are consulted
together on every call, so an unwanted keyword anywhere drops the document.
"""

from __future__ import annotations

import re
from typing import Iterable, List, Optional


def _compile_patterns(keywords: Iterable[str]) -> List:
    """Return compiled whole-word, case-insensitive patterns for *keywords*."""
    return [
        re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE)
        for kw in keywords
        if kw
    ]


def _any_match(text: str, patterns: List) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def matches_keywords(
    title: str,
    text: Optional[str] = None,
    *,
    keywords: Optional[Iterable[str]] = None,
) -> bool:
    """Return ``True`` if the document matches the keyword list.

    Pass-through semantics: when ``keywords`` is falsy or empty, every document
    is considered relevant (returns ``True``). This allows the actor to be
    disabled or left unconfigured without filtering out any documents.

    When ``keywords`` is provided, each keyword is matched as a whole word
    (case-insensitive) against ``title`` first. If ``title`` is empty the same
    patterns are applied to ``text`` as a fallback.

    Parameters
    ----------
    title:
        Primary field to match against (e.g. document or article title).
    text:
        Raw document text consulted only when ``title`` is empty.
    keywords:
        Iterable of keyword strings. ``None`` or an empty iterable triggers the
        pass-through — the function returns ``True`` immediately.
    """
    if not keywords:
        return True

    patterns = _compile_patterns(keywords)
    if not patterns:
        return True

    if title and _any_match(title, patterns):
        return True

    if not title and text:
        return _any_match(text, patterns)

    return False


def matches_any(
    title: Optional[str],
    text: Optional[str] = None,
    *,
    keywords: Optional[Iterable[str]] = None,
) -> bool:
    """Return ``True`` if any keyword matches *either* the title or the text.

    Unlike :func:`matches_keywords` (title-authoritative, body only as a
    fallback for untitled docs), this consults the title and the body together
    on every call. It exists for the *exclude* gate, where a keyword appearing
    anywhere — title or body — must drop the document.

    An empty/absent ``keywords`` iterable returns ``False``: with nothing to
    exclude, no document is excluded.
    """
    if not keywords:
        return False

    patterns = _compile_patterns(keywords)
    if not patterns:
        return False

    combined = "\n".join(part for part in (title, text) if part)
    return _any_match(combined, patterns)
