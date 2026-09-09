"""Upstream Turndown 7.2.4 fixtures and API tests, plus Python boundary checks."""

import json
import random
import unittest
from pathlib import Path
from xml.dom import minidom

import html5lib

from lexidown import TurndownService
from lexidown.dom import edge_whitespace, root_node
from lexidown.html_parser import HTMLParser
from lexidown.service import _join_parts

FIXTURES = json.loads(
    (Path(__file__).parent / "fixtures/turndown.json").read_text(encoding="utf-8")
)


class UpstreamFixtures(unittest.TestCase):
    """Each HTML fixture is tested as both a string and a DOM element."""


def fixture_test(case, mode):
    def test(self):
        service = TurndownService(case["options"])
        if mode == "string":
            value = case["html"]
        else:
            document = html5lib.parse(case["element"], treebuilder="dom")
            document.normalize()
            value = next(
                node
                for node in document.getElementsByTagName("div")
                if node.getAttribute("class") == "input"
            )
        self.assertEqual(service.turndown(value), case["expected"], case["name"])

    test.__doc__ = f"{case['name']} ({mode})"
    return test


for _index, _case in enumerate(FIXTURES):
    for _mode in ("string", "DOM"):
        setattr(
            UpstreamFixtures, f"test_{_index:03d}_{_mode}", fixture_test(_case, _mode)
        )


class UpstreamAPI(unittest.TestCase):
    def setUp(self):
        self.service = TurndownService()

    def test_malformed_documents(self):
        self.service.turndown(
            '<HTML><head></head><BODY><!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"><body onload=alert(document.cookie);></body></html>'
        )

    def test_null_input(self):
        with self.assertRaisesRegex(TypeError, "null is not a string"):
            self.service.turndown(None)

    def test_undefined_input(self):
        with self.assertRaisesRegex(TypeError, "undefined is not a string"):
            self.service.turndown()

    def test_add_rule_returns_instance(self):
        rule = {
            "filter": ["del", "s", "strike"],
            "replacement": lambda content: "~~" + content + "~~",
        }
        self.assertIs(self.service.addRule("strikethrough", rule), self.service)

    def test_add_rule_delegates_to_rules(self):
        rule = {
            "filter": ["del", "s", "strike"],
            "replacement": lambda content: "~~" + content + "~~",
        }
        calls = []
        self.service.rules.add = lambda key, value: calls.append((key, value))
        self.service.addRule("strikethrough", rule)
        self.assertEqual(calls, [("strikethrough", rule)])
        self.assertIs(calls[0][1], rule)

    def test_use_returns_instance(self):
        self.assertIs(self.service.use(lambda: None), self.service)

    def test_use_single_plugin(self):
        calls = []
        self.service.use(calls.append)
        self.assertEqual(calls, [self.service])

    def test_use_multiple_plugins(self):
        calls = []
        self.service.use(
            [
                lambda service: calls.append((1, service)),
                lambda service: calls.append((2, service)),
            ]
        )
        self.assertEqual(calls, [(1, self.service), (2, self.service)])

    def test_keep_elements_as_html(self):
        html = "<p>Hello <del>world</del><ins>World</ins></p>"
        self.assertEqual(self.service.turndown(html), "Hello worldWorld")
        self.service.keep(["del", "ins"])
        self.assertEqual(
            self.service.turndown(html), "Hello <del>world</del><ins>World</ins>"
        )

    def test_keep_returns_instance(self):
        self.assertIs(self.service.keep(["del", "ins"]), self.service)

    def test_keep_is_overridden_by_standard_rules(self):
        self.service.keep("p")
        self.assertEqual(self.service.turndown("<p>Hello world</p>"), "Hello world")

    def test_keep_blank_but_meaningful_elements(self):
        self.service.keep("figure")
        html = '<figure><iframe src="http://example.com"></iframe></figure>'
        self.assertEqual(self.service.turndown(html), html)

    def test_custom_keep_replacement(self):
        service = TurndownService(
            {"keepReplacement": lambda content, node: "\n\n" + node.outerHTML + "\n\n"}
        )
        service.keep(["del", "ins"])
        self.assertEqual(
            service.turndown("<p>Hello <del>world</del><ins>World</ins></p>"),
            "Hello \n\n<del>world</del>\n\n<ins>World</ins>",
        )

    def test_remove_elements(self):
        html = "<del>Please redact me</del>"
        self.assertEqual(self.service.turndown(html), "Please redact me")
        self.service.remove("del")
        self.assertEqual(self.service.turndown(html), "")

    def test_remove_returns_instance(self):
        self.assertIs(self.service.remove(["del", "ins"]), self.service)

    def test_remove_is_overridden_by_rules(self):
        self.service.remove("p")
        self.assertEqual(self.service.turndown("<p>Hello world</p>"), "Hello world")

    def test_remove_is_overridden_by_keep(self):
        self.service.keep(["del", "ins"]).remove(["del", "ins"])
        self.assertEqual(
            self.service.turndown("<p>Hello <del>world</del><ins>World</ins></p>"),
            "Hello <del>world</del><ins>World</ins>",
        )


