# Development

## Setup and checks

Use Python 3.10 or newer, a C compiler, and Python development headers:

```sh
python -m venv .venv
# Activate .venv using the command for your shell.
python -m pip install -e '.[dev]'
python -m unittest discover -s tests -v
ruff check .
ruff format --check .
```

To apply Ruff fixes and formatting:

```sh
ruff check --fix .
ruff format .
```

The configuration in `pyproject.toml` uses 88-column formatting, double quotes,
isort import ordering, and common checks for errors, outdated syntax, likely
bugs, and simpler Python constructs. Vendored C sources are excluded. Ruff
checks Python files; Cython sources are checked by the Cython compiler. Reinstall
the editable package after changing `.pyx`, `.pxi`, `.pxd`, or bundled C files.

The reusable [lint workflow](.github/workflows/lint.yml) runs Ruff lint and
formatting checks and is called by the wheel workflow on pushes and pull requests.

## Dependencies

| Dependency | Purpose |
| --- | --- |
| Runtime Python packages | None; the wheel includes the native engine and parser |
| Cython and setuptools | Build the extension from source |
| html5lib | Test-only parser for independent DOM inputs |
| Ruff | Python linting, import sorting, and formatting |
| Node.js and the root npm dev dependencies | Optional JavaScript comparisons |
| `benchmarks/requirements.txt` | Optional competing converters for benchmarks |
| build, Twine, and cibuildwheel | Distribution builds and validation |

`html5lib` deliberately constructs DOM inputs independently of Lexidown for
compatibility and non-mutation tests. Its `six` and `webencodings` dependencies
are test dependencies too. Lexidown never imports these during normal use.
`selectolax` is not needed: the Lexbor C sources are already bundled in `vendor/`.

## Compatibility tests

The Python suite runs without Node.js. It includes all 147 upstream HTML fixtures
in both string and DOM modes, plus native parser, serialization, callback,
mutation, and optimization regressions.

