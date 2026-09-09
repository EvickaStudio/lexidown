# Vendored Lexbor

Lexbor 3.1.0, copied from the selectolax 0.4.11 source distribution.
Only the core, DOM, HTML, namespace, tag and platform modules are included.

Source: https://pypi.org/project/selectolax/0.4.11/
Archive SHA-256: `2b565ddabce6c9a7b73fa28a39acf8f411a084fa2f169234ec2470f552d4421d`.

The Apache-2.0 license, NOTICE and bundled BSD notices are preserved.
The source is included in source distributions; wheels contain the compiled
parser and its license notices. Building does not download Lexbor.

## Local compatibility changes

The JavaScript Turndown dependency uses Domino's older HTML parsing behavior.
These patches implement that behavior in the C parser, without a second parser:

- `tree/insertion_mode/in_body.c`: enter text insertion mode after the first
  textarea newline so active formatting is not reconstructed inside the textarea;
  process an `image` token as `img` before leaving table foster parenting;
  treat `search` as an ordinary element; restore the legacy select-mode switch.
- `tag_res.h`: classify `search` as ordinary for scope and formatting handling.
- `tokenizer/state.c`: parse `<?...>` as a bogus HTML comment, as Domino does,
  instead of the processing-instruction nodes introduced in Lexbor 3.1.
- `tree.c` and `tree/insertion_mode.h`: restore select insertion-mode selection
  when resetting the parser state.
- `tree.h`, `tree.c`, and `tree/insertion_mode/in_body.c`: restore the legacy
  `menuitem` implied-end-tag and autoclosing rules used by Domino.
- `tree/insertion_mode/foreign_content.c`: include `sup` among the HTML tags
  that leave foreign SVG/MathML content, matching Domino.
- `tree/insertion_mode/in_select.c` and `in_select_in_table.c`: restore the
  legacy select rules from Lexbor 2.4.0. The former uses a local select-scope
  query because Lexbor 3.1.0 removed that scope category, and reports its
  doctype parse error with the current generic unexpected-token error code.
  `in_select_in_table.c` is an unmodified copy of the Lexbor 2.4.0 file.

The restored files come from the same Apache-2.0 licensed upstream project:

- https://github.com/lexbor/lexbor/blob/v2.4.0/source/lexbor/html/tree/insertion_mode/in_select.c
- https://github.com/lexbor/lexbor/blob/v2.4.0/source/lexbor/html/tree/insertion_mode/in_select_in_table.c

The select entry function was restored from:
https://github.com/lexbor/lexbor/blob/v2.4.0/source/lexbor/html/tree/insertion_mode/in_body.c

Locally modified upstream files carry a prominent modification notice above
their preserved copyright header. Keep these notices when redistributing the
source. Binary distributions must retain the Apache license, Lexbor NOTICE,
and BSD notices; the package includes them in its wheel license directory.
See [third-party notices](../../THIRD_PARTY_NOTICES.md) for distribution details.

## Building

Compile the C sources in `core`, `dom`, `html`, `ns`, and `tag`, plus exactly one
platform implementation from `ports/posix` or `ports/windows_nt`. Add `source`
to the include path and define `LEXBOR_STATIC`. No other Lexbor modules or
external libraries are required. Use an optimizing C99-compatible compiler.
