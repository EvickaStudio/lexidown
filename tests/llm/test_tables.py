"""LLM table fallback preserves information without Joplin's HTML wrappers."""

import unittest

from lexidown import TurndownService
from lexidown.plugins.joplin_gfm import gfm
from lexidown.plugins.llm import llm


class LLMTables(unittest.TestCase):
    def test_merged_duplicate_columns_render_as_one_markdown_column(self):
        html = (
            '<table><tr><th colspan="2">File</th><th>File</th><th>Size</th></tr>'
            '<tr><td colspan="2"><a href="/guide">guide.md</a></td>'
            '<td><a href="/guide">guide.md</a></td><td>12 KB</td></tr>'
            '<tr><td colspan="2"><a href="/app">app.py</a></td>'
            '<td><a href="/app">app.py</a></td><td>3 KB</td></tr>'
            '<tr><td colspan="3">Browse files</td></tr></table>'
        )
        for urls in (True, False):
            with self.subTest(urls=urls):
                guide = "[guide.md](/guide)" if urls else "guide.md"
                app = "[app.py](/app)" if urls else "app.py"
                self.assertEqual(
                    TurndownService({"includeLinkUrls": urls}).use(llm).turndown(html),
                    "| File | Size |\n| --- | --- |\n"
                    f"| {guide} | 12 KB |\n| {app} | 3 KB |\n"
                    "| Browse files |     |",
                )

    def test_varying_colspans_keep_values_under_their_headers(self):
        html = (
            '<table><tr><th colspan="2">Region</th><th>Rate</th></tr>'
            '<tr><td colspan="2">EU</td><td>20%</td></tr>'
            "<tr><td>North</td><td>South</td><td>15%</td></tr></table>"
        )
        self.assertEqual(
            TurndownService().use(llm).turndown(html),
            "| Region |     | Rate |\n| --- | --- | --- |\n"
            "| EU  |     | 20% |\n| North | South | 15% |",
        )

    def test_equal_labels_keep_distinct_destinations_and_column_headers(self):
        for second_header, first, second in (
            ("File", '<a href="/one">Read</a>', '<a href="/two">Read</a>'),
            ("Other file", "Read", "Read"),
        ):
            with self.subTest(second_header=second_header):
                html = (
                    '<table><tr><th colspan="2">File</th>'
                    f"<th>{second_header}</th></tr>"
                    f'<tr><td colspan="2">{first}</td><td>{second}</td></tr></table>'
                )
                self.assertEqual(
                    TurndownService({"includeLinkUrls": False}).use(llm).turndown(html),
                    f"| File | {second_header} |\n| --- | --- |\n| Read | Read |",
                )

    def test_sparse_colspans_use_bounded_fallback(self):
        html = (
            "<table>"
            + "".join(
                f'<tr><td colspan="{span}">Value {span}</td><td>End</td></tr>'
                for span in range(1, 102)
            )
            + "</table>"
        )
        output = TurndownService().use(llm).turndown(html)
        self.assertIn("Value 1", output)
        self.assertIn("Value 101", output)
        self.assertEqual(output.count("End"), 101)
        self.assertNotIn("| ---", output)
        self.assertLess(len(output), 20000)

    def test_distinct_reference_ids_remain_used_after_column_normalization(self):
        html = (
            '<table><tr><th colspan="2">File</th><th>File</th></tr>'
            '<tr><td colspan="2"><a href="/guide">Read</a></td>'
            '<td><a href="/guide">Read</a></td></tr></table>'
        )
        output = TurndownService({"linkStyle": "referenced"}).use(llm).turndown(html)
        self.assertIn("| [Read][1] | [Read][2] |", output)
        self.assertIn("[1]: /guide", output)
        self.assertIn("[2]: /guide", output)

    def test_presentation_tables_keep_cells_in_document_order(self):
        for role in ("presentation", "none"):
            with self.subTest(role=role):
                html = (
                    f'<table role="{role}"><tr><td>First</td><td>Second</td></tr>'
                    "<tr><td></td><td>Third</td></tr><caption>End note</caption></table>"
                )
                self.assertEqual(
                    TurndownService().use(llm).turndown(html),
                    "First\n\nSecond\n\nThird\n\nEnd note",
                )

    def test_nested_layout_tables_keep_comments_as_separate_blocks(self):
        html = (
            "<table><tr><td><table><tr><td></td><td></td><td>"
            '<div><a href="/ada">Ada</a></div><div><p>First comment.</p>'
            "<p>Second paragraph.</p></div></td></tr></table></td></tr>"
            "<tr><td><table><tr><td></td><td><div>Grace</div>"
            "<p>Second comment.</p></td></tr></table></td></tr></table>"
        )
        self.assertEqual(
            TurndownService().use(llm).turndown(html),
            "[Ada](/ada)\n\nFirst comment.\n\nSecond paragraph."
            "\n\nGrace\n\nSecond comment.",
        )

    def test_spacer_images_do_not_create_content_columns(self):
        html = (
            '<table><tr><td><img src="/spacer.gif" width="40" height="1"></td>'
            "<td><div>A readable comment.</div></td></tr></table>"
        )
        output = TurndownService().use(llm).turndown(html)
        self.assertTrue(output.endswith("A readable comment."))
        self.assertNotIn("|", output)
        self.assertNotIn("Cell", output)

    def test_layout_wrapper_preserves_nested_data_table(self):
        table = (
            "<table><tr><th>Service</th><th>Status</th></tr>"
            "<tr><td>API</td><td>Ready</td></tr></table>"
        )
        html = (
            "<table><tr><td></td><td><h2>Report</h2>"
            + table
            + "</td></tr><tr><td></td><td><p>End.</p></td></tr></table>"
        )
        self.assertEqual(
            TurndownService().use(llm).turndown(html),
            "## Report\n\n" + TurndownService().use(llm).turndown(table) + "\n\nEnd.",
        )

    def test_meaningful_images_and_code_preserve_data_columns(self):
        for content in (
            '<img src="/chart.png" alt="Chart" width="200" height="100">',
            "<pre><code>build\nstart\n</code></pre>",
        ):
            with self.subTest(content=content):
                html = (
                    "<table><tr><td>"
                    + content
                    + "</td><td><p>Instructions.</p></td></tr></table>"
                )
                output = TurndownService().use(llm).turndown(html)
                self.assertEqual(
                    output,
                    TurndownService({"codeBlockStyle": "fenced"})
                    .use(gfm)
                    .turndown(html),
                )
                self.assertIn("Instructions.", output)
                if "chart.png" in content:
                    self.assertIn("![Chart](/chart.png)", output)
                else:
                    self.assertIn("build", output)
                    self.assertIn("start", output)

    def test_semantic_content_with_blank_neighbor_requires_explicit_layout_role(self):
        for content in (
            '<div><img src="/chart.png" alt="Chart" width="200" height="100"></div>',
            "<pre><code>build\nstart\n</code></pre>",
        ):
            with self.subTest(content=content):
                html = f"<table><tr><td>{content}</td><td></td></tr></table>"
                self.assertEqual(
                    TurndownService().use(llm).turndown(html),
                    TurndownService({"codeBlockStyle": "fenced"})
                    .use(gfm)
                    .turndown(html),
                )
                self.assertEqual(
                    TurndownService()
                    .use(llm)
                    .turndown(html.replace("<table>", '<table role="presentation">')),
                    TurndownService().use(llm).turndown(content),
                )

    def test_ordinary_tables_keep_gfm_output(self):
        for html in (
            "<table><tr><th>Name</th><th>Value</th></tr>"
            "<tr><td>Alpha</td><td>3</td></tr></table>",
            "<table><caption>Measurements</caption>"
            '<tr><td align="right">One</td><td>A | B</td></tr>'
            '<tr><td align="right">Two</td><td>Line<br>break</td></tr></table>',
            "<table><tr><td>Single cell</td></tr></table>",
        ):
            with self.subTest(html=html):
                self.assertEqual(
                    TurndownService().use(llm).turndown(html),
                    TurndownService().use(gfm).turndown(html),
                )

    def test_spanning_section_headings_keep_recipe_columns(self):
        html = (
            "<table><caption>One portion</caption><thead>"
            '<tr><th colspan="2"><h3>Waffle ingredients</h3></th></tr>'
            "</thead><tbody><tr><td><div>125&nbsp;g</div></td>"
            "<td><div><strong>Mozzarella</strong></div></td></tr>"
            "<tr><td></td><td>Salt and pepper</td></tr>"
            '<tr><th colspan="2"><h3>Topping</h3></th></tr>'
            '<tr><td>4</td><td><a href="/tomato">Tomatoes</a></td></tr>'
            "</tbody></table>"
        )
        self.assertEqual(
            TurndownService().use(llm).turndown(html),
            "One portion\n\n### Waffle ingredients\n\n"
            "|     |     |\n| --- | --- |\n"
            "| 125\u00a0g | **Mozzarella** |\n|     | Salt and pepper |\n\n"
            "### Topping\n\n|     |     |\n| --- | --- |\n"
            "| 4   | [Tomatoes](/tomato) |",
        )
        self.assertIn(
            'class="joplin-table-wrapper"',
            TurndownService().use(gfm).turndown(html),
        )

    def test_merged_body_cells_keep_span_and_row_associations(self):
        html = (
            '<table><tr><td rowspan="2">Fruit</td><td>Pear</td><td>3</td></tr>'
            '<tr><td colspan="2">No apples in stock</td></tr></table>'
        )
        output = TurndownService().use(llm).turndown(html)
        self.assertIn("- Row 1:\n  - Cell 1 (spans 2 rows):\n\n    Fruit", output)
        self.assertIn("  - Cell 2:\n\n    Pear\n\n  - Cell 3:\n\n    3", output)
        self.assertIn(
            "- Row 2:\n  - Cell 1 (spans 2 columns):\n\n    No apples in stock",
            output,
        )
        self.assertNotIn("<table", output)

    def test_complex_blocks_and_nested_tables_keep_markdown_structure(self):
        html = (
            "<table><caption>Deployment</caption><tr><th>Service</th>"
            "<th>Instructions</th></tr><tr><td>API</td><td>"
            "<ul><li>Build</li><li>Start</li></ul>"
            '<pre><code class="language-sh">build\nstart\n</code></pre>'
            '<p>Read <a href="/docs">the docs</a>.</p>'
            "<table><caption>Checks</caption><tr><th>Name</th><th>Status</th></tr>"
            "<tr><td>HTTP</td><td>Ready</td></tr></table>"
            "</td></tr></table>"
        )
        output = TurndownService().use(llm).turndown(html)
        self.assertTrue(output.startswith("Deployment\n\n- Row 1:"))
        self.assertIn("- Row 2:\n  - Cell 1:\n\n    API", output)
        self.assertIn("    -   Build\n    -   Start", output)
        self.assertIn("    ```sh\n    build\n    start\n    ```", output)
        self.assertIn("    Read [the docs](/docs).", output)
        self.assertIn("    Checks\n\n    |", output)
        self.assertIn("    | Name | Status |", output)
        self.assertIn("    | HTTP | Ready |", output)
        self.assertEqual(output.count("HTTP"), 1)
        self.assertNotIn("<table", output)
        self.assertNotIn("joplin-table-wrapper", output)

    def test_extreme_spans_are_described_without_expanding_output(self):
        html = (
            '<table><tr><td colspan="' + "9" * 10000 + '">Huge span</td></tr>'
            '<tr><td rowspan="0">Rest of row group</td></tr></table>'
        )
        output = TurndownService().use(llm).turndown(html)
        self.assertIn("Cell 1 (spans 1000 columns):", output)
        self.assertIn("Cell 1 (spans remaining rows):", output)
        self.assertLess(len(output), 300)

    def test_span_parser_keeps_leading_zeros_and_rejects_unicode_digits(self):
        for span in ("00000001", "0" * 10000 + "1", "\u0662", "invalid"):
            with self.subTest(span=span[:20]):
                html = (
                    '<table><tr><th colspan="00000002"><h3>Ingredients</h3></th>'
                    f'</tr><tr><td colspan="{span}">125 g</td>'
                    "<td>Mozzarella</td></tr></table>"
                )
                output = TurndownService().use(llm).turndown(html)
                self.assertIn("| 125 g | Mozzarella |", output)
                self.assertNotIn("spans", output)
        html = '<table><tr><td rowspan="00000000">Until end</td></tr></table>'
        self.assertIn(
            "Cell 1 (spans remaining rows):",
            TurndownService().use(llm).turndown(html),
        )

    def test_fallback_cells_preserve_repeated_and_backslash_escaped_pipes(self):
        for source, expected in (
            ("A||B", r"A\|\|B"),
            (r"A\|B", r"A\\\|B"),
            ("<code>A||B</code>", r"`A\|\|B`"),
            (r"<code>A\|B</code>", r"`A\\|B`"),
        ):
            with self.subTest(source=source):
                html = (
                    '<table><tr><th colspan="2"><h3>Operators</h3></th></tr>'
                    f"<tr><td>{source}</td><td>Value</td></tr></table>"
                )
                self.assertIn(
                    f"| {expected} | Value |",
                    TurndownService().use(llm).turndown(html),
                )

    def test_blank_captions_and_cells_keep_column_positions(self):
        html = (
            '<table><caption> </caption><tr><th colspan="2"><h3>Values</h3></th>'
            "</tr><tr><th></th><th>Name</th></tr><tr><td></td><td>A</td></tr>"
            "<tr><td>B</td><td></td></tr></table>"
        )
        self.assertEqual(
            TurndownService().use(llm).turndown(html),
            "### Values\n\n|     | Name |\n| --- | --- |\n|     | A   |\n| B   |     |",
        )


if __name__ == "__main__":
    unittest.main()
