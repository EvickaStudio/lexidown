"""Readable Markdown for tables that do not fit the ordinary GFM rules."""

from textwrap import indent

from ..._native import _utf16_length
from ...utilities import is_block, js_trim
from ..joplin_gfm import _BLOCKS, _parent, _table_html


def _span(cell, attribute):
    raw = (cell.getAttribute(attribute) or "1").strip()
    if not raw.isascii() or not raw.isdecimal():
        return 1
    raw = raw.lstrip("0") or "0"
    limit = 1000 if attribute == "colspan" else 65534
    value = limit if len(raw) > 5 else int(raw)
    return min(limit, max(0 if attribute == "rowspan" else 1, value))


def _markdown(node):
    return getattr(node, "_llm_table_markdown", "")


def _rows(table):
    return [
        [cell for cell in row.children if cell.nodeName in {"TH", "TD"}]
        for row in table.getElementsByTagName("tr")
        if _parent(row, "TABLE") is table
    ]


def _spacer_image(image):
    return any(
        (value := (image.getAttribute(axis) or "").strip()).isascii()
        and value.isdecimal()
        and value.lstrip("0") in {"", "1"}
        for axis in ("width", "height")
    )


def _substantive(cell):
    return bool(cell.textContent.strip()) or any(
        not _spacer_image(image) for image in cell.getElementsByTagName("img")
    )


def _layout_table(table):
    role = (table.getAttribute("role") or "").strip().lower()
    if role in {"presentation", "none"}:
        return True
    if role in {"table", "grid", "treegrid"}:
        return False
    descendants = table.getElementsByTagName("*")
    if any(
        (
            node.nodeName in {"TH", "CAPTION", "PRE", "CODE"}
            or (node.nodeName == "IMG" and not _spacer_image(node))
        )
        and _parent(node, "TABLE") is table
        for node in descendants
    ):
        return False
    # ponytail: one content column only; broaden inference after corpus checks.
    return any(
        node.nodeName not in {"TBODY", "THEAD", "TFOOT", "TR", "TD"} and is_block(node)
        for node in descendants
    ) and all(sum(_substantive(cell) for cell in row) <= 1 for row in _rows(table))


def _cell(content, index):
    content = js_trim(content).replace("\n\r", "<br>").replace("\n", "<br>")
    content = content.replace("|", r"\|")
    content += " " * max(0, 3 - _utf16_length(content))
    return ("| " if index == 0 else " ") + content + " |"


def _grid(rows):
    lines = []
    if not all(cell is None or cell.nodeName == "TH" for cell in rows[0]):
        lines.append("".join(_cell("", index=i) for i in range(len(rows[0]))))
        lines.append("".join(_cell("---", index=i) for i in range(len(rows[0]))))
    for index, row in enumerate(rows):
        lines.append(
            "".join(_cell(_markdown(cell), index=i) for i, cell in enumerate(row))
        )
        if index == 0 and all(cell is None or cell.nodeName == "TH" for cell in row):
            lines.append("".join(_cell("---", index=i) for i in range(len(row))))
    return "\n".join(lines)


def _normalize_columns(rows):
    boundaries, placed = {0}, []
    for row in rows:
        end, cells = 0, []
        for cell in row:
            start, end = end, end + _span(cell, "colspan")
            cells.append((start, end, cell))
            boundaries.add(end)
        placed.append(cells)
    columns = {position: index for index, position in enumerate(sorted(boundaries))}
    width = len(columns) - 1
    # ponytail: bound sparse-grid padding; describe larger tables with the fallback.
    if len(rows) * width > 10000:
        return None
    grid = []
    for cells in placed:
        row = [None] * width
        for start, end, cell in cells:
            left, right = columns[start], columns[end]
            row[left:right] = [cell] * (right - left)
        grid.append(row)
    if not grid:
        return grid

    # Compare source and output so distinct links or reference IDs remain intact.
    keys = {
        cell: (cell.nodeName, cell.innerHTML, _markdown(cell))
        for row in rows
        for cell in row
    }
    keep = []
    for index, header in enumerate(grid[0]):
        previous = grid[0][index - 1] if index else None
        if (
            header is not None
            and previous is not None
            and header is not previous
            and header.nodeName == previous.nodeName == "TH"
            and _markdown(header)
            and all(keys.get(row[index]) == keys.get(row[index - 1]) for row in grid)
        ):
            continue
        keep.append(index)
    grid = [[row[index] for index in keep] for row in grid]
    return [
        [
            cell if not index or cell is not row[index - 1] else None
            for index, cell in enumerate(row)
        ]
        for row in grid
    ]


