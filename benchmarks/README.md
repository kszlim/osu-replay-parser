# Lazy native replay benchmarks

Both engines fully decompress and decode the replay. The native engine retains
Rust-owned data and creates Python event wrappers only when accessed. The Python
baseline is the independently frozen codec and models from commit `17d2315`.

## Python 3.13.5

| Mode | Python parse ms | Native parse ms | Parse speedup | Parse + one event | Parse + all event fields | Pack speedup |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Standard | 17.101 | 2.680 | 6.38× | 5.93× | 2.20× | 1.65× |
| Taiko | 11.747 | 1.057 | 11.12× | 10.72× | 2.10× | 1.71× |
| Catch | 7.334 | 1.764 | 4.16× | 4.23× | 2.00× | 1.77× |
| Mania | 10.861 | 0.998 | 10.89× | 10.75× | 2.20× | 1.71× |

[Raw samples and source hashes](results.json).

## Python 3.10.19

| Mode | Python parse ms | Native parse ms | Parse speedup | Parse + one event | Parse + all event fields | Pack speedup |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Standard | 26.206 | 2.596 | 10.10× | 10.22× | 2.99× | 1.89× |
| Taiko | 22.285 | 1.037 | 21.48× | 20.15× | 2.95× | 2.09× |
| Catch | 10.998 | 1.718 | 6.40× | 6.60× | 2.85× | 2.07× |
| Mania | 19.692 | 1.012 | 19.45× | 19.45× | 3.00× | 2.16× |

[Raw samples and source hashes](results-python310.json).

The 10× parse target is reached for Taiko and Mania on Python 3.13, and for
Standard, Taiko, and Mania on Python 3.10. Catch remains below the target. Full
Python field access still incurs event-wrapper and scalar-conversion costs.
These measurements do not establish a universal 10× speedup.

## Reproduction and interpretation

```sh
uv sync --locked
uv run maturin develop --release
uv run python benchmarks/compare.py --iterations 30 --repeats 7
```

Run on Linux x86_64 with release builds, medians of seven alternating samples,
and 30 operations per sample. Garbage collection is enabled. File reads are
excluded. Parse-only includes full event decoding and destruction of the returned
replay. Read-one accesses the final event; read-all consumes every event field
into a matching Python checksum. Packing uses an untouched native replay after
separate semantic validation, and asserts that zero event wrappers are created.

Every workload is validated against the frozen Python result. Raw reports include
fixture, source, and extension hashes. Python allocation peaks exclude native
Rust/liblzma allocations and total process RSS.

The 10× target is recorded per fixture. The command separately enforces a 3×
parse regression floor and no packing regression; hosted CI disables those
hardware-sensitive thresholds while retaining the measurements.

`zerocopy` is used for the fixed-width binary score block. The main speedup comes
from Rust-owned storage and lazy Python exposure. Compressed ASCII events still
require decompression and numeric conversion.

Earlier implementation reports remain in Git history at `62236fa`, `4e2da52`,
and `e686efb`. The frozen Python oracle is isolated under `tests/reference/`.

The original `tests/test_benchmark.py` remains unchanged and runs with the suite.
