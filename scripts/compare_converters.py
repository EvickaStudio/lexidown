"""Compare converter defaults on the saved corpus; different output is expected."""

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import random
import statistics
import subprocess
import sys
import tempfile
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from lexidown import _native

from .benchmark import (
    ROOT,
    javascript_reference,
    measured_sources,
    sha256,
    summarize,
    worker_sample,
)

ENGINES = {
    "javascript": ("Turndown JS", "turndown", "new TurndownService().turndown(html)"),
    "python": ("Lexidown", "lexidown", "TurndownService().turndown(html)"),
    "html2text": ("html2text", "html2text", "html2text.html2text(html)"),
    "markdownify": ("markdownify", "markdownify", "markdownify.markdownify(html)"),
    "markdownify-lxml": (
        "markdownify + lxml",
        "markdownify",
        "markdownify.markdownify(html, bs4_options='lxml')",
    ),
    "html-to-markdown": (
        "html-to-markdown",
        "html-to-markdown",
        "convert(html).content",
    ),
    "html-to-markdown-no-metadata": (
        "html-to-markdown, no metadata",
        "html-to-markdown",
        "convert(html, ConversionOptions(extract_metadata=False)).content",
    ),
    "fast-h2m": ("fast-h2m", "fast-h2m", "convert_to_markdown(html)"),
}


def competitor_worker(name):
    if name == "html2text":
        import html2text as module

        convert = module.html2text
    elif name.startswith("markdownify"):
        import markdownify as module

        if name == "markdownify-lxml":

            def convert(html):
                return module.markdownify(html, bs4_options="lxml")

        else:
            convert = module.markdownify
    elif name.startswith("html-to-markdown"):
        import html_to_markdown as module

        if name == "html-to-markdown-no-metadata":

            def convert(html):
                return module.convert(
                    html, module.ConversionOptions(extract_metadata=False)
                ).content

        else:

            def convert(html):
                return module.convert(html).content

    else:
        import fast_h2m as module

        convert = module.convert_to_markdown
    identity = {
        "distribution": ENGINES[name][1],
        "version": importlib.metadata.version(ENGINES[name][1]),
        "module_path": module.__file__,
        "python_version": platform.python_version(),
    }
    inputs = {}
    for line in sys.stdin:
        try:
            request = json.loads(line)
            path = request["path"]
            if path not in inputs:
                inputs[path] = Path(path).read_bytes().decode("utf-8")
            html = inputs[path]
            start = perf_counter()
            output = convert(html)
            elapsed = (perf_counter() - start) * 1000
            encoded = output.encode("utf-8")
            if "output_path" in request:
                Path(request["output_path"]).write_bytes(encoded)
            result = {
                "samples_ms": [elapsed],
                "output_sha256": hashlib.sha256(encoded).hexdigest(),
                "output_bytes": len(encoded),
                **identity,
            }
            del output, encoded
        except Exception as error:
            result = {"error": type(error).__name__, "message": str(error)}
        print(json.dumps(result), flush=True)


def combine_rounds(row):
    row["engines"] = {}
    for name in row["rounds"][0]["engines"]:
        runs = [run["engines"][name] for run in row["rounds"]]
        hashes = {value for run in runs for value in run["output_sha256"]}
        row["engines"][name] = {
            **summarize([value for run in runs for value in run["samples_ms"]]),
            "output_sha256": sorted(hashes),
            "stable": len(hashes) == 1,
            "equal_to_javascript": all(run["equal_to_javascript"] for run in runs),
            "output_bytes": runs[0]["output_bytes"],
            "round_medians_ms": [run["median_ms"] for run in runs],
        }
    baseline = row["engines"]["javascript"]
    for values in row["engines"].values():
        values["speedup_over_javascript"] = baseline["median_ms"] / values["median_ms"]
        values["round_speedups_over_javascript"] = [
            left / right
            for left, right in zip(
                baseline["round_medians_ms"], values["round_medians_ms"], strict=True
            )
        ]


def source_manifest():
    return {
        **measured_sources(),
        **{
            name: sha256(ROOT / name)
            for name in (
                "scripts/compare_converters.py",
                "benchmarks/requirements.txt",
                "benchmarks/comparison-example.json",
            )
        },
    }


def binary_manifest(javascript_bundle):
    paths = {Path(_native.__file__), javascript_bundle}
    for distribution in importlib.metadata.distributions():
        paths.update(
            Path(distribution.locate_file(path))
            for path in distribution.files or []
            if str(path).endswith((".so", ".pyd", ".dll"))
        )
    return {str(path.resolve()): sha256(path) for path in sorted(paths)}


