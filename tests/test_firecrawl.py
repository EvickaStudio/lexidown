"""Firecrawl-style links checked with Turndown 7.2.4 and Joplin GFM 1.0.68."""

import unittest

from lexidown import TurndownService
from lexidown.plugins.firecrawl import firecrawl
from lexidown.plugins.joplin_gfm import gfm


class FirecrawlPreset(unittest.TestCase):
    def test_inline_link_formatting(self):
        service = TurndownService().use(firecrawl)
        cases = {
            '<p>Before <a href="/a"> Alpha </a> between <a href="/b"> Beta </a> after.</p>': (
                "Before [Alpha](</a>)\n between [Beta](</b>)\n after."
            ),
            '<a href=" /path " title="a &quot;quote&quot;">Label</a>': '[Label](</path "a "quote"">)',
            '<a href=" ">X</a>': "[X](<>)",
            '<a href="/x"></a>': "[](</x>)",
            '<p><a>No href</a> <a href="">Empty href</a></p>': "No href Empty href",
            '<ul><li><a href="/x" role="checkbox" aria-checked="true">Done</a></li></ul>': (
                "*   [x]"
            ),
        }
        for html, expected in cases.items():
            with self.subTest(html=html):
                self.assertEqual(service.turndown(html), expected)

    def test_gfm_composes_with_link_override(self):
        service = TurndownService().use(firecrawl)
        self.assertEqual(
            service.turndown(
                '<p><a href="/x"><del>old</del></a></p>'
                '<ul><li><input type="checkbox" checked>Done</li></ul>'
            ),
            "[~~old~~](</x>)\n\n*   [x] Done",
        )
        self.assertEqual(
            TurndownService().use(gfm).turndown('<a href="/x">X</a>'), "[X](/x)"
        )

    def test_referenced_links_keep_their_format(self):
        service = TurndownService({"linkStyle": "referenced"}).use(firecrawl)
        self.assertEqual(
            service.turndown('<a href="/x" title="title">X</a>'),
            '[X][1]\n\n[1]: /x "title"',
        )

    def test_later_rules_override_the_preset(self):
        service = TurndownService().use(firecrawl)
        service.addRule(
            "inlineLink", {"filter": "a", "replacement": lambda content: content}
        )
        self.assertEqual(service.turndown('<a href="/x"><del>old</del></a>'), "~~old~~")


if __name__ == "__main__":
    unittest.main()
