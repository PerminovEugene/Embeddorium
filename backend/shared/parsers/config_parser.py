import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Source "type" values supported by ``Source.type``. "web" (the default) is a
# link to crawl; "xml" is a local directory of XML files to enumerate and
# ingest via the file chain (fetch_file_source -> filter_tax_acts -> ...).
ALLOWED_SOURCE_TYPES = frozenset({"web", "xml"})

DEFAULT_SOURCE_TYPE = "web"
DEFAULT_XML_GLOB = "*.xml"


@dataclass(frozen=True)
class Source:
    description: str
    link: str = ""
    type: str = DEFAULT_SOURCE_TYPE
    path: str | None = None
    glob: str = DEFAULT_XML_GLOB


@dataclass(frozen=True)
class ChunkDocumentSettingsConfig:
    strategy: str | None = None
    chunk_size: int | None = None
    chunk_overlap: int | None = None


@dataclass(frozen=True)
class EmbedChunksSettingsConfig:
    provider: str | None = None
    model: str | None = None
    mock_dim: int | None = None


@dataclass(frozen=True)
class VectorStoreSettingsConfig:
    similarity: str | None = None


@dataclass(frozen=True)
class PipelineSettingsConfig:
    """Per-actor launch settings declared in the config file for a group.

    Every field is optional — whatever a group omits falls back to the global
    env/constant defaults.
    """

    chunk_document: ChunkDocumentSettingsConfig | None = None
    embed_chunks: EmbedChunksSettingsConfig | None = None
    vector_store: VectorStoreSettingsConfig | None = None


@dataclass(frozen=True)
class SourceGroup:
    name: str
    attributes: dict[str, Any]
    sources: list[Source] = field(default_factory=list)
    settings: PipelineSettingsConfig | None = None


@dataclass(frozen=True)
class SourcesConfig:
    groups: list[SourceGroup]


def _parse_web_source(
    *, group_name: str, description: str, source_data: dict
) -> Source:
    link = source_data.get("link")

    if not isinstance(link, str):
        raise ValueError(f"Source link in group '{group_name}' must be a string")

    return Source(description=description, link=link, type=DEFAULT_SOURCE_TYPE)


def _parse_xml_source(
    *, group_name: str, description: str, source_data: dict
) -> Source:
    source_path = source_data.get("path")
    source_glob = source_data.get("glob", DEFAULT_XML_GLOB)

    if not isinstance(source_path, str) or not source_path:
        raise ValueError(
            f"Source path in group '{group_name}' must be a non-empty string"
        )

    if not isinstance(source_glob, str) or not source_glob:
        raise ValueError(
            f"Source glob in group '{group_name}' must be a non-empty string"
        )

    return Source(
        description=description,
        type="xml",
        path=source_path,
        glob=source_glob,
    )


def _opt_str(value: Any, *, group_name: str, field_name: str) -> str | None:
    if value is None or isinstance(value, str):
        return value
    raise ValueError(f"settings.{field_name} in group '{group_name}' must be a string")


def _opt_int(value: Any, *, group_name: str, field_name: str) -> int | None:
    # bool is a subclass of int — reject it explicitly so `true` isn't read as 1.
    if value is None or (isinstance(value, int) and not isinstance(value, bool)):
        return value
    raise ValueError(
        f"settings.{field_name} in group '{group_name}' must be an integer"
    )


