from osrparse import (ReplayEventOsu, GameMode, Mod, ReplayEventTaiko,
    ReplayEventCatch, ReplayEventMania, Replay)
from pathlib import Path


RES = Path(__file__).parent / "resources"

replay_path =  RES / "test.osr"
replay = Replay.from_path(replay_path)
print(replay.score_info.mods[0])
replay.write_path(replay_path)