"""Per-format parser plugins for ``parse_source``.

Each module here contributes one
:class:`~backend.plugins.parse_source.formats.base.FormatParser` — a near-pure
``(content, url) -> text`` handler for a specific content type (HTML, XML, plain
text). They are auto-discovered exactly like every other strategy plugin, so a
user adds a new format, swaps the library behind an existing one, or drops in a
custom parser by adding/replacing a single module here — no registry edits.

The ``content_type`` parse strategy selects among them (by explicit override or
by the fetched source's content type); see
:mod:`backend.plugins.parse_source.formats.registry`.
"""
