import re
from typing_extensions import TypedDict

LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


class LinkInfo(TypedDict):
    label: str
    url: str


class LinkExtractor:
    def extract_links(self, markdown: str) -> list[LinkInfo]:
        links: list[LinkInfo] = []

        for match in LINK_RE.finditer(markdown):
            links.append(
                {
                    "label": match.group(1),
                    "url": match.group(2),
                }
            )

        return links
