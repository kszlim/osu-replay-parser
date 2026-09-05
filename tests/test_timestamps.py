import struct
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from osrparse import Replay
from osrparse.replay import _Unpacker


@pytest.mark.parametrize("timestamp", [
    datetime.min.replace(tzinfo=timezone.utc),
    datetime(9135, 1, 1, microsecond=2226, tzinfo=timezone.utc),
    datetime.max.replace(tzinfo=timezone.utc),
    datetime(2026, 9, 4, microsecond=123456,
             tzinfo=timezone(timedelta(hours=-7))),
])
def test_timestamp_round_trip_is_exact(timestamp):
    replay = Replay.from_path(Path(__file__).parent / "resources" / "replay.osr")
    replay.timestamp = timestamp
    assert Replay.from_string(replay.pack()).timestamp == timestamp


@pytest.mark.parametrize("ticks, microseconds", [(4, 0), (5, 0), (6, 1), (15, 2), (25, 2)])
def test_submicrosecond_ticks_round_half_to_even(ticks, microseconds):
    unpacker = _Unpacker(struct.pack("<q", ticks))
    assert unpacker.unpack_timestamp() == (
        datetime.min.replace(tzinfo=timezone.utc) + timedelta(microseconds=microseconds)
    )
