"""Keep declared TeX alternatives without reconstructing MathML equations."""


def _visible(node, hidden_style, *, aria=True):
    while node is not None:
        if (
            node.nodeName in {"CODE", "PRE"}
            or (
                node.hasAttribute("hidden")
                and node.getAttribute("hidden").lower() != "until-found"
            )
            or hidden_style.search(node.getAttribute("style") or "")
            or (
                aria
                and (node.getAttribute("aria-hidden") or "").strip().lower() == "true"
            )
        ):
            return False
        node = node.parentNode
    return True


def preserve_math(root, hidden_style):
    """Mark visible TeX or its matching image before ordinary hidden-node cleanup.

    Register ``math_rule`` after other image rules to emit the marked alternative.
    Adjacent visible image alternatives keep their own alt when TeX differs.
    Only the image's ARIA flag is cleared; hidden ancestors remain hidden.
    """
    for node in root.getElementsByTagName("math"):
        tex = next(
            (
                annotation.textContent.strip()
                for annotation in node.getElementsByTagName("annotation")
                if (annotation.getAttribute("encoding") or "").strip().lower()
                == "application/x-tex"
                and annotation.textContent.strip()
            ),
            "",
        )
        alternative = (node.getAttribute("alttext") or "").strip()
        tex = tex or alternative
        if not tex:
            continue
        alternatives = {"".join(value.split()) for value in (tex, alternative) if value}
        images, boundaries = [], [node]
        wrapper = node.parentNode
        # ponytail: adjacent alternatives only, optionally across one math-only span.
        if (
            wrapper is not None
            and wrapper.nodeName == "SPAN"
            and wrapper.children == [node]
            and wrapper.textContent.strip() == node.textContent.strip()
        ):
            boundaries.append(wrapper)
        for boundary in boundaries:
            for direction in ("previousSibling", "nextSibling"):
                image = getattr(boundary, direction)
                while image is not None and (
                    image.nodeType == 8
                    or (image.nodeType == 3 and not image.nodeValue.strip())
                ):
                    image = getattr(image, direction)
                if (
                    image is not None
                    and image.nodeName == "IMG"
                    and (image.getAttribute("alt") or "").strip()
                ):
                    images.append(image)
        matching = [
            image
            for image in images
            if "".join(image.getAttribute("alt").split()) in alternatives
        ]
        if _visible(node, hidden_style):
            node._llm_math = tex
            node.textContent = tex
            for image in matching:
                image.parentNode.removeChild(image)
        else:
            image = next(
                (
                    image
                    for image in matching + images
                    if _visible(image, hidden_style, aria=False)
                ),
                None,
            )
            if image is not None:
                if image in matching:
                    image._llm_math = tex
                image.setAttribute("aria-hidden", "false")


math_rule = {
    "filter": lambda node: hasattr(node, "_llm_math"),
    "replacement": lambda content, node: "$" + node._llm_math + "$",
}
