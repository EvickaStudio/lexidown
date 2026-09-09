# Third-party notices

Lexidown contains a translated and optimized implementation of Turndown,
including its whitespace handling, and a modified copy of the Lexbor HTML
parser. The package's combined SPDX license expression is
`MIT AND Apache-2.0 AND BSD-2-Clause`: the licenses apply to their respective
components, rather than offering a choice of three licenses.

## Turndown and whitespace handling — MIT

The conversion rules, public interface, and test fixtures derive from
[Turndown 7.2.4](https://github.com/mixmark-io/turndown/tree/aa84dfa3e2361edea8c43acbfc2b7a9363494bfd),
copyright 2017 Dom Christie. The whitespace algorithm derives from
`collapse-whitespace`, copyright 2014 Luc Thevenard, as incorporated into
Turndown. Their copyright notices and the complete MIT permission and warranty
text are retained in [LICENSE](LICENSE).

The existing attribution to James Graham and other html5lib contributors is
also retained in that file from the earlier parser implementation. html5lib is
now a development dependency used to construct test inputs; its Python package
is not bundled or used to parse strings at runtime.

## Joplin Turndown GFM plugin — MIT

`src/lexidown/plugins/joplin_gfm.py` translates the published
[`@joplin/turndown-plugin-gfm` 1.0.68 npm archive](https://registry.npmjs.org/@joplin/turndown-plugin-gfm/-/turndown-plugin-gfm-1.0.68.tgz),
specifically `lib/turndown-plugin-gfm.cjs.js`, copyright 2017 Dom Christie.
The archive's MIT copyright, permission and warranty text is retained in
[LICENSE](LICENSE). The reference package is used only for development;
JavaScript is not bundled or required at runtime.

Archive integrity (SHA-512, base64):
`m8DfAQNC/V7g0j5H6Jv60WhekBBjodD+zTPGrU+g2m+ux/z8ZX07KQIl6kaAmbKwfvsQhC04op52g63I78sVgg==`.
The source SHA-256 and oracle versions are also recorded in
`tests/fixtures/joplin_gfm.json`. These fixtures were produced by running the
published plugin against Turndown 7.2.4 and Domino 2.2.0. The Python translation
uses the existing native DOM, isolates options per service, and caps colspan
expansion at 1,000 columns.

## Lexbor — Apache-2.0, with BSD-2-Clause portions

[Lexbor](https://github.com/lexbor/lexbor) 3.1.0 is bundled as C source and
statically compiled into the extension. It was obtained from the selectolax
0.4.11 source archive; the archive checksum, included modules, older Lexbor
2.4.0 source files, and local compatibility changes are recorded in
[vendor/lexbor/README.md](vendor/lexbor/README.md). The selectolax Python wrapper
is not included.

Source archive: [selectolax 0.4.11](https://pypi.org/project/selectolax/0.4.11/),
SHA-256 `2b565ddabce6c9a7b73fa28a39acf8f411a084fa2f169234ec2470f552d4421d`.

Lexbor's original [Apache license](vendor/lexbor/LICENSE),
[NOTICE](vendor/lexbor/NOTICE), and source copyright headers are preserved.
Each locally modified upstream file carries a notice identifying the change.
The numeric conversion files `diyfp.*`, `dtoa.*`, and `strtod.*` include code
derived from NGINX NJS; their additional BSD copyright, redistribution
conditions, and disclaimer are retained in
[vendor/lexbor/BSD-LICENSE](vendor/lexbor/BSD-LICENSE).

## Redistributing the package

The licenses permit modified source distributions and compiled wheels,
including commercial distribution, subject to their terms. In particular:

- Keep the MIT copyright and permission notice with distributed copies.
- Include the Apache license and readable Lexbor NOTICE with both source and
  binary distributions. Preserve applicable upstream notices in distributed
  source and identify locally changed files, as required by
  [Apache-2.0 section 4](https://www.apache.org/licenses/LICENSE-2.0).
- Retain the BSD notice, conditions, and disclaimer in source distributions and
  in the documentation or other materials accompanying binaries, as required
  by [BSD-2-Clause](https://spdx.org/licenses/BSD-2-Clause.html).

The release configuration includes this file and all four license/notice files
above in source distributions and in each wheel's `.dist-info/licenses/`
directory. Apache-2.0 does not require distributing source alongside a wheel;
the source archive is supplied so users can inspect, rebuild, and modify it.
Compatibility descriptions do not imply endorsement by the upstream projects;
Apache-2.0 section 6 does not grant their trademark rights.

These notes describe the bundled components and their distribution conditions;
the accompanying license texts govern their use.
