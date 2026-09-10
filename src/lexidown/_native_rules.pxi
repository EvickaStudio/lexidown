# CommonMark rules. Included after Node, JS_WS, js_trim and escape_markdown.
import math as _rules_math
import re as _rules_re
from decimal import Decimal as _RulesDecimal

from cpython.unicode cimport (
    PyUnicode_DATA, PyUnicode_GET_LENGTH, PyUnicode_KIND, PyUnicode_READ,
)

_LINE_START = r"(?:\A|(?<=[\r\n\u2028\u2029]))"
_BLOCKQUOTE_PREFIX = _rules_re.compile(_LINE_START)
_CLEAN_ATTRIBUTE = _rules_re.compile(r"\n[" + _rules_re.escape(JS_WS) + r"]*")
_LANGUAGE = _rules_re.compile(r"language-([^" + _rules_re.escape(JS_WS) + r"]+)")
_LINK_DESTINATION = _rules_re.compile(r"([<>()])")
_INLINE_NEWLINES = _rules_re.compile(r"\r?\n|\r")
_INLINE_PADDING = _rules_re.compile(
    r"\A`|\A [^\r\n\u2028\u2029]*?[^ ][^\r\n\u2028\u2029]* \Z|`\Z"
)
_BACKTICKS = _rules_re.compile(r"`+")
_DECIMAL_NUMBER = _rules_re.compile(
    r"[+-]?(?:Infinity|(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eE][+-]?[0-9]+)?)"
)
_BASED_NUMBER = _rules_re.compile(r"0(?:[xX][0-9a-fA-F]+|[bB][01]+|[oO][0-7]+)")
_CUSTOM_CALLBACK = object()


cpdef Py_ssize_t _utf16_length(str value):
    cdef Py_ssize_t length = PyUnicode_GET_LENGTH(value)
    cdef Py_ssize_t result = length
    cdef Py_ssize_t index
    cdef int kind = PyUnicode_KIND(value)
    cdef void* data = PyUnicode_DATA(value)
    if kind < 4:
        return length
    for index in range(length):
        if PyUnicode_READ(kind, data, index) > 0xffff:
            result += 1
    return result


cpdef object _number(str value):
    value = js_trim(value)
    if not value:
        return 0.0
    if _DECIMAL_NUMBER.fullmatch(value):
        return float(value)
    if _BASED_NUMBER.fullmatch(value):
        try:
            return float(int(value, 0))
        except OverflowError:
            return _rules_math.inf
    return _rules_math.nan


cpdef str _number_string(object value):
    if _rules_math.isnan(value):
        return "NaN"
    if _rules_math.isinf(value):
        return "Infinity" if value > 0 else "-Infinity"
    if value == 0:
        return "0"
    result = repr(value)
    if "e" in result:
        if 1e-6 <= abs(value) < 1e21:
            return format(_RulesDecimal(result), "f")
        mantissa, exponent = result.split("e")
        return mantissa + "e" + format(int(exponent), "+d")
    return result.removesuffix(".0")


cdef str _clean_attribute(object attribute):
    return _CLEAN_ATTRIBUTE.sub("\n", attribute) if attribute else ""


cdef str _escape_link_destination(str destination):
    cdef str escaped = _LINK_DESTINATION.sub(r"\\\1", destination)
    return "<" + escaped + ">" if " " in escaped else escaped


cdef str _escape_link_title(str title):
    return title.replace('"', '\\"')


cpdef str _paragraph(str content, Node node, dict options):
    return "\n\n" + content + "\n\n"


cpdef str _line_break(str content, Node node, dict options):
    return options["br"] + "\n"


cpdef str _heading(str content, Node node, dict options):
    cdef int level = int(node.nodeName[1])
    if options["headingStyle"] == "setext" and level < 3:
        underline = ("=" if level == 1 else "-") * _utf16_length(content)
        return "\n\n" + content + "\n" + underline + "\n\n"
    return "\n\n" + "#" * level + " " + content + "\n\n"


cpdef str _blockquote(str content, Node node, dict options):
    return "\n\n" + _BLOCKQUOTE_PREFIX.sub("> ", content.strip("\n")) + "\n\n"


