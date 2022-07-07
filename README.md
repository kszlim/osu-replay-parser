[![PyPi version](https://badge.fury.io/py/osrparse.svg)](https://pypi.org/project/osrparse/)
[![Build Status](https://travis-ci.org/kszlim/osu-replay-parse.svg?branch=master)](https://travis-ci.org/kszlim/osu-replay-parser)

# osrparse, a python parser for osu! replays

This is a parser for the ``.osr`` format for osu! replay files, as described by [the wiki](https://osu.ppy.sh/wiki/en/Client/File_formats/Osr_%28file_format%29).

## Installation

To install, simply:

```sh
pip install osrparse
```

## Documentation

Please see the full documentation for a comprehensive guide: <https://kevin-lim.ca/osu-replay-parser/>. A quickstart follows below for the impatient, but you should read the full documentation if you are at all confused.

### Quickstart

```python
from osrparse import Replay, parse_replay_data
# parse from a path
replay = Replay.from_path("path/to/osr.osr")

# or from an opened file object
with open("path/to/osr.osr") as f:
    replay = Replay.from_file(f)

# or from a string
with open("path/to/osr.osr") as f:
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
with open("path/to/osr.osr") as f:
    replay.write_file(f)

# or to a string
packed = replay.pack()

# edited attributes are saved
replay.username = "fake username"
replay.write_path("path/to/new_osr.osr")
```