def _render_table(table):
    if table._llm_layout_table:
        return "\n\n".join(
            _markdown(node)
            for node in table.getElementsByTagName("*")
            if node.nodeName in {"TH", "TD", "CAPTION"}
            and _parent(node, "TABLE") is table
            and _markdown(node)
        )
    rows = [row for row in _rows(table) if row]
    captions = [
        _markdown(caption)
        for caption in table.getElementsByTagName("caption")
        if _parent(caption, "TABLE") is table
    ]
    if not rows:
        return "\n\n".join(captions)
    width = max(len(row) for row in rows)

    def section(row):
        return (
            width > 1
            and len(row) == 1
            and row[0].nodeName == "TH"
            and _span(row[0], "colspan") == width
            and _span(row[0], "rowspan") == 1
        )

    simple = all(
        section(row)
        or (
            all(
                _span(cell, "rowspan") == 1
                and "\n\n" not in _markdown(cell)
                and not any(
                    child.nodeName in _BLOCKS | {"TABLE", "PRE"}
                    for child in cell.getElementsByTagName("*")
                )
                for cell in row
            )
        )
        for row in rows
    )
    normalized = (
        _normalize_columns([row for row in rows if not section(row)])
        if simple
        else None
    )
    parts = captions
    if normalized is not None:
        pending = []
        normalized = iter(normalized)
        for row in rows:
            if section(row):
                if pending:
                    parts.append(_grid(pending))
                    pending = []
                parts.append(_markdown(row[0]))
            else:
                pending.append(next(normalized))
        if pending:
            parts.append(_grid(pending))
    else:
        # ponytail: describe complex spans instead of expanding an unbounded grid.
        for row_index, row in enumerate(rows, 1):
            cells = []
            for cell_index, cell in enumerate(row, 1):
                spans = []
                for attribute, unit in (("colspan", "columns"), ("rowspan", "rows")):
                    span = _span(cell, attribute)
                    if span != 1:
                        spans.append(f"{span or 'remaining'} {unit}")
                label = f"Cell {cell_index}"
                if spans:
                    label += " (spans " + ", ".join(spans) + ")"
                cells.append(f"  - {label}:\n\n" + indent(_markdown(cell), "    "))
            parts.append(f"- Row {row_index}:\n" + "\n\n".join(cells))
    return "\n\n".join(part for part in parts if part)


def llm_tables(service):
    """Override only tables requiring an HTML or merged-cell fallback."""
    is_code_block = getattr(service, "isCodeBlock", None)

    def matches(table, options):
        if table is None:
            return False
        needed = getattr(table, "_llm_table_fallback", None)
        if needed is None:
            table._llm_layout_table = _layout_table(table)
            needed = bool(
                table._llm_layout_table
                or _table_html(table, options, is_code_block)
                or table.getElementsByTagName("table")
                or any(
                    _span(cell, "colspan") != 1 or _span(cell, "rowspan") != 1
                    for cell in table.getElementsByTagName("*")
                    if cell.nodeName in {"TH", "TD"}
                )
            )
            table._llm_table_fallback = needed
        return needed

    def capture(content, node):
        node._llm_table_markdown = content.strip()
        return content

    service.addRule(
        "llmTableCell",
        {
            "filter": lambda node, options: (
                node.nodeName in {"TH", "TD", "CAPTION"}
                and matches(_parent(node, "TABLE"), options)
            ),
            "replacement": capture,
        },
    )
    service.addRule(
        "llmTable",
        {
            "filter": lambda node, options: (
                node.nodeName == "TABLE" and matches(node, options)
            ),
            "replacement": lambda content, node: "\n\n" + _render_table(node) + "\n\n",
        },
    )