cpdef str _list(str content, Node node, dict options):
    cdef Node parent = node.parentNode
    if parent.nodeName == "LI" and parent.lastElementChild is node:
        return "\n" + content
    return "\n\n" + content + "\n\n"


cpdef str _list_item(str content, Node node, dict options):
    cdef str prefix = options["bulletListMarker"] + "   "
    cdef Node parent = node.parentNode
    if parent.nodeName == "OL":
        start = parent.getAttribute("start")
        index = node.element_index
        number = _number_string(_number(start) + index) if start else str(index + 1)
        prefix = number + ".  "
    is_paragraph = content.endswith("\n")
    content = content.strip("\n") + ("\n" if is_paragraph else "")
    content = content.replace("\n", "\n" + " " * _utf16_length(prefix))
    return prefix + content + ("\n" if node.nextSibling is not None else "")


cdef bint _is_code_block(Node node, dict options, str style):
    cdef Node child
    if node.nodeName != "PRE" or options["codeBlockStyle"] != style:
        return False
    child = node.firstChild
    return child is not None and child.nodeName == "CODE"


cpdef bint _is_indented_code_block(Node node, dict options):
    return _is_code_block(node, options, "indented")


cpdef bint _is_fenced_code_block(Node node, dict options):
    return _is_code_block(node, options, "fenced")


cpdef str _indented_code_block(str content, Node node, dict options):
    cdef Node child = node.firstChild
    return "\n\n    " + child.textContent.replace("\n", "\n    ") + "\n\n"


cpdef str _fenced_code_block(str content, Node node, dict options):
    cdef Node child = node.firstChild
    cdef str class_name = child.getAttribute("class") or ""
    match = _LANGUAGE.search(class_name)
    language = match[1] if match else ""
    cdef str code = child.textContent
    cdef str fence_char = (
        options["fence"]
        .encode("utf-16-le", "surrogatepass")[:2]
        .decode("utf-16-le", "surrogatepass")
    )
    cdef Py_ssize_t fence_size = 3
    for match in _rules_re.finditer(_LINE_START + fence_char + "{3,}", code):
        fence_size = max(fence_size, _utf16_length(match[0]) + 1)
    fence = fence_char * fence_size
    return "\n\n" + fence + language + "\n" + code.removesuffix("\n") + "\n" + fence + "\n\n"


cpdef str _horizontal_rule(str content, Node node, dict options):
    return "\n\n" + options["hr"] + "\n\n"


cpdef bint _is_inline_link(Node node, dict options):
    return node.nodeName == "A" and options["linkStyle"] == "inlined" and bool(node.getAttribute("href"))


cpdef bint _is_reference_link(Node node, dict options):
    return node.nodeName == "A" and options["linkStyle"] == "referenced" and bool(node.getAttribute("href"))


cpdef str _inline_link(str content, Node node, dict options):
    cdef str href = _escape_link_destination(node.getAttribute("href"))
    cdef str title = _escape_link_title(_clean_attribute(node.getAttribute("title")))
    title_part = ' "' + title + '"' if title else ""
    return "[" + content + "](" + href + title_part + ")"


cdef str _reference_link(str content, Node node, dict options, dict rule):
    references = rule["references"]
    cdef str href = _escape_link_destination(node.getAttribute("href"))
    cdef str title = _clean_attribute(node.getAttribute("title"))
    if title:
        title = ' "' + _escape_link_title(title) + '"'
    style = options["linkReferenceStyle"]
    if style == "collapsed":
        replacement = "[" + content + "][]"
        reference = "[" + content + "]: " + href + title
    elif style == "shortcut":
        replacement = "[" + content + "]"
        reference = "[" + content + "]: " + href + title
    else:
        reference_id = str(len(references) + 1)
        replacement = "[" + content + "][" + reference_id + "]"
        reference = "[" + reference_id + "]: " + href + title
    references.append(reference)
    return replacement


cpdef str _emphasis(str content, Node node, dict options):
    if not js_trim(content):
        return ""
    return options["emDelimiter"] + content + options["emDelimiter"]


cpdef str _strong(str content, Node node, dict options):
    if not js_trim(content):
        return ""
    return options["strongDelimiter"] + content + options["strongDelimiter"]


cpdef bint _is_inline_code(Node node, dict options):
    cdef Node parent
    if node.nodeName != "CODE":
        return False
    has_siblings = node.previousSibling is not None or node.nextSibling is not None
    parent = node.parentNode
    return not (parent.nodeName == "PRE" and not has_siblings)


