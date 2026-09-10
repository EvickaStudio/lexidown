"""Opt-in web content cleanup and the shared DOM preprocessing hook."""

import unittest
from xml.dom import minidom

from lexidown import TurndownService
from lexidown.dom import root_node
from lexidown.plugins.llm import llm


class LLMPreset(unittest.TestCase):
    def test_code_line_break_elements_preserve_separate_commands(self):
        for content in (
            "<span>first</span><br><span>  second</span>",
            "<code>first<br>  second</code>",
        ):
            with self.subTest(content=content):
                self.assertEqual(
                    TurndownService().use(llm).turndown("<pre>" + content + "</pre>"),
                    "```\nfirst\n  second\n```",
                )

    def test_main_content_keeps_every_discussion_article(self):
        for opening, closing in (
            ("<main>", "</main>"),
            ('<div role="main">', "</div>"),
        ):
            with self.subTest(opening=opening):
                html = (
                    "<div><p>Site banner</p><div>"
                    + opening
                    + "<h1>Discussion</h1><article><p>Opening post.</p></article>"
                    "<article><p>First reply.</p></article>"
                    "<article><p>Second reply.</p></article>"
                    + closing
                    + "</div><p>Site links</p></div>"
                )
                self.assertEqual(
                    TurndownService().use(llm).turndown(html),
                    "# Discussion\n\nOpening post.\n\nFirst reply.\n\nSecond reply.",
                )

    def test_cleanup_removes_noncontent_and_preserves_inline_spaces(self):
        html = (
            "<main><nav><a href='/menu'>Menu</a></nav>"
            "<script>track()</script><style>.noise { color: red }</style>"
            "<p hidden>Hidden text</p><p aria-hidden='true'>Accessible noise</p>"
            "<button>Subscribe</button>"
            "<p>Read <span hidden>hidden inline text</span> this.</p>"
            "<p aria-hidden='false'>Visible text.</p></main>"
        )
        self.assertEqual(
            TurndownService().use(llm).turndown(html),
            "Subscribe\n\nRead this.\n\nVisible text.",
        )

    def test_article_headers_footnotes_and_asides_remain_content(self):
        html = (
            "<article><header><h1>Research</h1><p>By Ada</p></header>"
            "<p>Claim.</p><aside><p>Useful explanation.</p></aside>"
            "<footer><p>Footnote: original source.</p></footer>"
            "</article>"
        )
        for value in (html, "<main>" + html + "</main>"):
            with self.subTest(html=value):
                self.assertEqual(
                    TurndownService().use(llm).turndown(value),
                    "# Research\n\nBy Ada\n\nClaim.\n\nUseful explanation."
                    "\n\nFootnote: original source.",
                )

    def test_single_article_does_not_discard_sibling_replies(self):
        html = (
            "<article><h1>Discussion</h1><p>Opening post.</p></article>"
            "<section><p>Reader reply.</p></section>"
        )
        self.assertEqual(
            TurndownService().use(llm).turndown(html),
            "# Discussion\n\nOpening post.\n\nReader reply.",
        )

    def test_unmarked_content_has_a_conservative_fallback(self):
        html = (
            "<div>Intro text.<p>First paragraph.</p>"
            "<section><p>Second paragraph.</p></section>Tail text.</div>"
        )
        self.assertEqual(
            TurndownService().use(llm).turndown(html),
            "Intro text.\n\nFirst paragraph.\n\nSecond paragraph.\n\nTail text.",
        )

    def test_markdown_defaults_and_gfm_keep_structured_content(self):
        service = TurndownService().use(llm)
        self.assertEqual(service.options["headingStyle"], "atx")
        self.assertEqual(service.options["codeBlockStyle"], "fenced")
        self.assertEqual(service.options["bulletListMarker"], "-")
        html = (
            '<main><h1>Notes</h1><pre><code class="language-python">'
            "a = 1\nprint(a)\n</code></pre>"
            '<ul><li><input type="checkbox" checked>Done</li>'
            '<li><input type="checkbox">Next</li></ul>'
            "<table><thead><tr><th>Name</th><th>Value</th></tr></thead>"
            "<tbody><tr><td>A</td><td>1</td></tr></tbody></table>"
            "<p><del>old</del></p></main>"
        )
        self.assertEqual(
            service.turndown(html),
            "# Notes\n\n```python\na = 1\nprint(a)\n```"
            "\n\n-   [x] Done\n-   [ ] Next"
            "\n\n| Name | Value |\n| --- | --- |\n| A   | 1   |\n\n~~old~~",
        )

    def test_linked_cards_keep_blocks_outside_the_link_label(self):
        html = (
            '<main><a href="/product"><h2>Product</h2><p>$65</p></a>'
            '<p>Read <a href="/guide" title="Guide">the guide</a>.</p>'
            '<ul><li><a href="/done" role="checkbox" aria-checked="true">'
            "Done</a></li></ul></main>"
        )
        self.assertEqual(
            TurndownService().use(llm).turndown(html),
            "## Product\n\n$65\n\n[/product](/product)"
            '\n\nRead [the guide](/guide "Guide").\n\n-   [x]',
        )

    def test_bare_pre_preserves_raw_text_and_uses_a_safe_fence(self):
        cases = (
            ("<pre>first\n  second\nthird\n</pre>", "```\nfirst\n  second\nthird\n```"),
            (
                "<pre><span>first</span>\n  ```\nlast &lt;value&gt;\n</pre>",
                "````\nfirst\n  ```\nlast <value>\n````",
            ),
        )
        for html, expected in cases:
            with self.subTest(html=html):
                self.assertEqual(TurndownService().use(llm).turndown(html), expected)

    def test_simple_block_link_labels_and_empty_image_links(self):
        for tag in ("p", "div"):
            html = (
                '<a href="/decoration"><img src="/decoration.png" alt=""></a>'
                f'<a href="/shop"><{tag}><strong>Shop</strong></{tag}></a>'
                '<a href="/card"><div><h2>Card</h2></div></a>'
            )
            with self.subTest(tag=tag):
                self.assertEqual(
                    TurndownService().use(llm).turndown(html),
                    "[**Shop**](/shop)\n\n## Card\n\n[/card](/card)",
                )

    def test_explicit_decorative_images_and_svg_are_removed(self):
        html = (
            '<main><img src="/decoration.png" alt="">'
            '<img src="/unknown.png"><img src="/chart.png" alt="Chart">'
            "<svg><text>Icon label</text></svg></main>"
        )
        self.assertEqual(
            TurndownService().use(llm).turndown(html),
            "![](/unknown.png)![Chart](/chart.png)",
        )

    def test_buttons_preserve_table_values_and_disclosure_headings(self):
        html = (
            "<main><nav><button>Menu</button></nav>"
            '<div role="toolbar"><button>Toolbar action</button></div>'
            "<table><thead><tr><th><button>Provider</button></th>"
            "<th><button>Availability</button></th></tr></thead>"
            "<tbody><tr><td><button>Provider A</button></td>"
            '<td><span role="button">Available</span></td></tr></tbody></table>'
            '<h3><button id="question" aria-controls="answer" aria-expanded="false">'
            "FAQ question</button></h3>"
            '<div id="answer" hidden="until-found" role="region"'
            ' aria-labelledby="question"><p>FAQ answer.</p></div>'
            "<p hidden>Ordinary hidden text</p></main>"
        )
        self.assertEqual(
            TurndownService().use(llm).turndown(html),
            "| Provider | Availability |\n| --- | --- |\n| Provider A | Available |"
            "\n\n### FAQ question\n\nFAQ answer.",
        )

    def test_base_url_resolves_links_and_images_per_service(self):
        html = (
            '<main><p><a href="../guide?q=1#part">Guide</a> '
            '<a href="https://other.example/">External</a></p>'
            '<img src="/images/chart.png" alt="Chart"></main>'
        )
        resolving = TurndownService({"baseUrl": "https://example.com/docs/page"}).use(
            llm
        )
        relative = TurndownService().use(llm)
        for _ in range(2):
            self.assertEqual(
                resolving.turndown(html),
                "[Guide](https://example.com/guide?q=1#part) "
                "[External](https://other.example/)"
                "\n\n![Chart](https://example.com/images/chart.png)",
            )
            self.assertEqual(
                relative.turndown(html),
                "[Guide](../guide?q=1#part) [External](https://other.example/)"
                "\n\n![Chart](/images/chart.png)",
            )

    def test_dom_inputs_are_unchanged_and_reusable(self):
        html = (
            "<div><nav>Menu</nav><main><h1>Title</h1>"
            "<p>Read <span hidden=''>noise</span> this.</p></main></div>"
        )
        python_dom = minidom.parseString(html)
        native_dom = root_node(html, {})
        service = TurndownService().use(llm)
        for node in (python_dom, python_dom.documentElement, native_dom):
            with self.subTest(kind=type(node).__name__):
                before = node.toxml() if hasattr(node, "toxml") else node.outerHTML
                for _ in range(2):
                    self.assertEqual(service.turndown(node), "# Title\n\nRead this.")
                    after = node.toxml() if hasattr(node, "toxml") else node.outerHTML
                    self.assertEqual(after, before)
        self.assertEqual(service.turndown("<p>Another page.</p>"), "Another page.")

    def test_malformed_scraped_url_does_not_discard_page_text(self):
        service = TurndownService({"baseUrl": "https://example.com/page"}).use(llm)
        output = service.turndown(
            '<p><a href="http://[invalid">Broken link</a></p><p>Readable text.</p>'
        )
        self.assertIn("Broken link", output)
        self.assertTrue(output.endswith("Readable text."))

    def test_base_url_changes_links_without_selecting_site_specific_content(self):
        html = (
            '<div><nav><a href="/">Global navigation</a></nav><main>'
            '<div><a href="/owner/repo">Repository controls</a>'
            "<button>Star</button></div>"
            "<h1>Improve conversion</h1>"
            '<div class="sticky-content"><h2>Improve conversion</h2></div>'
            '<nav><a href="/owner/repo/pull/6/files">Files changed</a></nav>'
            '<div class="timeline-comment"><div class="comment-body js-comment-body">'
            "<p>Description.</p></div></div>"
            '<div class="TimelineItem"><p>Someone pushed a commit.</p></div>'
            '<div class="timeline-comment"><div class="js-comment-body markdown-body">'
            "<p>Reply.</p></div></div>"
            '<aside role="complementary"><p>Assignees and labels</p></aside>'
            "</main></div>"
        )
        main = root_node(html, {}).getElementsByTagName("main")[0]
        before = main.outerHTML
        expected = (
            "[Repository controls](/owner/repo)Star\n\n# Improve conversion"
            "\n\n## Improve conversion\n\nDescription."
            "\n\nSomeone pushed a commit.\n\nReply."
        )
        for host, path in (
            ("github.com", "pull/6"),
            ("github.com", "issues/6"),
            ("github.com", "pull/6/files"),
            ("example.com", "pull/6"),
        ):
            base_url = f"https://{host}/owner/repo/{path}"
            service = TurndownService({"baseUrl": base_url}).use(llm)
            for value in (html, main):
                with self.subTest(base_url=base_url, input_type=type(value).__name__):
                    self.assertEqual(
                        service.turndown(value),
                        expected.replace(
                            "(/owner/repo)", f"(https://{host}/owner/repo)"
                        ),
                    )
                    self.assertEqual(main.outerHTML, before)

    def test_commerce_and_model_pages_keep_all_main_content(self):
        cases = (
            (
                "<nav>Shop navigation</nav><main><h1>Products</h1>"
                "<article><h2>Desk lamp</h2><p>€29.99</p>"
                "<button>Add lamp to cart</button></article>"
                "<article><h2>Reading light</h2><p>€44.50</p>"
                "<button>Add light to cart</button></article>"
                "<script>trackProducts()</script></main>",
                "# Products\n\n## Desk lamp\n\n€29.99\n\nAdd lamp to cart"
                "\n\n## Reading light\n\n€44.50\n\nAdd light to cart",
            ),
            (
                "<main><h1>Example model</h1><p>Context: 128K tokens</p>"
                '<div role="tablist"><button>Providers tab</button> '
                "<button>Details tab</button></div>"
                '<section role="tabpanel"><h2>Providers</h2>'
                "<article><h3>Provider A</h3><p>Throughput: 80 tokens/s</p></article>"
                "<article><h3>Provider B</h3><p>Latency: 0.5 seconds</p></article>"
                "</section>"
                '<section role="tabpanel"><h2>Details</h2>'
                "<p>Supports text and images.</p></section>"
                "<script>loadAnalytics()</script></main>",
                "# Example model\n\nContext: 128K tokens"
                "\n\nProviders tab Details tab\n\n## Providers"
                "\n\n### Provider A\n\nThroughput: 80 tokens/s"
                "\n\n### Provider B\n\nLatency: 0.5 seconds"
                "\n\n## Details\n\nSupports text and images.",
            ),
        )
        for html, expected in cases:
            with self.subTest(expected=expected.splitlines()[0]):
                self.assertEqual(TurndownService().use(llm).turndown(html), expected)

    def test_default_turndown_service_stays_compatible(self):
        ordinary = TurndownService()
        html = "<nav>Menu</nav><h1>Title</h1><button>Vote</button><p hidden>Hidden</p>"
        TurndownService().use(llm).turndown(html)
        for service in (ordinary, TurndownService()):
            self.assertEqual(
                service.turndown(html), "Menu\n\nTitle\n=====\n\nVote\n\nHidden"
            )
            self.assertEqual(service.options["codeBlockStyle"], "indented")
            self.assertEqual(service.options["bulletListMarker"], "*")

    def test_preprocess_runs_once_before_whitespace_and_composes_with_llm(self):
        for plugin in (None, llm):
            seen = []

            def preprocess(root, *, seen=seen):
                paragraph = root.getElementsByTagName("p")[0]
                seen.append(paragraph.textContent)
                paragraph.textContent = " first   second "

            service = TurndownService({"preprocess": preprocess})
            if plugin is not None:
                service.use(plugin)
            with self.subTest(plugin=plugin):
                for _ in range(2):
                    html = "<main><p> before   after </p><nav>Menu</nav></main>"
                    expected = "first second" if plugin else "first second\n\nMenu"
                    self.assertEqual(service.turndown(html), expected)
                self.assertEqual(seen, [" before   after ", " before   after "])


if __name__ == "__main__":
    unittest.main()
