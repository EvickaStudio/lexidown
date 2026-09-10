"""Python callbacks interoperate with the compiled rule functions."""

import unittest
from functools import partial

from lexidown import TurndownService
from lexidown._native import _utf16_length


class CompiledRuleCallbacks(unittest.TestCase):
    def test_utf16_length_for_each_unicode_storage_width(self):
        for text in (
            "",
            "ASCII",
            "caf\u00e9",
            "\u1234",
            "\ud800",
            "x\U0001f600\U0010ffff",
        ):
            with self.subTest(text=text):
                self.assertEqual(
                    _utf16_length(text),
                    len(text.encode("utf-16-le", "surrogatepass")) // 2,
                )

    def test_callable_plugin_bound_filter_and_partial_replacement(self):
        class Plugin:
            def filter(self, node, options):
                return node.nodeName == "P" and options["br"] == "  "

            def replacement(self, prefix, content, node):
                return prefix + content + node.nodeName

            def __call__(self, service):
                service.addRule(
                    "callable",
                    {
                        "filter": self.filter,
                        "replacement": partial(self.replacement, "!"),
                    },
                )

        service = TurndownService().use(Plugin())
        self.assertEqual(service.turndown("<p><em>x</em></p>"), "!_x_P")

        class Replacement:
            def __call__(self, content):
                return f"({content})"

        service.addRule(
            "callable-replacement",
            {
                "filter": partial(lambda name, node: node.nodeName == name, "P"),
                "replacement": Replacement(),
            },
        )
        self.assertEqual(service.turndown("<p>x</p>"), "(x)")

    def test_builtin_callbacks_can_be_partially_bound_and_reused(self):
        service = TurndownService()
        link = service.options["rules"]["inlineLink"]
        service.addRule(
            "partially-bound-builtins",
            {
                "filter": partial(link["filter"], options=service.options),
                "replacement": partial(link["replacement"], options=service.options),
            },
        )
        self.assertEqual(
            service.turndown('<p><a href="/x" title="Title">x</a></p>'),
            '[x](/x "Title")',
        )


if __name__ == "__main__":
    unittest.main()
