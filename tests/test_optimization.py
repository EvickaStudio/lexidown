"""Mutable Turndown API behavior that optimization must preserve."""

import random
import re
import unittest

from lexidown import TurndownService
from lexidown._native import escape_markdown


class NativeEscaping(unittest.TestCase):
    def test_escape_matches_original_algorithm(self):
        translation = str.maketrans({char: "\\" + char for char in "\\*`[]_"})
        special = re.compile(r"[\\*`\[\]_]")
        start = re.compile(r"^(?:-|\+ |[=]+|#{1,6} |~~~|>)")
        ordered = re.compile(r"^([0-9]+)\. ")

        def original(text):
            if not text:
                return text
            if special.search(text):
                text = text.translate(translation)
            if text[0] in "-+=#~>":
                return start.sub(lambda match: "\\" + match[0], text, count=1)
            if "0" <= text[0] <= "9":
                return ordered.sub(r"\1\\. ", text, count=1)
            return text

        randomizer = random.Random(20260910)
        alphabet = "abc 0123456789\\*`[]_-+=#~>.\t\n\r\x00\xa0\u1234\ud800\U0001f600"
        cases = ["", "\\*`[]_", "plain", "\ud800_", "\U0001f600*"]
        for prefix in ("", "-", "+ ", "===", "###### ", "~~~", ">", "123. "):
            cases.extend(
                prefix
                + "".join(randomizer.choices(alphabet, k=randomizer.randrange(100)))
                for _ in range(100)
            )
        for text in cases:
            with self.subTest(text=text):
                self.assertEqual(escape_markdown(text), original(text))


class MutableRuleDispatch(unittest.TestCase):
    def test_options_filter_lists_and_replacements_remain_live(self):
        service = TurndownService()
        rule = {
            "filter": ["p"],
            "replacement": lambda content, node, options: (
                options["emDelimiter"] + content
            ),
        }
        service.addRule("mutable", rule)
        self.assertEqual(service.turndown("<p>x</p>"), "_x")

        service.options["emDelimiter"] = "!"
        rule["filter"][:] = ["em"]
        rule["replacement"] = lambda content: f"({content})"
        self.assertEqual(service.turndown("<p>x</p><em>y</em><i>z</i>"), "x\n\n(y)!z!")

    def test_child_can_replace_already_selected_parent_replacement(self):
        service = TurndownService()
        parent_rule = service.options["rules"]["paragraph"]

        def replacement(content):
            parent_rule["replacement"] = lambda value: f"changed({value})"
            return content

        service.addRule("child", {"filter": "em", "replacement": replacement})
        self.assertEqual(service.turndown("<p><em>x</em></p>"), "changed(x)")

    def test_filter_dispatch_observes_appended_and_reordered_rules(self):
        service = TurndownService({"rules": {}})
        appended = False

        def filter_node():
            nonlocal appended
            if not appended:
                appended = True
                service.rules.array.append(
                    {"filter": "p", "replacement": lambda: "appended"}
                )
            return False

        service.addRule(
            "first", {"filter": filter_node, "replacement": lambda: "unused"}
        )
        self.assertEqual(service.turndown("<p>x</p>"), "appended")
        service.rules.array.append({"filter": "p", "replacement": lambda: "last"})
        self.assertEqual(service.turndown("<p>x</p>"), "appended")
        service.rules.array.reverse()
        self.assertEqual(service.turndown("<p>x</p>"), "last")


if __name__ == "__main__":
    unittest.main()
