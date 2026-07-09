"""Local-file validation strategy: path resolution + exists/readable checks.

Resolves the seeded path to its absolute form (``normalized_url`` becomes the
``file://`` URL used for dedup) and rejects sources whose file does not exist
or is not readable — the gate the old file chain lacked (it only discovered a
missing file at read time, after the target row was already created).
"""

from __future__ import annotations

import os
from pathlib import Path

from backend.plugins.validate_source.base import (
    NormalizedSource,
    SourceValidationError,
    SourceValidationStrategy,
    ValidationStrategyConfig,
)
from backend.shared.clients.queue.validate_source_payload import ValidateSourcePayload
from backend.shared.models import ValidateSourceSettings
from backend.shared.storage.sql.sql_store import SqlStore

_FILE_SCHEME = "file://"


class LocalFileSourceValidation(SourceValidationStrategy):
    config = ValidationStrategyConfig(
        name="local",
        label="Local file",
        description=(
            "Resolves the path to its absolute form and rejects files that "
            "do not exist or are not readable."
        ),
    )

    def normalize(
        self, *, payload: ValidateSourcePayload, settings: ValidateSourceSettings
    ) -> NormalizedSource:
        raw = payload.url.removeprefix(_FILE_SCHEME)
        abs_path = str(Path(raw).resolve())
        return NormalizedSource(
            original_url=abs_path,
            normalized_url=f"{_FILE_SCHEME}{abs_path}",
        )

    def validate(
        self,
        *,
        payload: ValidateSourcePayload,
        source: NormalizedSource,
        store: SqlStore,
    ) -> None:
        path = Path(source.original_url)
        if not path.is_file():
            raise SourceValidationError(
                "file_not_found", f"no file at {source.original_url}"
            )
        if not os.access(path, os.R_OK):
            raise SourceValidationError(
                "file_not_readable", f"file at {source.original_url} is not readable"
            )
