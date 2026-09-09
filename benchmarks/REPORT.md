# Compiled Python versus JavaScript Turndown

Historical run before the Lexidown rename: the Python engine was distributed under the development name `turndown-python` 7.2.4. Lexidown starts at 0.1.0 with the same conversion implementation; measurements and recorded hashes below are unchanged.

Run: 2026-09-09T10:05:53.926465+00:00 to 2026-09-09T10:38:48.294676+00:00.

**104/104 page/profile combinations produced identical, stable output.**

Across the 8 default-option pages, the geometric-mean speedup is **2.85x**; **5/8** reach 2x. Across all matching page/profile combinations, speedup ranges from **1.50x to 11.58x**; **52/104** reach 2x.

Speedup is JavaScript median / compiled Python median: greater than 1 means Python is faster. Counts use medians, not every individual sample. A result below 2x remains in the report. These pages were selected before timing.

## Default options

Times are pooled medians in milliseconds. Round range uses the separate process-round median ratios. Profile range covers all 13 option profiles.

| Page | HTML KiB | JS ms | Python ms | Speedup | Round range | Profile range |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| [python-functions](https://docs.python.org/3/library/functions.html) | 308.4 | 59.13 | 38.58 | 1.53x | 1.53-1.54x | 1.50-1.67x |
| [whatwg-parsing](https://html.spec.whatwg.org/multipage/parsing.html) | 769.3 | 197.48 | 95.26 | 2.07x | 1.95-2.13x | 1.81-2.09x |
| [wikipedia-world-war-ii](https://en.wikipedia.org/wiki/World_War_II) | 2019.5 | 216.96 | 106.97 | 2.03x | 2.01-2.12x | 1.77-2.07x |
| [mdn-array](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array) | 238.8 | 20.12 | 12.37 | 1.63x | 1.58-1.72x | 1.53-1.72x |
| [github-cpython](https://github.com/python/cpython) | 376.3 | 26.02 | 10.84 | 2.40x | 2.36-2.58x | 2.30-2.55x |
| [guardian-world](https://www.theguardian.com/world) | 746.8 | 30.30 | 19.63 | 1.54x | 1.52-1.63x | 1.53-1.67x |
| [gutenberg-pride-prejudice](https://www.gutenberg.org/files/1342/1342-h/1342-h.htm) | 787.4 | 546.50 | 51.71 | 10.57x | 10.43-10.67x | 10.28-10.88x |
| [rust-book](https://doc.rust-lang.org/book/print.html) | 1833.6 | 2471.94 | 231.67 | 10.67x | 10.26-11.09x | 10.12-11.58x |

## Method

Python 3.14.7; Node v22.23.2; V8 12.4.254.21-node.56; 12th Gen Intel(R) Core(TM) i7-1260P; Linux-7.2.3-arch1-3-x86_64-with-glibc2.44.

Both converters implement Turndown 7.2.4. Python uses the compiled Cython engine and bundled Lexbor 3.1.0 with compatibility patches. Only these two implementations are measured.

3 independent rounds each start fresh worker processes. Each page/profile has 5 warmups and 7 timed conversions per round: 21 recorded samples per engine per combination. Both workers remain alive within a round, but run conversions serially. Engine order alternates for paired samples; page/profile order is shuffled per round using seed 20260909. Raw order and timing samples are saved in results.json.

Timers include fresh service construction, parsing the complete HTML, whitespace normalization and returning the Markdown string. File/network access, imports, process startup, output encoding/hashing and byte comparisons are outside the timer. Input HTML is cached, converted output is never cached, and both engines use normal garbage collection. Previous result strings are released outside the next timer. This measures warm returned-string wall time, not cold startup, total CPU cost, memory usage, or concurrent throughput.

Both engines receive the same complete saved UTF-8 HTML. First measured outputs are compared byte for byte in every round. All measured hashes must agree within and across engines and rounds. A speedup with differing output is not a valid compatibility result. Source/input and actual worker binary/bundle hashes are recorded and verified at the end.

p10-p90 below describes the sample spread, not a confidence interval. The process rounds are the independent repeats; samples within one process and profiles of one page are correlated. Several profiles produce the same output on a given page. The default-page summary avoids counting those as additional sites. Measurements describe this machine and corpus, not a constant speedup for all HTML.

System load averages before/after: (0.61669921875, 1.0263671875, 1.47216796875) / (1.21923828125, 1.3017578125, 1.40673828125). No other builds or benchmark jobs were started during measurement.

## Built-in Functions — Python 3.14.7 documentation

[Source](https://docs.python.org/3/library/functions.html); 315,798 bytes; fetched 2026-09-09T08:28:28+00:00.
Input SHA-256: `48fa2539e7bb063823eb695a53417b45cb090360bd3887dd5ccdf7e50119dfde`.

| Profile | JS median [p10-p90] ms | Python median [p10-p90] ms | Speedup | Round range | Output |
| --- | ---: | ---: | ---: | ---: | --- |
| default | 59.13 [57.35-66.02] | 38.58 [37.07-39.09] | 1.53x | 1.53-1.54x | identical |
| atx-headings | 58.11 [55.71-61.90] | 34.77 [32.36-37.55] | 1.67x | 1.62-1.78x | identical |
| bullet-minus | 57.95 [55.71-65.36] | 36.29 [34.18-40.96] | 1.60x | 1.59-1.65x | identical |
| bullet-plus | 57.38 [55.94-63.75] | 36.25 [34.22-38.80] | 1.58x | 1.55-1.61x | identical |
| fenced-backticks | 57.84 [54.93-64.16] | 35.07 [33.22-37.85] | 1.65x | 1.55-1.68x | identical |
| fenced-tildes | 56.52 [54.21-63.03] | 35.81 [34.03-40.71] | 1.58x | 1.52-1.61x | identical |
| preformatted-code | 56.44 [52.98-66.93] | 35.77 [34.17-37.64] | 1.58x | 1.53-1.62x | identical |
| references-full | 58.03 [55.71-63.65] | 38.70 [34.27-43.71] | 1.50x | 1.48-1.56x | identical |
| references-collapsed | 55.86 [55.19-65.43] | 36.20 [34.63-75.02] | 1.54x | 1.52-1.68x | identical |
| references-shortcut | 57.35 [53.62-58.80] | 36.85 [34.94-71.52] | 1.56x | 1.46-1.63x | identical |
| emphasis-markers | 59.34 [56.57-65.20] | 37.70 [35.95-85.38] | 1.57x | 1.53-1.64x | identical |
| custom-breaks | 59.07 [56.30-60.66] | 37.67 [34.30-39.55] | 1.57x | 1.50-1.72x | identical |
| combined | 57.32 [53.63-63.80] | 38.03 [33.92-44.64] | 1.51x | 1.39-1.54x | identical |

## HTML Standard

[Source](https://html.spec.whatwg.org/multipage/parsing.html); 787,795 bytes; fetched 2026-09-09T08:28:29+00:00.
Input SHA-256: `311d356f10fcb9fbeedfa90964845568575f1802e2d7f34eba1f8fbc95c86e99`.

| Profile | JS median [p10-p90] ms | Python median [p10-p90] ms | Speedup | Round range | Output |
| --- | ---: | ---: | ---: | ---: | --- |
| default | 197.48 [184.77-207.96] | 95.26 [89.51-98.74] | 2.07x | 1.95-2.13x | identical |
| atx-headings | 193.30 [183.76-202.53] | 94.35 [91.77-102.16] | 2.05x | 1.94-2.10x | identical |
| bullet-minus | 191.79 [184.46-206.24] | 92.47 [89.11-151.53] | 2.07x | 2.00-2.08x | identical |
| bullet-plus | 193.92 [185.94-207.25] | 93.26 [87.00-282.92] | 2.08x | 1.99-2.15x | identical |
| fenced-backticks | 189.35 [184.21-205.02] | 96.21 [91.59-106.18] | 1.97x | 1.98-2.00x | identical |
| fenced-tildes | 194.74 [185.97-203.92] | 95.64 [90.42-101.73] | 2.04x | 1.94-2.12x | identical |
| preformatted-code | 197.05 [189.73-209.05] | 95.23 [90.29-101.01] | 2.07x | 2.04-2.11x | identical |
| references-full | 183.63 [169.95-194.25] | 97.31 [91.35-104.44] | 1.89x | 1.84-1.95x | identical |
| references-collapsed | 176.41 [168.67-188.61] | 96.51 [92.90-101.63] | 1.83x | 1.75-1.87x | identical |
| references-shortcut | 170.31 [162.81-183.49] | 94.25 [88.67-103.15] | 1.81x | 1.73-1.87x | identical |
| emphasis-markers | 195.13 [183.22-201.64] | 93.37 [88.35-253.32] | 2.09x | 2.07-2.10x | identical |
| custom-breaks | 194.09 [187.01-211.20] | 96.37 [88.52-102.46] | 2.01x | 2.00-2.09x | identical |
| combined | 176.34 [165.20-184.40] | 96.24 [91.06-103.08] | 1.83x | 1.75-1.89x | identical |

## World War II - Wikipedia

[Source](https://en.wikipedia.org/wiki/World_War_II); 2,067,968 bytes; fetched 2026-09-09T09:51:16+00:00.
Input SHA-256: `bc359e330c6505c9d661980a8a7198b17a2bced7e059dad3c366329c80f01e31`.

| Profile | JS median [p10-p90] ms | Python median [p10-p90] ms | Speedup | Round range | Output |
| --- | ---: | ---: | ---: | ---: | --- |
| default | 216.96 [213.59-233.48] | 106.97 [98.64-122.35] | 2.03x | 2.01-2.12x | identical |
| atx-headings | 217.21 [209.74-233.51] | 108.43 [98.79-121.42] | 2.00x | 1.98-2.03x | identical |
| bullet-minus | 211.23 [202.95-232.22] | 108.13 [93.91-125.91] | 1.95x | 1.86-2.19x | identical |
| bullet-plus | 214.77 [206.40-229.25] | 107.43 [95.50-119.89] | 2.00x | 1.91-2.20x | identical |
| fenced-backticks | 217.65 [208.99-225.21] | 108.08 [97.06-127.65] | 2.01x | 2.01-2.14x | identical |
| fenced-tildes | 215.08 [208.11-230.99] | 104.91 [94.24-121.87] | 2.05x | 2.04-2.11x | identical |
| preformatted-code | 220.07 [211.83-228.25] | 106.37 [97.52-116.22] | 2.07x | 1.97-2.12x | identical |
| references-full | 191.19 [183.27-199.47] | 106.08 [100.92-259.10] | 1.80x | 1.80-1.82x | identical |
| references-collapsed | 193.36 [183.42-199.90] | 105.40 [98.45-119.70] | 1.83x | 1.78-1.86x | identical |
| references-shortcut | 190.83 [181.54-208.05] | 107.65 [100.61-284.13] | 1.77x | 1.75-1.79x | identical |
| emphasis-markers | 222.88 [210.21-257.72] | 116.67 [100.42-135.10] | 1.91x | 2.02-2.16x | identical |
| custom-breaks | 225.28 [212.90-258.99] | 113.00 [99.13-132.26] | 1.99x | 1.94-1.99x | identical |
| combined | 189.56 [186.17-199.94] | 106.88 [104.43-256.61] | 1.77x | 1.74-1.79x | identical |

## Array - JavaScript | MDN

[Source](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array); 244,504 bytes; fetched 2026-09-09T09:51:15+00:00.
Input SHA-256: `889211d505bf9b7dd8451240049f7cc6e111857b65c1b1682e1a97a0fecea095`.

| Profile | JS median [p10-p90] ms | Python median [p10-p90] ms | Speedup | Round range | Output |
| --- | ---: | ---: | ---: | ---: | --- |
| default | 20.12 [19.23-21.19] | 12.37 [11.61-23.25] | 1.63x | 1.58-1.72x | identical |
| atx-headings | 19.86 [19.02-21.48] | 12.15 [11.38-21.26] | 1.63x | 1.58-1.67x | identical |
| bullet-minus | 20.05 [18.67-22.75] | 12.22 [11.10-20.65] | 1.64x | 1.55-1.82x | identical |
| bullet-plus | 19.65 [18.67-21.16] | 11.89 [10.97-20.62] | 1.65x | 1.63-1.65x | identical |
| fenced-backticks | 20.17 [19.24-21.23] | 12.96 [11.54-21.71] | 1.56x | 1.53-1.67x | identical |
| fenced-tildes | 20.72 [19.48-22.13] | 12.19 [11.69-21.15] | 1.70x | 1.62-1.73x | identical |
| preformatted-code | 19.87 [18.90-20.83] | 12.09 [11.02-21.99] | 1.64x | 1.67-1.67x | identical |
| references-full | 20.21 [18.63-34.88] | 12.81 [11.76-22.85] | 1.58x | 1.61-1.93x | identical |
| references-collapsed | 19.06 [18.45-20.82] | 12.23 [11.45-21.41] | 1.56x | 1.53-1.57x | identical |
| references-shortcut | 19.83 [18.85-20.28] | 12.40 [11.34-20.83] | 1.60x | 1.56-1.73x | identical |
| emphasis-markers | 20.59 [19.29-21.32] | 11.96 [11.71-21.27] | 1.72x | 1.60-1.75x | identical |
| custom-breaks | 20.44 [19.87-21.16] | 12.66 [12.13-23.28] | 1.61x | 1.57-1.64x | identical |
| combined | 20.11 [18.75-21.76] | 13.10 [11.77-22.09] | 1.53x | 1.52-1.61x | identical |

## GitHub - python/cpython: The Python programming language · GitHub

[Source](https://github.com/python/cpython); 385,288 bytes; fetched 2026-09-09T09:51:16+00:00.
Input SHA-256: `97322a8de53444a94dee061415c8771bdd37e59798e6d57b628deee3f8c31f2b`.

| Profile | JS median [p10-p90] ms | Python median [p10-p90] ms | Speedup | Round range | Output |
| --- | ---: | ---: | ---: | ---: | --- |
| default | 26.02 [24.17-28.06] | 10.84 [9.71-17.11] | 2.40x | 2.36-2.58x | identical |
| atx-headings | 25.98 [24.36-27.71] | 10.59 [9.90-18.16] | 2.45x | 2.38-2.56x | identical |
| bullet-minus | 25.74 [24.24-27.46] | 10.64 [9.71-17.01] | 2.42x | 2.34-2.59x | identical |
| bullet-plus | 26.97 [25.38-36.45] | 11.13 [10.18-19.96] | 2.42x | 2.43-2.60x | identical |
| fenced-backticks | 26.37 [24.96-28.65] | 10.75 [10.19-17.61] | 2.45x | 2.38-2.53x | identical |
| fenced-tildes | 26.55 [25.15-28.28] | 10.54 [9.80-16.50] | 2.52x | 2.45-2.61x | identical |
| preformatted-code | 26.59 [24.85-28.09] | 10.68 [9.99-16.97] | 2.49x | 2.43-2.54x | identical |
| references-full | 24.53 [23.23-26.99] | 10.35 [9.58-14.55] | 2.37x | 2.34-2.44x | identical |
| references-collapsed | 25.81 [24.30-26.91] | 10.35 [9.67-14.76] | 2.49x | 2.31-2.57x | identical |
| references-shortcut | 25.74 [24.59-28.61] | 11.17 [10.20-14.78] | 2.30x | 2.27-2.51x | identical |
| emphasis-markers | 26.94 [25.91-28.49] | 11.12 [10.34-18.08] | 2.42x | 2.40-2.50x | identical |
| custom-breaks | 25.50 [24.53-28.74] | 10.76 [9.84-16.98] | 2.37x | 2.34-2.48x | identical |
| combined | 26.20 [24.62-37.43] | 10.27 [9.74-13.68] | 2.55x | 2.34-2.49x | identical |

## Latest news from around the world | The Guardian

[Source](https://www.theguardian.com/world); 764,724 bytes; fetched 2026-09-09T09:51:16+00:00.
Input SHA-256: `7bf53cec9e260d3000e0876c70c7f00393ad0c8fa4811cb04cb66550c423b04d`.

| Profile | JS median [p10-p90] ms | Python median [p10-p90] ms | Speedup | Round range | Output |
| --- | ---: | ---: | ---: | ---: | --- |
| default | 30.30 [28.17-31.49] | 19.63 [17.11-27.52] | 1.54x | 1.52-1.63x | identical |
| atx-headings | 31.16 [29.07-36.13] | 19.55 [18.40-22.27] | 1.59x | 1.56-1.60x | identical |
| bullet-minus | 31.07 [29.80-33.50] | 19.50 [18.68-24.79] | 1.59x | 1.57-1.65x | identical |
| bullet-plus | 30.69 [29.85-33.41] | 18.93 [18.15-19.75] | 1.62x | 1.61-1.68x | identical |
| fenced-backticks | 32.11 [29.88-36.26] | 19.22 [18.72-20.41] | 1.67x | 1.64-1.67x | identical |
| fenced-tildes | 30.45 [29.37-31.15] | 18.27 [17.59-19.06] | 1.67x | 1.65-1.73x | identical |
| preformatted-code | 31.10 [28.73-33.71] | 19.06 [17.87-20.97] | 1.63x | 1.55-1.64x | identical |
| references-full | 29.84 [28.09-31.36] | 19.48 [18.71-24.67] | 1.53x | 1.46-1.58x | identical |
| references-collapsed | 31.14 [29.25-34.32] | 19.09 [17.63-26.47] | 1.63x | 1.60-1.72x | identical |
| references-shortcut | 31.50 [28.69-36.18] | 19.34 [18.15-24.44] | 1.63x | 1.58-1.70x | identical |
| emphasis-markers | 31.20 [29.19-34.71] | 19.63 [18.72-24.65] | 1.59x | 1.53-1.65x | identical |
| custom-breaks | 31.79 [30.42-36.15] | 19.68 [18.87-21.08] | 1.62x | 1.55-1.65x | identical |
| combined | 31.10 [29.41-33.25] | 19.53 [18.78-24.77] | 1.59x | 1.59-1.65x | identical |

## Pride and prejudice | Project Gutenberg

[Source](https://www.gutenberg.org/files/1342/1342-h/1342-h.htm); 806,295 bytes; fetched 2026-09-09T09:51:17+00:00.
Input SHA-256: `420b05f63fc1b50420edab9feb9147c87968413ad9487759e5e39c52471d62ba`.

| Profile | JS median [p10-p90] ms | Python median [p10-p90] ms | Speedup | Round range | Output |
| --- | ---: | ---: | ---: | ---: | --- |
| default | 546.50 [530.53-580.90] | 51.71 [50.54-59.33] | 10.57x | 10.43-10.67x | identical |
| atx-headings | 528.94 [519.22-595.16] | 51.46 [47.37-56.05] | 10.28x | 9.71-10.72x | identical |
| bullet-minus | 546.42 [530.23-587.22] | 51.30 [48.43-54.37] | 10.65x | 10.69-10.94x | identical |
| bullet-plus | 554.53 [528.56-605.70] | 51.96 [50.30-54.77] | 10.67x | 10.32-10.97x | identical |
| fenced-backticks | 559.87 [542.09-622.23] | 52.59 [48.27-54.57] | 10.65x | 10.26-11.55x | identical |
| fenced-tildes | 557.08 [539.43-598.50] | 52.60 [51.60-54.67] | 10.59x | 10.29-10.77x | identical |
| preformatted-code | 557.58 [541.56-591.44] | 52.32 [49.42-101.32] | 10.66x | 10.36-11.04x | identical |
| references-full | 562.58 [521.62-633.68] | 52.56 [49.12-100.65] | 10.70x | 10.28-10.95x | identical |
| references-collapsed | 559.29 [521.54-665.50] | 52.58 [50.80-92.98] | 10.64x | 10.04-11.45x | identical |
| references-shortcut | 551.15 [521.55-581.74] | 51.32 [49.70-91.46] | 10.74x | 10.47-10.86x | identical |
| emphasis-markers | 554.58 [541.61-595.20] | 50.96 [48.49-52.70] | 10.88x | 10.86-10.89x | identical |
| custom-breaks | 547.40 [530.31-581.08] | 50.82 [48.31-53.81] | 10.77x | 10.47-10.84x | identical |
| combined | 554.71 [522.92-599.26] | 52.22 [48.68-94.53] | 10.62x | 10.17-11.18x | identical |

## The Rust Programming Language

[Source](https://doc.rust-lang.org/book/print.html); 1,877,626 bytes; fetched 2026-09-09T09:51:16+00:00.
Input SHA-256: `40837ff83377df4ee0044a205ae82b0b4d1020143d02c9332c10afb008803c21`.

| Profile | JS median [p10-p90] ms | Python median [p10-p90] ms | Speedup | Round range | Output |
| --- | ---: | ---: | ---: | ---: | --- |
| default | 2471.94 [2367.13-2521.21] | 231.67 [216.31-247.81] | 10.67x | 10.26-11.09x | identical |
| atx-headings | 2438.36 [2392.65-2527.57] | 229.80 [209.41-597.52] | 10.61x | 9.94-11.26x | identical |
| bullet-minus | 2451.24 [2388.61-2531.28] | 224.41 [212.32-260.49] | 10.92x | 10.65-11.23x | identical |
| bullet-plus | 2464.56 [2378.81-2550.39] | 231.60 [216.69-531.84] | 10.64x | 10.07-10.62x | identical |
| fenced-backticks | 2410.17 [2322.76-2466.57] | 234.90 [219.46-444.81] | 10.26x | 10.26-10.38x | identical |
| fenced-tildes | 2416.69 [2350.18-2492.01] | 235.64 [226.71-437.81] | 10.26x | 10.22-10.35x | identical |
| preformatted-code | 2473.22 [2386.70-2646.53] | 213.50 [197.63-539.12] | 11.58x | 10.81-12.50x | identical |
| references-full | 2461.83 [2392.28-2496.22] | 226.85 [216.89-445.57] | 10.85x | 10.77-10.92x | identical |
| references-collapsed | 2386.25 [2304.69-2453.50] | 235.81 [214.66-596.03] | 10.12x | 9.98-10.45x | identical |
| references-shortcut | 2423.11 [2263.40-2475.16] | 227.24 [214.18-555.87] | 10.66x | 10.39-10.75x | identical |
| emphasis-markers | 2465.88 [2380.73-2671.55] | 233.86 [220.92-262.07] | 10.54x | 10.53-10.98x | identical |
| custom-breaks | 2456.19 [2358.64-2532.36] | 227.49 [217.38-253.97] | 10.80x | 10.27-11.25x | identical |
| combined | 2318.07 [2221.43-2404.41] | 217.27 [205.86-426.45] | 10.67x | 10.56-10.93x | identical |

## Option profiles

Unspecified options use upstream defaults. Every profile is run on every page.

```json
{
  "default": {},
  "atx-headings": {
    "headingStyle": "atx"
  },
  "bullet-minus": {
    "bulletListMarker": "-"
  },
  "bullet-plus": {
    "bulletListMarker": "+"
  },
  "fenced-backticks": {
    "codeBlockStyle": "fenced"
  },
  "fenced-tildes": {
    "codeBlockStyle": "fenced",
    "fence": "~~~"
  },
  "preformatted-code": {
    "preformattedCode": true
  },
  "references-full": {
    "linkStyle": "referenced",
    "linkReferenceStyle": "full"
  },
  "references-collapsed": {
    "linkStyle": "referenced",
    "linkReferenceStyle": "collapsed"
  },
  "references-shortcut": {
    "linkStyle": "referenced",
    "linkReferenceStyle": "shortcut"
  },
  "emphasis-markers": {
    "emDelimiter": "*",
    "strongDelimiter": "__"
  },
  "custom-breaks": {
    "hr": "---",
    "br": "\\"
  },
  "combined": {
    "headingStyle": "atx",
    "bulletListMarker": "-",
    "codeBlockStyle": "fenced",
    "fence": "~~~",
    "preformattedCode": true,
    "linkStyle": "referenced",
    "linkReferenceStyle": "full",
    "emDelimiter": "*",
    "strongDelimiter": "__",
    "hr": "---",
    "br": "\\"
  }
}
```

## Reproduce

Install the project and run `npm ci` for the optional JavaScript reference, as described in [Development](../DEVELOPMENT.md). Use the saved snapshots with their recorded hashes:

```sh
PYTHONPATH=src python scripts/benchmark.py --rounds 3 --samples 7 --warmups 5 --seed 20260909
```

Snapshots are excluded from version control. Download URLs are in sources.json; live pages may change, so a fresh download needs new hashes and represents a new corpus.
