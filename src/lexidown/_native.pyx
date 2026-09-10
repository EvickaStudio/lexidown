# cython: language_level=3, nonecheck=True
"""Compiled Turndown engine: one native DOM for strings, DOM input and callbacks."""

from inspect import Parameter, signature
from cpython.unicode cimport PyUnicode_New, PyUnicode_WRITE
from ._lexbor cimport *

import re

cdef extern from "Python.h":
    unsigned int PyUnicode_MAX_CHAR_VALUE(object string)

# ECMAScript's \s differs from Python's for NEL and several control characters.
JS_WS = "\t\n\v\f\r \u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"
BLOCK_ELEMENTS = frozenset(
    [
        "ADDRESS",
        "ARTICLE",
        "ASIDE",
        "AUDIO",
        "BLOCKQUOTE",
        "BODY",
        "CANVAS",
        "CENTER",
        "DD",
        "DIR",
        "DIV",
        "DL",
        "DT",
        "FIELDSET",
        "FIGCAPTION",
        "FIGURE",
        "FOOTER",
        "FORM",
        "FRAMESET",
        "H1",
        "H2",
        "H3",
        "H4",
        "H5",
        "H6",
        "HEADER",
        "HGROUP",
        "HR",
        "HTML",
        "ISINDEX",
        "LI",
        "MAIN",
        "MENU",
        "NAV",
        "NOFRAMES",
        "NOSCRIPT",
        "OL",
        "OUTPUT",
        "P",
        "PRE",
        "SECTION",
        "TABLE",
        "TBODY",
        "TD",
        "TFOOT",
        "TH",
        "THEAD",
        "TR",
        "UL",
    ]
)
VOID_ELEMENTS = frozenset(
    [
        "AREA",
        "BASE",
        "BR",
        "COL",
        "COMMAND",
        "EMBED",
        "HR",
        "IMG",
        "INPUT",
        "KEYGEN",
        "LINK",
        "META",
        "PARAM",
        "SOURCE",
        "TRACK",
        "WBR",
    ]
)
MEANINGFUL_WHEN_BLANK_ELEMENTS = frozenset(
    [
        "A",
        "TABLE",
        "THEAD",
        "TBODY",
        "TFOOT",
        "TH",
        "TD",
        "IFRAME",
        "SCRIPT",
        "AUDIO",
        "VIDEO",
    ]
)


cpdef str js_trim(str string):
    return string.strip(JS_WS)


def is_block(node):
    return node.nodeName in BLOCK_ELEMENTS


def is_void(node):
    return node.nodeName in VOID_ELEMENTS


def is_meaningful_when_blank(node):
    return node.nodeName in MEANINGFUL_WHEN_BLANK_ELEMENTS


def _has(node, names):
    pending = list(node.childNodes)
    while pending:
        child = pending.pop()
        if child.nodeName in names:
            return True
        pending.extend(child.childNodes)
    return False


def has_void(node):
    cached = getattr(node, "_has_void", None)
    return _has(node, VOID_ELEMENTS) if cached is None else cached


def has_meaningful_when_blank(node):
    cached = getattr(node, "_has_meaningful", None)
    return _has(node, MEANINGFUL_WHEN_BLANK_ELEMENTS) if cached is None else cached


_MARKDOWN_START = re.compile(r"^(?:-|\+ |[=]+|#{1,6} |~~~|>)")
_ORDERED_LIST_START = re.compile(r"^([0-9]+)\. ")


def _escape_start(match):
    return "\\" + match[0]