def _parse_group_settings(
    *, group_name: str, settings_data: Any
) -> PipelineSettingsConfig | None:
    if settings_data is None:
        return None
    if not isinstance(settings_data, dict):
        raise ValueError(f"Group '{group_name}' settings must be an object")

    chunk = None
    chunk_data = settings_data.get("chunk_document")
    if chunk_data is not None:
        if not isinstance(chunk_data, dict):
            raise ValueError(
                f"settings.chunk_document in group '{group_name}' must be an object"
            )
        chunk = ChunkDocumentSettingsConfig(
            strategy=_opt_str(
                chunk_data.get("strategy"),
                group_name=group_name,
                field_name="chunk_document.strategy",
            ),
            chunk_size=_opt_int(
                chunk_data.get("chunk_size"),
                group_name=group_name,
                field_name="chunk_document.chunk_size",
            ),
            chunk_overlap=_opt_int(
                chunk_data.get("chunk_overlap"),
                group_name=group_name,
                field_name="chunk_document.chunk_overlap",
            ),
        )

    embed = None
    embed_data = settings_data.get("embed_chunks")
    if embed_data is not None:
        if not isinstance(embed_data, dict):
            raise ValueError(
                f"settings.embed_chunks in group '{group_name}' must be an object"
            )
        embed = EmbedChunksSettingsConfig(
            provider=_opt_str(
                embed_data.get("provider"),
                group_name=group_name,
                field_name="embed_chunks.provider",
            ),
            model=_opt_str(
                embed_data.get("model"),
                group_name=group_name,
                field_name="embed_chunks.model",
            ),
            mock_dim=_opt_int(
                embed_data.get("mock_dim"),
                group_name=group_name,
                field_name="embed_chunks.mock_dim",
            ),
        )

    vector = None
    vector_data = settings_data.get("vector_store")
    if vector_data is not None:
        if not isinstance(vector_data, dict):
            raise ValueError(
                f"settings.vector_store in group '{group_name}' must be an object"
            )
        vector = VectorStoreSettingsConfig(
            similarity=_opt_str(
                vector_data.get("similarity"),
                group_name=group_name,
                field_name="vector_store.similarity",
            ),
        )

    return PipelineSettingsConfig(
        chunk_document=chunk, embed_chunks=embed, vector_store=vector
    )


def parse_sources_config(path: str | Path) -> SourcesConfig:
    path = Path(path)

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    groups_data = data.get("groups")

    if not isinstance(groups_data, list):
        raise ValueError("'groups' must be a list")

    groups: list[SourceGroup] = []

    for group_data in groups_data:
        if not isinstance(group_data, dict):
            raise ValueError("Each group must be an object")

        name = group_data.get("name")
        attributes = group_data.get("attributes")
        sources_data = group_data.get("sources")

        if not isinstance(name, str):
            raise ValueError("Group 'name' must be a string")

        if not isinstance(attributes, dict):
            raise ValueError(f"Group '{name}' attributes must be an object")

        if not isinstance(sources_data, list):
            raise ValueError(f"Group '{name}' sources must be a list")

        sources: list[Source] = []

        for source_data in sources_data:
            if not isinstance(source_data, dict):
                raise ValueError(f"Each source in group '{name}' must be an object")

            description = source_data.get("description")
            source_type = source_data.get("type", DEFAULT_SOURCE_TYPE)

            if not isinstance(description, str):
                raise ValueError(
                    f"Source description in group '{name}' must be a string"
                )

            if (
                not isinstance(source_type, str)
                or source_type not in ALLOWED_SOURCE_TYPES
            ):
                raise ValueError(
                    f"Source type in group '{name}' must be one of "
                    f"{sorted(ALLOWED_SOURCE_TYPES)}"
                )

            if source_type == "xml":
                sources.append(
                    _parse_xml_source(
                        group_name=name,
                        description=description,
                        source_data=source_data,
                    )
                )
            else:
                sources.append(
                    _parse_web_source(
                        group_name=name,
                        description=description,
                        source_data=source_data,
                    )
                )

        settings = _parse_group_settings(
            group_name=name, settings_data=group_data.get("settings")
        )

        groups.append(
            SourceGroup(
                name=name,
                attributes=attributes,
                sources=sources,
                settings=settings,
            )
        )

    return SourcesConfig(groups=groups)


if __name__ == "__main__":
    config = parse_sources_config("sources.json")

    for group in config.groups:
        print(group.name)
        print(group.attributes)

        for source in group.sources:
            print(" -", source.description, source.link)
