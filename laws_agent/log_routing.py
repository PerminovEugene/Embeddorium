"""Per-URL file logging.

Every crawl target gets its own nested log folder (mirroring the discovery
chain: a link found inside a page's content logs into a subfolder of that
page's folder). ``crawl_target.log_dir`` holds the relative path; actors
activate it for the duration of one message via :func:`log_to`, and the
:class:`ContextRoutingFileHandler` installed on the root logger fans every
record out to the right file based on the current ``contextvars`` value.

This makes per-URL routing transparent to actor code: handlers keep logging
via the normal ``logging`` module, and whichever file the *currently active*
context points at receives a copy of the record (stdout still gets
everything, unconditionally, via the existing ``StreamHandler``).
"""

from __future__ import annotations

import hashlib
import logging
import threading
from contextlib import contextmanager
from contextvars import ContextVar, Token
from pathlib import Path
from typing import Iterator, Optional
from urllib.parse import urlparse

from laws_agent import config

# Keep nested paths filesystem-safe: cap each slug, and cap how deep the
# discovery chain may nest. Each folder name is a complete slug (never split),
# and deep chains drop whole leading folders rather than truncating mid-name.
_MAX_SLUG_LENGTH = 60
_HASH_SUFFIX_LENGTH = 8
_MAX_DEPTH = 12

LOG_ROOT: Path = Path(config.LOG_DIR)

_current_log_dir: ContextVar[Optional[str]] = ContextVar(
    "current_log_dir", default=None
)


def _slugify(url: str) -> str:
    """Turn ``netloc + path`` into a short, filesystem-safe slug."""
    parsed = urlparse(url)
    raw = f"{parsed.netloc}{parsed.path}".lower().strip("/")
    slug = "".join(c if c.isalnum() else "_" for c in raw)
    while "__" in slug:
        slug = slug.replace("__", "_")
    slug = slug.strip("_") or "root"
    return slug[:_MAX_SLUG_LENGTH]


def build_log_dir(
    *, url: str, normalized_url: str, parent_log_dir: Optional[str] = None
) -> str:
    """Build the relative ``log_dir`` for a crawl target.

    The slug comes from ``url`` (human-readable); a short hash of
    ``normalized_url`` is appended to keep folder names collision-safe even
    when two URLs slugify to the same string. When ``parent_log_dir`` is
    given, the result is nested inside it, mirroring the discovery chain.
    """
    digest = hashlib.sha256(normalized_url.encode("utf-8")).hexdigest()
    leaf = f"{_slugify(url)}-{digest[:_HASH_SUFFIX_LENGTH]}"

    components = parent_log_dir.split("/") if parent_log_dir else []
    components.append(leaf)
    # Bound the path by nesting depth, dropping whole leading folders so every
    # surviving component stays a complete, valid slug (never split mid-name).
    return "/".join(components[-_MAX_DEPTH:])


@contextmanager
def log_to(log_dir: Optional[str]) -> Iterator[None]:
    """Activate per-URL file routing for the current context.

    No-op when ``log_dir`` is ``None`` (e.g. the target has none set yet),
    so callers can always wrap their handler body in this context manager.
    """
    if log_dir is None:
        yield
        return

    token: Token = _current_log_dir.set(log_dir)
    try:
        yield
    finally:
        _current_log_dir.reset(token)


class ContextRoutingFileHandler(logging.Handler):
    """Routes log records to ``<LOG_ROOT>/<log_dir>/<leaf>.log``.

    ``log_dir`` is read from a ``contextvars.ContextVar`` on every ``emit``,
    so concurrent dramatiq worker threads each route to their own file
    without interfering with one another. When no context is active the
    handler does nothing — stdout already covers that case.
    """

    def __init__(self, log_root: Path, formatter: logging.Formatter) -> None:
        super().__init__()
        self._log_root = log_root
        self.setFormatter(formatter)
        self._streams: dict[Path, "logging.TextIO"] = {}
        self._lock = threading.Lock()

    def emit(self, record: logging.LogRecord) -> None:
        log_dir = _current_log_dir.get()
        if log_dir is None:
            return

        try:
            file_path = self._file_path_for(log_dir)
            message = self.format(record)
            stream = self._stream_for(file_path)
            with self._lock:
                stream.write(message + "\n")
                stream.flush()
        except Exception:
            self.handleError(record)

    def _file_path_for(self, log_dir: str) -> Path:
        leaf = Path(log_dir).name
        return self._log_root / log_dir / f"{leaf}.log"

    def _stream_for(self, file_path: Path) -> "logging.TextIO":
        with self._lock:
            stream = self._streams.get(file_path)
            if stream is None:
                file_path.parent.mkdir(parents=True, exist_ok=True)
                stream = file_path.open("a", encoding="utf-8")
                self._streams[file_path] = stream
            return stream

    def close(self) -> None:
        with self._lock:
            for stream in self._streams.values():
                stream.close()
            self._streams.clear()
        super().close()


def install_file_routing(
    root_logger: logging.Logger, formatter: logging.Formatter
) -> None:
    """Attach the routing handler to ``root_logger`` exactly once."""
    already_installed = any(
        isinstance(handler, ContextRoutingFileHandler) for handler in root_logger.handlers
    )
    if already_installed:
        return

    handler = ContextRoutingFileHandler(LOG_ROOT, formatter)
    root_logger.addHandler(handler)
