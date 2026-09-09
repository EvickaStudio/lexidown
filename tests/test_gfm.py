"""Published Joplin GFM 1.0.68 outputs, generated with Turndown 7.2.4/DOMino."""

import json
import unittest
from pathlib import Path

import html5lib

from lexidown import TurndownService
from lexidown.plugins import joplin_gfm

FIXTURES = json.loads(
    (Path(__file__).parent / "fixtures/joplin_gfm.json").read_text(encoding="utf-8")
)["cases"]


def is_code_block(node):
    """The same optional PRE/CODE predicate used for the JavaScript oracle."""
    return (
        node.nodeName == "PRE"
        and node.firstChild is not None
        and node.firstChild.nodeName == "CODE"
    )


class JoplinGFM(unittest.TestCase):
    def test_published_outputs_individually_and_combined(self):
        for case in FIXTURES:
            plugins = {case["plugin"], "gfm"}
            for plugin in sorted(plugins):
                with self.subTest(case=case["name"], plugin=plugin):
                    service = TurndownService(case["options"])
                    if case.get("isCodeBlock"):
                        service.isCodeBlock = is_code_block
                    self.assertIs(service.use(getattr(joplin_gfm, plugin)), service)
                    for _ in range(2):
                        self.assertEqual(
                            service.turndown(case["html"]), case["expected"]
                        )

    def test_table_options_and_code_hooks_belong_to_each_service(self):
        preserving = TurndownService(
            {"preserveTableStyles": True, "preserveNestedTables": True}
        )
        preserving.isCodeBlock = is_code_block
        preserving.use(joplin_gfm.tables)
        ordinary = TurndownService().use(joplin_gfm.tables)
        for name in (
            "custom table styles preserved",
            "preserve nested table as wrapped html",
            "isCodeBlock hook preserves code table html",
        ):
            case = next(case for case in FIXTURES if case["name"] == name)
            with self.subTest(case=name):
                for _ in range(2):
                    self.assertEqual(
                        preserving.turndown(case["html"]), case["expected"]
                    )
                    self.assertNotIn("<table", ordinary.turndown(case["html"]))

    def test_dom_input_is_reusable_and_unchanged(self):
        service = TurndownService().use(joplin_gfm.gfm)
        for name in (
            "all plugins together",
            "table with heading preserved as html",
            "colspan expansion",
        ):
            case = next(case for case in FIXTURES if case["name"] == name)
            document = html5lib.parse(case["html"], treebuilder="dom")
            body = document.getElementsByTagName("body")[0]
            before = body.toxml()
            with self.subTest(case=name):
                for _ in range(2):
                    self.assertEqual(service.turndown(body), case["expected"])
                    self.assertEqual(body.toxml(), before)

    def test_large_colspan_is_bounded(self):
        # The port caps spans at the HTML maximum instead of expanding indefinitely.
        html = '<table><tr><th colspan="1000000000">wide</th><th>end</th></tr></table>'
        output = TurndownService().use(joplin_gfm.tables).turndown(html)
        self.assertEqual(len(output.splitlines()[0].split("|")) - 2, 1001)
        self.assertLess(len(output), 15000)


if __name__ == "__main__":
    unittest.main()
