import trafilatura

class HtmlParser:
    def parse(self, html: str, url: str = "") -> str:
        text = trafilatura.extract(
            html,
            url=url,
            favor_precision=True,
            include_links=True,
            include_images=False,
            include_comments=False,
            output_format="markdown",
        ) or ""
        return text