class UpstreamInternals(unittest.TestCase):
    def test_textarea_parser_removes_only_one_initial_line_feed(self):
        document = HTMLParser().parse("<textarea>&#10;&#10;x</textarea>")
        textarea = document.getElementsByTagName("textarea")[0]
        self.assertEqual(
            "".join(child.nodeValue for child in textarea.childNodes), "\nx"
        )

    def test_edge_whitespace_detection(self):
        ws = "\r\n \t"

        def edges(leading_ascii, leading_non_ascii, trailing_non_ascii, trailing_ascii):
            return {
                "leading": leading_ascii + leading_non_ascii,
                "leadingAscii": leading_ascii,
                "leadingNonAscii": leading_non_ascii,
                "trailing": trailing_non_ascii + trailing_ascii,
                "trailingNonAscii": trailing_non_ascii,
                "trailingAscii": trailing_ascii,
            }

        cases = [
            (f"{ws}HELLO WORLD{ws}", edges(ws, "", "", ws)),
            (f"{ws}H{ws}", edges(ws, "", "", ws)),
            (
                f"{ws}\xa0{ws}HELLO{ws}WORLD{ws}\xa0{ws}",
                edges(ws, f"\xa0{ws}", f"{ws}\xa0", ws),
            ),
            (
                f"\xa0{ws}HELLO{ws}WORLD{ws}\xa0",
                edges("", f"\xa0{ws}", f"{ws}\xa0", ""),
            ),
            (f"\xa0{ws}\xa0", edges("", f"\xa0{ws}\xa0", "", "")),
            (f"{ws}\xa0{ws}", edges(ws, f"\xa0{ws}", "", "")),
            (f"{ws}\xa0", edges(ws, "\xa0", "", "")),
            ("HELLO WORLD", edges("", "", "", "")),
            ("", edges("", "", "", "")),
            ("TEST" + " " * 32767 + "END", edges("", "", "", "")),
        ]
        for value, expected in cases:
            with self.subTest(value=value[:60]):
                self.assertEqual(edge_whitespace(value), expected)


