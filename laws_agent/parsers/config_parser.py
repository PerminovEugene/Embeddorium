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
class SourceGroup:
    name: str
    attributes: dict[str, Any]
    sources: list[Source] = field(default_factory=list)


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

        groups.append(
            SourceGroup(
                name=name,
                attributes=attributes,
                sources=sources,
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
