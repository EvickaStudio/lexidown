"""Omit link destinations while preserving source text and Markdown structure."""

import unittest

from lexidown import TurndownService
from lexidown.plugins.llm import llm


class LLMUrls(unittest.TestCase):
    def test_link_and_image_urls_are_independent_and_enabled_by_default(self):
        html = (
            '<p><a href="/guide"><strong>Guide</strong></a> '
            '<img src="/chart.png" alt="Chart *one*"> '
            '<a href="/photo"><img src="/photo.png" alt="Photo"></a></p>'
        )
        for links, images, expected in (
            (
                True,
                True,
                r"[**Guide**](/guide) ![Chart \*one\*](/chart.png) [![Photo](/photo.png)](/photo)",
            ),
            (
                False,
                True,
                r"**Guide** ![Chart \*one\*](/chart.png) ![Photo](/photo.png)",
            ),
            (True, False, r"[**Guide**](/guide) Chart \*one\* [Photo](/photo)"),
            (False, False, r"**Guide** Chart \*one\* Photo"),
        ):
            with self.subTest(links=links, images=images):
                self.assertEqual(
                    TurndownService(
                        {"includeLinkUrls": links, "includeImageUrls": images}
                    )
                    .use(llm)
                    .turndown(html),
                    expected,
                )
        self.assertEqual(
            TurndownService().use(llm).turndown(html),
            TurndownService({"includeLinkUrls": True, "includeImageUrls": True})
            .use(llm)
            .turndown(html),
        )

    def test_reference_styles_leave_no_destinations_or_definitions(self):
        html = '<p><a href="https://example.com/guide" title="Updated">Guide</a></p>'
        for style in ("full", "collapsed", "shortcut"):
            with self.subTest(style=style):
                service = TurndownService(
                    {"linkStyle": "referenced", "linkReferenceStyle": style}
                ).use(llm)
                self.assertIn("https://example.com/guide", service.turndown(html))
                service.options["includeLinkUrls"] = False
                self.assertEqual(service.turndown(html), "Guide")
                service.options["includeLinkUrls"] = True
                self.assertIn("https://example.com/guide", service.turndown(html))

    def test_linked_blocks_tables_and_inline_code_keep_their_content(self):
        html = (
            '<a href="/product"><h2>Product</h2><p>$65</p></a>'
            '<table><tr><th colspan="2"><h3>Inventory</h3></th></tr>'
            '<tr><td><a href="/item">Item</a></td><td><img src="/map.svg" alt="Map"></td>'
            '</tr></table><p>Read <a href="/api"><code>api.run()</code></a>.</p>'
        )
        self.assertEqual(
            TurndownService({"includeLinkUrls": False, "includeImageUrls": False})
            .use(llm)
            .turndown(html),
            "## Product\n\n$65\n\n### Inventory\n\n|     |     |\n| --- | --- |\n"
            "| Item | Map |\n\nRead `api.run()`.",
        )

    def test_literal_urls_in_prose_and_code_are_not_removed(self):
        html = (
            '<p>Visit https://example.com/source or <a href="/tracking">'
            "https://example.com/label</a>.</p>"
            '<pre><code>fetch("https://example.com/api")\n</code></pre>'
            "<p><code>https://example.com/inline</code></p>"
        )
        self.assertEqual(
            TurndownService({"includeLinkUrls": False, "includeImageUrls": False})
            .use(llm)
            .turndown(html),
            "Visit https://example.com/source or https://example.com/label.\n\n"
            '```\nfetch("https://example.com/api")\n```\n\n'
            "`https://example.com/inline`",
        )

    def test_math_and_embedded_media_keep_their_labels(self):
        html = (
            '<p><math alttext="x^2"><mi>x</mi><mn>2</mn></math>'
            '<img src="/equation.svg" alt="x^2"></p>'
            '<p><a href="data:application/pdf;base64,AAAA">Report</a> '
            '<img src="data:image/png;base64,BBBB" alt="Figure"></p>'
            '<h2><img src="/unknown.png"></h2>'
        )
        self.assertEqual(
            TurndownService({"includeLinkUrls": False, "includeImageUrls": False})
            .use(llm)
            .turndown(html),
            "$x^2$\n\nReport Figure",
        )

    def test_text_only_image_labels_stay_separated(self):
        service = TurndownService({"includeImageUrls": False}).use(llm)
        self.assertEqual(
            " ".join(
                service.turndown(
                    '<p>Before<img src="/one.png" alt="First">'
                    '<img src="/two.png" alt="Second">after.</p>'
                ).split()
            ),
            "Before First Second after.",
        )
        self.assertEqual(
            service.turndown('<p>Before <img src="/one.png" alt="First"> after.</p>'),
            "Before First after.",
        )

    def test_options_do_not_change_ordinary_turndown(self):
        html = '<a href="/guide">Guide</a><img src="/image.png" alt="Image">'
        self.assertEqual(
            TurndownService(
                {"includeLinkUrls": False, "includeImageUrls": False}
            ).turndown(html),
            TurndownService().turndown(html),
        )

    def test_picture_sources_do_not_change_list_indentation(self):
        html = (
            '<ul><li><picture><source srcset="/large.png">'
            '<img src="/photo.png" alt="Photo"></picture>'
            "<h3>Headline</h3><p>Summary.</p></li></ul>"
        )
        self.assertEqual(
            TurndownService({"includeImageUrls": False}).use(llm).turndown(html),
            "-   Photo\n    \n    ### Headline\n    \n    Summary.",
        )

    def test_linked_task_checkboxes_keep_their_state(self):
        html = (
            '<ul><li><a href="/done" role="checkbox" aria-checked="true">Done</a></li>'
            '<li><a href="/next" role="checkbox" aria-checked="false">Next</a></li></ul>'
        )
        self.assertEqual(
            TurndownService({"includeLinkUrls": False}).use(llm).turndown(html),
            "-   [x] \n-   [ ]",
        )


if __name__ == "__main__":
    unittest.main()
