# HTML-to-Markdown converter comparison

Historical run before the Lexidown rename: "This port" refers to the development package `turndown-python` 7.2.4. Lexidown starts at 0.1.0 with the same conversion implementation; measurements and recorded hashes below are unchanged.

Run: 2026-09-09T10:51:57.651266+00:00 to 2026-09-09T10:58:31.987990+00:00.

All converters receive the same complete HTML. Their defaults produce different Markdown and may retain different content; timing is not a quality or equivalence score.

## Median conversion time

Milliseconds; lower is faster. Medians pool all measured process rounds.

| Page | Turndown JS | This port | html2text | markdownify | markdownify + lxml | html-to-markdown | html-to-markdown, no metadata | fast-h2m |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| [python-functions](https://docs.python.org/3/library/functions.html) | 58.73 | 35.46 | 81.76 | 185.41 | 145.78 | 18.89 | 18.26 | 21.99 |
| [whatwg-parsing](https://html.spec.whatwg.org/multipage/parsing.html) | 183.43 | 93.91 | 185.66 | 490.27 | 314.97 | 44.25 | 40.65 | 59.13 |
| [wikipedia-world-war-ii](https://en.wikipedia.org/wiki/World_War_II) | 212.08 | 104.22 | 261.13 | 555.33 | 439.05 | 89.15 | 84.64 | 191.27 |
| [mdn-array](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array) | 20.16 | 11.47 | 37.65 | 70.78 | 56.99 | 8.75 | 8.28 | 9.42 |
| [github-cpython](https://github.com/python/cpython) | 28.84 | 10.16 | 29.35 | 73.21 | 56.77 | 20.68 | 19.86 | 20.35 |
| [guardian-world](https://www.theguardian.com/world) | 30.71 | 18.54 | 35.98 | 68.27 | 53.13 | 20.89 | 19.59 | 22.28 |
| [gutenberg-pride-prejudice](https://www.gutenberg.org/files/1342/1342-h/1342-h.htm) | 523.93 | 50.60 | 198.18 | 173.20 | 145.27 | 13.56 | 12.70 | 11.25 |
| [rust-book](https://doc.rust-lang.org/book/print.html) | 2349.23 | 237.95 | 486.57 | 807.53 | 649.44 | 84.49 | 85.11 | 114.04 |

## Versions and configurations

Project documentation: [html2text](https://pypi.org/project/html2text/2025.4.15/), [markdownify and parser options](https://pypi.org/project/markdownify/1.2.3/), [html-to-markdown](https://pypi.org/project/html-to-markdown/3.12.2/), and [fast-h2m](https://pypi.org/project/fast-h2m/0.4.2/). The latter two use Rust native cores; fast-h2m is a fork of html-to-markdown. markdownify uses BeautifulSoup with html.parser by default; its lxml variant still runs the Markdown conversion in Python. These are selected libraries and configurations, not an exhaustive ranking of all available converters.

Speed ratio is JavaScript median / converter median, then the geometric mean across the eight pages. Greater than 1 means faster than JavaScript. Exact matches compare the first measured output bytes in every process round; every measured output is also hashed to check stability.

| Converter | Version | Call inside timer | Speed ratio | Exact JS matches |
| --- | --- | --- | ---: | ---: |
| Turndown JS | 7.2.4 | `new TurndownService().turndown(html)` | 1.00x | 8/8 |
| This port | 7.2.4 | `TurndownService().turndown(html)` | 2.94x | 8/8 |
| html2text | 2025.4.15 | `html2text.html2text(html)` | 1.16x | 0/8 |
| markdownify | 1.2.3 | `markdownify.markdownify(html)` | 0.61x | 0/8 |
| markdownify + lxml | 1.2.3 | `markdownify.markdownify(html, bs4_options='lxml')` | 0.79x | 0/8 |
| html-to-markdown | 3.12.2 | `convert(html).content` | 4.46x | 0/8 |
| html-to-markdown, no metadata | 3.12.2 | `convert(html, ConversionOptions(extract_metadata=False)).content` | 4.68x | 0/8 |
| fast-h2m | 0.4.2 | `convert_to_markdown(html)` | 3.72x | 0/8 |

## Output sizes

UTF-8 bytes, not a quality score. The two html-to-markdown configurations time their complete calls, but only compare the returned Markdown content; metadata returned separately is not included in these sizes.

| Page | Turndown JS | This port | html2text | markdownify | markdownify + lxml | html-to-markdown | html-to-markdown, no metadata | fast-h2m |
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

System load averages before/after: (0.3662109375, 0.43359375, 0.775390625) / (1.14111328125, 1.0185546875, 0.95654296875).

Raw samples, p10/p90 spread, separate round medians and ratios, package versions, worker identities, binary/source hashes, and snapshot hashes are in [comparison-results.json](comparison-results.json). These are sample spreads, not confidence intervals. All input, source, and binary hashes were checked again at completion. The original 13-profile Turndown compatibility run remains in [REPORT.md](REPORT.md).

```bash
PYTHONPATH=src python -m scripts.compare_converters --rounds 3 --samples 7 --warmups 5 --seed 20260909
```

Install the comparison-only dependencies documented in [Development](../DEVELOPMENT.md) first. Snapshots are excluded from version control; sources.json records URLs and hashes. A fresh download may change the corpus and requires new hashes.
