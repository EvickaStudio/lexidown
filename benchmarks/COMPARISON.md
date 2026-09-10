# HTML-to-Markdown converter comparison

Run: 2026-09-10T07:53:52.378169+00:00 to 2026-09-10T08:00:34.214863+00:00.

All converters receive the same complete HTML. Their defaults produce different Markdown and may retain different content; timing is not a quality or equivalence score.

## Median conversion time

Milliseconds; lower is faster. Medians pool all measured process rounds.

| Page | Turndown JS | Lexidown | html2text | markdownify | markdownify + lxml | html-to-markdown | html-to-markdown, no metadata | fast-h2m |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| [python-functions](https://docs.python.org/3/library/functions.html) | 65.18 | 29.66 | 87.75 | 187.33 | 150.74 | 19.73 | 19.15 | 23.16 |
| [whatwg-parsing](https://html.spec.whatwg.org/multipage/parsing.html) | 194.63 | 73.94 | 187.16 | 498.21 | 317.86 | 46.02 | 43.76 | 62.81 |
| [wikipedia-world-war-ii](https://en.wikipedia.org/wiki/World_War_II) | 214.48 | 79.87 | 273.78 | 562.67 | 444.42 | 92.67 | 87.94 | 197.74 |
| [mdn-array](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array) | 20.51 | 9.31 | 39.79 | 71.53 | 56.86 | 8.61 | 7.86 | 9.01 |
| [github-cpython](https://github.com/python/cpython) | 27.85 | 8.13 | 29.69 | 73.22 | 57.51 | 20.53 | 20.30 | 21.48 |
| [guardian-world](https://www.theguardian.com/world) | 32.51 | 9.71 | 36.59 | 71.00 | 56.84 | 22.27 | 20.52 | 23.09 |
| [gutenberg-pride-prejudice](https://www.gutenberg.org/files/1342/1342-h/1342-h.htm) | 552.99 | 25.66 | 202.40 | 176.67 | 147.03 | 13.74 | 13.64 | 11.92 |
| [rust-book](https://doc.rust-lang.org/book/print.html) | 2497.99 | 184.34 | 496.91 | 824.63 | 670.26 | 88.19 | 87.50 | 116.34 |

## Versions and configurations

Project documentation: [html2text](https://pypi.org/project/html2text/2025.4.15/), [markdownify and parser options](https://pypi.org/project/markdownify/1.2.3/), [html-to-markdown](https://pypi.org/project/html-to-markdown/3.12.2/), and [fast-h2m](https://pypi.org/project/fast-h2m/0.4.2/). The latter two use Rust native cores; fast-h2m is a fork of html-to-markdown. markdownify uses BeautifulSoup with html.parser by default; its lxml variant still runs the Markdown conversion in Python. These are selected libraries and configurations, not an exhaustive ranking of all available converters.

Speed ratio is JavaScript median / converter median, then the geometric mean across the eight pages. Greater than 1 means faster than JavaScript. Exact matches compare the first measured output bytes in every process round; every measured output is also hashed to check stability.

| Converter | Version | Call inside timer | Speed ratio | Exact JS matches |
| --- | --- | --- | ---: | ---: |
| Turndown JS | 7.2.4 | `new TurndownService().turndown(html)` | 1.00x | 8/8 |
| Lexidown | 0.2.0 | `TurndownService().turndown(html)` | 4.29x | 8/8 |
| html2text | 2025.4.15 | `html2text.html2text(html)` | 1.17x | 0/8 |
| markdownify | 1.2.3 | `markdownify.markdownify(html)` | 0.63x | 0/8 |
| markdownify + lxml | 1.2.3 | `markdownify.markdownify(html, bs4_options='lxml')` | 0.81x | 0/8 |
| html-to-markdown | 3.12.2 | `convert(html).content` | 4.52x | 0/8 |
| html-to-markdown, no metadata | 3.12.2 | `convert(html, ConversionOptions(extract_metadata=False)).content` | 4.71x | 0/8 |
| fast-h2m | 0.4.2 | `convert_to_markdown(html)` | 3.75x | 0/8 |

## Output sizes

UTF-8 bytes, not a quality score. The two html-to-markdown configurations time their complete calls, but only compare the returned Markdown content; metadata returned separately is not included in these sizes.

| Page | Turndown JS | Lexidown | html2text | markdownify | markdownify + lxml | html-to-markdown | html-to-markdown, no metadata | fast-h2m |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| python-functions | 107439 | 107439 | 102076 | 111412 | 111412 | 111118 | 109856 | 113352 |
| whatwg-parsing | 435903 | 435903 | 360324 | 411287 | 399549 | 436312 | 436157 | 487221 |
| wikipedia-world-war-ii | 651419 | 651419 | 554774 | 588941 | 588941 | 596545 | 595901 | 809785 |
| mdn-array | 76546 | 76546 | 76033 | 75601 | 75597 | 70852 | 69782 | 70854 |
| github-cpython | 76567 | 76567 | 22738 | 23498 | 23498 | 127837 | 124460 | 144524 |
| guardian-world | 488114 | 488114 | 33159 | 28971 | 28971 | 30936 | 30561 | 31404 |
| gutenberg-pride-prejudice | 745373 | 745373 | 736207 | 739794 | 739794 | 740666 | 740610 | 740742 |
| rust-book | 1453486 | 1453486 | 1413070 | 1402366 | 1402366 | 1409577 | 1409415 | 1409573 |

## Method and reproduction

The [small example and exact outputs](comparison-example.json) illustrate the semantic differences: Turndown preserves script/style text and flattens tables by default. The other tested converters omit that script/style text and render Markdown tables. Heading, emphasis, code-fence, metadata and newline conventions also differ. html-to-markdown's default result includes metadata work and frontmatter; its separate no-metadata configuration disables extraction. No input cleaning or output normalization was applied. All six competitor configurations differ from Turndown on every corpus page; this does not by itself indicate an error or worse Markdown.

Python 3.14.7; Node v22.23.2; 12th Gen Intel(R) Core(TM) i7-1260P; Linux-7.2.3-arch1-3-x86_64-with-glibc2.44.

3 fresh-process rounds, 5 warmups and 7 measured conversions per page/engine in each round. Page order is shuffled per round; engine order rotates per iteration. Conversions run serially with normal garbage collection. Timing includes a fresh converter/options where the API constructs them, parsing, and Markdown conversion. Imports, process startup, HTML reads, hashing, and output encoding/writing are excluded. Only input HTML is cached. Previous outputs are released outside the next timer.

This measures warm returned-string wall time, not cold startup, memory, concurrent throughput, or total CPU cost. Independent repeats are process rounds; samples within each round are correlated. Results describe this machine and corpus, not a constant speedup for arbitrary HTML.

System load averages before/after: (2.908203125, 1.31640625, 1.18017578125) / (2.08935546875, 1.67578125, 1.36279296875).

Raw samples, p10/p90 spread, separate round medians and ratios, package versions, worker identities, binary/source hashes, and snapshot hashes are in [comparison-results.json](comparison-results.json). These are sample spreads, not confidence intervals. All input, source, and binary hashes were checked again at completion. The original 13-profile Turndown compatibility run remains in [REPORT.md](REPORT.md).

```bash
PYTHONPATH=src python -m scripts.compare_converters --rounds 3 --samples 7 --warmups 5 --seed 20260909
```

Install the comparison-only dependencies documented in DEVELOPMENT.md first. Snapshots are excluded from version control; sources.json records URLs and hashes. A fresh download may change the corpus and requires new hashes.
