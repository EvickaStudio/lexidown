"""Compare deterministic Python conversions with the original JavaScript code.

Run after `npm ci --prefix turndown` with `PYTHONPATH=src python scripts/differential.py`.
"""

import argparse
import json
import random
import subprocess
import sys
from pathlib import Path

import html5lib

from lexidown import TurndownService

ROOT = Path(__file__).resolve().parent.parent


def corpus():
    gfm_fixtures = json.loads((ROOT / "tests/fixtures/joplin_gfm.json").read_text())
    for case in gfm_fixtures["cases"]:
        for mode in ("string", "element"):
            yield {**case, "mode": mode}
    fixtures = json.loads((ROOT / "tests/fixtures/turndown.json").read_text())
    for case in fixtures:
        for mode in ("string", "element"):
            yield {
                "name": case["name"],
                "html": case["html"],
                "options": case["options"],
                "mode": mode,
            }

    texts = [
        "",
        "word",
        " a  b ",
        "\t\ntext\r\n",
        "**_\\[`x`]",
        "1. ordered",
        "- item",
        "# heading",
        "===",
        "&lt;&amp;&gt;&quot;&#39;",
        "\xa0 \u202f word \xa0",
        "🙂𝄞 e\u0301",
        "\u0085\u001c\ufefftext\ufeff",
        "` one `` two ``` three",
        "line\nnext",
        " ",
        "\xa0",
    ]
    wrappers = [
        "{}",
        "<p>{}</p>",
        "<h1>{}</h1>",
        "<h2>{}</h2>",
        "<em>{}</em>",
        "<strong>{}</strong>",
        "<code>{}</code>",
        "<pre><code>{}</code></pre>",
        '<pre><code class="language-py extra">{}</code></pre>',
        '<a href="https://e.test/a (b)&lt;c&gt;" title="a &quot;quote&quot;">{}</a>',
        "<ul><li>{}</li><li>second</li></ul>",
        "<ol start='4'><li>{}</li></ol>",
        "<blockquote><p>{}</p><p>end</p></blockquote>",
        "before<span>{}</span>after",
        "<span> before </span><em>{}</em><span> after </span>",
        "<div><br>{}<hr></div>",
    ]
    options = [
        {},
        {"headingStyle": "atx", "emDelimiter": "*", "strongDelimiter": "__"},
        {"codeBlockStyle": "fenced"},
        {"codeBlockStyle": "fenced", "fence": "~~~", "preformattedCode": True},
        {"linkStyle": "referenced"},
        {"linkStyle": "referenced", "linkReferenceStyle": "collapsed"},
        {"linkStyle": "referenced", "linkReferenceStyle": "shortcut"},
        {"bulletListMarker": "-", "hr": "---", "br": "\\"},
    ]
    for text in texts:
        for wrapper in wrappers:
            for option in options:
                yield {"html": wrapper.format(text), "options": option}

    malformed = [
        "<p>one<p>two",
        "<b><i>x</b>y</i>",
        "<ul><li>one<li>two</ul>",
        "<table>outside<tr><td>inside</table>after",
        "<select>text<option>x<option>y</select>",
        "<p>before<div>middle</div>after",
        "<pre>\n<code>x\n\n</code></pre>",
        "<!doctype html><html><head><title>T</title></head><body><p>Body</p></body></html>",
        "<script>if (a < b) x = '*';</script><p>x</p>",
        "<style>p > b {}</style>tail",
        "a<!-- comment --> b",
        "<template><p>inside</p></template>after",
        "<svg><title>title</title><text>word</text></svg>",
        "<math><mi>x</mi></math>",
        "<p>x&#0;y&#xD800;z</p>",
        "<textarea>\n &amp; <b>x</b></textarea>",
        "<pre><code>x</code> tail</pre>",
        "<pre> <code>x</code></pre>",
        "<a href=''>empty</a><a>none</a>",
        "<img alt='a [b] *c*' src='a (b)' title='a &quot;b&quot;'>",
        "<ol start='-2'><li>x<li>y</ol>",
        "<ol start='nope'><li>x</ol>",
        "<div id='root'><br><wbr><input value='x'><iframe></iframe></div>",
    ]
    for html in malformed:
        for option in options:
            yield {"html": html, "options": option}

    for html in [
        '<del title="a &quot;b&quot;"> x </del><ins>y</ins>',
        '<figure><iframe src="/x?a=1&amp;b=2"></iframe></figure>',
        '<mark data-x="&lt; &amp; &quot;" disabled>x &lt; y &amp; z\xa0</mark>',
        "<section><mark>x</mark><p>p</p></section>",
    ]:
        for extra in (
            {"keep": ["del", "ins", "figure", "mark", "section"]},
            {"remove": ["del", "ins", "figure", "mark", "section"]},
            {"strikethrough": True},
            {"keep": ["del", "ins"], "remove": ["del", "ins"]},
        ):
            yield {"html": html, **extra}
    for mode in ("string", "element", "document", "fragment"):
        yield {"html": "<p>before</p><em>middle</em><p>after</p>", "mode": mode}
    for style in ("full", "collapsed", "shortcut"):
        yield {
            "sequence": ['<a href="/a">a</a>', "plain", '<a href="/b">b</a>'],
            "options": {"linkStyle": "referenced", "linkReferenceStyle": style},
        }
    for text in [
        *texts,
        "\u0661. arabic digit",
        "\uff11\uff12. fullwidth",
        "7. latin",
        "line\n# heading",
    ]:
        yield {"escape": text}

    whitespace = "\t\n\v\f\r \xa0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff\u0085\u001c\u200b"
    for char in whitespace:
        for text in (char + "x", "x" + char, char + "x" + char, char):
            for tag in ("em", "code", "span", "h1", "p"):
                for option in ({}, {"preformattedCode": True}):
                    yield {"html": f"a<{tag}>{text}</{tag}>b", "options": option}

    generator = random.Random(724)
    inline = ["em", "b", "span", "del", "code", "a", "u"]
    for _ in range(300):
        pieces = []
        for _ in range(generator.randint(1, 12)):
            tag = generator.choice(inline)
            text = generator.choice(texts)
            pieces.append(f'<{tag} href="/a">{text}</{tag}>')
            pieces.append(generator.choice(["", " ", "\n", "\xa0", "<br>"]))
        yield {"html": "".join(pieces), "options": generator.choice(options)}

    # Parser coverage: valid and malformed HTML with a reproducible seed.
    generator = random.Random(724091)
    texts = [
        "",
        "x",
        " hello  world ",
        "&amp; &unknown; &#0;",
        "&lt;b&gt;x&lt;/b&gt;",
        "1. x",
        "&#13;&#10;",
        "\xa0\ufeff\u2000\u202f",
        "\u0085\u001c\u200b",
        "🙂",
    ]
    tags = [
        "p",
        "b",
        "i",
        "code",
        "pre",
        "em",
        "span",
        "li",
        "ul",
        "ol",
        "a",
        "section",
        "mark",
        "div",
        "custom-tag",
        "table",
        "tr",
        "td",
        "form",
        "template",
        "noscript",
        "svg",
        "math",
        "text",
        "script",
        "style",
        "textarea",
    ]
    voids = [
        "<br>",
        "<hr>",
        "<img src='a (b)' title='a &quot;b&quot;'>",
        "<!-- hi -->",
        "<!--",
        "<!doctype html>",
    ]
    attributes = [
        "",
        " title='a &quot;b&quot;'",
        " href='a (b)&lt;c&gt;'",
        " start='0'",
        " class='language-python'",
        " x=' &amp; \xa0 '",
    ]
    options = [
        {},
        {"preformattedCode": True},
        {"codeBlockStyle": "fenced"},
        {"linkStyle": "referenced"},
    ]

    def fragment(depth=0):
        if depth > generator.randrange(1, 7) or generator.random() < 0.3:
            return generator.choice(texts + voids)
        tag = generator.choice(tags)
        content = "".join(fragment(depth + 1) for _ in range(generator.randrange(1, 4)))
        closing = "</" + tag + ">" if generator.random() < 0.85 else ""
        return "<" + tag + generator.choice(attributes) + ">" + content + closing

    for _ in range(5000):
        yield {"html": fragment(), "options": generator.choice(options)}

    # Native parser boundaries and legacy Domino behavior.
    options = [
        {},
        {"headingStyle": "atx", "emDelimiter": "*", "strongDelimiter": "__"},
        {"preformattedCode": True},
        {"codeBlockStyle": "fenced", "fence": "~~~"},
        {"linkStyle": "referenced"},
        {"linkStyle": "referenced", "linkReferenceStyle": "collapsed"},
        {"linkStyle": "referenced", "linkReferenceStyle": "shortcut"},
        {"bulletListMarker": "+", "hr": "---", "br": "\\"},
    ]
    keep = [
        "div",
        "figure",
        "svg",
        "math",
        "select",
        "command",
        "basefont",
        "bgsound",
        "plaintext",
        "isindex",
    ]
    regressions = [
        "<textarea>&#10;&#10;x</textarea>",
        "<span><em></span><textarea>x</textarea>tail",
        "<template><b></template>x",
        "<p><template><hr>",
        "<template><td><tr>",
        "<template><td></td></table>",
        "<table><template><tr><td>x</td></tr></template><tr><td>y</td></tr></table>",
        "<svg viewBox='0 0 1 1'><text>x &amp; y</text></svg>",
        "<svg><foreignObject><p>x</p></foreignObject></svg>",
        "<math><annotation-xml encoding='text/html'><p>x</p></annotation-xml></math>",
        "<div>\ud800x\udfff</div>",
        "<p><select>x</p>y</select>",
        "<select><b>x</select>y</b>",
        "<select><b>x</b></select>",
        "<select><p>x</select>y</p>",
        "<select><option>a<optgroup><option>b</select>c",
        "<select><table><tr><td>x</td></tr></table></select>",
        "<select>x<input>y</select>",
        "<search><p>x</search>y</p>",
        "<p>a<search>b</search>c",
        "<div><command>x</command></div>",
        "<div>x<basefont color='red'>y</div>",
        "<div>x<bgsound src='sound.wav'>y</div>",
        "<div><plaintext>x <b>y</b>&amp;</plaintext></div>",
        "<isindex>hello",
        "<isindex prompt='Find:' action='/search' name='query'>tail",
        "<form><isindex>inside</form>outside",
        "<div><isindex disabled>x</div>",
        "<isindex><p>x</isindex>y</p>",
        "<frameset><frame src='x'></frameset>",
        "<div><image src='x' alt='y'></div>",
        "<table><image src=x></table>",
        "<table><li>a<li>b",
        "<table><dd>a<dd>b<dt>c",
        "<div>x<pre><?test></pre></div>",
        "<div>x<template><?test?></template></div>",
        "<div>x<template><?target  data ?></template></div>",
        "<div><math><sup>x</sup><![CDATA[y<z>]]></math></div>",
        "<div><svg><sup>x</sup><![CDATA[y<z>]]></svg></div>",
        "<div><menuitem>a<menuitem>b</div>",
        "<div><menuitem>a<menu>b</menu>c</div>",
        "<div><menuitem>a<hr>b</div>",
        "<div><p><menuitem>a<div>b</div></div>",
    ]
    for html in regressions:
        for option in options:
            yield {"html": html, "options": option}
            yield {"html": html, "options": option, "keep": keep}

    # A separate seed exercises the wider HTML vocabulary and obsolete elements.
    generator = random.Random(99909)
    tags = (  # noqa: SIM905
        "a abbr acronym address applet area article aside audio b base basefont bdi "
        "bdo bgsound big blockquote body br button canvas caption center cite code "
        "col colgroup command data datalist dd del details dfn dialog dir div dl dt "
        "em embed fieldset figcaption figure font footer form frame frameset h1 h2 "
        "h3 head header hgroup hr html i iframe image img input ins isindex kbd "
        "keygen label legend li link listing main map mark marquee menu menuitem "
        "meta meter multicol nav nextid nobr noembed noframes noscript object ol "
        "optgroup option output p param picture plaintext pre progress q rb rp rt "
        "rtc ruby s samp script search section select slot small source spacer "
        "span strike strong style sub summary sup table tbody td textarea template "
        "th thead time title tr track tt u ul var video wbr xmp custom-foo"
    ).split()
    texts = [
        "",
        "hello",
        "\u0085\u001c\u200b",
        "&amp; &unknown; &#0;",
        "&#x000D;",
        " x  y ",
        "<br>",
        "<!-- hi -->",
        "<!doctype html>",
    ]

    def broad_fragment(depth=0):
        if depth > 4 or generator.random() < 0.35:
            return generator.choice(texts)
        tag = generator.choice(tags)
        content = "".join(
            broad_fragment(depth + 1) for _ in range(generator.randrange(1, 4))
        )
        closing = "</" + tag + ">" if generator.random() < 0.8 else ""
        attribute = generator.choice(
            ["", ' X="y"', " disabled", ' href="/a"', ' color="red"']
        )
        return "<" + tag + attribute + ">" + content + closing

    for index in range(10000):
        html = broad_fragment()
        yield {"html": html, "options": options[index % len(options)]}
        if index % 250 == 0:
            yield {"html": html, "keep": keep}
    for outer in tags:
        for inner in (
            "b",
            "p",
            "table",
            "select",
            "option",
            "form",
            "button",
            "plaintext",
            "textarea",
            "svg",
            "template",
        ):
            yield {"html": f"<{outer}><{inner}>x</{outer}>y</{inner}>"}