The golden fixtures in `tests/fixtures/turndown.json` were extracted from
[Turndown's test document at aa84dfa](https://github.com/mixmark-io/turndown/blob/aa84dfa3e2361edea8c43acbfc2b7a9363494bfd/test/index.html).
Their upstream MIT attribution is retained in `THIRD_PARTY_NOTICES.md`.

For live comparisons against JavaScript, install the optional reference packages:

```sh
npm ci
python scripts/differential.py
```

`package-lock.json` pins Turndown 7.2.4 and Domino 2.2.0. The differential suite
compares outputs for option combinations, Unicode, malformed HTML, kept HTML,
plugins, and repeated conversions. Updating the compatibility target requires
reviewing the fixtures and differential results along with parser changes.

## Benchmarks

Install the npm reference with `npm ci`. With saved HTML snapshots present, run:

```sh
python scripts/benchmark.py --rounds 3 --samples 7 --warmups 5
```

This compares Lexidown and JavaScript across eight pages and 13 option profiles.
For the additional Python converters:

```sh
python -m pip install -r benchmarks/requirements.txt
python -m scripts.compare_converters --rounds 3 --samples 7 --warmups 5
```

Use a separate environment for competitor packages if they are not needed for
other development work. They are not part of Lexidown's development extra.

`benchmarks/sources.json` records source URLs and SHA-256 hashes. HTML snapshots
live in `benchmarks/inputs/` and are excluded from version control. The scripts
verify these hashes before measuring. Downloading a page again can change the
corpus; record new hashes and rerun the comparison instead of mixing results.

Each round uses fresh worker processes, shuffled page order, warmups, and serial
timed conversions with normal garbage collection. Timing includes parsing,
service construction, and Markdown generation. Startup, imports, file reads,
and output hashing are excluded. Converted output is never cached.

The scripts record exact output matches, sample spread, versions, and source,
binary, and input hashes. See [the Turndown report](benchmarks/REPORT.md) and
[the converter comparison](benchmarks/COMPARISON.md) for results and methodology.
Treat speed as workload-specific; different converters implement different
output conventions.

## Implementation

Lexbor parses HTML in C. Lexidown's own Cython code converts that DOM to Markdown.
Cython generates C at build time, and `setup.py` compiles it with the bundled
parser into one extension, `lexidown._native`.

1. The parser constructs a native DOM. Cython node wrappers retain its owning
   document; supplied Python DOMs are cloned into this representation.
2. The engine normalizes whitespace and collects text boundaries and blank-node
   metadata. Cached node names and list positions avoid repeated scans; mutations
   invalidate affected caches.
3. An explicit traversal stack applies the Turndown rules. Sibling output is
   joined in chunks to avoid repeatedly copying accumulated Markdown. The engine
   also implements kept-HTML serialization, JavaScript whitespace behavior, and
   UTF-16 heading lengths.

Options and rule dictionaries remain Python objects. Built-in rules use compiled
calls, while Python callbacks and method overrides run within the same engine.
There is no alternate parser or converter fallback.

| File | Responsibility |
| --- | --- |
| [`_native.pyx`](src/lexidown/_native.pyx) | Service, rule dispatch, and traversal |
| [`_native_dom.pxi`](src/lexidown/_native_dom.pxi) | DOM, parsing, serialization, and whitespace |
| [`_native_rules.pxi`](src/lexidown/_native_rules.pxi) | Built-in Markdown rules |
| [`_lexbor.pxd`](src/lexidown/_lexbor.pxd) | Lexbor C declarations |
| [`setup.py`](setup.py) | Combined native build |

The bundled Lexbor 3.1.0 has local C patches to match Domino's older parsing
behavior. They cover legacy select/menuitem handling and quirks involving
textarea, tables, processing instructions, and foreign content. Exact changes,
upstream versions, and attribution are documented in
[`vendor/lexbor/README.md`](vendor/lexbor/README.md).

## Distribution builds

Build a source archive and local wheel into an empty output directory:

```sh
python -m pip install build==1.6.0 twine==7.0.0
python -m build --outdir dist/release
python -m twine check --strict dist/release/*
```

Local wheels target the build machine. Use the
[wheel workflow](.github/workflows/wheels.yml) for portable distributions. It
builds a source archive, builds wheels from that archive, validates metadata,
and runs the full suite against each installed wheel outside the source tree.
`scripts/check_wheel.py` also verifies that the compiled extension and required
license notices are installed. Wheel tests need html5lib, but no Node.js.

Pull requests, pushes to `dev`, and manual runs build and test Linux wheels on
CPython 3.10 and 3.14, with JavaScript comparisons on 3.14. Only dependency
downloads are cached; project wheels are rebuilt from the source archive.

Pushes to `main` run the full release build, configuring standard CPython
3.10–3.14 for these targets:

| Platform | Architectures | Build baseline |
| --- | --- | --- |
| Linux with glibc | x86-64, ARM64 | manylinux, glibc 2.28 |
| Linux with musl | x86-64, ARM64 | musllinux, musl 1.2 |
| macOS | Intel x86-64, Apple Silicon ARM64 | macOS 11 |
| Windows | x64 | AMD64 |

There are 35 configured wheel builds. Each Python version needs its own wheel;
the extension does not use the stable `abi3` ABI. Windows ARM64, 32-bit systems,
PyPy, and free-threaded CPython are outside this matrix. A platform is validated
by its own successful build and installed-wheel tests.

## Licensing

The conversion code retains Turndown's MIT license and attribution. Lexbor's
Apache-2.0 license, NOTICE, BSD-2-Clause notices, and local modification notices
must be preserved. The package metadata describes these component obligations
with `MIT AND Apache-2.0 AND BSD-2-Clause`.

See [LICENSE](LICENSE), [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), and the
[Apache redistribution terms](https://www.apache.org/licenses/LICENSE-2.0).
