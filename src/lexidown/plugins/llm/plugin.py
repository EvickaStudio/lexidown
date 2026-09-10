"""Conservative main-content cleanup and Markdown for scraped HTML."""

import re
from contextlib import suppress
from urllib.parse import urljoin

from ..._native import _heading, _inline_link, _is_inline_link
from ...utilities import is_block
from ..joplin_gfm import gfm
from ._math import math_rule, preserve_math
from ._tables import llm_tables

__all__ = ["llm"]

_DROP_TAGS = {
    "HEAD",
    "TITLE",
    "META",
    "LINK",
    "SCRIPT",
    "STYLE",
    "NOSCRIPT",
    "TEMPLATE",
    "NAV",
    "SELECT",
    "TEXTAREA",
    "IFRAME",
    "OBJECT",
    "EMBED",
    "CANVAS",
}
_DROP_ROLES = {
    "navigation",
    "banner",
    "contentinfo",
    "search",
    "dialog",
    "menu",
    "menubar",
    "toolbar",
    "tooltip",
    "complementary",
    "menuitem",
    "menuitemcheckbox",
    "menuitemradio",
}
_HIDDEN_STYLE = re.compile(
    r"(?:^|;)\s*(?:display\s*:\s*none|visibility\s*:\s*(?:hidden|collapse))"
    r"\s*(?:!important\s*)?(?:;|$)",
    re.I,
)
_HEADINGS = {"H1", "H2", "H3", "H4", "H5", "H6"}
_READER_ONLY_CLASS = re.compile(
    r"(?:^|[\s_-])(?:sr-only|visually-hidden|screen-reader-(?:only|text)|show-for-sr)"
    r"(?:$|[\s_-])"
)
_CONTENT_TAGS = _HEADINGS | {
    "P",
    "PRE",
    "CODE",
    "TABLE",
    "FIGURE",
    "IMG",
    "DL",
    "BLOCKQUOTE",
    "ARTICLE",
}
_CONTENT_ROLES = {"table", "grid", "row", "cell", "gridcell", "radiogroup", "tablist"}
_CONTROL_CLASS = re.compile(r"(?:^|[\s_-])(?:btn|button)(?:$|[\s_-])", re.I)
_ICON_CLASS = re.compile(r"(?:^|[\s_-])icons?(?:$|[\s_-])", re.I)
_ICON_TEXT = re.compile(
    r"(?:[a-z][a-z0-9_-]{0,63}|"
    r"[\ue000-\uf8ff\U000f0000-\U000ffffd\U00100000-\U0010fffd]{1,4})"
)
_DATA_URL = re.compile(r"^\s*data:", re.I)


def _redundant_author_image(link):
    children = link.children
    if len(children) != 1 or children[0].nodeName != "IMG" or link.textContent.strip():
        return False
    img = children[0]
    alt = (img.getAttribute("alt") or "").strip()
    if not alt or not all(
        (size := img.getAttribute(attr) or "").isascii()
        and size.isdecimal()
        and len(size) <= 2
        and 0 < int(size) <= 64
        for attr in ("width", "height")
    ):
        return False
    for direction in ("previousSibling", "nextSibling"):
        sibling = getattr(link, direction)
        while sibling is not None and (
            sibling.nodeType == 8
            or (sibling.nodeType == 3 and not sibling.nodeValue.strip())
        ):
            sibling = getattr(sibling, direction)
        if sibling is None:
            continue
        if sibling.nodeName in {"SPAN", "STRONG", "B"} and len(sibling.children) == 1:
            sibling = sibling.children[0]
        if (
            sibling.nodeName == "A"
            and link.getAttribute("href")
            and link.getAttribute("href") == sibling.getAttribute("href")
            and alt.removeprefix("@")
            == " ".join(sibling.textContent.split()).removeprefix("@")
            and (
                alt.startswith("@")
                or "author" in (link.getAttribute("rel") or "").lower().split()
                or "author" in (sibling.getAttribute("rel") or "").lower().split()
            )
        ):
            return True
    return False


