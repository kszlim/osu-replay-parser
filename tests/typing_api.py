"""Static consumer test. Unused ignores fail if a stub becomes overly broad."""

from collections.abc import MutableSequence
from datetime import datetime
from pathlib import Path

from typing_extensions import assert_type

from osrparse import (
    GameMode,
    Key,
    KeyMania,
    Replay,
    ReplayData,
    ReplayEvent,
    ReplayEventOsu,
    parse_replay_data,
)


def consumer(path: Path) -> None:
    replay = Replay.from_path(path)
    assert_type(replay, Replay)
    assert_type(replay.mode, GameMode)
    assert_type(replay.timestamp, datetime)
    assert_type(replay.replay_data, MutableSequence[ReplayEvent])
    replay.username = "edited"
    event = ReplayEventOsu(16, 1.0, 2.0, Key.K1)
    assert_type(event.keys, Key)
    assert_type(event.x, float)
    event.x = 3.0
    data = ReplayData([event])
    assert_type(data[0], ReplayEvent)
    assert_type(data[:], list[ReplayEvent])
    data += [event]
    data *= 2
    assert_type(data, ReplayData)
    replay.replay_data = data
    assert_type(replay.pack(), bytes)
    assert_type(parse_replay_data("", mode=GameMode.STD), MutableSequence[ReplayEvent])
    event.x = "wrong"  # type: ignore[assignment]
    event.keys = KeyMania.K1  # type: ignore[assignment]
    data.append("wrong")  # type: ignore[arg-type]
    ReplayEventOsu(16, 1.0, 2.0)  # type: ignore[call-arg]
    Replay.from_path(123)  # type: ignore[arg-type]
