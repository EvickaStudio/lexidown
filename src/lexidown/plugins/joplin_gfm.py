"""Port of @joplin/turndown-plugin-gfm 1.0.68 (MIT, Dom Christie).

Enable the suite with ``service.use(gfm)`` or select individual plugins.
See THIRD_PARTY_NOTICES.md for the published source and attribution.
"""

import math
import re

from .._native import _number, _utf16_length
from ..utilities import JS_WS, js_trim

__all__ = ["gfm", "highlightedCodeBlock", "strikethrough", "tables", "taskListItems"]

_HIGHLIGHT = re.compile(r"highlight-(?:text|source)-([a-z0-9]+)")
_ALIGN = {"left": ":---", "right": "---:", "center": ":---:"}
_BLOCKS = {"UL", "OL", "H1", "H2", "H3", "H4", "H5", "H6", "HR", "BLOCKQUOTE"}
_CUSTOM_STYLES = {
    "background-color",
    "background",
    "border-color",
    "border",
    "border-top",
    "border-right",
    "border-bottom",
    "border-left",
    "border-style",
    "border-width",
    "padding",
    "padding-top",
    "padding-right",
    "padding-bottom",
    "padding-left",
    "float",
    "margin-left",
    "margin-right",
}


def highlightedCodeBlock(service):
    """Convert GitHub highlight wrappers to fenced code blocks."""
    service.addRule(
        "highlightedCodeBlock",
        {
            "filter": lambda node: (
                node.nodeName == "DIV"
                and bool(_HIGHLIGHT.search(node.className))
                and node.firstChild is not None
                and node.firstChild.nodeName == "PRE"
            ),
            "replacement": lambda content, node, options: (
                "\n\n"
                + options["fence"]
                + _HIGHLIGHT.search(node.className)[1]
                + "\n"
                + node.firstChild.textContent
                + "\n"
                + options["fence"]
                + "\n\n"
            ),
        },
    )


def strikethrough(service):
    """Convert del, s, and strike elements to double-tilde Markdown."""
    service.addRule(
        "strikethrough",
        {
            "filter": ["del", "s", "strike"],
            "replacement": lambda content: "~~" + content + "~~",
        },
    )


def _parent(node, name):
    node = node.parentNode
    while node is not None and node.nodeName != name:
        node = node.parentNode
    return node


def _rows(table):
    return table.getElementsByTagName("tr")


def _skip_table(table):
    if table is None:
        return True
    skipped = getattr(table, "_joplin_gfm_skip", None)
    if skipped is None:
        rows = _rows(table)
        skipped = (len(rows) == 1 and len(rows[0].childNodes) <= 1) or bool(
            table.getElementsByTagName("table")
        )
        # Cache on the conversion's cloned node, without retaining documents.
        table._joplin_gfm_skip = skipped
    return skipped


def _style_alignment(style):
    # Read only inline text-align; quoted values/URLs may contain semicolons.
    start, depth, quote = 0, 0, ""
    alignment = ""
    for index, char in enumerate(style + ";"):
        if quote:
            if char == quote:
                quote = ""
        elif char in "\"'":
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char == ";" and depth == 0:
            name, _, value = style[start:index].partition(":")
            name = re.sub(r"([a-z])([A-Z])", r"\1-\2", js_trim(name)).lower()
            if name == "text-align":
                alignment = js_trim(js_trim(value).removesuffix("!important"))
            start = index + 1
    return alignment


def _alignment(node):
    return (
        node.getAttribute("align") or _style_alignment(node.getAttribute("style") or "")
    ).lower()


def _column_alignment(table, index):
    votes = dict.fromkeys((*_ALIGN, ""), 0)
    alignment = ""
    for row in _rows(table):
        if index < len(row.childNodes):
            candidate = _alignment(row.childNodes[index])
            if candidate in votes:
                votes[candidate] += 1
                if votes[candidate] > votes[alignment]:
                    alignment = candidate
    return alignment


def _heading_row(row):
    parent = row.parentNode
    previous = parent.previousSibling
    first_body = parent.nodeName == "TBODY" and (
        previous is None
        or (previous.nodeName == "THEAD" and not js_trim(previous.textContent))
    )
    return parent.nodeName == "THEAD" or (
        parent.firstChild is row
        and (parent.nodeName == "TABLE" or first_body)
        and all(child.nodeName == "TH" for child in row.childNodes)
    )


def _cell(content, node=None, index=None):
    if index is None:
        index = node.parentNode.childNodes.index(node)
    content = js_trim(content).replace("\n\r", "<br>").replace("\n", "<br>")
    content = re.sub(r"\|+", r"\\|", content)
    content += " " * max(0, 3 - _utf16_length(content))
    if node is not None:
        span = _number(node.getAttribute("colspan") or "1")
        # ponytail: cap expansion at HTML's 1000-column limit; streaming output
        # would be needed to support arbitrary untrusted spans safely.
        if span > 1:
            content += " |    " * (math.ceil(min(span, 1000)) - 1)
    return ("| " if index == 0 else " ") + content + " |"