def report_markdown(report):
    names = list(ENGINES)
    rows = report["results"]
    lines = [
        "# HTML-to-Markdown converter comparison",
        "",
        f"Run: {report['run_at_utc']} to {report['finished_at_utc']}.",
        "",
        "All converters receive the same complete HTML. Their defaults produce different "
        "Markdown and may retain different content; timing is not a quality or equivalence score.",
        "",
        "## Median conversion time",
        "",
        "Milliseconds; lower is faster. Medians pool all measured process rounds.",
        "",
        "| Page | " + " | ".join(ENGINES[name][0] for name in names) + " |",
        "| --- | " + " | ".join("---:" for _ in names) + " |",
    ]
    for row, source in zip(rows, report["sources"], strict=True):
        lines.append(
            f"| [{row['source']}]({source['url']}) | "
            + " | ".join(f"{row['engines'][name]['median_ms']:.2f}" for name in names)
            + " |"
        )
    lines.extend(
        [
            "",
            "## Versions and configurations",
            "",
            "Project documentation: [html2text](https://pypi.org/project/html2text/2025.4.15/), "
            "[markdownify and parser options](https://pypi.org/project/markdownify/1.2.3/), "
            "[html-to-markdown](https://pypi.org/project/html-to-markdown/3.12.2/), "
            "and [fast-h2m](https://pypi.org/project/fast-h2m/0.4.2/). "
            "The latter two use Rust native cores; fast-h2m is a fork of html-to-markdown. "
            "markdownify uses BeautifulSoup with html.parser by default; its lxml variant "
            "still runs the Markdown conversion in Python. These are selected libraries "
            "and configurations, not an exhaustive ranking of all available converters.",
            "",
            "Speed ratio is JavaScript median / converter median, then the geometric mean "
            "across the eight pages. Greater than 1 means faster than JavaScript. "
            "Exact matches compare the first measured output bytes in every process round; "
            "every measured output is also hashed to check stability.",
            "",
            "| Converter | Version | Call inside timer | Speed ratio | Exact JS matches |",
            "| --- | --- | --- | ---: | ---: |",
        ]
    )
    for name, (label, distribution, call) in ENGINES.items():
        values = [row["engines"][name] for row in rows]
        version = report["versions"][distribution]
        ratio = statistics.geometric_mean(v["speedup_over_javascript"] for v in values)
        matches = sum(v["equal_to_javascript"] for v in values)
        lines.append(
            f"| {label} | {version} | `{call}` | {ratio:.2f}x | {matches}/{len(rows)} |"
        )
    lines.extend(
        [
            "",
            "## Output sizes",
            "",
            "UTF-8 bytes, not a quality score. The two html-to-markdown configurations time "
            "their complete calls, but only compare the returned Markdown content; metadata "
            "returned separately is not included in these sizes.",
            "",
            "| Page | " + " | ".join(ENGINES[name][0] for name in names) + " |",
            "| --- | " + " | ".join("---:" for _ in names) + " |",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row['source']} | "
            + " | ".join(str(row["engines"][name]["output_bytes"]) for name in names)
            + " |"
        )
    lines.extend(
        [
            "",
            "## Method and reproduction",
            "",
            "The [small example and exact outputs](comparison-example.json) illustrate "
            "the semantic differences: Turndown preserves script/style text and flattens "
            "tables by default. The other tested converters omit that script/style text "
            "and render Markdown tables. Heading, emphasis, code-fence, metadata and "
            "newline conventions also differ. html-to-markdown's default result includes "
            "metadata work and frontmatter; its separate no-metadata configuration disables "
            "extraction. No input cleaning or output normalization was applied. "
            "All six competitor configurations differ from Turndown on every corpus page; "
            "this does not by itself indicate an error or worse Markdown.",
            "",
            f"Python {report['python_version']}; Node {report['workers'][0]['javascript']['node_version']}; "
            f"{report['cpu_model']}; {report['platform']}.",
            "",
            f"{report['round_count']} fresh-process rounds, {report['warmups']} warmups and "
            f"{report['samples']} measured conversions per page/engine in each round. "
            "Page order is shuffled per round; engine order rotates per iteration. "
            "Conversions run serially with normal garbage collection. Timing includes a fresh "
            "converter/options where the API constructs them, parsing, and Markdown conversion. "
            "Imports, process startup, HTML reads, hashing, and output encoding/writing are excluded. "
            "Only input HTML is cached. Previous outputs are released outside the next timer.",
            "",
            "This measures warm returned-string wall time, not cold startup, memory, "
            "concurrent throughput, or total CPU cost. Independent repeats are process "
            "rounds; samples within each round are correlated. Results describe this "
            "machine and corpus, not a constant speedup for arbitrary HTML.",
            "",
            f"System load averages before/after: {report['load_average_start']} / "
            f"{report['load_average_end']}.",
            "",
            "Raw samples, p10/p90 spread, separate round medians and ratios, package versions, "
            "worker identities, binary/source hashes, and snapshot hashes are in "
            "[comparison-results.json](comparison-results.json). These are sample spreads, "
            "not confidence intervals. All input, source, and binary hashes were checked again "
            "at completion. The original 13-profile Turndown compatibility run remains in "
            "[REPORT.md](REPORT.md).",
            "",
            "```bash",
            "PYTHONPATH=src python -m scripts.compare_converters "
            f"--rounds {report['round_count']} --samples {report['samples']} "
            f"--warmups {report['warmups']} --seed {report['seed']}",
            "```",
            "",
            "Install the comparison-only dependencies documented in DEVELOPMENT.md first. "
            "Snapshots are excluded from version control; sources.json records URLs and hashes. "
            "A fresh download may change the corpus and requires new hashes.",
            "",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", choices=list(ENGINES)[2:])
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--samples", type=int, default=7)
    parser.add_argument("--warmups", type=int, default=5)
    parser.add_argument("--seed", type=int, default=20260909)
    args = parser.parse_args()
    if args.worker:
        competitor_worker(args.worker)
        return
    if args.rounds < 1 or args.samples < 1 or args.warmups < 0:
        parser.error("rounds/samples must be positive and warmups nonnegative")
    reference = javascript_reference()
    javascript_bundle = Path(reference["path"])
    sources = json.loads((ROOT / "benchmarks/sources.json").read_text())
    for source in sources:
        if sha256(ROOT / source["path"]) != source["sha256"]:
            raise ValueError(f"Input changed since download: {source['path']}")
    cpuinfo = Path("/proc/cpuinfo")
    cpu_model = platform.processor()
    if cpuinfo.exists():
        cpu_model = next(
            line.split(":", 1)[1].strip()
            for line in cpuinfo.read_text().splitlines()
            if line.startswith("model name")
        )
    versions = {
        distribution.metadata["Name"]: distribution.version
        for distribution in importlib.metadata.distributions()
    }
    versions["turndown"] = reference["version"]
    report = {
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "cpu_model": cpu_model,
        "logical_cpus": os.cpu_count(),
        "load_average_start": os.getloadavg() if hasattr(os, "getloadavg") else None,
        "round_count": args.rounds,
        "samples": args.samples,
        "warmups": args.warmups,
        "seed": args.seed,
        "versions": dict(sorted(versions.items())),
        "source_sha256": source_manifest(),
        "binary_sha256": binary_manifest(javascript_bundle),
        "sources": sources,
        "execution_order": [],
        "workers": [],
        "results": [{"source": source["id"], "rounds": []} for source in sources],
    }
    rows = {row["source"]: row for row in report["results"]}
    result_path = ROOT / "benchmarks/comparison-results.json"
    names = list(ENGINES)
    try:
        with tempfile.TemporaryDirectory(prefix="turndown-comparison-") as scratch:
            output_paths = {name: Path(scratch) / f"{name}.md" for name in names}
            for round_index in range(args.rounds):
                order = sources.copy()
                random.Random(args.seed + round_index).shuffle(order)
                report["execution_order"].append([source["id"] for source in order])
                identities = {}
                report["workers"].append(identities)
                with ExitStack() as processes:
                    workers = {}
                    for name in names:
                        if name == "javascript":
                            command = ["node", str(ROOT / "scripts/benchmark_js.cjs")]
                        elif name == "python":
                            command = [
                                sys.executable,
                                str(ROOT / "scripts/benchmark_python.py"),
                            ]
                        else:
                            command = [
                                sys.executable,
                                "-m",
                                "scripts.compare_converters",
                                "--worker",
                                name,
                            ]
                        workers[name] = processes.enter_context(
                            subprocess.Popen(
                                command,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                text=True,
                                encoding="utf-8",
                                cwd=ROOT,
                                env=dict(os.environ, PYTHONPATH=str(ROOT / "src")),
                            )
                        )
                    try:
                        for case_index, source in enumerate(order):
                            timings = {name: [] for name in names}
                            hashes = {name: set() for name in names}
                            for iteration in range(-args.warmups, args.samples):
                                offset = (round_index + case_index + iteration) % len(
                                    names
                                )
                                for name in names[offset:] + names[:offset]:
                                    request = {
                                        "path": str(ROOT / source["path"]),
                                        "options": {},
                                    }
                                    if iteration == 0:
                                        request["output_path"] = str(output_paths[name])
                                    try:
                                        sample = worker_sample(workers[name], request)
                                    except Exception as error:
                                        raise RuntimeError(
                                            f"{name}, {source['id']}, round {round_index + 1}, "
                                            f"iteration {iteration}: {error}"
                                        ) from error
                                    identity = {
                                        key: value
                                        for key, value in sample.items()
                                        if key
                                        not in {
                                            "samples_ms",
                                            "output_sha256",
                                            "output_bytes",
                                        }
                                    }
                                    if (
                                        name in identities
                                        and identity != identities[name]
                                    ):
                                        raise RuntimeError(
                                            f"Worker identity changed: {name}"
                                        )
                                    identities[name] = identity
                                    if name == "javascript":
                                        actual = sample["bundle_sha256"]
                                        expected = report["binary_sha256"][
                                            str(javascript_bundle.resolve())
                                        ]
                                    elif name == "python":
                                        actual = sample["native_binary_sha256"]
                                        expected = report["binary_sha256"][
                                            str(Path(_native.__file__).resolve())
                                        ]
                                        if (
                                            Path(sample["package_path"])
                                            != (ROOT / "src/lexidown").resolve()
                                        ):
                                            raise RuntimeError(
                                                "Worker imported a different Python package"
                                            )
                                    else:
                                        actual = sample["version"]
                                        expected = versions[ENGINES[name][1]]
                                    if actual != expected:
                                        raise RuntimeError(
                                            f"Worker imported a different engine: {name}"
                                        )
                                    if iteration >= 0:
                                        timings[name].extend(sample["samples_ms"])
                                        hashes[name].add(sample["output_sha256"])
                            expected = output_paths["javascript"].read_bytes()
                            run = {"round": round_index + 1, "engines": {}}
                            for name in names:
                                actual = output_paths[name].read_bytes()
                                run["engines"][name] = {
                                    **summarize(timings[name]),
                                    "output_sha256": sorted(hashes[name]),
                                    "output_bytes": len(actual),
                                    "equal_to_javascript": actual == expected,
                                }
                            row = rows[source["id"]]
                            row["rounds"].append(run)
                            combine_rounds(row)
                            result_path.write_text(json.dumps(report, indent=2) + "\n")
                            if not row["engines"]["python"]["equal_to_javascript"]:
                                raise RuntimeError(
                                    f"Turndown output differs: {source['id']}"
                                )
                            if not all(
                                values["stable"] for values in row["engines"].values()
                            ):
                                raise RuntimeError(
                                    f"Unstable converter output: {source['id']}"
                                )
                            print(
                                f"Round {round_index + 1}/{args.rounds} {case_index + 1}/{len(order)} "
                                f"{source['id']}: "
                                + ", ".join(
                                    f"{name} {run['engines'][name]['median_ms']:.2f} ms"
                                    for name in names
                                ),
                                flush=True,
                            )
                    finally:
                        for worker in workers.values():
                            worker.stdin.close()
                report["completed_rounds"] = round_index + 1
        if source_manifest() != report["source_sha256"]:
            raise RuntimeError("Measured source changed during benchmark")
        if binary_manifest(javascript_bundle) != report["binary_sha256"]:
            raise RuntimeError("Measured binary changed during benchmark")
        for source in sources:
            if sha256(ROOT / source["path"]) != source["sha256"]:
                raise RuntimeError(f"Input changed during benchmark: {source['id']}")
        report["artifacts_unchanged"] = True
        report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        report["load_average_end"] = (
            os.getloadavg() if hasattr(os, "getloadavg") else None
        )
    except Exception as error:
        report["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        result_path.write_text(json.dumps(report, indent=2) + "\n")
    markdown_path = ROOT / "benchmarks/COMPARISON.md"
    markdown_path.write_text(report_markdown(report))
    print(f"Completed {len(sources)} pages x {len(names)} engines; {markdown_path}")


if __name__ == "__main__":
    main()
