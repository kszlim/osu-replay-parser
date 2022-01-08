[![PyPi version](https://badge.fury.io/py/osrparse.svg)](https://pypi.org/project/osrparse/)
[![Build Status](https://travis-ci.org/kszlim/osu-replay-parse.svg?branch=master)](https://travis-ci.org/kszlim/osu-replay-parser)

# osrparse, a python parser for osu! replays

This is a parser for osu! replay files (.osr) as described by <https://osu.ppy.sh/wiki/en/osu%21_File_Formats/Osr_%28file_format%29>.

## Installation

To install, simply:

```sh
pip install osrparse
```

## Documentation

### Parsing

To parse a replay:

```python
from osrparse import Replay
replay = Replay.from_path("path/to/osr.osr")

# or from an opened file object
with open("path/to/osr.osr") as f:
    replay = Replay.from_file(f)

# or from a string
with open("path/to/osr.osr") as f:
    replay_string = f.read()
replay = Replay.from_string(replay_string)
```

To parse only the `replay_data` portion of a `Replay`, such as the data returned from the api `/get_replay` endpoint:

```python
from osrparse import parse_replay_data
import base64
import lzma

lzma_string = retrieve_from_api()
replay_data = parse_replay_data(lzma_string)
assert isinstance(replay_data[0], ReplayEvent)

# or parse an already decoded lzma string
lzma_string = retrieve_from_api()
lzma_string = base64.b64decode(lzma_string)
replay_data = parse_replay_data(lzma_string, decoded=True)

# or parse an already decoded and decompressed lzma string
lzma_string = retrieve_from_api()
lzma_string = base64.b64decode(lzma_string)
lzma_string = lzma.decompress(lzma_string).decode("ascii")
replay_data = parse_replay_data(lzma_string, decompressed=True)
```

The response returned from `/get_replay` is base 64 encoded, which is why we provide automatic decoding in `parse_replay_data`. If you are retrieving this data from a different source where the replay data is already decoded, pass `decoded=True`.

### Writing

Existing `Replay` objects can be written back to `.osr` files:

```python
replay.write_path("path/to/osr.osr")

# or to an opened file object
with open("path/to/osr.osr") as f:
    replay.write_file(f)

# or to a string
dumped = replay.dump()
```

You can also edit osr files by parsing a replay, editing an attribute, and dumping it back to its file:

```python
replay = Replay.from_path("path/to/osr.osr")
replay.username = "fake username"
replay.write_path("path/to/osr.osr")
```

### Attributes

`Replay` objects have the following attibutes:

```python
self.mode               # GameMode
self.game_version       # int
self.beatmap_hash       # str
self.username           # str
self.replay_hash        # str
self.count_300          # int
self.count_100          # int
self.count_50           # int
self.count_geki         # int
self.count_katu         # int
self.count_miss         # int
self.score              # int
self.max_combo          # int
self.perfect            # bool
self.mods               # Mod
self.life_bar_graph     # str or None
self.timestamp          # datetime
self.replay_data        # List[ReplayEvent]
self.replay_id          # int
self.rng_seed           # int or None
# list of either ReplayEventOsu, ReplayEventTaiko, ReplayEventCatch,
# or ReplayEventMania objects, depending on self.game_mode
self.play_data
```

`ReplayEventOsu` objects have the following attributes:

```python
self.time_delta # int, time since previous event in milliseconds
self.x          # float, x axis location
self.y          # float, y axis location
self.keys       # Key enum, keys pressed
```

`ReplayEventTaiko` objects have the following attributes:

```python
self.time_delta # int, time since previous event in milliseconds
self.x          # float, x axis location
self.keys       # KeyTaiko enum, keys pressed
```

`ReplayEventCatch` objects have the following attributes:

```python
self.time_delta # int, time since previous event in milliseconds
self.x          # float, x axis location
self.dashing    # bool, whether the player was dashing or not
```

`ReplayEventMania` objects have the following attributes:

```python
self.time_delta # int, time since previous event in milliseconds
self.keys       # KeyMania enum, keys pressed
```

The `Key` enums used in the above `ReplayEvent`s are defined as follows:

```python
class Key(IntFlag):
    M1    = 1 << 0
    M2    = 1 << 1
    K1    = 1 << 2
    K2    = 1 << 3
    SMOKE = 1 << 4

class KeyTaiko(IntFlag):
    LEFT_DON  = 1 << 0
    LEFT_KAT  = 1 << 1
    RIGHT_DON = 1 << 2
    RIGHT_KAT = 1 << 3

class KeyMania(IntFlag):
    K1 = 1 << 0
    K2 = 1 << 1
    K3 = 1 << 2
    K4 = 1 << 3
    K5 = 1 << 4
    K6 = 1 << 5
    K7 = 1 << 6
    K8 = 1 << 7
    K9 = 1 << 8
    K10 = 1 << 9
    K11 = 1 << 10
    K12 = 1 << 11
    K13 = 1 << 12
    K14 = 1 << 13
    K15 = 1 << 14
    K16 = 1 << 15
    K17 = 1 << 16
    K18 = 1 << 17
```
