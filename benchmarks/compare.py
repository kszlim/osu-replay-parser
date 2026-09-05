"""Compare release-native and frozen Python codecs on the same interpreter.

Run from the repository root with `uv run python benchmarks/compare.py` after
`uv run maturin develop --release`. Timings alternate engine order, include
object construction, exclude file I/O, and use median per-operation latency.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import platform
import statistics
import subprocess
import sys
import time
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from osrparse import Replay, _native  # noqa: E402
from tests.reference.python_replay import Replay as PythonReplay  # noqa: E402


def sample(function, iterations):
    gc.collect()
    start = time.perf_counter_ns()
    for _ in range(iterations):
        result = function()
        del result
    return (time.perf_counter_ns() - start) / iterations / 1_000_000


def peak_python_bytes(function):
    gc.collect()
    tracemalloc.start()
    result = function()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    del result
    return peak


def compare(python, native, iterations, repeats):
    for function in [python, native]:
        function()
    samples = {"python": [], "native": []}
    for repeat in range(repeats):
        engines = [("python", python), ("native", native)]
        if repeat % 2:
            engines.reverse()
        for name, function in engines:
            samples[name].append(sample(function, iterations))
    python_ms = statistics.median(samples["python"])
    native_ms = statistics.median(samples["native"])
    return {
        "python_ms": python_ms,
        "native_ms": native_ms,
        "speedup": python_ms / native_ms,
        "samples_ms": samples,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=30)
    parser.add_argument("--repeats", type=int, default=7)
    parser.add_argument("--output", type=Path, default=ROOT / "benchmarks/results.json")
    parser.add_argument("--min-parse-speedup", type=float, default=1.5)
    parser.add_argument("--min-pack-speedup", type=float, default=1.0)
    args = parser.parse_args()
    if args.iterations < 1 or args.repeats < 1:
        parser.error("iterations and repeats must be positive")
    report = {
        "baseline_commit": "17d2315b4934bc9da14e6965211444b16ad4affd",
        "working_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "working_tree_dirty": bool(
            subprocess.check_output(
                ["git", "status", "--porcelain"], cwd=ROOT, text=True
            )
        ),
        "python": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "native_extension": Path(_native.__file__).name,
        "native_sha256": hashlib.sha256(
            Path(_native.__file__).read_bytes()
        ).hexdigest(),
        "iterations": args.iterations,
        "repeats": args.repeats,
        "gc_enabled": gc.isenabled(),
        "fixtures": {},
        "source_sha256": {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in [
                *sorted((ROOT / "rust").glob("*.rs")),
                ROOT / "Cargo.lock",
                ROOT / "Cargo.toml",
                ROOT / "osrparse/replay.py",
            ]
        },
    }
    for filename in ["replay.osr", "taiko.osr", "ctb.osr", "mania.osr"]:
        data = (ROOT / "tests/resources" / filename).read_bytes()
        python_replay = PythonReplay.from_string(data)
        native_replay = Replay.from_string(data)
        assert vars(python_replay) == vars(native_replay)
        assert python_replay.pack() == native_replay.pack()

        def python_parse():
            return PythonReplay.from_string(data)

        def native_parse():
            return Replay.from_string(data)

        parse = compare(python_parse, native_parse, args.iterations, args.repeats)
        pack = compare(
            python_replay.pack, native_replay.pack, args.iterations, args.repeats
        )
        report["fixtures"][filename] = {
            "sha256": hashlib.sha256(data).hexdigest(),
            "events": len(native_replay.replay_data),
            "parse": parse,
            "pack": pack,
            "parse_peak_python_bytes": {
                "python": peak_python_bytes(python_parse),
                "native": peak_python_bytes(native_parse),
                "note": "tracemalloc measures Python allocations, not Rust/liblzma allocations or total RSS",
            },
        }
        print(
            f"{filename}: parse {parse['speedup']:.2f}x, pack {pack['speedup']:.2f}x",
            flush=True,
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    failures = [
        name
        for name, row in report["fixtures"].items()
        if row["parse"]["speedup"] < args.min_parse_speedup
    ]
    failures += [
        f"{name} (pack)"
        for name, row in report["fixtures"].items()
        if row["pack"]["speedup"] < args.min_pack_speedup
    ]
    if failures:
        raise SystemExit(
            f"Speedup below required parse {args.min_parse_speedup}x / pack {args.min_pack_speedup}x: {', '.join(failures)}"
        )


if __name__ == "__main__":
    main()