class PythonBoundaries(unittest.TestCase):
    def test_optimized_join_matches_upstream_pairwise_join(self):
        generator = random.Random(724)
        alphabet = ["", "x", "\n", "\n\n", "\n\n\n", "\ntext\n", " \n ", "🙂"]
        for _ in range(200):
            parts = generator.choices(alphabet, k=generator.randrange(20))
            expected = ""
            for part in parts:
                left, right = expected.rstrip("\n"), part.lstrip("\n")
                separator = "\n\n"[
                    : max(len(expected) - len(left), len(part) - len(right))
                ]
                expected = left + separator + right
            self.assertEqual(_join_parts(parts), expected, parts)

    def test_invalid_inputs(self):
        document = minidom.Document()
        for value in (
            False,
            True,
            1,
            1.2,
            b"<p>x</p>",
            [],
            {},
            document.createTextNode("x"),
        ):
            with self.subTest(value=value), self.assertRaises(TypeError):
                TurndownService().turndown(value)

    def test_document_fragment_and_element_do_not_mutate_input(self):
        document = html5lib.parse(
            "<p> first   <em> second </em> </p>", treebuilder="dom"
        )
        fragment = document.createDocumentFragment()
        fragment.appendChild(document.getElementsByTagName("p")[0].cloneNode(True))
        for value in (document, fragment, document.getElementsByTagName("body")[0]):
            with self.subTest(kind=value.nodeType):
                before = (
                    value.toxml()
                    if value.nodeType != 11
                    else "".join(child.toxml() for child in value.childNodes)
                )
                service = TurndownService()
                self.assertEqual(service.turndown(value), "first _second_")
                after = (
                    value.toxml()
                    if value.nodeType != 11
                    else "".join(child.toxml() for child in value.childNodes)
                )
                self.assertEqual(after, before)

    def test_caller_supplied_adjacent_text_nodes_keep_their_boundaries(self):
        document = minidom.Document()
        element = document.createElement("div")
        element.appendChild(document.createTextNode("-"))
        element.appendChild(document.createTextNode("-"))
        self.assertEqual(TurndownService().turndown(element), "\\-\\-")

    def test_dom_metadata_caches_follow_mutation(self):
        service = TurndownService()
        root = root_node(
            "<div><em>old</em><b>same</b></div><ol><li>a</li><li>b</li></ol>",
            service.options,
        )
        div, ol = root.children
        em, bold = div.children
        self.assertEqual(div.textContent, "oldsame")
        em.textContent = "new"
        self.assertEqual(div.textContent, "newsame")
        self.assertEqual(bold.textContent, "same")
        first, second = ol.children
        self.assertEqual(second.element_index, 1)
        ol.removeChild(first)
        self.assertEqual(second.element_index, 0)

    def test_filter_options_and_callback_arities(self):
        service = TurndownService({"mark": "!"})
        seen = []

        def filter_node(node, options):
            seen.append((node.nodeName, options["mark"]))
            return node.nodeName == "DEL"

        service.add_rule(
            "strike",
            {
                "filter": filter_node,
                "replacement": lambda content, node, options: options["mark"] + content,
            },
        )
        self.assertEqual(service.turndown("<del>x</del>"), "!x")
        self.assertIn(("DEL", "!"), seen)
        service.addRule("zero", {"filter": "del", "replacement": lambda: "zero"})
        self.assertEqual(service.turndown("<del>x</del>"), "zero")

    def test_custom_rules_override_and_append(self):
        service = TurndownService()
        rule = {
            "filter": "p",
            "replacement": lambda content: "(" + content + ")",
            "append": lambda options: "\n\n" + options["hr"],
        }
        service.addRule("paragraph", rule)
        self.assertIs(service.rules.array[0], rule)
        self.assertEqual(service.turndown("<p>x</p>"), "(x)\n\n* * *")

    def test_rules_can_remove_later_siblings(self):
        def replacement(content, node):
            if node.nextSibling is not None:
                node.parentNode.removeChild(node.nextSibling)
            return content

        service = TurndownService().addRule(
            "remove-next", {"filter": "p", "replacement": replacement}
        )
        self.assertEqual(service.turndown("<p>first</p><p>second</p>"), "first")

    def test_rules_appending_siblings_do_not_extend_current_traversal(self):
        def replacement(content, node):
            extra = node.cloneNode(True)
            extra.textContent = "extra"
            node.parentNode.appendChild(extra)
            return content

        service = TurndownService().addRule(
            "append-next", {"filter": "p", "replacement": replacement}
        )
        self.assertEqual(service.turndown("<p>first</p>"), "first")

    def test_custom_blank_and_default_replacements(self):
        service = TurndownService(
            {
                "blankReplacement": lambda: "blank",
                "defaultReplacement": lambda content: "(" + content + ")",
            }
        )
        self.assertEqual(service.turndown("<div></div><mark>x</mark>"), "blank(x)")

    def test_kept_command_element_has_a_closing_tag(self):
        self.assertEqual(
            TurndownService().keep("command").turndown("<command>"),
            "<command></command>",
        )

    def test_callback_type_error_is_not_swallowed(self):
        def broken(content):
            raise TypeError("intentional callback failure")

        service = TurndownService().addRule(
            "broken", {"filter": "p", "replacement": broken}
        )
        with self.assertRaisesRegex(TypeError, "intentional callback failure"):
            service.turndown("<p>x</p>")

    def test_invalid_plugin_and_filter(self):
        with self.assertRaises(TypeError):
            TurndownService().use("not a plugin")
        with self.assertRaises(TypeError):
            TurndownService().addRule(
                "bad", {"filter": 1, "replacement": lambda: ""}
            ).turndown("<p>x</p>")

    def test_referenced_link_state_resets_between_calls_and_instances(self):
        service = TurndownService({"linkStyle": "referenced"})
        html = '<a href="/one">one</a>'
        expected = "[one][1]\n\n[1]: /one"
        self.assertEqual(service.turndown(html), expected)
        self.assertEqual(service.turndown("plain"), "plain")
        self.assertEqual(service.turndown(html), expected)
        self.assertEqual(
            TurndownService({"linkStyle": "referenced"}).turndown(html), expected
        )

    def test_reference_rule_uses_and_replaces_public_references(self):
        service = TurndownService({"linkStyle": "referenced"})
        rule = service.options["rules"]["referenceLink"]
        assigned = ["[x]: /x"]
        rule["references"] = assigned
        self.assertEqual(service.turndown("plain"), "plain\n\n[x]: /x")
        self.assertEqual(rule["references"], [])
        self.assertIsNot(rule["references"], assigned)
        self.assertEqual(assigned, ["[x]: /x"])

    def test_escape_overriding(self):
        service = TurndownService()
        service.escape = lambda value: value
        self.assertEqual(
            service.turndown("<p>*text*</p><code>*code*</code>"), "*text*\n\n`*code*`"
        )

    def test_deep_and_wide_documents(self):
        service = TurndownService()
        self.assertEqual(
            service.turndown("<span>" * 1500 + "deep" + "</span>" * 1500), "deep"
        )
        self.assertEqual(service.turndown("<p>x</p>" * 2000), "\n\n".join(["x"] * 2000))

    def test_utf16_heading_lengths_and_javascript_whitespace(self):
        self.assertEqual(TurndownService().turndown("<h1>🙂</h1>"), "🙂\n==")
        self.assertEqual(TurndownService().turndown("<em>\u0085</em>"), "_\u0085_")

    def test_parser_regressions_from_javascript_differential_fuzzing(self):
        cases = [
            ("<p><template><hr>", ""),
            ("<template><div></template> hello  world ", "hello world"),
            ("<template><b></template>x", "x"),
            ("<i><template></i>1. x", ""),
            ("<li><template><li><hr>", ""),
            ("<noscript><template></noscript><img src='x'>", ""),
            (
                "<table><template><tr><td>x</td></tr></template><tr><td>y</td></tr></table>",
                "y",
            ),
            ("<table><template><td><hr>", ""),
            ("<table><template><table>x", ""),
            ("<template><td><tr>", ""),
            ("<template><td></td></table>", ""),
            ("<span><em></span><textarea>", "</x-turndown>"),
            ("<span><em></span><textarea>x</textarea>tail", "x_tail_"),
            ("<pre><i></pre><textarea>", "</x-turndown>"),
            ("<table><li>a<li>b", "*   a\n*   b"),
            ("<table><dd>a<dd>b<dt>c", "a\n\nb\n\nc"),
        ]
        for html, expected in cases:
            with self.subTest(html=html):
                self.assertEqual(TurndownService().turndown(html), expected)


if __name__ == "__main__":
    unittest.main()