def _tooltip_context(node):
    parts, size, visited = [], 0, 0
    pending = [node]
    # ponytail: bound nearby matches; keep tooltips needing larger/deeper context.
    while pending:
        current = pending.pop()
        visited += 1
        if visited > 256:
            return None
        if current.nodeType == 3:
            value = current.nodeValue
            size += len(value)
            if size > 4096:
                return None
            parts.append(value)
        else:
            pending.extend(reversed(current.childNodes))
    return " ".join("".join(parts).split())


def _tidy_markup(root):
    links = root.getElementsByTagName("a")
    for link in links:
        if _redundant_author_image(link):
            link.parentNode.removeChild(link)
    for heading in root.getElementsByTagName("*"):
        if heading.nodeName in _HEADINGS and (
            _reader_only_heading(heading)
            or (
                not heading.textContent.strip()
                and not heading.getElementsByTagName("img")
            )
        ):
            heading.parentNode.removeChild(heading)
    contexts = {}
    for link in links:
        title = " ".join((link.getAttribute("title") or "").split())
        if not title:
            continue
        label = " ".join(link.textContent.split())
        if not label or (title != label and not title.startswith(label + " ")):
            continue
        remainder = title[len(label) :].strip()
        if not remainder:
            link.setAttribute("title", "")
            continue
        parent = link.parentNode
        # ponytail: nearby context only; retain tooltips requiring distant matches.
        for _ in range(8):
            if parent is None or parent is root:
                break
            if parent not in contexts:
                contexts[parent] = _tooltip_context(parent)
            context = contexts[parent]
            if context is None:
                break
            context = context.removeprefix(label).lstrip()
            if re.search(r"(?<!\w)" + re.escape(remainder) + r"(?!\w)", context):
                link.setAttribute("title", "")
                break
            parent = parent.parentNode


def _prune_control_groups(root):
    nodes, protected = [], set()
    pending = [root]
    while pending:
        node = pending.pop()
        nodes.append(node)
        role = (node.getAttribute("role") or "").strip().lower()
        if (
            node.nodeName in _CONTENT_TAGS
            or role in _CONTENT_ROLES
            or any(
                node.hasAttribute(attr)
                for attr in (
                    "aria-controls",
                    "aria-pressed",
                    "aria-checked",
                    "aria-expanded",
                    "aria-selected",
                )
            )
            or (
                node.nodeName == "A" and any(is_block(child) for child in node.children)
            )
        ):
            protected.add(node)
        else:
            pending.extend(node.children)

    summaries = {}
    for node in reversed(nodes):
        if node in protected:
            summaries[node] = (0, 0, 0, True, False, False, None)
            continue
        text = "".join(
            child.nodeValue for child in node.childNodes if child.nodeType == 3
        )
        size, control_size, controls = len(text.strip()), 0, 0
        has_content, numeric = False, any(char.isnumeric() for char in text)
        outside_numeric = numeric
        targets = set()
        for child in node.children:
            length, linked, count, content, numbers, outside_numbers, target = (
                summaries[child]
            )
            size += length
            control_size += linked
            controls += count
            has_content |= content
            numeric |= numbers
            outside_numeric |= outside_numbers
            if count:
                targets.add(target)
        target = next(iter(targets)) if len(targets) == 1 else None
        role = (node.getAttribute("role") or "").strip().lower()
        if (
            node.nodeName == "BUTTON"
            or role == "button"
            or (node.nodeName == "A" and _CONTROL_CLASS.search(node.className))
        ):
            controls, control_size = 1, size
            outside_numeric = False
            target = node.getAttribute("href") if node.nodeName == "A" else None
        if (
            node is not root
            and node.nodeName in {"DIV", "UL", "OL", "SECTION", "FORM", "FIELDSET"}
            and not has_content
            and not outside_numeric
            and controls >= 2
            # ponytail: prune only small control groups; retain ambiguous layouts.
            and 0 < size <= 400
            and control_size >= size * (0.3 if target and controls >= 3 else 0.7)
            and (not numeric or target)
        ):
            node.parentNode.removeChild(node)
        else:
            summaries[node] = (
                size,
                control_size,
                controls,
                has_content,
                numeric,
                outside_numeric,
                target,
            )


