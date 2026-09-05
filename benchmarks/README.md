# Native event benchmarks

Measured on Linux x86_64 with CPython 3.13.5 and Rust release builds. The
Python baseline is commit `17d2315b4934bc9da14e6965211444b16ad4affd`. Both its
codec and model classes are frozen: it does not use the new native event classes.

| Mode | Python parse (ms) | Native parse (ms) | Parse speedup | Python pack (ms) | Native pack (ms) | Pack speedup |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Standard | 16.484 | 3.717 | 4.44× | 66.295 | 47.822 | 1.39× |
| Taiko | 11.235 | 1.974 | 5.69× | 31.448 | 23.840 | 1.32× |
| Catch | 7.318 | 2.220 | 3.30× | 26.291 | 18.022 | 1.46× |
| Mania | 10.988 | 2.070 | 5.31× | 30.026 | 22.084 | 1.36× |

Reproduce from the repository root:

```sh
uv sync --locked
uv run maturin develop --release
uv run python benchmarks/compare.py --iterations 30 --repeats 7
```

Medians of seven samples, 30 operations per sample, with alternating engine
order, garbage collection enabled, and file reads excluded. Full parsing includes
construction and destruction of the returned event objects; header-only parsing
is not used. Field values and packed bytes are checked before measuring.

The default command requires at least a 3× parsing speedup in every mode and no
packing regression. Hosted CI records timings with thresholds disabled to avoid
hardware-dependent failures. Measurements on this machine are not guarantees
for every system.

[results.json](results.json) contains every sample, fixture and source hashes,
interpreter/platform information, and extension hashes. Python allocation peaks
exclude Rust/liblzma allocations and total RSS. [previous-port-results.json](previous-port-results.json)
preserves the measurements for commit `62236fa`, before native event storage.

## Comparison with rust3

A separate comparison used CPython 3.10.19, the same fixture bytes, release
builds, and seven alternating samples of 30 full parses. `rust3` refers to
`origin/rust3` at commit `da0dcc3`; its public facade includes conversion from
Rust vectors into a Python list of native event objects.

| Mode | This native API (ms) | rust3 public API (ms) |
| --- | ---: | ---: |
| Standard | 4.318 | 2.745 |
| Taiko | 2.611 | 1.188 |
| Catch | 2.494 | 1.839 |
| Mania | 2.655 | 1.085 |

[rust3-comparison.json](rust3-comparison.json) retains the samples. This API
preserves Python enum identity, live dictionaries, dataclass helpers, subclassing,
pickle/copy behavior, and cyclic GC. The older branch does not provide the same
contract; its packing property test uses the Python decoder, and native header
fields use incorrect signed widths for some valid values. Its speed remains a
useful comparison, with those compatibility differences recorded.

The original `tests/test_benchmark.py` remains unchanged and runs with the full
suite.
