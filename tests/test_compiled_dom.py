"""Native DOM ownership, callback mutations, and Python DOM import."""

import gc
import unittest
from xml.dom import minidom

from lexidown._native import Node, parse_html, root_node


class CompiledDOM(unittest.TestCase):
    def test_native_nodes_and_live_children_preserve_identity(self):
        root = root_node("<p>first</p><p>second</p>", {})
        self.assertIsInstance(root, Node)
        self.assertIs(root._dom, root)
        children = root.childNodes
        first, second = children
        self.assertIs(root.firstChild, first)
        self.assertIs(first.nextSibling, second)
        root.removeChild(first)
        self.assertEqual(children, [second])
        root.appendChild(first)
        self.assertEqual(children, [second, first])
        self.assertIs(first.previousSibling, second)
        self.assertIs(first.parentNode, root)
        self.assertEqual(root.textContent, "secondfirst")

    def test_import_copies_python_dom_and_keeps_adjacent_text(self):
        document = minidom.Document()
        element = document.createElement("div")
        element.appendChild(document.createTextNode("-"))
        element.appendChild(document.createTextNode("-"))
        imported = Node(element)
        imported.firstChild.data = "changed"
        self.assertEqual(element.firstChild.data, "-")
        self.assertEqual(len(imported.childNodes), 2)
        self.assertEqual(imported.textContent, "changed-")

    def test_unchanged_text_setters_preserve_cached_metadata(self):
        root = root_node("<p>unchanged</p>", {})
        text = root.firstChild.firstChild
        index = root._text_index
        for attribute in ("nodeValue", "data", "textContent"):
            with self.subTest(attribute=attribute):
                setattr(text, attribute, "unchanged")
                self.assertTrue(text._metadata_valid)
                self.assertTrue(root._metadata_valid)
                self.assertIs(root._text_index, index)
        text.data = "changed"
        self.assertFalse(root._metadata_valid)
        self.assertEqual(root.textContent, "changed")

    def test_attribute_existence_matches_lookup_with_empty_values(self):
        root = root_node('<input checked><svg viewBox=""></svg>text', {})
        checkbox, svg, text = root.childNodes
        self.assertTrue(checkbox.hasAttribute("CHECKED"))
        self.assertFalse(checkbox.hasAttribute("missing"))
        self.assertTrue(svg.hasAttribute("viewBox"))
        self.assertTrue(svg.hasAttribute("viewbox"))
        self.assertFalse(svg.hasAttribute("VIEWBOX"))
        self.assertFalse(text.hasAttribute("checked"))

    def test_detached_and_reparented_nodes_retain_their_documents(self):
        source = root_node("<em>retained</em>", {})
        child = source.firstChild
        target = root_node("<b>target</b>", {})
        target.appendChild(child)
        del source
        gc.collect()
        self.assertEqual(child.textContent, "retained")
        self.assertIs(child.parentNode, target)
        del target
        gc.collect()
        self.assertEqual(child.parentNode.textContent, "targetretained")
        child.parentNode.removeChild(child)
        gc.collect()
        child.textContent = "still alive"
        self.assertEqual(child.outerHTML, "<em>still alive</em>")

    def test_native_foreign_attributes_templates_and_surrogates(self):
        document = parse_html(
            '<svg><linearGradient viewBox="1" xlink:href="/x"/></svg>'
            '<template><p>inside</p></template><p data-x="\ud800">\udfff</p>'
        )
        gradient = document.getElementsByTagName("linearGradient")[0]
        self.assertEqual(gradient.namespaceURI, "http://www.w3.org/2000/svg")
        self.assertEqual(gradient.getAttribute("viewBox"), "1")
        self.assertEqual(gradient.localName, "linearGradient")
        self.assertEqual(gradient.cloneNode(True).outerHTML, gradient.outerHTML)
        self.assertEqual(
            gradient.attributes["xlink:href"].namespaceURI,
            "http://www.w3.org/1999/xlink",
        )
        template = document.getElementsByTagName("template")[0]
        self.assertEqual(template.childNodes, [])
        self.assertEqual(template.innerHTML, "<p>inside</p>")
        self.assertEqual(template.cloneNode(True).innerHTML, "<p>inside</p>")
        paragraph = document.getElementsByTagName("p")[0]
        self.assertEqual(paragraph.getAttribute("data-x"), "\ud800")
        self.assertEqual(paragraph.textContent, "\udfff")

    def test_import_preserves_attribute_namespaces(self):
        document = minidom.Document()
        element = document.createElementNS("urn:custom", "p:item")
        element.setAttributeNS("urn:attribute", "q:value", "data")
        imported = Node(element)
        self.assertEqual(imported.nodeName, "p:item")
        self.assertEqual(imported.namespaceURI, "urn:custom")
        attribute = imported.attributes["q:value"]
        self.assertEqual(attribute.namespaceURI, "urn:attribute")
        self.assertEqual(attribute.localName, "value")
        self.assertEqual(attribute.value, "data")

    def test_import_preserves_colons_without_an_explicit_namespace(self):
        document = minidom.Document()
        element = document.createElement("p:mark")
        element.appendChild(document.createTextNode("kept"))
        imported = Node(element)
        self.assertEqual(imported.outerHTML, "<p:mark>kept</p:mark>")
        self.assertEqual(imported.cloneNode(True).outerHTML, imported.outerHTML)

    def test_invalid_native_node_operations_raise_python_errors(self):
        text = root_node("text", {}).firstChild
        with self.assertRaises(AttributeError):
            text.setAttribute("x", "y")
        with self.assertRaises(AttributeError):
            _ = text.publicId
        with self.assertRaises(AttributeError):
            _ = text.systemId
