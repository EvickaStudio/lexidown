"""Serialization regressions checked against the bundled Domino oracle."""

import unittest
from xml.dom import minidom

from lexidown import TurndownService
from lexidown.dom import Node


class Serialization(unittest.TestCase):
    def test_kept_void_elements_and_plaintext(self):
        cases = [
            (
                "<div>x<basefont color=red>y</div>",
                '<div>x<basefont color="red">y</div>',
            ),
            ("<div>x<bgsound src=x>y</div>", '<div>x<bgsound src="x">y</div>'),
            (
                "<div><plaintext>x <b>y</b>&amp;</plaintext></div>",
                "<div><plaintext>x <b>y</b>&amp;&lt;/plaintext></div>"
                "</x-turndown></plaintext></div>",
            ),
            (
                "<div><noscript>&lt;b&gt;&amp;</noscript></div>",
                "<div><noscript><b>&</noscript></div>",
            ),
        ]
        for html, expected in cases:
            with self.subTest(html=html):
                self.assertEqual(TurndownService().keep("div").turndown(html), expected)
        document = minidom.Document()
        for name in ("basefont", "bgsound", "frame", "command"):
            element = document.createElement(name)
            element.appendChild(document.createTextNode("child"))
            expected = "<command>child</command>" if name == "command" else f"<{name}>"
            self.assertEqual(Node(element).outerHTML, expected)

    def test_raw_closing_tag_escaping_spans_text_nodes(self):
        document = minidom.Document()
        for name in (
            "style",
            "script",
            "xmp",
            "iframe",
            "noembed",
            "noframes",
            "plaintext",
        ):
            for prefix in ("", "🙂"):
                with self.subTest(name=name, prefix=prefix):
                    element = document.createElement(name)
                    element.appendChild(document.createTextNode(prefix + "</"))
                    element.appendChild(document.createTextNode(name + ">"))
                    node = Node(element)
                    self.assertEqual(node.innerHTML, prefix + f"</{name}>")
                    escaped = f"🙂<&lt;{name}>" if prefix else f"&lt;/{name}>"
                    self.assertEqual(node.outerHTML, f"<{name}>{escaped}</{name}>")
        element = document.createElement("style")
        element.appendChild(document.createTextNode("🙂" * 20 + "</style>"))
        self.assertEqual(
            Node(element).outerHTML,
            "<style>" + "🙂" * 20 + "</style>&lt;</style>",
        )

    def test_comment_and_processing_instruction_escaping(self):
        document = minidom.Document()
        element = document.createElement("pre")
        element.appendChild(document.createComment("a --> b --!> c >"))
        element.appendChild(document.createProcessingInstruction("target", "a > b"))
        self.assertEqual(
            Node(element).outerHTML,
            "<pre><!--a --&gt; b --!&gt; c >--><?target a &gt; b?></pre>",
        )

    def test_noscript_serialization_retains_explicit_scripting_flag(self):
        document = minidom.Document()
        element = document.createElement("noscript")
        element.appendChild(document.createTextNode("<b>&"))
        for enabled, content in ((False, "&lt;b&gt;&amp;"), (True, "<b>&")):
            document._scripting_enabled = enabled
            for node in (Node(element), Node(element).cloneNode(True)):
                self.assertEqual(node.innerHTML, content)
                self.assertEqual(node.outerHTML, f"<noscript>{content}</noscript>")
