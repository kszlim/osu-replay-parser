# Native codec benchmarks

Measured on Linux x86_64 with CPython 3.13.5 and a Rust release build.
The baseline is commit `17d2315b4934bc9da14e6965211444b16ad4affd`,
loaded from the frozen Python codec in test support.

| Mode | Python parse (ms) | Rust parse (ms) | Parse speedup | Python pack (ms) | Rust pack (ms) | Pack speedup |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Standard | 16.890 | 6.083 | 2.78× | 66.410 | 50.635 | 1.31× |
| Taiko | 11.244 | 3.544 | 3.17× | 32.219 | 24.027 | 1.34× |
| Catch | 7.441 | 3.451 | 2.16× | 26.880 | 18.229 | 1.47× |
| Mania | 10.883 | 3.286 | 3.31× | 30.490 | 22.980 | 1.33× |

Reproduce from the repository root:

```sh
uv sync --locked
uv run maturin develop --release
uv run python benchmarks/compare.py --iterations 30 --repeats 7
```

Each result is the median of seven samples, with 30 operations per sample.
Engine order alternates between samples; both engines use the same interpreter
and input bytes. Timings include Python object construction and destruction,
with garbage collection enabled, and exclude disk reads. Fixture fields and
packed bytes are checked for equality before measuring.

The command fails if any mode parses less than 1.5× faster or packing regresses.
Hosted CI records timings without enforcing hardware-sensitive speed thresholds.
These are measurements on one machine, not guaranteed speedups on every system.

[results.json](results.json) contains every sample, fixture hashes, interpreter
and platform information, extension and source hashes, and Python allocation
peaks. `tracemalloc` does not include Rust/liblzma allocations or total process
RSS; those figures must not be interpreted as total memory usage.

The original 1,000-replay benchmark in `tests/test_benchmark.py` is unchanged
and still runs as part of the full test suite.
