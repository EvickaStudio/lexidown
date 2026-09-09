"""Compare Turndown output and warm conversion times on saved web HTML."""

import argparse
import hashlib
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

from lexidown import __turndown_version__, __version__, _native

ROOT = Path(__file__).resolve().parent.parent
PROFILES = {
    "default": {},
    "atx-headings": {"headingStyle": "atx"},
    "bullet-minus": {"bulletListMarker": "-"},
    "bullet-plus": {"bulletListMarker": "+"},
    "fenced-backticks": {"codeBlockStyle": "fenced"},
    "fenced-tildes": {"codeBlockStyle": "fenced", "fence": "~~~"},
    "preformatted-code": {"preformattedCode": True},
    "references-full": {"linkStyle": "referenced", "linkReferenceStyle": "full"},
    "references-collapsed": {
        "linkStyle": "referenced",
        "linkReferenceStyle": "collapsed",
    },
    "references-shortcut": {
        "linkStyle": "referenced",
        "linkReferenceStyle": "shortcut",
    },
    "emphasis-markers": {"emDelimiter": "*", "strongDelimiter": "__"},
    "custom-breaks": {"hr": "---", "br": "\\"},
    "combined": {
        "headingStyle": "atx",
        "bulletListMarker": "-",
        "codeBlockStyle": "fenced",
        "fence": "~~~",
        "preformattedCode": True,
        "linkStyle": "referenced",
        "linkReferenceStyle": "full",
        "emDelimiter": "*",
        "strongDelimiter": "__",
        "hr": "---",
        "br": "\\",
    },
}


def worker_sample(worker, request):
    worker.stdin.write(json.dumps(request) + "\n")
    worker.stdin.flush()
    line = worker.stdout.readline()
    if not line:
        raise RuntimeError("Benchmark worker exited without a result")
    result = json.loads(line)
    if "error" in result:
        raise RuntimeError(f"{result['error']}: {result['message']}")
    return result


def summarize(samples):
    ordered = sorted(samples)

    def percentile(fraction):
        position = (len(ordered) - 1) * fraction
        lower = int(position)
        upper = min(lower + 1, len(ordered) - 1)
        return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)

    return {
        "samples_ms": samples,
        "median_ms": statistics.median(samples),
        "p10_ms": percentile(0.1),
        "p90_ms": percentile(0.9),
        "min_ms": min(samples),
        "max_ms": max(samples),
    }


def first_difference(expected, actual):
    expected = expected.decode("utf-8")
    actual = actual.decode("utf-8")
    index = next(
        (
            i
            for i, (left, right) in enumerate(zip(expected, actual, strict=False))
            if left != right
        ),
        min(len(expected), len(actual)),
    )
    return {
        "character_offset": index,
        "javascript": expected[max(0, index - 30) : index + 60],
        "python": actual[max(0, index - 30) : index + 60],
    }


