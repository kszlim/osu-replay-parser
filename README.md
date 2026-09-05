[![PyPi version](https://badge.fury.io/py/osrparse.svg)](https://pypi.org/project/osrparse/)

# osrparse, a python parser for osu! replays

This is a parser for the ``.osr`` format for osu! replay files, as described by [the wiki](https://osu.ppy.sh/wiki/en/Client/File_formats/Osr_%28file_format%29).

## Installation

Requires Python 3.10 or newer (tested through Python 3.14).

Replays are decoded into Rust-owned headers and event vectors. `Replay` is a
lightweight PyO3 object, and `replay.replay_data` is a lazy `ReplayData` mutable
sequence. Event wrappers are created only when accessed. Game modes, mods, and
key flags remain Python enum singletons, so `replay.mode is GameMode.STD` works.

`ReplayData` is not a built-in list; use `list(replay.replay_data)` when one is
required. Dataclass introspection and structural edits materialize Python data
as needed, while preserving existing event references and edits.

To install:

```sh
python -m pip install osrparse
```

## Documentation

Please see the full documentation for a comprehensive guide: <https://kszlim.github.io/osu-replay-parser>. A quickstart follows below for the impatient, but you should read the full documentation if you are at all confused.

### Quickstart

```python
from osrparse import Replay, parse_replay_data
# parse from a path
replay = Replay.from_path("path/to/osr.osr")

# or from an opened file object
with open("path/to/osr.osr", "rb") as f:
    replay = Replay.from_file(f)

# or from bytes
with open("path/to/osr.osr", "rb") as f:
    replay_string = f.read()
replay = Replay.from_string(replay_string)

# a replay has various attributes
r = replay
print(r.mode, r.game_version, r.beatmap_hash, r.username,
    r.replay_hash, r.count_300, r.count_100, r.count_50,
    r.count_geki, r.count_miss, r.score, r.max_combo, r.perfect,
    r.mods, r.life_bar_graph, r.timestamp, r.replay_data,
    r.replay_id, r.rng_seed)

# parse the replay data from api v1's /get_replay endpoint
lzma_string = retrieve_from_api()
replay_data = parse_replay_data(lzma_string)
# replay_data is a list of ReplayEvents

# write a replay back to a path
replay.write_path("path/to/osr.osr")

# or to an opened file object
with open("path/to/osr.osr", "wb") as f:
    replay.write_file(f)

# or to bytes
packed = replay.pack()

# edited attributes are saved
replay.username = "fake username"
replay.write_path("path/to/new_osr.osr")
```

## Development

Install [uv](https://docs.astral.sh/uv/getting-started/installation/),
[Rust](https://rustup.rs/), and a C compiler, then run:

```sh
uv sync --locked
uv run maturin develop --release
uv run pytest -q
cargo test --locked
cargo fmt --check
cargo clippy --locked --all-targets -- -D warnings
uv run ruff check
uv run ruff format --check
uv run --group docs sphinx-build -W --keep-going -b html docs build/html
uv build
uv run twine check dist/*
uv run python benchmarks/compare.py
```

`uv.lock` pins development dependencies; `uv lock --upgrade` refreshes them.
The `dev` dependency group contains the test and release tools. The existing
`osrparse[dev]` extra remains available for consumers of the Hypothesis strategies.
The runtime package has no third-party Python dependencies. uv manages the
environment and invokes Maturin as the build backend for the PyO3 extension.
Cargo.lock pins Rust dependencies; rust-toolchain.toml pins the development
toolchain. liblzma is statically linked, so installed wheels do not need Rust
or a system liblzma. Source builds require Rust and a C compiler.
GitHub Actions runs the suite on Python 3.10–3.14 on Linux, macOS, and Windows,
and checks Rust formatting, Clippy, documentation, distributions, an installed
wheel, and records benchmark results. Rebuild with `maturin develop --release`
after editing Rust sources; performance measurements require a release build.

Python versions older than 3.10 are no longer supported. Event fields, list edits,
`vars`, dataclass helpers, pickling, and subclassing remain supported. Timestamp
encoding uses integer arithmetic to avoid precision loss for distant dates.

See the [Rust implementation notes](docs/rust-port.md) and
[benchmark results](benchmarks/README.md). The original
[PyO3 port plan](docs/pyo3-port-plan.md) records the compatibility gates.
