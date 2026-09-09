"""Mutable Turndown API behavior that optimization must preserve."""

import unittest

from lexidown import TurndownService


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
        rule["replacement"] = lambda content: "(" + content + ")"
        self.assertEqual(service.turndown("<p>x</p><em>y</em><i>z</i>"), "x\n\n(y)!z!")

    def test_child_can_replace_already_selected_parent_replacement(self):
        service = TurndownService()
        parent_rule = service.options["rules"]["paragraph"]

        def replacement(content):
            parent_rule["replacement"] = lambda value: "changed(" + value + ")"
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