cpdef str escape_markdown(str string):
    cdef Py_ssize_t length, index, extra = 0, output = 0
    cdef int kind
    cdef unsigned int character
    cdef void *data
    cdef void *target
    cdef str escaped
    if not string:
        return string
    length = PyUnicode_GET_LENGTH(string)
    kind = PyUnicode_KIND(string)
    data = PyUnicode_DATA(string)
    for index in range(length):
        character = PyUnicode_READ(kind, data, index)
        if character in (92, 42, 96, 91, 93, 95):
            extra += 1
    if extra:
        escaped = PyUnicode_New(length + extra, PyUnicode_MAX_CHAR_VALUE(string))
        target = PyUnicode_DATA(escaped)
        for index in range(length):
            character = PyUnicode_READ(kind, data, index)
            if character in (92, 42, 96, 91, 93, 95):
                PyUnicode_WRITE(kind, target, output, 92)
                output += 1
            PyUnicode_WRITE(kind, target, output, character)
            output += 1
        string = escaped
    if string[0] in "-+=#~>":
        return _MARKDOWN_START.sub(_escape_start, string, count=1)
    if "0" <= string[0] <= "9":
        return _ORDERED_LIST_START.sub(r"\1\\. ", string, count=1)
    return string

include "_native_dom.pxi"

include "_native_rules.pxi"

cpdef _blank(str content, Node node, dict options):
    return "\n\n" if node.isBlock else ""


cpdef _keep(str content, Node node, dict options):
    return "\n\n" + node.outerHTML + "\n\n" if node.isBlock else node.outerHTML


cpdef _default(str content, Node node, dict options):
    return "\n\n" + content + "\n\n" if node.isBlock else content


cpdef _join_parts(parts):
    """Apply Turndown's newline joining without copying the accumulated output."""
    cdef str part, rest, separator, body
    cdef Py_ssize_t trailing = 0
    if not parts:
        return ""
    if len(parts) == 1:
        part = parts[0]
        if not part.startswith("\n\n\n"):
            return part
    chunks = []
    for part in parts:
        rest = part.lstrip("\n")
        separator = "\n" * min(2, max(trailing, len(part) - len(rest)))
        if rest:
            body = rest.rstrip("\n")
            chunks.extend((separator, body))
            trailing = len(rest) - len(body)
        else:
            trailing = len(separator)
    chunks.append("\n" * trailing)
    return "".join(chunks)


def _children(Node node):
    # Like Array.reduce: capture the length, then read live child indices.
    cdef list children = node.childNodes
    cdef Py_ssize_t index
    for index in range(len(children)):
        if index < len(children):
            yield children[index]


class Rules:
    """Rules retain the same precedence and public collection as JavaScript."""

    def __init__(self, options, invoke):
        self.options = options
        self._invoke = invoke
        self._keep = []
        self._remove = []
        self.blankRule = {"replacement": options["blankReplacement"]}
        self.keepReplacement = options["keepReplacement"]
        self.defaultRule = {"replacement": options["defaultReplacement"]}
        self.array = list(options["rules"].values())

    def add(self, key, rule):
        self.array.insert(0, rule)

    def keep(self, filter):
        self._keep.insert(0, {"filter": filter, "replacement": self.keepReplacement})

    def remove(self, filter):
        self._remove.insert(0, {"filter": filter, "replacement": lambda: ""})

    def forNode(self, Node node):
        cdef int native_match
        if node.isBlank:
            return self.blankRule
        tag = node.nodeName.lower()
        for rules in (self.array, self._keep, self._remove):
            for rule in rules:
                filter = rule.get("filter")
                if isinstance(filter, str):
                    matches = filter == tag
                elif isinstance(filter, (list, tuple)):
                    matches = tag in filter
                elif callable(filter):
                    native_match = _builtin_filter(filter, node, self.options)
                    matches = self._invoke(filter, node, self.options) if native_match == -1 else native_match
                else:
                    raise TypeError("`filter` needs to be a string, array, or function")
                if matches:
                    return rule
        return self.defaultRule

    def forEach(self, fn):
        index = 0
        while index < len(self.array):
            self._invoke(fn, self.array[index], index)
            index += 1

    for_node = forNode
    for_each = forEach


_MISSING = object()