def _column_count(table):
    return max((len(row.childNodes) for row in _rows(table)), default=0)


def _custom_formatting(node):
    properties = {
        js_trim(part.split(":", 1)[0]).lower()
        for part in (node.getAttribute("style") or "").split(";")
    }
    if properties & _CUSTOM_STYLES:
        return True
    if any(
        js_trim(node.getAttribute(name) or "")
        for name in ("bgcolor", "bordercolor", "background")
    ):
        return True
    return node.nodeName == "TABLE" and any(
        js_trim(node.getAttribute(name) or "").lower() not in ("", "0", "0px")
        for name in ("cellpadding", "cellspacing")
    )


def _table_html(table, options, is_code_block):
    descendants = table.getElementsByTagName("*")
    if any(
        node.nodeName in _BLOCKS
        or (options.get("preserveNestedTables") and node.nodeName == "TABLE")
        or (is_code_block and is_code_block(node))
        for node in descendants
    ):
        return True
    return options.get("preserveTableStyles") and (
        _custom_formatting(table)
        or any(
            _custom_formatting(node)
            for node in descendants
            if node.nodeName in ("TR", "TH", "TD")
        )
    )


def tables(service):
    """Convert tables using Joplin's layout, alignment and preservation rules.

    Options: preserveNestedTables and preserveTableStyles (both false by default).
    An optional service.isCodeBlock(node) callback identifies code tables to keep
    as HTML, as in Joplin's extended Turndown service; set it before use(tables).
    """
    is_code_block = getattr(service, "isCodeBlock", None)

    def table_cell(content, node):
        return content if _skip_table(_parent(node, "TABLE")) else _cell(content, node)

    def table_row(content, node):
        table = _parent(node, "TABLE")
        if _skip_table(table):
            return content
        borders = ""
        if _heading_row(node):
            for index in range(_column_count(table)):
                child = node.childNodes[index] if index < len(node.childNodes) else None
                borders += _cell(
                    _ALIGN.get(_column_alignment(table, index), "---"), child, index
                )
        return "\n" + content + ("\n" + borders if borders else "")

    def table(content, node, options):
        if _table_html(node, options, is_code_block):
            parent = _parent(node, "DIV")
            if parent is None or "joplin-table-wrapper" not in re.split(
                r"[\t\n\f\r ]+", parent.className
            ):
                return (
                    '\n\n<div class="joplin-table-wrapper">'
                    + node.outerHTML
                    + "</div>\n\n"
                )
            return node.outerHTML
        if _skip_table(node):
            return content
        content = re.sub(r"\n+", "\n", content)
        lines = js_trim(content).split("\n")
        second_line = lines[1] if len(lines) >= 2 else lines[0]
        columns = _column_count(node)
        header = ""
        if columns and not re.search(r"\| :?---", second_line):
            header = "|" + "     |" * columns + "\n|"
            header += "".join(
                " " + _ALIGN.get(_column_alignment(node, index), "---") + " |"
                for index in range(columns)
            )
        captions = node.getElementsByTagName("caption")
        caption = captions[0].textContent if captions else ""
        if caption:
            caption += "\n\n"
        return "\n\n" + caption + (header + content).lstrip(JS_WS) + "\n\n"

    for name, rule in {
        "tableCell": {"filter": ["th", "td"], "replacement": table_cell},
        "tableRow": {"filter": "tr", "replacement": table_row},
        "table": {"filter": "table", "replacement": table},
        "tableCaption": {"filter": "caption", "replacement": lambda: ""},
        "tableColgroup": {"filter": ["colgroup", "col"], "replacement": lambda: ""},
        "tableSection": {
            "filter": ["thead", "tbody", "tfoot"],
            "replacement": lambda content: content,
        },
    }.items():
        service.addRule(name, rule)


def taskListItems(service):
    """Convert native and ARIA checkboxes directly in list items, labels or spans."""

    def matches(node):
        parent = node.parentNode
        grandparent = parent.parentNode
        checkbox = (
            node.nodeName == "INPUT"
            and (node.getAttribute("type") or "").lower() == "checkbox"
        ) or node.getAttribute("role") == "checkbox"
        return checkbox and (
            parent.nodeName == "LI"
            or (
                parent.nodeName in ("LABEL", "SPAN")
                and grandparent is not None
                and grandparent.nodeName == "LI"
            )
        )

    def replacement(content, node):
        checked = (
            node.hasAttribute("checked")
            if node.nodeName == "INPUT"
            else node.getAttribute("aria-checked") == "true"
        )
        return ("[x]" if checked else "[ ]") + " "

    service.addRule("taskListItems", {"filter": matches, "replacement": replacement})


def gfm(service):
    """Enable highlighted code blocks, strikethrough, tables and task lists."""
    service.use([highlightedCodeBlock, strikethrough, tables, taskListItems])
