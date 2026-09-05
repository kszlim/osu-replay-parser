# Native replay data with Python enum identity

The PyO3 extension parses events into typed Rust vectors and creates native
`ReplayEventOsu`, `ReplayEventTaiko`, `ReplayEventCatch`, and `ReplayEventMania`
objects directly. Numeric fields stay in Rust, and normal parsing bypasses
Python dataclass initializers for events. `replay_data` remains a mutable
Python list, with stable references to its native event objects.

`GameMode`, `Mod`, `Key`, `KeyTaiko`, and `KeyMania` remain the original Python
`Enum`/`IntFlag` classes. Header conversion calls those classes once per field;
event conversion resolves each distinct key mask once per parse and shares the
resulting enum member. Getters return that same object. This supports:

```python
replay.mode is GameMode.STD
replay.mods is Mod.NoMod
frame.keys is Key.K1
frame.keys is (Key.M1 | Key.K1)
```

This follows `origin/rust3`'s native event-storage approach while preserving
Python enum singletons, correct unsigned header widths, signed replay IDs,
error handling, and packing compatibility.

## Storage and compatibility

- `rust/events.rs` parses the common event stream into native scalar fields,
  handles all four modes and sentinel frames, and releases the interpreter lock.
  Unusual integer spellings, arbitrary-size integers, non-finite floats, and
  malformed input use the compatibility decoder in Rust bindings, preserving Python conversions
  and exception classes instead of dropping data.
- `rust/models.rs` defines native event types with real base-class inheritance,
  weak references, and garbage collection support. Numeric fields stay in Rust
  until accessed. An edit or dictionary inspection promotes an event's fields
  to a live Python dictionary; later getters, setters, and packing use that
  dictionary. `vars(event)["x"] = value` remains an effective edit.
- `osrparse/utils.py` retains the Python enums and installs the existing
  dataclass constructors, signatures, annotations, equality, repr, matching
  metadata, and serialization helpers on the native event classes. Python
  construction and Hypothesis inference work normally. Parsing skips these
  Python initializers and allocates native objects directly.
- `rust/codec.rs` provides checked binary reads, string encoding, exact integer
  timestamps, and LZMA transport. liblzma is statically linked via the `liblzma`
  crate, which follows the binding used by `rust3`. Compression options and
  byte-for-byte output are checked against the Python implementation.
- `rust/bindings.rs` joins the codec to the public objects, preserves enum
  identity, and serializes edited events. Python numeric formatting preserves
  wire text. Base64 decoding uses the standard library's permissive decoder.
- `Replay` and `LifeBarState` retain Python dataclass storage. File/path methods
  remain small Python adapters and preserve ownership of caller-provided streams.

Own Rust code forbids unsafe code. There is no Python replay-codec fallback in
installed wheels. Native dependency notices ship in `THIRD_PARTY_LICENSES.md`.

## Evidence and release scope

The original tests and the 111-test codec compatibility suite remain unchanged.
The expanded 147-test suite passes on CPython 3.10–3.14 on Linux, and seven Rust
unit tests pass on Rust 1.85 and 1.97. Clippy, formatting, and docs checks pass.
Additional tests cover enum identity for every game mode, individual keys,
combinations, unknown/negative masks, arbitrary-size masks, round trips,
pickling, copying, dictionary mutation, subclasses, cyclic references, and the
absence of Python event initializer calls during common parsing.

`tests/reference/python_replay.py` is the unchanged codec from baseline commit
`17d2315`. Differential tests exercise that algorithm against the current public
models. Benchmarks separately load the frozen Python model classes as well, so
native constructors cannot inflate the measured Python baseline. Raw samples
and prior-port results are retained under `benchmarks/`.

Builds use Maturin through uv, with Cargo.lock and uv.lock checked in. Development
uses pinned Rust 1.97, and the declared minimum is Rust 1.85. CI covers Python
3.10–3.14 on Linux, macOS, and Windows, plus Rust checks, docs, builds, installed
wheels, and benchmark artifacts. Local validation covers Linux. Hosted macOS
and Windows results are required before a release; this work does not publish
packages. Stable-ABI, free-threaded, PyPy, and GraalPy support are not claimed.

Existing codec quirks remain unchanged: zero RNG seeds are omitted when packing,
empty lifebars normalize to None, `perfect` is read as an integer, legacy
non-minimal string lengths are preserved, and four-byte replay IDs are accepted.

See [benchmark results](../benchmarks/README.md) for measured performance.
