"""Check cached DOM metadata against the tree it summarizes."""

import unittest

from lexidown.dom import root_node
from lexidown.utilities import (
    JS_WS,
    MEANINGFUL_WHEN_BLANK_ELEMENTS,
    VOID_ELEMENTS,
)


class DOMMetadata(unittest.TestCase):
    def test_metadata_matches_text_and_descendants(self):
        root = root_node(
            "<div>\xa0<em> x </em>\u202f<b> \ufeff </b><img src='/x'></div>"
            "<pre><!-- ignored --> <code>\ntext\n</code> </pre>"
            "<div><a href='/x'></a><span></span></div>"
            "<svg><linearGradient><text> value </text></linearGradient></svg>",
            {},
        )
        pending = [root]
        while pending:
            node = pending.pop()
            pending.extend(node.childNodes)
            if node.nodeType not in (1, 3):
                continue
            text = node.textContent
            self.assertEqual(node._blank_text, not text.strip(JS_WS))
            descendants = {child.nodeName for child in node.getElementsByTagName("*")}
            self.assertEqual(node._has_void, bool(descendants & VOID_ELEMENTS))
            self.assertEqual(
                node._has_meaningful,
                bool(descendants & MEANINGFUL_WHEN_BLANK_ELEMENTS),
            )
            index = node._text_index[0]
            self.assertEqual(index[node._text_start : node._text_end], text)
            self.assertEqual(
                index[node._text_start : node._leading_end],
                text[: len(text) - len(text.lstrip(JS_WS))],
            )
            if not node._blank_text:
                self.assertEqual(
                    index[node._trailing_start : node._text_end],
                    text[len(text.rstrip(JS_WS)) :],
                )
