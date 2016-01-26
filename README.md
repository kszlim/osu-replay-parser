[![Build Status](https://travis-ci.org/kszlim/osu-replay-parser.svg?branch=master)](https://travis-ci.org/kszlim/osu-replay-parser)
# osrparse, a parser for osu replays in Python

This is a parser for osu! rhythm game replays as described by https://osu.ppy.sh/wiki/Osr_(file_format)

## Installation
To install osrparse, simply:
```
$ pip install osrparse
```

## Documentation
To parse a replay from a filepath:
```python
from osrparse import parse_replay_file

#returns instance of Replay
parse_replay_file("path_to_osr.osr")
```

To parse a replay from a bytestring:
```python
from osrparse import parse_replay

#returns instance of Replay given the replay data encoded as a bytestring
parse_replay_file(byteString)
```
Replay instances provide these fields
```python
self.game_mode #GameMode enum
self.game_version #Integer
self.beatmap_hash #String
self.player_name #String
self.replay_hash #String
self.number_300s #Integer
self.number_100s #Integer
self.number_50s #Integer
self.gekis #Integer
self.katus #Integer
self.misses #Integer
self.score #Integer
self.max_combo #Integer
self.is_perfect_combo #Boolean
self.mod_combination #frozenset of Mods
self.life_bar_graph #String, unparsed as of now
self.timestamp #Integer
self.play_data #List of ReplayEvent instances
```

ReplayEvent instances provide these fields
```python
self.time_since_previous_action #Integer representing time in milliseconds
self.x #x axis location
self.y #y axis location
self.keys_pressed #bitwise sum of keys pressed, documented in OSR format page.
```
