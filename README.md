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
parse_replay(byteString)
```

To check for a gamemode:
```python
from osrparse.enums import GameMode
if replay.game_mode is GameMode.Standard:
  print("This is GameMode Standard indeed!")
```

Replay instances provide these fields (Both instances)
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
self.timestamp #Python Datetime object
self.play_data #List of ReplayEvent instances
```

ReplayEvent instances provide these fields
```python
self.time_since_previous_action #Integer representing time in milliseconds
self.x #x axis location
self.y #y axis location
self.keys_pressed #bitwise sum of keys pressed, documented in OSR format page.
```

On the other hand, ReplayEventMania instances have similar features on ReplayEvent but differ on a few things
```python
self.time_since_previous_action
self.rawcol #A binary that represents the columns pressed at a particular time.
# 0001001 means columns 4 and 7 were pressed
self.keys_pressed # A dictionary of inputs derived from self.rawcol. Each key represents the column from 0 to 9 while the values contain a boolean that represents if the key is pressed or not
# There are a total of 10 bits that represents 10 keys. It would output the same number of keys regardless of the beatmap's keymode. (It's just that the unused keys would always output as False)
```