def _svg_text(node):
    label = (node.getAttribute("aria-label") or "").strip()
    if label:
        return label
    descriptions = [
        child.textContent.strip()
        for child in node.getElementsByTagName("*")
        if child.nodeName.upper() in {"TITLE", "DESC"} and child.textContent.strip()
    ]
    if descriptions:
        return " ".join(descriptions)
    labels = [
        child.textContent.strip()
        for child in node.getElementsByTagName("text")
        if child.textContent.strip()
    ]
    # ponytail: retain diagram labels, not geometry or inferred connections.
    return "Diagram labels: " + "; ".join(labels) if len(labels) > 1 else ""


def _should_drop(node, role, in_content=False):
    return (
        node.nodeName.upper() in _DROP_TAGS
        or (
            role in _DROP_ROLES
            and not (in_content and role in {"banner", "contentinfo"})
        )
        or (
            node.hasAttribute("hidden")
            and node.getAttribute("hidden").lower() != "until-found"
        )
        or (node.getAttribute("aria-hidden") or "").strip().lower() == "true"
        or _HIDDEN_STYLE.search(node.getAttribute("style") or "")
        or (
            node.nodeName == "INPUT"
            and (node.getAttribute("type") or "").lower() != "checkbox"
        )
        or (
            node.nodeName == "IMG"
            and (
                (node.hasAttribute("alt") and node.getAttribute("alt") == "")
                or (
                    not (node.getAttribute("alt") or "").strip()
                    and any(
                        (node.getAttribute(size) or "").strip() in {"0", "1"}
                        for size in ("width", "height")
                    )
                )
            )
        )
    )


def _reader_only_heading(node):
    if node.nodeName not in _HEADINGS or node.nodeName == "H1":
        return False
    # ponytail: class hints only; CSS overrides require a rendered visibility check.
    classes = re.sub(r"(?<=[a-z])(?=[A-Z])", "-", node.className).lower()
    if "not-sr-only" in classes or not _READER_ONLY_CLASS.search(classes):
        return False
    parent = node.parentNode
    while parent is not None:
        if parent.nodeName in {"PRE", "CODE", "TABLE"}:
            return False
        parent = parent.parentNode
    return True


def _select_main_content(root, nodes, mains):
    # ponytail: semantic landmarks only; use a site-specific preprocessor when
    # an unmarked page needs more aggressive content extraction.
    scopes = mains
    if (
        root.nodeName == "MAIN"
        or (root.getAttribute("role") or "").strip().lower() == "main"
    ):
        scopes = [root]
    selected = set(scopes)
    inside = {root: root in selected}
    scopes = []
    for node in nodes:
        parent_inside = inside.get(node.parentNode, False)
        inside[node] = parent_inside or node in selected
        if node in selected and not parent_inside:
            scopes.append(node)

    if scopes:
        headings = [node for node in nodes if node.nodeName == "H1"]
        # Some pages put their only title just before the main landmark.
        if len(headings) == 1 and not inside[headings[0]]:
            scopes.append(headings[0])
        selected = set(scopes)
        scopes = [node for node in nodes if node in selected]
        for child in list(root.childNodes):
            root.removeChild(child)
        for node in scopes:
            root.appendChild(node)
    return inside


