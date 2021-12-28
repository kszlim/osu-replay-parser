import lzma
import struct

from osrparse.utils import (ReplayEventOsu, ReplayEventTaiko, ReplayEventCatch,
    ReplayEventMania)
from osrparse.replay import Replay

def pack_byte(data: int):
    return struct.pack("<B", data)

def pack_short(data: int):
    return struct.pack("<H", data)

def pack_int(data: int):
    return struct.pack("<I", data)

def pack_long(data: int):
    return struct.pack("<Q", data)

def pack_ULEB128(data):
    # taken from https://github.com/mohanson/leb128
    r, i = [], len(data)

    while True:
        byte = i & 0x7f
        i = i >> 7

        if (i == 0 and byte & 0x40 == 0) or (i == -1 and byte & 0x40 != 0):
            r.append(byte)
            return b"".join(map(pack_byte, r))

        r.append(0x80 | byte)

def pack_string(data: str):
    if data:
        return pack_byte(11) + pack_ULEB128(data) + data.encode("utf-8")
    return pack_byte(11) + pack_byte(0)

def dump_timestamp(replay):
    # windows ticks starts at year 0001, in contrast to unix time (1970).
    # 62135596800 is the number of seconds between these two years and is added
    # to account for this difference.
    # The factor of 10000000 converts seconds to ticks.
    ticks = (62135596800 + replay.timestamp.timestamp()) * 10000000
    ticks = int(ticks)
    return pack_long(ticks)


def dump_replay_data(replay):
    replay_data = ""
    for event in replay.play_data:
        if isinstance(event, ReplayEventOsu):
            replay_data += f"{event.time_delta}|{event.x}|{event.y}|{event.keys.value},"
        elif isinstance(event, ReplayEventTaiko):
            replay_data += f"{event.time_delta}|{event.x}|0|{event.keys.value},"
        elif isinstance(event, ReplayEventCatch):
            replay_data += f"{event.time_delta}|{event.x}|0|{int(event.dashing)},"
        elif isinstance(event, ReplayEventMania):
            replay_data += f"{event.time_delta}|{event.keys}|0|0,"

    filters = [{"id": lzma.FILTER_LZMA1, "dict_size": 1 << 21, "mode": lzma.MODE_NORMAL}]
    compressed = lzma.compress(replay_data.encode("ascii"), format=lzma.FORMAT_ALONE, filters=filters)

    return pack_int(len(compressed)) + compressed


def dump_replay(replay: Replay):
    data = b""

    data += pack_byte(replay.game_mode.value)
    data += pack_int(replay.game_version)
    data += pack_string(replay.beatmap_hash)

    data += pack_string(replay.player_name)
    data += pack_string(replay.replay_hash)

    data += pack_short(replay.number_300s)
    data += pack_short(replay.number_100s)
    data += pack_short(replay.number_50s)
    data += pack_short(replay.gekis)
    data += pack_short(replay.katus)
    data += pack_short(replay.misses)

    data += pack_int(replay.score)
    data += pack_short(replay.max_combo)
    data += pack_byte(replay.is_perfect_combo)

    data += pack_int(replay.mod_combination.value)
    data += pack_string(replay.life_bar_graph)
    data += dump_timestamp(replay)

    data += dump_replay_data(replay)
    data += pack_long(replay.replay_id)

    return data

def dump_replay_file(replay: Replay, file_name: str):
    with open(file_name, "wb") as f:
        f.write(dump_replay(replay))
