# Rust-owned replays and lazy event access

Normal `.osr` parsing performs full header validation, LZMA decompression, and
numeric event decoding in Rust, then returns one native `Replay` object. No
Python field values, enum conversions, or event wrappers are created on that
path. The Rust storage owns its strings and decoded vectors independently of
the input file or Python byte buffer.

Reading a header field creates and caches its Python value. Reading
`replay.replay_data` creates a `ReplayData` sequence over the Rust vector.
`len(data)` needs no event wrappers. Indexing or iteration creates wrappers on
demand and caches them, so repeated access returns the same object and mutations
remain visible. Retained views survive deletion of the parent replay.

## Compatibility and materialization

`GameMode`, `Mod`, `Key`, `KeyTaiko`, and `KeyMania` remain the original Python
`Enum`/`IntFlag` classes. Getters return their actual singleton members, including
combinations and unknown masks. Python 3.10's signed negative flags and newer
Python's normalization are both preserved by the native writer.

`ReplayData` implements mutable-sequence operations, including indexing,
slicing, insertion, deletion, append/extend, sorting, comparison, and copying.
It is **not a built-in list**. Structural edits promote it to a backing Python
list. Cached event objects are reused, so references held before an insertion
or deletion still refer to the same events. `list(data)` provides an explicit
ordinary list when an external API requires one.

`vars(replay)` and instance dataclass introspection (`fields`, `asdict`,
`replace`) materialize replay fields and replace `replay.replay_data` with the
backing list. Earlier `ReplayData` aliases continue to delegate to that same
list. This adapter preserves standard-library dataclass behavior without
patching `dataclasses`. Class-level metadata inspection stays lazy.

Events preserve dictionary edits, dataclass helpers, subclassing, weakrefs,
pickle, deepcopy, and cyclic garbage collection. Numeric fields initially live
in Rust; edits and dictionary inspection promote an individual event to Python
state. Serialization combines edited views with untouched native frames.
Unusual numeric spellings, arbitrary-size integers, and non-finite values use
the compatibility decoder and may materialize Python values eagerly. Errors
retain the existing Python exception classes.

## Native layout and serialization

- `rust/storage.rs` owns decoded headers and vectors and implements fully native
  encoding for unchanged headers/events. Header reads and unchanged event views
  do not disable this path. Mutable lifebar exposure or header edits use the
  compatibility header writer; unchanged events still serialize natively.
- `rust/sequence.rs` implements lazy views, caches, list promotion, iteration,
  and copy/pickle/GC support. `rust/replay.rs` implements native field access and
  the dataclass adapter's materialization boundary.
- `rust/events.rs` parses checked integers and floats into Rust frames.
- `rust/formatting.rs` uses Ryu with Python's decimal/exponent notation and
  rounding, including a regression for a tie where Rust's default debug output
  differs from Python. Native packing creates neither field caches nor event
  wrappers for untouched replays.
- `rust/codec.rs` handles checked reads and complete LZMA streams. Its bounded
  initial output-buffer estimate can grow; it does not impose a truncating
  output-size cap. Compression and full native decoding release the GIL.

The fixed 23-byte score/count/mod block uses `zerocopy` with little-endian,
alignment-one numeric fields. Borrowed header views and native writes are
checked by derived layout traits. Variable-length strings are validated and
owned as Rust strings. LZMA-compressed text cannot be cast directly into event
structs: decompression and numeric conversion remain necessary. Avoiding eager
Python allocations is the main architectural gain; no large speedup is attributed
solely to `zerocopy`. Own Rust code forbids unsafe code.

## Validation and benchmarks

The previously committed tests remain unchanged. The 193-test suite passes on
CPython 3.10–3.14 on Linux; ten Rust tests pass on Rust 1.85 and 1.97. Additional
coverage checks
lazy allocation, event/sequence aliases after edits, native packing without
materialization, malformed inputs, negative flags across Python versions,
float formatting, cyclic references, and iterator exhaustion.

Benchmarks separately measure full decoding with lazy Python exposure, parsing
plus one event read, parsing plus reading every event field, and native packing.
They compare against independently frozen Python codec **and model** classes.
The 10× parse speedup is a measured target, not a guarantee for every game mode
or machine; see [the results](../benchmarks/README.md), including full-field costs.

Builds use uv and Maturin, pinned Rust 1.97, and a tested minimum Rust 1.85.
GitHub Actions covers Python 3.10–3.14 on Linux, macOS, and Windows, Rust checks,
docs, distributions, and installed wheels. Local validation covers Linux;
hosted macOS/Windows jobs must pass before release. No packages are published
by this change. Native dependency notices ship in `THIRD_PARTY_LICENSES.md`.

Existing format quirks remain: zero RNG seeds are omitted on packing, empty
lifebars normalize to None, `perfect` is an integer when decoded, legacy
non-minimal string lengths remain, and four-byte replay IDs are accepted.
