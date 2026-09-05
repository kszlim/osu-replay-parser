# Rust replay codec

The PyO3 extension `osrparse._native` handles binary reads/writes, replay-event
parsing and serialization, timestamp conversion, lifebars, and LZMA transport.
There is no Python replay codec fallback in the installed package.

Public dataclasses and enums remain Python objects. This preserves constructor
signatures, `isinstance`, equality, mutation, subclassing, pickle, weakrefs,
dataclass introspection, and Hypothesis type inference. File and path methods
remain small Python adapters, so caller-owned streams retain their ordinary
Python behavior. This is a native codec with a Python-compatible object model,
not a replacement of every public class by a Rust `#[pyclass]`.

## Implementation

- `rust/codec.rs`: checked, borrowed binary cursor; exact integer tick rounding;
  legacy string encoding; LZMA-alone compression and auto/concatenated decoding.
  It has no Python dependency and has native unit tests.
- `rust/bindings.rs`: public-object conversion, event parsing, and serialization.
  Rust enums select the event format, and a per-parse cache reuses Python key
  flags. Ordinary numbers parse in Rust; Python conversions handle arbitrary
  precision integers and unusual spellings. Python float formatting preserves
  byte-for-byte wire output. Base64 decoding uses the Python standard library
  at the API boundary to retain its permissive input and exception behavior.
- `osrparse/replay.py`: dataclass definition and adapters into the extension.
  `osrparse/utils.py` and `osrparse/strategies.py` keep their existing models and
  generators.

Own Rust code forbids unsafe code. Binary reads check bounds; conversion and
compression failures become Python exceptions. Compression and decompression
release the interpreter lock over immutable/owned data. Python object access
stays attached to the interpreter. liblzma is statically linked through xz2;
the top-level license remains MIT, and native dependency notices ship in
`THIRD_PARTY_LICENSES.md`.

## Compatibility and validation

The frozen Python oracle is the unmodified `osrparse/replay.py` from commit
`17d2315b4934bc9da14e6965211444b16ad4affd`, stored in test support. All baseline
test files are unchanged. The expanded suite has 111 tests and passes locally
on CPython 3.10, 3.11, 3.12, 3.13, and 3.14. All five Rust unit tests pass on
Rust 1.85 and 1.97; Clippy, formatting, and documentation checks pass. Added
tests compare every fixture field, exact packed
bytes, generated cross-engine round trips, all four modes, Unicode, huge
integers, options, stream concatenation, malformed/truncated input, file
ownership, dataclass behavior, and import identity.

Existing quirks remain explicit compatibility behavior: zero RNG seeds are
omitted when packing; empty lifebars normalize to None; the `perfect` field is
read as an integer; string lengths can have the old non-minimal encoding; and
legacy four-byte IDs remain supported. Timestamp behavior uses the exact integer
fix already present in the modernization baseline.

Builds use Maturin through uv, with Cargo.lock and uv.lock checked in. The
development toolchain is pinned to Rust 1.97; the crate declares Rust 1.85 as
its minimum (the native tests pass on both toolchains). Wheels are CPython-version-specific. Stable-ABI, free-threaded,
PyPy, and GraalPy support are not claimed by this migration.

GitHub Actions covers Python 3.10–3.14 on Linux, macOS, and Windows, plus Rust
checks, documentation, sdist-to-wheel builds, installed-wheel tests, and
benchmark artifacts. Local evidence covers Linux; hosted macOS/Windows jobs
must pass before release. This change does not publish packages or claim a
complete manylinux/musllinux/architecture wheel release matrix.

See [benchmark methodology and results](../benchmarks/README.md) for measured
performance, sample distributions, and allocation-measurement limits.
