"""Compare default and customized HTML-to-Markdown conversion.

Install with `python -m pip install lexidown` (or `python -m pip install .`
from a source checkout), then run `python examples/formatting.py`.
Replace html_sample with your HTML and edit clean_service's options below.
"""

from lexidown import TurndownService

html_sample = """
<div class="content-wrapper" style="padding: 16px; background: #fff;">
    <style>
        .content-wrapper { font-family: Arial, sans-serif; }
        h1 { color: #111; }
        .highlight { background-color: yellow; }
    </style>

    <h1 class="main-title">Lexidown Test Document</h1>
    <p>This paragraph contains <strong>bold text</strong>, <em>italics</em>, and a <a href="https://example.com">hyperlink</a>.</p>

    <h2>Lists and Code</h2>
    <ul>
        <li>Item with inline <code>config = True</code></li>
        <li>Second bullet point</li>
    </ul>

    <pre><code class="language-python">def calculate_speedup(js_time, native_time):
    return js_time / native_time
</code></pre>

    <h2>Custom Rules and Filters</h2>
    <p>Testing modifications: <del>legacy data</del> replaced by <ins>updated value</ins>.</p>

    <script>
        document.addEventListener("DOMContentLoaded", () => {
            console.log("Interactive script running.");
        });
    </script>
</div>
"""

# 1. Defaults: Setext headings, indented code, and inline links.
# Script/style text is retained; inline CSS attributes are ignored.
raw_service = TurndownService()
default_output = raw_service.turndown(html_sample)

# 2. Configured conversion:
# - Drops <script> and <style> tags and their contents
# - Preserves <ins> as raw HTML
# - Converts <del> into strikethrough (requires a renderer supporting ~~text~~)
clean_service = (
    TurndownService(
        {
            "headingStyle": "atx",  # "atx" (# Heading) or "setext"
            "codeBlockStyle": "fenced",  # "fenced" or "indented"
            "bulletListMarker": "-",  # "-", "*", or "+"
            "emDelimiter": "*",  # "*" or "_"
            "linkStyle": "referenced",  # "referenced" or "inlined"
            "linkReferenceStyle": "full",  # "full", "collapsed", or "shortcut"
        }
    )
    .remove(["script", "style"])
    .keep("ins")
    .addRule(
        "strikethrough",
        {
            "filter": ["del", "s", "strike"],
            "replacement": lambda content: f"~~{content}~~",
        },
    )
)
clean_output = clean_service.turndown(html_sample)

# Small checks you can keep when adapting the example.
assert "DOMContentLoaded" in default_output
assert "DOMContentLoaded" not in clean_output
assert ".content-wrapper" not in clean_output
assert "~~legacy data~~" in clean_output
assert "<ins>updated value</ins>" in clean_output
assert "```python\n" in clean_output

print("=== Default Output (Scripts/Styles Present) ===")
print(default_output)
print("\n=== Clean Output (Removed, Kept, and Custom Rules Applied) ===")
print(clean_output)
