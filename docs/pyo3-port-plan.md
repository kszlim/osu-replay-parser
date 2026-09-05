# PyO3 port plan

## Goal and baseline

Move all replay decoding and encoding into Rust exposed through PyO3, with no
changes, deletions, skips, or weakened assertions in existing tests. Preserve
the public `osrparse`, `osrparse.replay`, `osrparse.utils`, and
`osrparse.strategies` imports. This document is a plan; no Rust implementation
has been introduced yet.

The modernization baseline supports CPython 3.10–3.14. There are 17 original
tracked test cases, a pre-existing untracked 1,000-replay benchmark, and nine
new timestamp cases (27 total locally). Capture the eventual baseline commit,
test node IDs, fixture hashes, Python versions, and lockfile before porting.
Use that baseline as the oracle, including its integer timestamp fix.

Passing these tests is necessary but cannot prove every downstream use remains
compatible. Expand characterization coverage before replacing code. Never
hide native import failures with an automatic fallback in native test jobs.

## Architecture and tooling

Use a mixed Maturin package with extension `osrparse._native`, a Rust codec
crate independent of Python, and a PyO3 binding crate. Keep public Python module
paths as re-export/compatibility modules. Initially retain the current Python
codec as a test oracle, loaded independently rather than through production
dispatch. Remove it from shipped runtime code after parity is established.

Use the stable PyO3 release (0.29.2 at planning time), a compatible stable
Maturin 1.x release, and Rust edition 2024 with an explicitly tested MSRV of at
least 1.85. Pin the selected toolchain and commit Cargo.lock. Recheck versions
at implementation time. PyO3's own current minimum is Rust 1.83; edition 2024
raises this project's proposed floor.

Keep uv for locking, environments, commands, and `uv build`. When adding the
extension, change only the PEP 517 backend from `uv_build` to Maturin:
`uv_build` currently builds pure Python packages only. Configure
`[tool.maturin]` with `module-name = "osrparse._native"` and `python-source = "."`.
Include `.pyi` files and `py.typed` once the complete public API has accurate
typing. Use `uv run maturin develop --release` for native development and
`uv build` for distribution checks.

## Compatibility contract

| Surface | Required behavior and characterization |
| --- | --- |
| Imports and identity | Same exports, version metadata, module paths, and identical class objects across re-exports; pickle compatibility. |
| Public models | Positional/keyword constructors, field order and annotations, mutable fields and lists, equality, repr, unhashability, inheritance, subclassing, `__dict__`, weak references, dataclass introspection/replace/asdict, and pattern matching. |
| Enums and flags | Actual `Enum`/`IntFlag` semantics, singleton identity (`mode is GameMode.STD`), bitwise operations, combinations and unknown/negative bits. |
| Hypothesis | Existing `builds`, `from_type`, and `replays()` work without changing original tests or narrowing their generated domains. Event integers may exceed Rust fixed-width types. |
| Entry points | `from_path`, `from_file`, `from_string`, `parse_replay_data`, `pack`, `write_path`, and `write_file` retain signatures, keyword-only options, return types, and file ownership. Preserve bytes paths, PathLike, bytearray input, and duck-typed binary file objects. |
| Binary format | Little-endian widths/signs, both string markers, UTF-8 byte lengths and existing ULEB128 output, life bars, legacy four-byte replay IDs, and ignored trailing data. |
| Event stream | All four modes, initial sentinel frames only in the first two positions, terminal RNG frame only at the end, no trailing comma in some lazer streams, and CTB dashing only for key value 1. |
| Timestamps | UTC-aware results, exact integer tick packing, half-even rounding below one microsecond, full datetime range, offsets, and the existing local-time interpretation of naive inputs. |
| Compression | Base64 input routes, LZMA FORMAT_AUTO decoding and FORMAT_ALONE/LZMA1 writing, `dict_size`/`mode` defaults including falsey inputs, Unicode/ASCII handling. |
| Errors | Characterize exception classes for truncated headers, bad markers/UTF-8/base64/LZMA, invalid modes/events, out-of-range fields and I/O failures. Preserve established classes and useful messages; do not expose panics. |

Known baseline quirks need explicit fixtures: zero RNG seeds are currently
omitted on packing; empty life bars normalize to None; empty event streams
fail to parse; `perfect` is parsed as an integer; ULEB128 output can be
non-minimal. Do not silently repair these during the port. Track fixes
separately with intentional API/format decisions. The current property test
does not compare RNG seeds, so passing it alone is insufficient.

## Ordered implementation steps

1. **Freeze and characterize the Python oracle.** Add all public entry-point,
   model, enum, error, and edge-case tests described above. Exercise Unicode,
   zero and missing seeds, flag combinations, integer boundaries, special
   floats, every compression option, and repeated edit/write/read cycles.
   Record fixture results and benchmark distributions on a fixed machine.
   Gate: original suite unchanged and green; new behavior fixtures reproducible.

