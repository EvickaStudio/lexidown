"""Firecrawl-style inline links with the bundled Joplin GFM preset.

Reference: https://github.com/firecrawl/firecrawl/blob/4d9847872f3c8e89ff7080e48778c778c04b3fb3/apps/api/src/lib/html-to-markdown.ts#L114-L129
This variant brackets link targets and escapes link titles.
"""

from ..utilities import js_trim
from .joplin_gfm import gfm

__all__ = ["firecrawl"]


def firecrawl(service):
    """Enable GFM and inline links with bracketed targets and trailing newlines."""

    def inline_link(content, node):
        href = js_trim(node.getAttribute("href"))
        title = node.getAttribute("title") or ""
        title = title.replace("\\", "\\\\").replace('"', '\\"')
        title_part = f' "{title}"' if title else ""
        return f"[{js_trim(content)}](<{href}>{title_part})\n"

    service.addRule(
        "inlineLink",
        {
            "filter": lambda node, options: (
                options["linkStyle"] == "inlined"
                and node.nodeName == "A"
                and bool(node.getAttribute("href"))
            ),
            "replacement": inline_link,
        },
    )
    service.use(gfm)
