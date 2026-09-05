from pathlib import Path
from unittest import TestCase
from datetime import datetime, timezone
from osrparse import (ReplayEventOsu, GameMode, Mod, ReplayEventTaiko,
    ReplayEventCatch, ReplayEventMania, Replay)
import time

RES = Path(__file__).parent / "resources"

def test_benchmark():
    replay1_path =  RES / "replay.osr"
    with open(replay1_path, "rb") as f:
        data = f.read()
    start = time.time()
    for _ in range(1000):
        replays = Replay.from_string(data)
    print(f"{time.time() - start} seconds to parse 1000 replays")