def _clean(root, options):
    preserve_math(root, _HIDDEN_STYLE)
    nodes, mains = [], []
    break_parents = set()
    pending = [
        (
            node,
            root.nodeName == "PRE",
            root.nodeName == "CODE",
            root.nodeName in {"MAIN", "ARTICLE"}
            or (root.getAttribute("role") or "").strip().lower() == "main",
        )
        for node in reversed(root.children)
    ]
    while pending:
        node, in_pre, in_code, in_content = pending.pop()
        role = (node.getAttribute("role") or "").strip().lower()
        in_content = (
            in_content or node.nodeName in {"MAIN", "ARTICLE"} or role == "main"
        )
        if _should_drop(node, role, in_content):
            node.parentNode.removeChild(node)
            continue
        if node.nodeName.upper() == "SVG":
            label = _svg_text(node)
            if not label:
                node.parentNode.removeChild(node)
                continue
            node.textContent = " " + label + " "
        if (
            not in_pre
            and not in_code
            and node.nodeName in {"I", "SPAN"}
            and not node.children
            and _ICON_CLASS.search(node.className)
            and _ICON_TEXT.fullmatch(node.textContent.strip())
        ):
            label = node.getAttribute("aria-label") or node.getAttribute("title")
            if label and label.strip():
                node.textContent = label.strip()
            else:
                node.parentNode.removeChild(node)
                continue
        nodes.append(node)
        if node.nodeName == "MAIN" or role == "main":
            mains.append(node)
        if in_pre and node.nodeName == "BR":
            break_parents.add(node.parentNode)
        pending.extend(
            (
                child,
                in_pre or node.nodeName == "PRE",
                in_code or node.nodeName == "CODE",
                in_content,
            )
            for child in reversed(node.children)
        )

    # Code copied from rich-text editors often uses BR instead of literal LF.
    for parent in break_parents:
        children = list(parent.childNodes)
        for child in children:
            parent.removeChild(child)
        for child in children:
            parent.appendChild(
                root.createTextNode("\n") if child.nodeName == "BR" else child
            )

    inside = _select_main_content(root, nodes, mains)
    base_url = options.get("baseUrl")
    pending = [
        (node, inside[root] or root.nodeName == "ARTICLE")
        for node in reversed(root.children)
    ]
    while pending:
        node, in_content = pending.pop()
        in_content = in_content or inside.get(node, False) or node.nodeName == "ARTICLE"
        if (
            not in_content
            and node.nodeName in ("HEADER", "FOOTER")
            and not node.getElementsByTagName("h1")
        ):
            node.parentNode.removeChild(node)
            continue
        if base_url:
            attribute = (
                "href"
                if node.nodeName == "A"
                else "src"
                if node.nodeName == "IMG"
                else None
            )
            if attribute and (value := node.getAttribute(attribute)):
                # Preserve malformed scraped URLs rather than discard the page.
                with suppress(ValueError):
                    node.setAttribute(attribute, urljoin(base_url, value.strip()))
        pending.extend((child, in_content) for child in reversed(node.children))

    _prune_control_groups(root)
    _tidy_markup(root)


def _bare_code_block(content, node, options):
    code = node.textContent
    marker = options["fence"][0]
    size = max(
        (len(match[0]) + 1 for match in re.finditer(re.escape(marker) + r"{3,}", code)),
        default=3,
    )
    fence = marker * size
    return "\n\n" + fence + "\n" + code.removesuffix("\n") + "\n" + fence + "\n\n"