def python_result(request):
    service = TurndownService(request.get("options"))
    if request.get("plugin"):
        from lexidown.plugins import joplin_gfm

        if request.get("isCodeBlock"):
            service.isCodeBlock = lambda node: (
                node.nodeName == "PRE"
                and node.firstChild is not None
                and node.firstChild.nodeName == "CODE"
            )
        service.use(getattr(joplin_gfm, request["plugin"]))
    if "keep" in request:
        service.keep(request["keep"])
    if "remove" in request:
        service.remove(request["remove"])
    if request.get("strikethrough"):
        service.use(
            lambda instance: instance.addRule(
                "strikethrough",
                {
                    "filter": ["del", "s", "strike"],
                    "replacement": lambda content: "~~" + content + "~~",
                },
            )
        )
    if "escape" in request:
        return service.escape(request["escape"])

    def convert(html):
        mode = request.get("mode", "string")
        if mode == "string":
            return service.turndown(html)
        document = html5lib.parse(
            '<div id="fixture-root">' + html + "</div>", treebuilder="dom"
        )
        document.normalize()
        element = next(
            node
            for node in document.getElementsByTagName("div")
            if node.getAttribute("id") == "fixture-root"
        )
        if mode == "document":
            return service.turndown(document)
        if mode == "fragment":
            fragment = document.createDocumentFragment()
            while element.firstChild:
                fragment.appendChild(element.firstChild)
            return service.turndown(fragment)
        return service.turndown(element)

    if "sequence" in request:
        return [convert(html) for html in request["sequence"]]
    return convert(request["html"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, help="Write all mismatches as JSON")
    args = parser.parse_args()
    cases = list(corpus())
    output = subprocess.run(
        ["node", str(ROOT / "scripts/js_oracle.cjs")],
        input="".join(json.dumps(case, ensure_ascii=True) + "\n" for case in cases),
        capture_output=True,
        text=True,
        check=True,
    )
    actual_lines = output.stdout.rstrip("\n").split("\n")
    if len(actual_lines) != len(cases):
        raise RuntimeError(
            f"Oracle returned {len(actual_lines)} results for {len(cases)} cases: {output.stderr}"
        )
    mismatches = []
    for index, (case, line) in enumerate(zip(cases, actual_lines, strict=True)):
        expected = json.loads(line)
        try:
            actual = {"result": python_result(case)}
        except Exception as error:
            actual = {"error": type(error).__name__, "message": str(error)}
        if actual != expected:
            mismatches.append(
                {"index": index, "case": case, "js": expected, "python": actual}
            )
    if args.report:
        args.report.write_text(
            json.dumps(mismatches, ensure_ascii=True, indent=2) + "\n"
        )
    for mismatch in mismatches[:10]:
        print(json.dumps(mismatch, ensure_ascii=True))
    print(
        f"{len(cases) - len(mismatches)}/{len(cases)} JavaScript differential cases passed"
    )
    return bool(mismatches)


if __name__ == "__main__":
    sys.exit(main())
