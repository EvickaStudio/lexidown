"""Check cached DOM metadata against the tree it summarizes."""

import random
import re
import unittest

from lexidown._native import _collapse_text
from lexidown.dom import Node, collapse_whitespace, root_node
from lexidown.native_parser import parse_html
from lexidown.utilities import (
    JS_WS,
    MEANINGFUL_WHEN_BLANK_ELEMENTS,
    VOID_ELEMENTS,
)


class DOMMetadata(unittest.TestCase):
    def test_whitespace_traversal_respects_subclass_properties(self):
        class LastFirst(Node):
            @property
            def firstChild(self):
                return self.lastChild

        document = parse_html(
            "<div><span> first   </span><span> second   </span></div>"
        )
        root = LastFirst(document.getElementsByTagName("div")[0])
        collapse_whitespace(root)
        self.assertEqual(root.innerHTML, "<span> first   </span><span>second</span>")

        class FalseNode(Node):
            def __bool__(self):
                return False

        root = parse_html("<div>first</div>").getElementsByTagName("div")[0]
        child = FalseNode(
            parse_html("<span> second    text </span>").getElementsByTagName("span")[0]
        )
        root.appendChild(child)
        collapse_whitespace(root)
        self.assertEqual(root.innerHTML, "first<span> second    text </span>")

    def test_native_text_collapse_matches_ascii_whitespace_regex(self):
        randomizer = random.Random(20260910)
        alphabet = "ab \t\r\n" + JS_WS + "\x00\u0085é中🙂\ud800"
        cases = ["", "plain text", " \t\r\n", "é\n中\t🙂", "a " * 10000]
        cases.extend(
            "".join(randomizer.choices(alphabet, k=length)) for length in range(256)
        )
        for text in cases:
            with self.subTest(text=text):
                self.assertEqual(_collapse_text(text), re.sub(r"[ \r\n\t]+", " ", text))

    def test_metadata_matches_text_and_descendants(self):
        root = root_node(
            "<div>\xa0<em> x </em>\u202f<b> \ufeff </b><img src='/x'></div>"
            "<pre><!-- ignored --> <code>\ntext\n</code> </pre>"
            "<div><a href='/x'></a><span></span></div>"
            "<svg><linearGradient><text> value </text></linearGradient></svg>"
            f"<pre>{JS_WS}\x85{JS_WS}</pre><pre>{JS_WS}</pre>",
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