def llm(service):
    """Enable GFM, ATX headings, fenced code and conservative page cleanup.

    Set ``baseUrl`` to the fetched page URL to resolve relative links/images.
    Set ``includeLinkUrls`` or ``includeImageUrls`` to False to keep only labels.
    Both default to True; literal URLs in page text and code remain unchanged.
    The optional ``preprocess(root)`` callback runs before this preset's cleanup.
    Input HTML/DOM is local data; this plugin never fetches or summarizes pages.
    """

    service.addRule(
        "heading",
        {
            "filter": ["h1", "h2", "h3", "h4", "h5", "h6"],
            "replacement": lambda content, node, options: (
                _heading(content.strip(), node, options) if content.strip() else ""
            ),
        },
    )

    def emphasis(content, node, options):
        text = content.strip()
        if not text:
            return ""
        delimiter = options[
            "strongDelimiter" if node.nodeName in {"STRONG", "B"} else "emDelimiter"
        ]
        return (
            content[: len(content) - len(content.lstrip())]
            + delimiter
            + text
            + delimiter
            + content[len(content.rstrip()) :]
        )

    service.addRule(
        "llmEmphasis",
        {"filter": ["strong", "b", "em", "i"], "replacement": emphasis},
    )

    def stateful_control(content, node):
        states = []
        for attribute, label in (
            ("aria-pressed", "pressed"),
            ("aria-selected", "selected"),
        ):
            state = (node.getAttribute(attribute) or "").strip().lower()
            if state in {"true", "mixed"}:
                states.append(label if state == "true" else label + ": mixed")
        suffix = " (" + ", ".join(states) + ")" if states else ""
        return " " + content.strip() + suffix + " "

    service.addRule(
        "statefulControl",
        {
            "filter": lambda node: (
                not node.isCode
                and (
                    node.nodeName == "BUTTON"
                    or (node.getAttribute("role") or "").strip().lower()
                    in {"button", "tab"}
                )
                and any(
                    node.hasAttribute(attribute)
                    for attribute in ("aria-pressed", "aria-selected")
                )
            ),
            "replacement": stateful_control,
        },
    )

    def inline_link(content, node, options):
        label = content.strip()
        if not label:
            return ""
        if "\n\n" in content:
            children = node.children
            if (
                "\n" not in label
                and len(children) == 1
                and children[0].nodeName in ("P", "DIV")
                and not any(n.isBlock for n in children[0].getElementsByTagName("*"))
            ):
                return "\n\n" + _inline_link(label, node, options) + "\n\n"
            label = node.getAttribute("title") or node.getAttribute("href")
            label = service.escape(" ".join(label.split()))
            return (
                content.rstrip("\n")
                + "\n\n"
                + _inline_link(label, node, options)
                + "\n\n"
            )
        return _inline_link(content, node, options)

    service.addRule(
        "inlineLink", {"filter": _is_inline_link, "replacement": inline_link}
    )
    service.addRule(
        "bareCodeBlock",
        {
            "filter": lambda node, options: (
                node.nodeName == "PRE"
                and options["codeBlockStyle"] == "fenced"
                and (node.firstChild is None or node.firstChild.nodeName != "CODE")
            ),
            "replacement": _bare_code_block,
        },
    )

    def media_text(content, node, options):
        if node.nodeName == "A":
            return content
        label = service.escape(" ".join((node.getAttribute("alt") or "").split()))
        if label and not options.get("includeImageUrls", True):
            before, after = node.previousSibling, node.nextSibling
            if (
                before is not None
                and not is_block(before)
                and (text := before.textContent or before.getAttribute("alt"))
                and not text[-1:].isspace()
            ):
                label = " " + label
            if (
                after is not None
                and not is_block(after)
                and (text := after.textContent or after.getAttribute("alt"))
                and not text[:1].isspace()
            ):
                label += " "
        return label

    service.addRule(
        "embeddedMedia",
        {
            "filter": lambda node, options: (
                node.nodeName in {"IMG", "A"}
                and (
                    not options.get(
                        "includeImageUrls"
                        if node.nodeName == "IMG"
                        else "includeLinkUrls",
                        True,
                    )
                    or _DATA_URL.match(
                        node.getAttribute("src" if node.nodeName == "IMG" else "href")
                        or ""
                    )
                    is not None
                )
            ),
            "replacement": media_text,
        },
    )
    service.use(gfm)
    service.use(llm_tables)
    service.addRule("math", math_rule)
    service.options.update(
        {"headingStyle": "atx", "codeBlockStyle": "fenced", "bulletListMarker": "-"}
    )
    previous = service.options.get("preprocess")

    def preprocess(root):
        if previous is not None:
            previous(root)
        _clean(root, service.options)

    service.options["preprocess"] = preprocess
