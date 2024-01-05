from pathlib import Path
from datetime import timedelta

from hypothesis import given

from osrparse import Replay
from osrparse.strategies import replays


RES = Path(__file__).parent / "resources"

@given(replays())
def test_packing(replay: Replay):
    packed = replay.pack()
    replay2 = Replay.from_string(packed)

    # `replay_length` is intentionally not tested for equality here, as the
    # length of the compressed replay data may change after dumping due to
    # varying lzma settings.
    attrs = [
        "mode", "game_version", "beatmap_hash", "username",
        "replay_hash", "count_300", "count_100", "count_50", "count_geki",
        "count_katu", "count_miss", "score", "max_combo", "perfect",
        "mods", "life_bar_graph", "timestamp", "replay_data",
        "replay_id"
    ]
    for attr in attrs:
        if attr == "timestamp":
            # TODO floating point issues, maybe? but probably going to be limited
            # by precision of windows ticks compared to python microseconds.
            assert abs(replay.timestamp - replay2.timestamp) < timedelta(microseconds=50)
            continue
        assert getattr(replay, attr) == getattr(replay2, attr), attr
