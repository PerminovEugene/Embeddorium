import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Source:
    description: str
    link: str


@dataclass(frozen=True)
class SourceGroup:
    name: str
    attributes: dict[str, Any]
    sources: list[Source]


@dataclass(frozen=True)
class SourcesConfig:
    groups: list[SourceGroup]


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
            link = source_data.get("link")

            if not isinstance(description, str):
                raise ValueError(f"Source description in group '{name}' must be a string")

            if not isinstance(link, str):
                raise ValueError(f"Source link in group '{name}' must be a string")

            sources.append(
                Source(
                    description=description,
                    link=link,
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