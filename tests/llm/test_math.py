"""Declared math alternatives survive without duplicating hidden renderings."""

import unittest

from lexidown import TurndownService
from lexidown.dom import root_node
from lexidown.plugins.llm import llm


def equation(tex):
    return (
        f'<math alttext="{tex}"><semantics><mi>x</mi><mn>2</mn>'
        f'<annotation encoding="application/x-tex">{tex}</annotation>'
        "</semantics></math>"
    )


class LLMMath(unittest.TestCase):
    def test_visible_math_emits_annotation_once_with_tex_unchanged(self):
        for tex in (r"x^{2}", r"\frac{-b\pm\sqrt{b^2-4ac}}{2a}", r"x_{1}+x_{2}"):
            with self.subTest(tex=tex):
                output = (
                    TurndownService()
                    .use(llm)
                    .turndown("<p>Equation " + equation(tex) + ".</p>")
                )
                self.assertEqual(output, "Equation $" + tex + "$.")

    def test_css_hidden_math_uses_matching_visible_image(self):
        tex = r"x_{1}^{2}"
        for wrapper in (
            '<span style="display: none">{math}</span>',
            '<span aria-hidden="true">{math}</span>',
        ):
            html = (
                "<p>Equation <span>"
                + wrapper.format(math=equation(tex))
                + f'<img aria-hidden="true" src="/equation.svg" alt="{tex}">'
                "</span>.</p>"
            )
            with self.subTest(wrapper=wrapper):
                self.assertEqual(
                    TurndownService().use(llm).turndown(html),
                    "Equation $" + tex + "$.",
                )

    def test_visible_math_removes_only_matching_image_alternative(self):
        html = (
            equation("x^2") + '<img src="/equation.svg" alt="x^2">'
            '<img src="/diagram.svg" alt="Graph">'
        )
        self.assertEqual(
            TurndownService().use(llm).turndown(html),
            "$x^2$![Graph](/diagram.svg)",
        )

    def test_hidden_sections_stay_hidden_and_unmatched_images_keep_own_alt(self):
        hidden = (
            '<span style="display:none">'
            + equation("x^2")
            + '</span><img aria-hidden="true" src="/equation.svg" alt="x^2">'
        )
        for attribute in ('hidden=""', 'aria-hidden="true"', 'style="display:none"'):
            with self.subTest(attribute=attribute):
                self.assertEqual(
                    TurndownService()
                    .use(llm)
                    .turndown(
                        f"<section {attribute}>{hidden}</section><p>Visible.</p>"
                    ),
                    "Visible.",
                )
        output = (
            TurndownService()
            .use(llm)
            .turndown(
                hidden.replace('alt="x^2"', 'alt="Other equation"') + "<p>Visible.</p>"
            )
        )
        self.assertEqual(output, "![Other equation](/equation.svg)\n\nVisible.")
        self.assertNotIn("$x^2$", output)

    def test_alttext_without_annotation_and_original_dom_are_preserved(self):
        node = root_node('<p><math alttext="x^2"><mi>x</mi><mn>2</mn></math></p>', {})
        before = node.outerHTML
        service = TurndownService().use(llm)
        for _ in range(2):
            self.assertEqual(service.turndown(node), "$x^2$")
            self.assertEqual(node.outerHTML, before)

        self.assertEqual(service.turndown('<math alttext="x^2"></math>'), "$x^2$")

    def test_renderer_whitespace_differences_keep_original_tex(self):
        tex = r"\operatorname {sgn}(b)"
        html = (
            '<span><span style="display:none">'
            + equation(tex)
            + '</span><img aria-hidden="true" src="/math.svg" '
            r'alt="\operatorname {sgn} (b)"></span>'
        )
        self.assertEqual(TurndownService().use(llm).turndown(html), "$" + tex + "$")

    def test_hidden_sections_are_not_treated_as_inline_math_wrappers(self):
        html = (
            '<section style="display:none">'
            + equation("x^2")
            + '</section><img aria-hidden="true" src="/math.svg" alt="x^2">'
            "<p>Visible.</p>"
        )
        self.assertEqual(TurndownService().use(llm).turndown(html), "Visible.")


if __name__ == "__main__":
    unittest.main()