cpdef str _code(str content, Node node, dict options):
    cdef set lengths = set()
    cdef Py_ssize_t size = 1
    if not content:
        return ""
    content = _INLINE_NEWLINES.sub(" ", content)
    extra_space = " " if _INLINE_PADDING.search(content) else ""
    for match in _BACKTICKS.findall(content):
        lengths.add(len(match))
    while size in lengths:
        size += 1
    delimiter = "`" * size
    return delimiter + extra_space + content + extra_space + delimiter


cpdef str _image(str content, Node node, dict options):
    cdef str alt = escape_markdown(_clean_attribute(node.getAttribute("alt")))
    cdef str src = _escape_link_destination(node.getAttribute("src") or "")
    cdef str title = _clean_attribute(node.getAttribute("title"))
    title_part = ' "' + _escape_link_title(title) + '"' if title else ""
    return "![" + alt + "](" + src + title_part + ")" if src else ""


def commonmark_rules():
    """Fresh public dictionaries retain reference-link state and callback mutation."""
    reference_rule = {"references": []}

    def reference_link(str content, Node node, dict options):
        return _reference_link(content, node, options, reference_rule)

    def append_references(options):
        references = reference_rule["references"]
        if not references:
            return ""
        result = "\n\n" + "\n".join(references) + "\n\n"
        reference_rule["references"] = []
        return result

    reference_rule.update({"filter": _is_reference_link, "replacement": reference_link, "append": append_references})
    return {
        "paragraph": {"filter": "p", "replacement": _paragraph},
        "lineBreak": {"filter": "br", "replacement": _line_break},
        "heading": {"filter": ["h1", "h2", "h3", "h4", "h5", "h6"], "replacement": _heading},
        "blockquote": {"filter": "blockquote", "replacement": _blockquote},
        "list": {"filter": ["ul", "ol"], "replacement": _list},
        "listItem": {"filter": "li", "replacement": _list_item},
        "indentedCodeBlock": {"filter": _is_indented_code_block, "replacement": _indented_code_block},
        "fencedCodeBlock": {"filter": _is_fenced_code_block, "replacement": _fenced_code_block},
        "horizontalRule": {"filter": "hr", "replacement": _horizontal_rule},
        "inlineLink": {"filter": _is_inline_link, "replacement": _inline_link},
        "referenceLink": reference_rule,
        "emphasis": {"filter": ["em", "i"], "replacement": _emphasis},
        "strong": {"filter": ["strong", "b"], "replacement": _strong},
        "code": {"filter": _is_inline_code, "replacement": _code},
        "image": {"filter": "img", "replacement": _image},
    }


cdef int _builtin_filter(object callback, Node node, dict options) except -2:
    if callback is _is_indented_code_block:
        return _is_indented_code_block(node, options)
    if callback is _is_fenced_code_block:
        return _is_fenced_code_block(node, options)
    if callback is _is_inline_link:
        return _is_inline_link(node, options)
    if callback is _is_reference_link:
        return _is_reference_link(node, options)
    if callback is _is_inline_code:
        return _is_inline_code(node, options)
    return -1


cdef object _builtin_replace(object callback, str content, Node node, dict options):
    if callback is _paragraph:
        return _paragraph(content, node, options)
    if callback is _line_break:
        return _line_break(content, node, options)
    if callback is _heading:
        return _heading(content, node, options)
    if callback is _blockquote:
        return _blockquote(content, node, options)
    if callback is _list:
        return _list(content, node, options)
    if callback is _list_item:
        return _list_item(content, node, options)
    if callback is _indented_code_block:
        return _indented_code_block(content, node, options)
    if callback is _fenced_code_block:
        return _fenced_code_block(content, node, options)
    if callback is _horizontal_rule:
        return _horizontal_rule(content, node, options)
    if callback is _inline_link:
        return _inline_link(content, node, options)
    if callback is _emphasis:
        return _emphasis(content, node, options)
    if callback is _strong:
        return _strong(content, node, options)
    if callback is _code:
        return _code(content, node, options)
    if callback is _image:
        return _image(content, node, options)
    return _CUSTOM_CALLBACK
