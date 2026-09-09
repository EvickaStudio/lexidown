"""Native parser fidelity against frozen Domino results."""

import subprocess
import sys
import textwrap
import unittest

from lexidown import TurndownService
from lexidown.dom import root_node
from lexidown.native_parser import parse_html


class NativeParser(unittest.TestCase):
    def test_native_dom_and_kept_html_preserve_attributes_and_text(self):
        html = '<mark ID="Case" disabled Data-x="&quot;&amp;&nbsp;">a<!-- c -->🙂<em>b</em></mark>'
        document = parse_html(html)
        mark = document.getElementsByTagName("mark")[0]
        self.assertEqual(mark.namespaceURI, "http://www.w3.org/1999/xhtml")
        self.assertEqual(mark.getAttribute("id"), "Case")
        self.assertTrue(mark.hasAttribute("disabled"))
        self.assertEqual(mark.getAttribute("disabled"), "")
        self.assertEqual(mark.getAttribute("data-x"), '"&\xa0')
        self.assertEqual(mark.childNodes[1].nodeType, 8)
        self.assertEqual(mark.childNodes[1].data, " c ")
        self.assertIs(mark.childNodes[2].previousSibling, mark.childNodes[1])
        self.assertIs(mark.lastChild.parentNode, mark)
        self.assertEqual(
            TurndownService().keep("mark").turndown(html),
            '<mark id="Case" disabled="" data-x="&quot;&amp;&nbsp;">a🙂<em>b</em></mark>',
        )

    def test_case_and_tag_boundaries_match_domino(self):
        # Frozen results from scripts/js_oracle.cjs, not another parser alias.
        for tag, expected in (
            ("textarea", "x</x-turndown>"),
            ("template", ""),
            ("svg", "x"),
            ("math", "x"),
            ("select", "x"),
            ("search", "x"),
            ("image", "x"),
            ("frameset", None),
            ("isindex", "x"),
        ):
            for suffix in (">x", "\t>x", "\n>x", "\f>x", "/>x", ""):
                html = "<x-turndown><" + tag.upper() + suffix
                with self.subTest(html=html):
                    if suffix and expected is None:
                        with self.assertRaisesRegex(
                            TypeError, "Cannot read properties of null"
                        ):
                            TurndownService().turndown(html)
                    else:
                        self.assertEqual(
                            TurndownService().turndown(html), expected if suffix else ""
                        )

    def test_lone_surrogates_survive_text_and_attributes(self):
        self.assertEqual(
            TurndownService().turndown("<p>\ud800x\udfff</p>"), "\ud800x\udfff"
        )
        document = parse_html('<p data-x="\ud800">x</p>')
        paragraph = document.getElementsByTagName("p")[0]
        self.assertEqual(paragraph.getAttribute("data-x"), "\ud800")
        self.assertEqual(paragraph.textContent, "x")

    def test_processing_instructions_are_domino_comments(self):
        for tag in ("pre", "template"):
            with self.subTest(tag=tag):
                document = parse_html(f"<{tag}><?test></{tag}>")
                element = document.getElementsByTagName(tag)[0]
                parent = element.content if tag == "template" else element
                self.assertEqual(parent.firstChild.nodeType, 8)
                self.assertEqual(parent.firstChild.nodeName, "#comment")
                self.assertEqual(parent.firstChild.data, "?test")
                self.assertEqual(element.innerHTML, "<!--?test-->")

    def test_compiled_converter_needs_no_external_parser_imports(self):
        script = textwrap.dedent(
            """
            import importlib.machinery
            import sys

            class BlockExternalParsers:
                def find_spec(self, fullname, path=None, target=None):
                    if fullname.split('.', 1)[0] in {'html5lib', 'selectolax'}:
                        raise ImportError('Unexpected parser dependency: ' + fullname)

            sys.meta_path.insert(0, BlockExternalParsers())
            from lexidown import TurndownService, _native

            assert any(_native.__file__.endswith(suffix)
                       for suffix in importlib.machinery.EXTENSION_SUFFIXES)
            service = TurndownService()
            assert service.turndown('<h1>Title</h1><p>Hello <em>world</em>.</p>') == (
                'Title\\n=====\\n\\nHello _world_.'
            )
            assert service.turndown('<select><b>x</b></select>') == 'x'

            def plugin(converter):
                converter.addRule('strike', {
                    'filter': ['del', 's'],
                    'replacement': lambda content: '~~' + content + '~~',
                })

            service.use(plugin)
            assert service.turndown('<p><del>x</del> and <s>y</s></p>') == (
                '~~x~~ and ~~y~~'
            )
            assert not any(name.split('.', 1)[0] in {'html5lib', 'selectolax'}
                           for name in sys.modules)
            """
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_domino_parser_regressions(self):
        for html, expected in (
            ("<select><b>x</b></select>", "x"),
            ("<p>a<search>b</search>c", "abc"),
            ("<table><image src=x></table>", "![](x)"),
            ("<span><em></span><textarea>x</textarea>tail", "x_tail_"),
            ("<p>a\ud800b</p>", "a\ud800b"),
        ):
            with self.subTest(html=html):
                self.assertEqual(TurndownService().turndown(html), expected)

    def test_foreign_namespaces_and_template_content_remain_available(self):
        root = root_node(
            '<svg><linearGradient viewBox="1"/></svg>'
            "<math><mi>x</mi></math><template><p>inside</p></template>",
            {},
        )
        svg, math, template = root.children
        self.assertEqual(svg.namespaceURI, "http://www.w3.org/2000/svg")
        self.assertEqual(svg.firstChild.nodeName, "linearGradient")
        self.assertEqual(svg.firstChild.getAttribute("viewBox"), "1")
        self.assertEqual(math.namespaceURI, "http://www.w3.org/1998/Math/MathML")
        self.assertEqual(template.childNodes, [])
        self.assertEqual(template.content.firstChild.nodeName, "P")
        self.assertEqual(template.innerHTML, "<p>inside</p>")