class TurndownService:
    """Convert HTML or a DOM node to Markdown using Turndown 7.2.4 rules.

    Options and rule dictionaries use the original JavaScript names. Callbacks
    may accept just the positional arguments they need, as in JavaScript.
    """

    def __init__(self, options=None):
        self.options = {
            "rules": commonmark_rules(),
            "headingStyle": "setext",
            "hr": "* * *",
            "bulletListMarker": "*",
            "codeBlockStyle": "indented",
            "fence": "```",
            "emDelimiter": "_",
            "strongDelimiter": "**",
            "linkStyle": "inlined",
            "linkReferenceStyle": "full",
            "br": "  ",
            "preformattedCode": False,
            "blankReplacement": _blank,
            "keepReplacement": _keep,
            "defaultReplacement": _default,
        }
        if options is not None:
            self.options.update(options)
        self._callback_arities = {}
        self.rules = Rules(self.options, self._invoke)

    def _invoke(self, callback, *args):
        key = id(callback)
        cached = self._callback_arities.get(key)
        if cached is None:
            try:
                parameters = signature(callback).parameters.values()
                count = sum(
                    p.kind
                    in (Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD)
                    for p in parameters
                )
                if any(p.kind == Parameter.VAR_POSITIONAL for p in parameters):
                    count = None
            except (TypeError, ValueError):
                count = None
            self._callback_arities[key] = (callback, count)
        else:
            count = cached[1]
        return callback(*args if count is None else args[:count])

    def turndown(self, input=_MISSING):
        cdef Node root, parent, node
        if not (
            isinstance(input, str) or getattr(input, "nodeType", None) in (1, 9, 11)
        ):
            label = (
                "undefined"
                if input is _MISSING
                else "null"
                if input is None
                else str(input)
            )
            raise TypeError(
                label + " is not a string, or an element/document/fragment node."
            )
        if isinstance(input, str) and not input:
            return ""

        root = root_node(input, self.options)
        # An explicit stack handles deeply nested documents without Python recursion.
        stack = [(root, _children(root), [], None)]
        while stack:
            parent, children, parts, rule = stack[-1]
            node = next(children, None)
            if node is not None:
                decorate_node(node, self.options)
                if node.nodeType == 3:
                    parts.append(
                        node.nodeValue if node.isCode else self.escape(node.nodeValue)
                    )
                elif node.nodeType == 1:
                    stack.append((node, _children(node), [], self.rules.forNode(node)))
                else:
                    parts.append("")
                continue

            content = _join_parts(parts)
            stack.pop()
            if not stack:
                output = content
                break
            whitespace = parent.flankingWhitespace
            if whitespace["leading"] or whitespace["trailing"]:
                content = js_trim(content)
            callback = rule["replacement"]
            replacement = _builtin_replace(callback, content, parent, self.options)
            if replacement is _CUSTOM_CALLBACK:
                if callback is _blank:
                    replacement = _blank(content, parent, self.options)
                elif callback is _keep:
                    replacement = _keep(content, parent, self.options)
                elif callback is _default:
                    replacement = _default(content, parent, self.options)
                else:
                    replacement = self._invoke(callback, content, parent, self.options)
            stack[-1][2].append(
                whitespace["leading"] + replacement + whitespace["trailing"]
            )

        index = 0
        while index < len(self.rules.array):
            append = self.rules.array[index].get("append")
            if callable(append):
                output = _join_parts((output, self._invoke(append, self.options)))
            index += 1
        return output.lstrip("\t\r\n").rstrip(JS_WS)

    def use(self, plugin):
        if isinstance(plugin, (list, tuple)):
            for item in plugin:
                self.use(item)
        elif callable(plugin):
            self._invoke(plugin, self)
        else:
            raise TypeError("plugin must be a Function or an Array of Functions")
        return self

    def addRule(self, key, rule):
        self.rules.add(key, rule)
        return self

    def keep(self, filter):
        self.rules.keep(filter)
        return self

    def remove(self, filter):
        self.rules.remove(filter)
        return self

    def escape(self, string):
        return escape_markdown(string)

    add_rule = addRule
