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

To parse a replay from a filepath:

```python
from osrparse import parse_replay_file

# returns a Replay object
replay = parse_replay_file("path/to/osr.osr")
```

To parse a replay from an lzma string (such as the one returned from the `/get_replay` osu! api endpoint):

```python
from osrparse import parse_replay

# returns a Replay object that only has a `play_data` attribute
replay = parse_replay(lzma_string, pure_lzma=True)
```

Note that if you use the `/get_replay` endpoint to retrieve a replay, you must decode the response before passing it to osrparse, as the response is encoded in base 64 by default.

### Attributes

`Replay` objects have the following attibutes:

```python
self.game_mode        # GameMode enum
self.game_version     # int
self.beatmap_hash     # str
self.player_name      # str
self.replay_hash      # str
self.number_300s      # int
self.number_100s      # int
self.number_50s       # int
self.gekis            # int
self.katus            # int
self.misses           # int
self.score            # int
self.max_combo        # int
self.is_perfect_combo # bool
self.mod_combination  # Mod enum
self.life_bar_graph   # str, currently unparsed
self.timestamp        # datetime.datetime object
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
self.keys       # KeyMania enum
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
