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

To parse a replay from a filepath:

```python
from osrparse import parse_replay_file

# returns a Replay object
parse_replay_file("path/to/osr.osr")
```

To parse a replay from an lzma string (such as the one returned from the `/get_replay` osu! api endpoint):

```python
from osrparse import parse_replay

# returns a Replay object that only has a `play_data` attribute
parse_replay(lzma_string, pure_lzma=True)
```

Note that if you use the `/get_replay` endpoint to retrieve a replay, you must decode the response before passing it to osrparse, as the response is encoded in base 64 by default.

Replay objects provide the following fields:

```python
self.game_mode # GameMode enum
self.game_version # int
self.beatmap_hash # str
self.player_name # str
self.replay_hash # str
self.number_300s # int
self.number_100s # int
self.number_50s # int
self.gekis # int
self.katus # int
self.misses # int
self.score # int
self.max_combo # int
self.is_perfect_combo # bool
self.mod_combination # Mod enum
self.life_bar_graph # str, currently unparsed
self.timestamp # datetime.datetime object
self.play_data # list[ReplayEvent]
```

ReplayEvent objects provide the following fields:

```python
self.time_delta # int (in milliseconds)
self.x # x axis location
self.y # y axis location
self.keys # Key IntFlag of keys pressed
```
