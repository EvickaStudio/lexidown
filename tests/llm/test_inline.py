"""LLM-only inline cleanup keeps readable Markdown delimiters."""

import unittest

from lexidown import TurndownService
from lexidown.plugins.joplin_gfm import gfm
from lexidown.plugins.llm import llm


class LLMInline(unittest.TestCase):
    def test_hard_breaks_stay_outside_emphasis_edges(self):
        for tag, delimiter in (("strong", "**"), ("b", "**"), ("em", "_"), ("i", "_")):
            with self.subTest(tag=tag):
                html = f"<p>Before<{tag}><br>Manufacturer<br></{tag}>Address</p>"
                self.assertEqual(
                    TurndownService().use(llm).turndown(html),
                    f"Before  \n{delimiter}Manufacturer{delimiter}  \nAddress",
                )

    def test_inner_breaks_and_nested_code_are_preserved(self):
        self.assertEqual(
            TurndownService()
            .use(llm)
            .turndown("<p><strong>First<br><code>x_y</code><br></strong>Next</p>"),
            "**First  \n`x_y`**  \nNext",
        )
        self.assertEqual(
            TurndownService()
            .use(llm)
            .turndown("<pre><code><strong>first<br>second</strong></code></pre>"),
            "```\nfirst\nsecond\n```",
        )

    def test_ordinary_spaces_and_configured_delimiters_are_preserved(self):
        self.assertEqual(
            TurndownService({"emDelimiter": "*", "strongDelimiter": "__"})
            .use(llm)
            .turndown(
                "<p>Before <em> gentle </em> and <strong> bold </strong> after.</p>"
            ),
            "Before *gentle* and __bold__ after.",
        )

    def test_default_and_gfm_behavior_remain_unchanged(self):
        html = "<p><strong>Manufacturer<br></strong>Address</p>"
        for service in (TurndownService(), TurndownService().use(gfm)):
            with self.subTest(service=service):
                self.assertEqual(service.turndown(html), "**Manufacturer  \n**Address")

    def test_stateful_choices_preserve_selection_without_changing_other_controls(self):
        service = TurndownService().use(llm)
        output = service.turndown(
            '<main><div role="group"><button aria-pressed="true">2</button>'
            '<button aria-pressed="false">3</button><button aria-pressed="false">4</button>'
            '</div><div role="tablist"><span role="tab" aria-selected="true">Per portion</span>'
            '<span role="tab" aria-selected="false">Per 100g</span></div>'
            '<span role="button" aria-pressed="mixed">Blend</span></main>'
        )
        self.assertEqual(
            " ".join(output.split()),
            "2 (pressed) 3 4 Per portion (selected) Per 100g Blend (pressed: mixed)",
        )
        ordinary = (
            '<p><button>Save</button></p><ul><li><input type="checkbox" checked>Done</li></ul>'
            '<p><code><button aria-pressed="true">literal</button></code></p>'
            '<pre><button aria-selected="true">source</button></pre>'
        )
        self.assertEqual(
            service.turndown(ordinary),
            "Save\n\n-   [x] Done\n\n`literal`\n\n```\nsource\n```",
        )
