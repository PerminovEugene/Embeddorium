"""The one field-descriptor dataclass shared by every plugin kind.

A :class:`FieldSpec` describes a single UI-configurable setting a plugin
exposes so the web UI can render a form for it: a labelled input of a known
``type``, with an optional default/range/option-list/placeholder and a
``required`` flag. Every strategy package (chunkers, fetch_source,
validate_source, embed_chunks, filter_documents, parse_source) declares its
configs' ``fields`` with this exact type, and the API serves them camelCased
the same way for all of them — one schema, one frontend contract.

``key`` is the *exact* snake_case key the value is stored/read under in the
relevant ``*Settings`` model (e.g. ``ChunkDocumentSettings.settings`` or
``FetchSourceSettings.verify_tls``); it is never transformed, even though the
API layer camelCases every other JSON object key. Keeping it verbatim is what
lets the UI round-trip the value straight back into the settings dict.

``type`` vocabulary
-------------------
``"text"`` | ``"number"`` | ``"checkbox"`` | ``"select"`` — the same set the
chunker plugins have always used — plus ``"provider_id"`` for fields whose
value selects a configured LLM/embedding :class:`~backend.shared.models.
provider.Provider` (the UI renders a provider picker; how the picked provider
is materialised into the stored value is a frontend/run-creation concern).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class FieldSpec:
    """One UI-configurable setting exposed by a plugin's static config.

    ``key`` is the exact snake_case storage key (never camelCased). ``type``
    is one of ``"text" | "number" | "checkbox" | "select" | "provider_id"``.
    ``min``/``max`` bound numeric inputs, ``options`` lists the choices of a
    ``"select"`` field (``[{"value": ..., "label": ...}, ...]``),
    ``placeholder`` is an optional hint, and ``required`` marks a field the UI
    must not leave blank.
    """

    key: str
    label: str
    type: str
    default: Any
    min: Optional[int] = None
    max: Optional[int] = None
    options: Optional[List[Dict[str, Any]]] = None
    placeholder: Optional[str] = None
    required: bool = False