def combine_rounds(row):
    rounds = row["rounds"]
    for engine in ("javascript", "python"):
        row[engine] = summarize(
            [sample for run in rounds for sample in run[engine]["samples_ms"]]
        )
    hashes = {
        value
        for run in rounds
        for values in run["output_sha256"].values()
        for value in values
    }
    row["equal"] = all(run["equal"] for run in rounds)
    row["stable"] = len(hashes) == 1 and all(run["stable"] for run in rounds)
    row["speedup"] = row["javascript"]["median_ms"] / row["python"]["median_ms"]
    row["round_speedups"] = [run["speedup"] for run in rounds]
    row["output_bytes"] = rounds[0]["output_bytes"]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def javascript_reference():
    """Resolve the optional npm reference only when running a JS comparison."""
    result = subprocess.run(
        [
            "node",
            "-p",
            "JSON.stringify({path: require.resolve('turndown'), "
            "version: require('turndown/package.json').version})",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def measured_sources():
    paths = [
        path
        for path in (ROOT / "src/lexidown").iterdir()
        if path.suffix in {".py", ".pyx", ".pxi", ".pxd"}
    ]
    paths.extend(path for path in (ROOT / "vendor/lexbor").rglob("*") if path.is_file())
    paths.extend(
        ROOT / name
        for name in (
            "setup.py",
            "pyproject.toml",
            "package.json",
            "package-lock.json",
            "scripts/benchmark.py",
            "scripts/benchmark_python.py",
            "scripts/benchmark_js.cjs",
        )
    )
    return {str(path.relative_to(ROOT)): sha256(path) for path in sorted(paths)}


def report_markdown(report):
    rows = report["results"]
    valid = [row for row in rows if row["equal"] and row["stable"]]
    defaults = [row for row in valid if row["profile"] == "default"]
    speedups = [row["speedup"] for row in valid]
    default_speedups = [row["speedup"] for row in defaults]
    lines = [
        "# Compiled Python versus JavaScript Turndown",
        "",
        f"Run: {report['run_at_utc']} to {report['finished_at_utc']}.",
        "",
        f"**{len(valid)}/{len(rows)} page/profile combinations produced identical, stable output.**",
        "",
    ]
    if speedups:
        lines.extend(
            [
                f"Across the {len(report['sources'])} default-option pages, the geometric-mean speedup is "
                f"**{statistics.geometric_mean(default_speedups):.2f}x**; "
                f"**{sum(value >= 2 for value in default_speedups)}/{len(defaults)}** reach 2x. "
                f"Across all matching page/profile combinations, speedup ranges from "
                f"**{min(speedups):.2f}x to {max(speedups):.2f}x**; "
                f"**{sum(value >= 2 for value in speedups)}/{len(valid)}** reach 2x.",
                "",
                "Speedup is JavaScript median / compiled Python median: greater than 1 means "
                "Python is faster. Counts use medians, not every individual sample. "
                "A result below 2x remains in the report. These pages were selected before timing.",
                "",
            ]
        )
    lines.extend(
        [
            "## Default options",
            "",
            "Times are pooled medians in milliseconds. Round range uses the separate "
            "process-round median ratios. Profile range covers all 13 option profiles.",
            "",
            "| Page | HTML KiB | JS ms | Python ms | Speedup | Round range | Profile range |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for source in report["sources"]:
        page_rows = [row for row in rows if row["source"] == source["id"]]
        default = next(row for row in page_rows if row["profile"] == "default")
        factors = [row["speedup"] for row in page_rows]
        rounds = default["round_speedups"]
        match = "" if default["equal"] and default["stable"] else " (OUTPUT DIFFERS)"
        lines.append(
            f"| [{source['id']}]({source['url']}){match} | {source['bytes'] / 1024:.1f} | "
            f"{default['javascript']['median_ms']:.2f} | {default['python']['median_ms']:.2f} | "
            f"{default['speedup']:.2f}x | {min(rounds):.2f}-{max(rounds):.2f}x | "
            f"{min(factors):.2f}-{max(factors):.2f}x |"
        )
    lines.extend(
        [
            "",
            "## Method",
            "",
            f"Python {report['python_version']}; Node {report['node_version']}; "
            f"V8 {report['v8_version']}; {report['cpu_model']}; {report['platform']}.",
            "",
            f"Both converters implement Turndown {report['javascript_turndown_version']}. "
            f"Python uses the compiled Cython engine and bundled Lexbor {report['lexbor_version']} "
            "with compatibility patches. Only these two implementations are measured.",
            "",
            f"{report['round_count']} independent rounds each start fresh worker processes. "
            f"Each page/profile has {report['warmups']} warmups and {report['samples']} timed "
            f"conversions per round: {report['round_count'] * report['samples']} recorded samples "
            "per engine per combination. Both workers remain alive within a round, but "
            "run conversions serially. Engine order alternates for paired samples; "
            f"page/profile order is shuffled per round using seed {report['seed']}. "
            "Raw order and timing samples are saved in results.json.",
            "",
            "Timers include fresh service construction, parsing the complete HTML, whitespace "
            "normalization and returning the Markdown string. File/network access, imports, "
            "process startup, output encoding/hashing and byte comparisons are outside the "
            "timer. Input HTML is cached, converted output is never cached, and both engines "
            "use normal garbage collection. Previous result strings are released outside "
            "the next timer. This measures warm returned-string wall time, not cold startup, "
            "total CPU cost, memory usage, or concurrent throughput.",
            "",
            "Both engines receive the same complete saved UTF-8 HTML. First measured outputs "
            "are compared byte for byte in every round. All measured hashes must agree within "
            "and across engines and rounds. A speedup with differing output is not a valid "
            "compatibility result. Source/input and actual worker binary/bundle hashes are "
            "recorded and verified at the end.",
            "",
            "p10-p90 below describes the sample spread, not a confidence interval. The "
            "process rounds are the independent repeats; samples within one process and "
            "profiles of one page are correlated. Several profiles produce the same output "
            "on a given page. The default-page summary avoids counting those as additional sites. "
            "Measurements describe this machine and corpus, not a constant speedup for all HTML.",
            "",
            f"System load averages before/after: {report['load_average_start']} / "
            f"{report['load_average_end']}. No other builds or benchmark jobs were started during measurement.",
            "",
        ]
    )
    for source in report["sources"]:
        page_rows = [row for row in rows if row["source"] == source["id"]]
        lines.extend(
            [
                f"## {source['title']}",
                "",
                f"[Source]({source['url']}); {source['bytes']:,} bytes; fetched {source['fetched_at_utc']}.",
                f"Input SHA-256: `{source['sha256']}`.",
                "",
                "| Profile | JS median [p10-p90] ms | Python median [p10-p90] ms | Speedup | Round range | Output |",
                "| --- | ---: | ---: | ---: | ---: | --- |",
            ]
        )
        for row in page_rows:
            js, py = row["javascript"], row["python"]
            rounds = row["round_speedups"]
            match = "identical" if row["equal"] and row["stable"] else "DIFFERENT"
            lines.append(
                f"| {row['profile']} | {js['median_ms']:.2f} [{js['p10_ms']:.2f}-{js['p90_ms']:.2f}] | "
                f"{py['median_ms']:.2f} [{py['p10_ms']:.2f}-{py['p90_ms']:.2f}] | "
                f"{row['speedup']:.2f}x | {min(rounds):.2f}-{max(rounds):.2f}x | {match} |"
            )
        lines.append("")
    lines.extend(
        [
            "## Option profiles",
            "",
            "Unspecified options use upstream defaults. Every profile is run on every page.",
            "",
            "```json",
            json.dumps(PROFILES, indent=2),
            "```",
            "",
            "## Reproduce",
            "",
            "Install the project and run npm ci for the optional JavaScript reference, "
            "as described in DEVELOPMENT.md. "
            "Use the saved snapshots with their recorded hashes:",
            "",
            "```sh",
            f"PYTHONPATH=src python scripts/benchmark.py --rounds {report['round_count']} "
            f"--samples {report['samples']} --warmups {report['warmups']} --seed {report['seed']}",
            "```",
            "",
            "Snapshots are excluded from version control. Download URLs are in sources.json; "
            "live pages may change, so a fresh download needs new hashes and represents a new corpus.",
            "",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--samples", type=int, default=7)
    parser.add_argument("--warmups", type=int, default=5)
    parser.add_argument("--seed", type=int, default=20260909)
    args = parser.parse_args()
    if args.rounds < 1 or args.samples < 1 or args.warmups < 0:
        parser.error("rounds/samples must be positive and warmups nonnegative")
    reference = javascript_reference()
    javascript_bundle = Path(reference["path"])
    sources = json.loads((ROOT / "benchmarks/sources.json").read_text())
    for source in sources:
        path = ROOT / source["path"]
        if sha256(path) != source["sha256"]:
            raise ValueError(f"Input changed since download: {path}")
    cpuinfo = Path("/proc/cpuinfo")
    cpu_model = platform.processor() or "unknown CPU"
    if cpuinfo.exists():
        cpu_model = next(
            (
                line.split(":", 1)[1].strip()
                for line in cpuinfo.read_text().splitlines()
                if line.startswith("model name")
            ),
            cpu_model,
        )
    report = {
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "cpu_model": cpu_model,
        "logical_cpus": os.cpu_count(),
        "load_average_start": os.getloadavg() if hasattr(os, "getloadavg") else None,
        "round_count": args.rounds,
        "warmups": args.warmups,
        "samples": args.samples,
        "seed": args.seed,
        "javascript_turndown_version": reference["version"],
        "python_package": "lexidown",
        "python_package_version": __version__,
        "python_turndown_version": __turndown_version__,
        "lexbor_version": (ROOT / "vendor/lexbor/version")
        .read_text()
        .strip()
        .split("=")[-1],
        "native_binary_sha256": sha256(Path(_native.__file__)),
        "javascript_bundle_sha256": sha256(javascript_bundle),
        "source_sha256": measured_sources(),
        "sources": sources,
        "execution_order": [],
        "workers": [],
        "results": [],
    }
    by_case = {}
    for source in sources:
        for name, options in PROFILES.items():
            row = {
                "source": source["id"],
                "profile": name,
                "options": options,
                "rounds": [],
            }
            report["results"].append(row)
            by_case[(source["id"], name)] = row
    cases = [(source, name) for source in sources for name in PROFILES]
    result_path = ROOT / "benchmarks/results.json"
    markdown_path = ROOT / "benchmarks/REPORT.md"
    engines = ("javascript", "python")
    with tempfile.TemporaryDirectory(prefix="turndown-benchmark-") as scratch:
        output_paths = {engine: Path(scratch) / f"{engine}.md" for engine in engines}
        for round_index in range(args.rounds):
            order = cases.copy()
            random.Random(args.seed + round_index).shuffle(order)
            report["execution_order"].append(
                [[source["id"], name] for source, name in order]
            )
            identities = {}
            with ExitStack() as processes:
                workers = {}
                for engine in engines:
                    command = (
                        ["node", str(ROOT / "scripts/benchmark_js.cjs")]
                        if engine == "javascript"
                        else [sys.executable, str(ROOT / "scripts/benchmark_python.py")]
                    )
                    workers[engine] = processes.enter_context(
                        subprocess.Popen(
                            command,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            text=True,
                            encoding="utf-8",
                            env=dict(os.environ, PYTHONPATH=str(ROOT / "src")),
                        )
                    )
                try:
                    for case_index, (source, name) in enumerate(order):
                        row = by_case[(source["id"], name)]
                        request = {
                            "path": str(ROOT / source["path"]),
                            "options": row["options"],
                        }
                        timings = {engine: [] for engine in engines}
                        hashes = {engine: set() for engine in engines}
                        for iteration in range(-args.warmups, args.samples):
                            offset = (round_index + case_index + iteration) % 2
                            for engine in engines[offset:] + engines[:offset]:
                                if iteration == 0:
                                    request["output_path"] = str(output_paths[engine])
                                else:
                                    request.pop("output_path", None)
                                sample = worker_sample(workers[engine], request)
                                if engine == "javascript":
                                    if (
                                        sample["bundle_sha256"]
                                        != report["javascript_bundle_sha256"]
                                    ):
                                        raise RuntimeError(
                                            "Worker imported a different JavaScript bundle"
                                        )
                                    report["node_version"] = sample["node_version"]
                                    report["v8_version"] = sample["v8_version"]
                                    identities[engine] = {
                                        key: sample[key]
                                        for key in (
                                            "bundle_path",
                                            "bundle_sha256",
                                            "node_version",
                                            "v8_version",
                                        )
                                    }
                                else:
                                    if (
                                        Path(sample["package_path"])
                                        != (ROOT / "src/lexidown").resolve()
                                        or sample["native_binary_sha256"]
                                        != report["native_binary_sha256"]
                                    ):
                                        raise RuntimeError(
                                            "Worker imported a different Python engine"
                                        )
                                    identities[engine] = {
                                        key: sample[key]
                                        for key in (
                                            "package_path",
                                            "native_binary_path",
                                            "native_binary_sha256",
                                        )
                                    }
                                if iteration >= 0:
                                    timings[engine].extend(sample["samples_ms"])
                                    hashes[engine].add(sample["output_sha256"])
                        expected = output_paths["javascript"].read_bytes()
                        actual = output_paths["python"].read_bytes()
                        run = {
                            "round": round_index + 1,
                            "javascript": summarize(timings["javascript"]),
                            "python": summarize(timings["python"]),
                            "equal": expected == actual,
                            "stable": len(set.union(*hashes.values())) == 1,
                            "output_sha256": {
                                engine: sorted(values)
                                for engine, values in hashes.items()
                            },
                            "output_bytes": {
                                "javascript": len(expected),
                                "python": len(actual),
                            },
                        }
                        run["speedup"] = (
                            run["javascript"]["median_ms"] / run["python"]["median_ms"]
                        )
                        if expected != actual:
                            run["first_difference"] = first_difference(expected, actual)
                        row["rounds"].append(run)
                        combine_rounds(row)
                        match = (
                            "equal" if run["equal"] and run["stable"] else "DIFFERENT"
                        )
                        print(
                            f"Round {round_index + 1}/{args.rounds} {case_index + 1}/{len(order)} "
                            f"{source['id']} / {name}: JS {run['javascript']['median_ms']:.2f} ms, "
                            f"Python {run['python']['median_ms']:.2f} ms, "
                            f"speedup {run['speedup']:.2f}x; {match}",
                            flush=True,
                        )
                finally:
                    for worker in workers.values():
                        worker.stdin.close()
            report["workers"].append(identities)
            report["completed_rounds"] = round_index + 1
            result_path.write_text(json.dumps(report, indent=2) + "\n")
    if report["source_sha256"] != measured_sources():
        raise RuntimeError("Measured source changed during benchmark")
    if sha256(Path(_native.__file__)) != report["native_binary_sha256"]:
        raise RuntimeError("Native binary changed during benchmark")
    if sha256(javascript_bundle) != report["javascript_bundle_sha256"]:
        raise RuntimeError("JavaScript bundle changed during benchmark")
    for source in sources:
        if sha256(ROOT / source["path"]) != source["sha256"]:
            raise RuntimeError("Benchmark input changed during measurement")
    report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    report["load_average_end"] = os.getloadavg() if hasattr(os, "getloadavg") else None
    report["artifacts_unchanged"] = True
    result_path.write_text(json.dumps(report, indent=2) + "\n")
    markdown_path.write_text(report_markdown(report))
    matches = sum(row["equal"] and row["stable"] for row in report["results"])
    print(
        f"{matches}/{len(report['results'])} profiles identical and stable; {markdown_path}"
    )
    return 0 if matches == len(report["results"]) else 1


if __name__ == "__main__":
    sys.exit(main())
