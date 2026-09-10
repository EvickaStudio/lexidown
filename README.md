# Lexidown

**Fast native HTML-to-Markdown for Python, compatible with Turndown.**

[![PyPI version](https://badge.fury.io/py/lexidown.svg)](https://badge.fury.io/py/lexidown)
[![Downloads](https://pepy.tech/badge/lexidown)](https://pepy.tech/project/lexidown)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/lexidown.svg)](https://pypi.org/project/lexidown/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

Lexidown brings [Turndown](https://github.com/mixmark-io/turndown)'s conversion
behavior, options, and extensible service API to Python. Its Cython conversion
engine and bundled Lexbor C parser require no runtime dependencies.
Joplin's GitHub Flavored Markdown (GFM) rules are included as an optional preset.

## Performance

Across eight complete HTML pages, Lexidown was **4.29× faster than JavaScript
Turndown on the Linux laptop** and **3.13× faster on the Windows desktop**, with
identical output. These are geometric means for this corpus. Lexidown's absolute
conversion times were lower on the desktop for every page.

<details>
<summary>Benchmark tables and timings: Linux laptop (Intel Core i7-1260P) vs Windows desktop (AMD Ryzen 7 9700X)</summary>

### Machines and method

| | Linux laptop | Windows desktop |
| --- | --- | --- |
| CPU | Intel Core i7-1260P | AMD Ryzen 7 9700X |
| OS | Arch Linux, kernel 7.2.3, glibc 2.44 | Windows 11 Pro, build 26200 |
| Python / Node.js | CPython 3.14.7 / Node.js 22.23.2 | CPython 3.14.7 / Node.js 22.23.2 |
| Timed samples per page/converter | 21 across 3 fresh-process rounds | 42 across 6 fresh-process rounds (two complete passes) |

Measured on 10 September 2026 using the same source build inputs, saved HTML
snapshots, converter versions, and default settings. Each round uses five warmups
and seven measured conversions per page/converter. Conversions run serially;
timing includes service construction, parsing, and Markdown conversion, while
excluding process startup, file reads, and output hashing. Desktop medians pool
both complete passes; no samples were discarded.

**The CPU, OS, and build environment differ, so these results cannot isolate an
OS effect.** The desktop ran Lexidown **1.26× faster** and JavaScript **1.72×
faster** overall. JavaScript's larger improvement explains why Lexidown's lead
over JavaScript fell from 4.29× to 3.13× even though Lexidown itself ran faster.
These measurements do not establish whether the laptop thermally throttled.

### Converter comparison

All speed ratios are geometric means across the eight pages. "Vs JS" compares
with JavaScript on the **same machine**. "Desktop vs laptop" is laptop time
divided by desktop time; above 1 means the desktop was faster overall. Individual
pages can behave differently. Exact JS output counts apply to both machines.

| Converter | Linux laptop vs JS | Windows desktop vs JS | Desktop vs laptop | Exact JS output |
| --- | ---: | ---: | ---: | ---: |
| JavaScript Turndown | 1.00× | 1.00× | 1.72× | 8/8 |
| **Lexidown** | **4.29×** | **3.13×** | **1.26×** | **8/8** |
| [html2text](https://pypi.org/project/html2text/) | 1.17× | 0.84× | 1.24× | 0/8 |
| [markdownify](https://pypi.org/project/markdownify/) | 0.63× | 0.53× | 1.45× | 0/8 |
| markdownify + lxml | 0.81× | 0.64× | 1.38× | 0/8 |
| [html-to-markdown](https://pypi.org/project/html-to-markdown/) | 4.52× | 3.25× | 1.24× | 0/8 |
| html-to-markdown, no metadata | 4.71× | 3.37× | 1.23× | 0/8 |
| [fast-h2m](https://pypi.org/project/fast-h2m/) | 3.75× | 2.51× | 1.15× | 0/8 |

The converters produce different Markdown; speed and exact-match counts are not
quality scores. markdownify + lxml also produced slightly different output
between machines on the MDN page; the desktop report records that difference.

### Absolute conversion times

Median milliseconds per complete page; **lower is faster**. Laptop means
Linux/i7-1260P; desktop means Windows/Ryzen 7 9700X.

| Page | Laptop Lexidown | Desktop Lexidown | Laptop JS | Desktop JS |
| --- | ---: | ---: | ---: | ---: |
| python-functions | 29.66 | 21.53 | 65.18 | 45.55 |
| whatwg-parsing | 73.94 | 53.82 | 194.63 | 114.31 |
| wikipedia-world-war-ii | 79.87 | 65.99 | 214.48 | 144.49 |
| mdn-array | 9.31 | 7.49 | 20.51 | 14.01 |
| github-cpython | 8.13 | 6.74 | 27.85 | 18.07 |
| guardian-world | 9.71 | 8.56 | 32.51 | 19.77 |
| gutenberg-pride-prejudice | 25.66 | 21.77 | 552.99 | 244.26 |
| rust-book | 184.34 | 136.45 | 2497.99 | 977.48 |

For example, the Rust book took Lexidown 184.34 ms on the laptop and 136.45 ms on
the desktop. JavaScript improved from 2497.99 ms to 977.48 ms on the same input.

The corpus focuses on large, complete pages (about 240 KiB–2 MiB of HTML),
rather than small snippets. Results depend on page structure, enabled plugins,
CPU, OS, power settings, and background load. Full timings for all converters,
versions, methodology, and raw samples are in the
[Linux laptop report](benchmarks/COMPARISON.md) and
[Windows desktop comparison](benchmarks/COMPARISON.md#windows-desktop-comparison).

</details>

Lexidown also matches Turndown byte for byte across all **104 page/option
combinations** in the [compatibility benchmark](benchmarks/REPORT.md).

## Installation

Requires Python 3.10 or newer.

```sh
python -m pip install lexidown
```

Platform wheels contain the native conversion engine and Lexbor. Installing a
matching wheel requires no compiler, Cython, Node.js, or separate HTML parser.
For platforms without a matching wheel, see [building from source](#building-from-source).

## Usage

```python
from lexidown import TurndownService

service = TurndownService({"headingStyle": "atx"})
markdown = service.turndown(
    "<h1>Hello world!</h1><p>Made with <strong>Python</strong>.</p>"
)
assert markdown == "# Hello world!\n\nMade with **Python**."
```

To discard scripts and styles along with their contents:

```python
service = TurndownService().remove(["script", "style"])
assert service.turndown("<style>p { color: red }</style><p>Hello</p>") == "Hello"
```

Like Turndown, the default conversion retains the text inside unsupported tags.
Inline styling attributes do not appear in converted Markdown.

For a runnable example comparing default output with custom formatting, HTML
cleanup, and a strikethrough rule, see [examples/formatting.py](examples/formatting.py).
After installing Lexidown, run it from the project directory:

```sh
python examples/formatting.py
```

## Bundled plugins

Two presets are included in the normal installation:

```python
from lexidown import TurndownService
from lexidown.plugins.firecrawl import firecrawl
from lexidown.plugins.joplin_gfm import gfm

service = TurndownService().use(gfm)  # or .use(firecrawl)
```

| Plugin | Provides |
| --- | --- |
| `gfm` | Tables, task lists, strikethrough and highlighted code blocks |
| `firecrawl` | GFM plus Firecrawl-style inline links |

See [GFM compatibility and table options](DEVELOPMENT.md#joplin-gfm-compatibility)
for details.

## Options

Pass a dictionary to `TurndownService`. Option names and defaults match
Turndown 7.2.4.

| Option | Default | Alternatives |
| --- | --- | --- |
| `headingStyle` | `"setext"` | `"atx"` |
| `hr` | `"* * *"` | Thematic break text |
| `bulletListMarker` | `"*"` | `"-"`, `"+"` |
| `codeBlockStyle` | `"indented"` | `"fenced"` |
| `fence` | `"```"` | `"~~~"` |
| `emDelimiter` | `"_"` | `"*"` |
| `strongDelimiter` | `"**"` | `"__"` |
| `linkStyle` | `"inlined"` | `"referenced"` |
| `linkReferenceStyle` | `"full"` | `"collapsed"`, `"shortcut"` |
| `br` | `"  "` | Text inserted before a line-break newline |
| `preformattedCode` | `False` | `True` |

### Advanced options

`blankReplacement`, `keepReplacement`, and `defaultReplacement` accept callbacks
with `(content, node, options)` arguments to customize blank elements, kept HTML,
and elements without a matching rule. `options` is a dictionary. Callbacks may
omit unused trailing arguments.

The `rules` option accepts an ordered dictionary of rules to replace the
built-in rule set.

## Methods

### `turndown(html_or_node)`

Convert an HTML string or DOM node to a Markdown string. A service can be reused
for multiple conversions.

### `addRule(key, rule)`

Register a conversion rule. `add_rule` is also available as a Python-style alias.

```python
service = TurndownService().addRule(
    "strikethrough",
    {
        "filter": ["del", "s", "strike"],
        "replacement": lambda content: "~~" + content + "~~",
    },
)
assert service.turndown("<del>old</del>") == "~~old~~"
```

### `keep(filter)`

Preserve matching elements as HTML:

```python
service = TurndownService().keep("ins")
assert service.turndown("<ins>new</ins>") == "<ins>new</ins>"
```

### `remove(filter)`

Discard matching elements and their contents. `keep` and `remove` accept the
same filters as rules. Added and built-in rules take precedence over both;
use `addRule` to override an element that already has a conversion rule.

### `use(plugin)`

Apply a plugin function, or a list of plugin functions. Plugins receive the
service and can register rules or change options:

```python
def strikethrough(service):
    service.addRule(
        "strikethrough",
        {"filter": "del", "replacement": lambda content: "~~" + content + "~~"},
    )


service = TurndownService().use(strikethrough)
assert service.turndown("<del>old</del>") == "~~old~~"
```

`addRule`, `keep`, `remove`, and `use` return the service for chaining.
JavaScript plugins need to be translated into Python functions.

## Extending with rules

A rule is a dictionary containing:

- `filter`: a lowercase tag name, a list of tag names, or a callback taking
  `(node, options)` and returning whether the rule matches.
- `replacement`: a callback taking `(content, node, options)` and returning
  Markdown. `content` is the converted content of the element's children.
- `append` (optional): a callback taking `options` and returning text to append
  after conversion, useful for reference definitions. Use a closure or bound
  method to maintain rule state.

Callbacks may omit unused trailing arguments. Rules are selected in this order:
blank rules, added rules (newest first), built-in rules, keep rules, remove rules,
then the default rule.

Rule callbacks receive DOM nodes with Turndown's camelCase properties, including
`nodeName`, `nodeType`, `textContent`, `outerHTML`, `parentNode`, `childNodes`,
`children`, `firstChild`, `nextSibling`, `previousSibling`, and `getAttribute`.
Conversion also exposes `isBlock`, `isCode`, `isBlank`, and
`flankingWhitespace` (a dictionary).

### Escaping

Text is escaped to prevent Markdown syntax from changing its meaning. Override
`service.escape` to customize this behavior. Text inside code bypasses escaping.

## DOM input

In addition to HTML strings, `turndown()` accepts native Lexidown DOM nodes and
`xml.dom.minidom` element, document, and fragment nodes. DOM inputs are cloned
before whitespace normalization, leaving the input tree unchanged.

```python
from xml.dom.minidom import parseString

from lexidown import TurndownService

# minidom parses XML; use well-formed markup when constructing a DOM this way.
document = parseString("<p>Hello <strong>world</strong></p>")
assert TurndownService().turndown(document.documentElement) == "Hello **world**"
```

## Building from source

From a source checkout or unpacked source distribution:

```sh
python -m pip install .
```

A C compiler and Python development headers are required. The build installs
Cython automatically and compiles the included Lexbor sources. No parser sources
need to be downloaded separately.

See [Development](DEVELOPMENT.md) for tests, Ruff formatting, benchmarks,
implementation details, and wheel builds.

## Development details

Turndown was ported to Python and optimized using **Codex + GPT-6 Astra Ultra**.

## License

Lexidown's conversion code is [MIT licensed](LICENSE), with Turndown's original
credits retained. Bundled Lexbor is Apache-2.0 licensed and includes BSD-2-Clause
components. Their licenses and notices are included in source distributions and
wheels; the combined package expression is `MIT AND Apache-2.0 AND BSD-2-Clause`.

See [third-party notices](THIRD_PARTY_NOTICES.md) and
[Lexbor's provenance and modifications](vendor/lexbor/README.md).
