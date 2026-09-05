"""Compare release-native and frozen Python codecs on the same interpreter.

Run from the repository root with `uv run python benchmarks/compare.py` after
`uv run maturin develop --release`. Timings alternate engine order, include
object construction, exclude file I/O, and use median per-operation latency.
"""

from __future__ import annotations

import argparse
import dataclasses
import gc
import hashlib
import json
import platform
import statistics
import subprocess
import sys
import time
import tracemalloc
from enum import Enum
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from osrparse import Replay, ReplayData, _native  # noqa: E402
from tests.reference.baseline import Replay as PythonReplay  # noqa: E402


def canonical(value):
    if isinstance(value, Enum):
        return type(value).__name__, value.value
    if dataclasses.is_dataclass(value):
        return {
            field.name: canonical(getattr(value, field.name))
            for field in dataclasses.fields(value)
        }
    if isinstance(value, (list, ReplayData)):
        return [canonical(item) for item in value]
    return value


def read_fields(replay, mode, one=False):
    data = replay.replay_data
    count = 0
    checksum = 0.0
    entries = (data[-1],) if one and len(data) else data
    for event in entries:
        count += 1
        checksum += event.time_delta
        if mode == 0:
            checksum += event.x + event.y + event.keys.value
        elif mode == 1:
            checksum += event.x + event.keys.value
        elif mode == 2:
            checksum += event.x + event.dashing
        else:
            checksum += event.keys.value
    return count, checksum


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
    parser.add_argument("--min-parse-speedup", type=float, default=3.0)
    parser.add_argument("--min-pack-speedup", type=float, default=1.0)
    parser.add_argument("--target-parse-speedup", type=float, default=10.0)
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
        "target_parse_speedup": args.target_parse_speedup,
        "parse_work": "Full decompression and event decoding; Python field/event wrappers remain lazy",
        "read_all_work": "Parse then read every event field into a Python checksum",
        "fixtures": {},
        "source_sha256": {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in [
                *sorted((ROOT / "rust").glob("*.rs")),
                ROOT / "Cargo.lock",
                ROOT / "Cargo.toml",
                ROOT / "osrparse/_model.py",
                ROOT / "osrparse/replay.py",
                ROOT / "osrparse/utils.py",
                ROOT / "tests/reference/baseline.py",
                ROOT / "tests/reference/python_replay.py",
                ROOT / "tests/reference/python_utils.py",
                Path(__file__).resolve(),
            ]
        },
    }
    for filename in ["replay.osr", "taiko.osr", "ctb.osr", "mania.osr"]:
        data = (ROOT / "tests/resources" / filename).read_bytes()
        python_replay = PythonReplay.from_string(data)
        native_replay = Replay.from_string(data)
        assert canonical(python_replay) == canonical(native_replay)
        assert python_replay.pack() == native_replay.pack()
        # Validation introspects the object and therefore materializes it.
        # Pack timing must use a fresh, untouched native replay.
        native_replay = Replay.from_string(data)
        mode = data[0]

        def python_parse():
            return PythonReplay.from_string(data)

        def native_parse():
            return Replay.from_string(data)

        def python_read_one():
            return read_fields(python_parse(), mode, one=True)

        def native_read_one():
            return read_fields(native_parse(), mode, one=True)

        def python_read_all():
            return read_fields(python_parse(), mode)

        def native_read_all():
            return read_fields(native_parse(), mode)

        assert native_read_all() == python_read_all()
        assert native_read_one() == python_read_one()
        parse = compare(python_parse, native_parse, args.iterations, args.repeats)
        read_one = compare(
            python_read_one, native_read_one, args.iterations, args.repeats
        )
        read_all = compare(
            python_read_all, native_read_all, args.iterations, args.repeats
        )
        pack = compare(
            python_replay.pack, native_replay.pack, args.iterations, args.repeats
        )
        assert native_replay._cached_event_count == 0
        report["fixtures"][filename] = {
            "sha256": hashlib.sha256(data).hexdigest(),
            "events": len(native_replay.replay_data),
            "parse": parse,
            "pack": pack,
            "parse_and_read_one": read_one,
            "parse_and_read_all": read_all,
            "target_met": parse["speedup"] >= args.target_parse_speedup,
            "cached_views_after_pack": native_replay._cached_event_count,
            "parse_peak_python_bytes": {
                "python": peak_python_bytes(python_parse),
                "native": peak_python_bytes(native_parse),
                "note": "tracemalloc measures Python allocations, not Rust/liblzma allocations or total RSS",
            },
        }
        print(
            f"{filename}: parse {parse['speedup']:.2f}x, one event {read_one['speedup']:.2f}x, "
            f"all fields {read_all['speedup']:.2f}x, pack {pack['speedup']:.2f}x",
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
