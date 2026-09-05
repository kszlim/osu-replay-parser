# Lazy native replay benchmarks

Both engines fully decompress and decode the replay. The native engine retains
Rust-owned data and creates Python event wrappers only when accessed. The Python
baseline is the independently frozen codec and models from commit `17d2315`.

## Python 3.13.5

| Mode | Python parse ms | Native parse ms | Parse speedup | Parse + one event | Parse + all event fields | Pack speedup |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Standard | 16.435 | 2.615 | 6.29× | 5.96× | 2.10× | 1.69× |
| Taiko | 11.336 | 1.058 | 10.72× | 10.76× | 2.04× | 1.68× |
| Catch | 7.383 | 1.747 | 4.23× | 4.35× | 1.98× | 1.76× |
| Mania | 10.863 | 1.025 | 10.60× | 10.72× | 2.10× | 1.70× |

[Raw samples and source hashes](results.json).

## Python 3.10.19

| Mode | Python parse ms | Native parse ms | Parse speedup | Parse + one event | Parse + all event fields | Pack speedup |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Standard | 26.791 | 2.665 | 10.05× | 10.12× | 2.93× | 1.95× |
| Taiko | 21.383 | 1.063 | 20.12× | 20.25× | 2.77× | 2.10× |
| Catch | 11.319 | 1.735 | 6.52× | 6.42× | 2.74× | 2.05× |
| Mania | 20.624 | 1.068 | 19.31× | 19.04× | 2.86× | 2.24× |

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

## Historical measurements

- [Eager native-event port](native-events-results.json), commit `4e2da52`.
- [Earlier codec-only port](previous-port-results.json), commit `62236fa`.
- [Historical rust3 comparison](rust3-comparison.json), before this lazy-storage change.

The original `tests/test_benchmark.py` remains unchanged and runs with the suite.
