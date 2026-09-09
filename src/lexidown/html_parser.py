"""DOM parsing through the same native parser used by conversion."""

from ._native import parse_html


class HTMLParser:
    """Retain the parser entry point for callers constructing DOM input."""

    def parse(self, text):
        return parse_html(text)
