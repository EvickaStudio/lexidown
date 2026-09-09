"""Native and Python parser compatibility at malformed HTML boundaries."""

import unittest

import html5lib

from lexidown import TurndownService
from lexidown.html_parser import HTMLParser


class ParserCompatibility(unittest.TestCase):
    def test_domino_special_elements_in_both_parsers(self):
        cases = [
            ("<span><figcaption>a</span>b", "ab"),
            ("<i><figcaption>x</i>", "_x_"),
            ("<li><main>a<li>b", "*   a*   b"),
            ("<i><command>x</i>y", "_x_y"),
            ("<b>a<summary>b</b>c", "**a****b**c"),
            ("<select><template>", ""),
        ]
        for html, expected in cases:
            with self.subTest(html=html):
                self.assertEqual(TurndownService().turndown(html), expected)
                document = HTMLParser().parse(html)
                self.assertEqual(TurndownService().turndown(document), expected)

    def test_compatibility_does_not_modify_html5lib_globally(self):
        html = "<i><figcaption>x</i>"
        before = html5lib.parse(html, treebuilder="dom").toxml()
        HTMLParser().parse(html)
        after = html5lib.parse(html, treebuilder="dom").toxml()
        self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
