"""Remove redundant interface content without discarding useful page content."""

import unittest

from lexidown import TurndownService
from lexidown.plugins.llm import llm


class LLMCleanup(unittest.TestCase):
    def test_reader_only_headings_are_removed_using_shared_class_patterns(self):
        for class_name in (
            "sr-only",
            "visually-hidden",
            "screen-reader-only",
            "screen-reader-text",
            "show-for-sr",
            "ui__sr-only",
            "ui-InternalVisuallyHidden-a1b2",
        ):
            with self.subTest(class_name=class_name):
                html = (
                    f'<main><h2 class="{class_name}">Section navigation</h2>'
                    "<article><h1>Guide</h1><h2>Usage</h2><p>Instructions.</p>"
                    "</article></main>"
                )
                self.assertEqual(
                    TurndownService().use(llm).turndown(html),
                    "# Guide\n\n## Usage\n\nInstructions.",
                )
                self.assertIn("Section navigation", TurndownService().turndown(html))

    def test_reader_only_cleanup_preserves_titles_descriptions_code_and_overrides(self):
        html = (
            '<main><h1 class="sr-only">Product</h1>'
            '<p><span class="visually-hidden">Original price:</span> $120</p>'
            '<p><span class="sr-only">Rating: 4.5 out of 5</span></p>'
            '<pre><h2 class="sr-only">Code sample</h2></pre>'
            '<h2 class="sr-only not-sr-only">Visible override</h2>'
            '<h2 class="sr-only lg:not-sr-only">Responsive override</h2>'
            '<h2 class="md:sr-only">Responsive heading</h2>'
            '<h2 class="sr-onlyish">Unrelated class</h2></main>'
        )
        self.assertEqual(
            TurndownService().use(llm).turndown(html),
            "# Product\n\nOriginal price: $120\n\nRating: 4.5 out of 5"
            "\n\n```\nCode sample\n```\n\n## Visible override"
            "\n\n## Responsive override\n\n## Responsive heading"
            "\n\n## Unrelated class",
        )
        self.assertIn(
            "Quantity",
            TurndownService()
            .use(llm)
            .turndown(
                '<table><tr><th><h2 class="sr-only">Quantity</h2></th></tr>'
                "<tr><td>2</td></tr></table>"
            ),
        )

    def test_content_landmarks_keep_nested_banner_and_footer_metadata(self):
        for opening, closing in (
            ("<main>", "</main>"),
            ('<div role="main">', "</div>"),
            ("<article>", "</article>"),
        ):
            with self.subTest(opening=opening):
                html = (
                    '<div role="banner">Site promotion</div>'
                    + opening
                    + '<div role="banner"><h1>Pancakes</h1><p>By Ada; 10 minutes.</p></div>'
                    '<p>Mix and cook.</p><div role="contentinfo">Makes 12.</div>'
                    + closing
                    + '<div role="contentinfo">Site links</div>'
                )
                self.assertEqual(
                    TurndownService().use(llm).turndown(html),
                    "# Pancakes\n\nBy Ada; 10 minutes.\n\nMix and cook.\n\nMakes 12.",
                )

    def test_svg_keeps_descriptions_or_diagram_labels_without_geometry(self):
        html = (
            '<main><p><svg aria-label="Warning"><path d="M10 20"/></svg> Details</p>'
            "<div><svg><title>Revenue</title><desc>Rises in June</desc>"
            "<text>10</text><text>20</text></svg></div>"
            '<div><svg><path d="M20 30"/><text>SELECT</text><text>FROM</text></svg></div>'
            '<svg aria-hidden="true"><title>Hidden icon</title></svg>'
            "<svg><text>Icon</text></svg></main>"
        )
        output = TurndownService().use(llm).turndown(html)
        self.assertEqual(
            output,
            "Warning Details\n\nRevenue Rises in June\n\nDiagram labels: SELECT; FROM",
        )

    def test_tiny_spacers_drop_but_labeled_images_remain(self):
        html = (
            '<p>Read<img src="/spacer.gif" height="1" width="40"> this.</p>'
            '<img src="/unknown.png"><img src="/scan.png" width="1" alt="Scan">'
        )
        self.assertEqual(
            TurndownService().use(llm).turndown(html),
            "Read this.\n\n![](/unknown.png)![Scan](/scan.png)",
        )

    def test_embedded_media_keeps_labels_without_payloads(self):
        html = (
            '<p><a href="/list"><img alt="Bring! Logo" '
            'src="data:image/svg+xml,%3Csvg%3E%3C/svg%3E"> Shopping list</a></p>'
            '<p><img alt="Revenue *chart*" src=" DaTa:image/png;base64,AAAA"></p>'
            '<p><a href="data:application/pdf;base64,BBBB">Report</a></p>'
            '<p><img alt="Diagram" src="/diagram.svg"></p>'
        )
        for style in ("inlined", "referenced"):
            with self.subTest(style=style):
                output = TurndownService({"linkStyle": style}).use(llm).turndown(html)
                self.assertNotIn("data:", output.lower())
                self.assertNotIn("%3Csvg", output)
                self.assertIn("Bring! Logo", output)
                self.assertIn("Shopping list", output)
                self.assertIn(r"Revenue \*chart\*", output)
                self.assertIn("Report", output)
                self.assertIn("![Diagram](/diagram.svg)", output)
        ordinary = TurndownService().turndown(html)
        self.assertIn("data:image/svg+xml", ordinary)

    def test_icon_fonts_remove_glyphs_and_ligatures_but_keep_labels(self):
        html = (
            '<p><i class="site-icons">\ue916</i>Profile</p>'
            '<p><span class="material-icons">time</span>25 Min. Arbeitszeit</p>'
            '<p><i class="meta__icon">difficulty_level</i>Simpel</p>'
            '<p><i class="site-icons" aria-label="Vegetarian">veggi_vegan</i></p>'
        )
        output = TurndownService().use(llm).turndown(html)
        self.assertEqual(
            output, "Profile\n\n25 Min. Arbeitszeit\n\nSimpel\n\n_Vegetarian_"
        )
        self.assertIn("\ue916", TurndownService().turndown(html))

    def test_icon_cleanup_preserves_prose_private_characters_and_code(self):
        html = (
            '<p><i>time</i> <i class="iconic">time</i> \ue916</p>'
            '<p><span class="icon-label">Important label</span></p>'
            '<p><code><i class="site-icons">\ue916</i></code></p>'
            '<pre><span class="site-icons">time</span>\n\ue916</pre>'
        )
        output = TurndownService().use(llm).turndown(html)
        self.assertIn("_time_ _time_ \ue916", output)
        self.assertIn("Important label", output)
        self.assertIn("`_\ue916_`", output)
        self.assertIn("```\ntime\n\ue916\n```", output)

    def test_large_context_preserves_unique_link_titles(self):
        link = '<a href="/item" title="Item Missing">Item</a>'
        html = "<main><div>" + link * 300 + "</div></main>"
        output = TurndownService().use(llm).turndown(html)
        self.assertEqual(output.count('[Item](/item "Item Missing")'), 300)

    def test_empty_headings_are_removed_after_child_cleanup(self):
        html = (
            "<main><h1>Release notes</h1><h2> </h2>"
            "<h3><span hidden>Hidden heading</span></h3>"
            "<h4><svg><text>Menu icon</text></svg></h4>"
            "<h2>Useful <span hidden>hidden</span>heading</h2>"
            '<h3><img src="/chart.png" alt="Architecture"></h3></main>'
        )
        self.assertEqual(
            TurndownService().use(llm).turndown(html),
            "# Release notes\n\n## Useful heading\n\n### ![Architecture](/chart.png)",
        )

    def test_block_wrapped_heading_keeps_text_attached_to_marker(self):
        self.assertEqual(
            TurndownService()
            .use(llm)
            .turndown("<h2><div>Release notes</div></h2><p>Release details.</p>"),
            "## Release notes\n\nRelease details.",
        )

    def test_redundant_link_titles_are_removed(self):
        for content in (
            '<a href="/release" title="Release notes">Release notes</a>',
            '<a href="/release" title=" Release\n notes ">Release <b>notes</b></a>',
        ):
            with self.subTest(content=content):
                output = TurndownService().use(llm).turndown(content)
                self.assertIn("(/release)", output)
                self.assertNotIn('"', output)
                self.assertIn("Release", output)

    def test_link_title_repeating_adjacent_description_is_removed(self):
        html = (
            '<div><a href="/commit" title="Fix conversion Preserve code lines">'
            "Fix conversion</a><p>Preserve code lines</p></div>"
        )
        self.assertEqual(
            TurndownService().use(llm).turndown(html),
            "[Fix conversion](/commit)\n\nPreserve code lines",
        )

    def test_distinct_link_title_is_preserved(self):
        html = (
            '<p><a href="/guide" title="Updated for version 2">Guide</a></p>'
            '<p><a href="/details" title="Additional details">Details</a></p>'
            '<p><a href="/version" title="Version 12">Version 1</a> 2</p>'
            '<p><a href="/pro-guide" title="Guide pro">Guide</a> A product review</p>'
        )
        self.assertEqual(
            TurndownService().use(llm).turndown(html),
            '[Guide](/guide "Updated for version 2")'
            '\n\n[Details](/details "Additional details")'
            '\n\n[Version 1](/version "Version 12") 2'
            '\n\n[Guide](/pro-guide "Guide pro") A product review',
        )

    def test_redundant_adjacent_author_image_link_is_removed(self):
        for image_alt, author_attribute in (("Ada", ' rel="author"'), ("@Ada", "")):
            with self.subTest(image_alt=image_alt):
                html = (
                    f'<p><a href="/people/ada"><img src="/ada.png" alt="{image_alt}" '
                    'width="32" height="32"></a> '
                    f'<a href="/people/ada"{author_attribute}>Ada</a> wrote this.</p>'
                )
                self.assertEqual(
                    TurndownService().use(llm).turndown(html),
                    "[Ada](/people/ada) wrote this.",
                )

    def test_distinct_adjacent_images_are_preserved(self):
        for image_alt, image_href in (
            ("Grace", "/people/ada"),
            ("Ada", "/people/grace"),
        ):
            with self.subTest(image_alt=image_alt, image_href=image_href):
                html = (
                    f'<p><a href="{image_href}"><img src="/portrait.png" '
                    f'alt="{image_alt}" width="32" height="32"></a> '
                    '<a href="/people/ada" rel="author">Ada</a></p>'
                )
                output = TurndownService().use(llm).turndown(html)
                self.assertIn(f"[![{image_alt}](/portrait.png)]({image_href})", output)
                self.assertIn("[Ada](/people/ada)", output)

    def test_malformed_author_image_dimensions_are_preserved(self):
        for width in ("²", "9" * 5000):
            with self.subTest(width=width[:10]):
                html = (
                    '<a href="/ada"><img src="/ada.png" alt="@Ada" '
                    f'width="{width}" height="32"></a> <a href="/ada">Ada</a>'
                )
                self.assertEqual(
                    TurndownService().use(llm).turndown(html),
                    "[![@Ada](/ada.png)](/ada) [Ada](/ada)",
                )

    def test_product_card_and_figure_images_are_preserved(self):
        cases = (
            (
                '<a href="/lamp"><img src="/lamp.png" alt="Desk lamp" '
                'width="32" height="32"><h2>Desk lamp</h2><p>$25</p></a>',
                ("![Desk lamp](/lamp.png)", "## Desk lamp", "$25"),
            ),
            (
                '<a href="/lamp"><img src="/lamp.png" alt="Desk lamp" '
                'width="32" height="32"></a> <a href="/lamp">Desk lamp</a>',
                ("[![Desk lamp](/lamp.png)](/lamp)", "[Desk lamp](/lamp)"),
            ),
            (
                '<figure><a href="/diagram"><img src="/diagram.png" '
                'alt="Architecture" width="640" height="480"></a>'
                '<figcaption><a href="/diagram">Architecture</a></figcaption>'
                "</figure>",
                (
                    "[![Architecture](/diagram.png)](/diagram)",
                    "[Architecture](/diagram)",
                ),
            ),
        )
        for html, expected in cases:
            with self.subTest(html=html):
                output = TurndownService().use(llm).turndown(html)
                for text in expected:
                    self.assertIn(text, output)

    def test_short_control_group_removal_keeps_sibling_prose(self):
        for controls in (
            "<button>Share</button> <button>Copy link</button>",
            '<a class="btn" href="/share">Share</a> '
            '<a class="button" href="/copy">Copy link</a>',
        ):
            with self.subTest(controls=controls):
                html = (
                    "<main><h1>Release notes</h1><div>"
                    + controls
                    + "</div><p>The release fixes conversion.</p></main>"
                )
                self.assertEqual(
                    TurndownService().use(llm).turndown(html),
                    "# Release notes\n\nThe release fixes conversion.",
                )

    def test_control_groups_inside_structured_content_are_preserved(self):
        cases = (
            "<table><tr><th><div><button>Provider</button> "
            "<button>Availability</button></div></th></tr></table>",
            "<h2><div><button>Provider</button> "
            "<button>Availability</button></div></h2>",
            '<a href="/provider"><h2>Provider details</h2>'
            '<div><span role="button">Provider</span> '
            '<span role="button">Availability</span></div></a>',
        )
        for html in cases:
            with self.subTest(html=html):
                output = TurndownService().use(llm).turndown(html)
                self.assertIn("Provider", output)
                self.assertIn("Availability", output)

    def test_link_dense_references_and_controls_with_data_are_preserved(self):
        html = (
            '<ul><li><a href="/first">First reference</a></li>'
            '<li><a href="/second">Second reference</a></li></ul>'
            "<div><button>Buy</button> <button>Compare</button><span>$25</span></div>"
        )
        output = TurndownService().use(llm).turndown(html)
        for text in (
            "[First reference](/first)",
            "[Second reference](/second)",
            "Buy",
            "Compare",
            "$25",
        ):
            self.assertIn(text, output)

    def test_numeric_and_stateful_controls_are_preserved(self):
        cases = (
            (
                '<div><span role="button">Prompt 38.9B</span> '
                '<span role="button">Completion 12B</span></div>',
                ("Prompt 38.9B", "Completion 12B"),
            ),
            (
                '<div><button aria-controls="shipping">Shipping</button> '
                '<button aria-controls="returns">Returns</button></div>',
                ("Shipping", "Returns"),
            ),
            (
                '<div><button aria-pressed="true">Available</button> '
                '<button aria-pressed="false">Unavailable</button></div>',
                ("Available", "Unavailable"),
            ),
            (
                '<div><button aria-expanded="false">Where do you ship?</button> '
                '<button aria-expanded="false">When will it arrive?</button></div>'
                '<div hidden="until-found">Worldwide, within one week.</div>',
                (
                    "Where do you ship?",
                    "When will it arrive?",
                    "Worldwide, within one week.",
                ),
            ),
            (
                '<div><button aria-selected="true">Monthly</button> '
                '<button aria-selected="false">Yearly</button></div>',
                ("Monthly", "Yearly"),
            ),
        )
        for html, expected in cases:
            with self.subTest(html=html):
                output = TurndownService().use(llm).turndown(html)
                for text in expected:
                    self.assertIn(text, output)

    def test_repeated_target_controls_remove_helpers_but_preserve_external_data(self):
        controls = (
            '<a class="btn" href="/login">Watch 0</a> '
            '<a class="btn" href="/login">Fork 2</a> '
            '<a class="btn" href="/login">Star 3</a>'
        )
        for helper in ("Alerts", "$25"):
            with self.subTest(helper=helper):
                html = (
                    f"<div>{controls}<span>{helper}</span></div><p>Release notes.</p>"
                )
                output = TurndownService().use(llm).turndown(html)
                if helper == "Alerts":
                    self.assertEqual(output, "Release notes.")
                else:
                    for text in ("Watch 0", "Fork 2", "Star 3", "$25"):
                        self.assertIn(text, output)


if __name__ == "__main__":
    unittest.main()
