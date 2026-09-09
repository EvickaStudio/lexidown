# Lexidown

**Fast native HTML-to-Markdown for Python, compatible with Turndown.**

Lexidown brings [Turndown](https://github.com/mixmark-io/turndown)'s conversion
behavior, options, and extensible service API to Python. Its Cython conversion
engine and bundled Lexbor C parser require no runtime dependencies.

## Performance

Default settings, eight complete HTML pages, CPython 3.14.7 and Node.js 22.23.2
on an Intel Core i7-1260P:

| Converter | Implementation | Speed vs JS Turndown | Exact JS output |
| --- | --- | ---: | ---: |
| JavaScript Turndown | JavaScript + Domino | 1.00× | 8/8 |
| **Lexidown** | **Cython + Lexbor** | **2.94×** | **8/8** |
| [html2text](https://pypi.org/project/html2text/) | Python | 1.16× | 0/8 |
| [markdownify](https://pypi.org/project/markdownify/) | Python + BeautifulSoup | 0.61× | 0/8 |
| [html-to-markdown](https://pypi.org/project/html-to-markdown/) | Rust | 4.46× | 0/8 |
| [fast-h2m](https://pypi.org/project/fast-h2m/) | Rust | 3.72× | 0/8 |

Speed is the geometric mean of JavaScript time divided by converter time;
above 1 means faster. Each page has 21 timed conversions across three fresh
processes. Results depend on the input, and different output is not a quality
score. See the [full comparison](benchmarks/COMPARISON.md) for per-page timings,
versions, methodology, and additional configurations.

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