2. **Land extension scaffolding.** Add Cargo workspace, binding module, Maturin
   metadata, stubs, and a native import/build smoke test. Continue using Python
   for production parsing at this stage. Test editable installs, wheel imports
   outside the checkout, and rebuilding wheels from the sdist.
   Gate: all baseline tests pass through the same public imports.

3. **Port event decoding.** Implement an independent Rust cursor/event codec,
   sentinel handling, and four game modes. Return existing Python dataclasses
   initially, with real Python enums and Python lists. Avoid narrowing arbitrary
   Python event integers to i64; choose big integers or an equivalent exact
   representation where required. Compare full event lists and RNG seeds
   against the oracle for fixtures and generated inputs, including malformed
   streams. Preserve Python numeric parsing behavior where Rust differs.
   Gate: both implementations pass the unchanged suite and differential tests.

4. **Port complete replay decoding.** Add checked binary reads, string lengths,
   UTF-8, header/lifebar parsing, integer timestamps, ID fallback and base64/LZMA
   decoding. Initially calling Python's LZMA implementation from bindings is a
   useful intermediate checkpoint. Select and validate a Rust/liblzma-backed
   implementation before declaring native codec completion; assess wheel
   linking, licenses and availability on all target platforms. Map failures
   deliberately to the existing Python exception classes.
   Gate: identical full public objects and error classes across both engines.

5. **Port encoding and file APIs.** Implement field validation, Python-compatible
   numeric text formatting, ULEB128, timestamp/lifebar/event serialization and
   LZMA settings. Compare uncompressed wire bytes to the oracle, then decode
   both outputs with both implementations. Compare compressed bytes with the
   same liblzma version/settings; if a codec changes output bytes, document and
   approve that deviation independently of semantic round-trip success.
   Keep Python path/file protocol calls at the boundary and never close a
   caller-owned handle. Gate: original packing property passes without changing
   its timestamp tolerance, plus generated cross-engine round trips.

6. **Resolve public class compatibility and finish the native runtime.** Treat
   direct replacement of dataclasses by `#[pyclass]` as its own prototype:
   properties/getters alone do not preserve dataclass or Hypothesis behavior.
   Prove the entire model contract before switching. Preserve real Python
   `Enum`/`IntFlag` objects instead of replacing them with Rust enum lookalikes.
   If native storage cannot satisfy dataclass semantics, keep thin Python
   dataclass definitions with every codec operation in Rust. That is a complete
   native codec but not a literal all-classes Rust port; report this distinction
   and do not claim the latter is complete. A literal port must supply and test
   compatible dataclass metadata, constructors, mutation, inheritance and
   introspection, possibly creating Python-compatible types from module init.
   `osrparse.strategies` remains Python test support in either case.
   Gate: no lost introspection, identity, mutation or generated-test behavior.

7. **Optimize and ship only after parity.** Release the interpreter while
   processing owned Rust data; reacquire it to construct/access Python objects.
   Benchmark parsing, packing, object allocation and peak memory separately,
   using release builds. The existing benchmark only prints elapsed time and
   has no performance assertion. Choose a speed/memory budget from measured
   baseline results rather than inventing a speedup promise. Remove the shipped
   Python codec only after native-required CI passes and keep the oracle in
   test tooling or an archived baseline checkout for regression comparison.

## CI and release gates

Run the unchanged suite on every supported Python version on Linux, macOS and
Windows for both the baseline and native implementations in isolated processes.
Use fixed Hypothesis seeds in PR jobs and larger rotating-seed runs on a GitHub
Actions schedule. Run Rust unit/property tests, `cargo fmt --check`, and Clippy;
fuzz malformed binary and event inputs for panics and unchecked reads.

Build Linux manylinux/musllinux, macOS and Windows wheels for the architectures
actually selected for release. Start with ordinary CPython-specific wheels;
evaluate `abi3-py310` only after the chosen APIs and dependencies pass the full
matrix. Free-threaded Python and alternative interpreters require separate
validation and wheel decisions before any support claim. Test each installed
wheel outside the checkout, without Rust installed, and test an sdist build
with the documented toolchain. Verify bundled native library dependencies.

Release acceptance requires all baseline node IDs executed, zero failures or
new skips/xfails, passing added characterization/differential tests, build and
install validation, documented benchmark results, and no Python codec fallback
in production. Keep the previous release available for rollback; do not publish
until the distribution matrix passes. Plan a major release if full class or
interpreter compatibility proves impossible instead of weakening the tests.

## Sources

- [Stable PyO3 guide](https://pyo3.rs/v0.29.2/)
- [Rust 1.85 and edition 2024](https://blog.rust-lang.org/2025/02/20/Rust-1.85.0/)
- [PyO3 Python classes](https://pyo3.rs/v0.29.2/class.html)
- [Maturin mixed project layout](https://www.maturin.rs/project_layout.html)
- [uv build backend and extension limitation](https://docs.astral.sh/uv/concepts/build-backend/)
- [uv in GitHub Actions](https://docs.astral.sh/uv/guides/integration/github/)
