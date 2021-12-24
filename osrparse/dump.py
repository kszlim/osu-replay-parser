import hashlib, lzma
import struct

from osrparse.utils import (ReplayEventOsu, ReplayEventTaiko, ReplayEventCatch,
    ReplayEventMania)
from osrparse.replay import Replay

class PackFormat:
    # data types
    def Byte(data: int):
        return struct.pack("<B", data)

    def Short(data: int):
        return struct.pack("<H", data)

    def Integer(data: int):
        return struct.pack("<I", data)

    def Long(data: int):
        return struct.pack("<Q", data)

    def ULEB128(data):
        # taken from https://github.com/mohanson/leb128
        r, i = [], len(data)

        while True:
            byte = i & 0x7f
            i = i >> 7

            if (i == 0 and byte & 0x40 == 0) or (i == -1 and byte & 0x40 != 0):
                r.append(byte)
                return b"".join(map(PackFormat.Byte, r))

            r.append(0x80 | byte)

    def String(data: str):
        if data:
            return PackFormat.Byte(11) + PackFormat.ULEB128(data) + data.encode("utf-8")
        else:
            return PackFormat.Byte(11) + PackFormat.Byte(0)

class ReplayDumper:
    def __init__(self, replay: Replay):
        self.replay = replay
        self.data = b""

        self._hash = ""
        self._play_data = b""

    def dump(self):
        self.data = b""
        self._dump_replay_data(self.replay.play_data)

        self.data += PackFormat.Byte(self.replay.game_mode.value)       # game mode
        self.data += PackFormat.Integer(self.replay.game_version)       # game version
        self.data += PackFormat.String(self.replay.beatmap_hash)        # beatmap hash

        self.data += PackFormat.String(self.replay.player_name)         # player name
        self.data += PackFormat.String(self._hash)                      # replay hash

        self.data += PackFormat.Short(self.replay.number_300s)          # number of 300s
        self.data += PackFormat.Short(self.replay.number_100s)          # number of 100s
        self.data += PackFormat.Short(self.replay.number_50s)           # number of 50s
        self.data += PackFormat.Short(self.replay.gekis)                # number of gekis
        self.data += PackFormat.Short(self.replay.katus)                # number of katus
        self.data += PackFormat.Short(self.replay.misses)               # number of misses

        self.data += PackFormat.Integer(self.replay.score)              # score
        self.data += PackFormat.Short(self.replay.max_combo)            # max combo
        self.data += PackFormat.Byte(self.replay.is_perfect_combo)      # is perfect combo

        self.data += PackFormat.Integer(self.replay.mod_combination.value) # mods
        self.data += PackFormat.String(self.replay.life_bar_graph)      # life bar graph
        self.data += self._dump_timestamp()                             # time stamp

        self.data += self._play_data                                    # replay data
        self.data += PackFormat.Long(self.replay.replay_id)             # replay id

        return self.data

    def _dump_timestamp(self):
        # due to converting ticks into an int, there appears to be some precision loss in the ticks value
        # even though it's small (around 4 ticks), it might be an issue with reproccessing the same replay
        # for many times in a row

        shift = 62135596800 + 3600 # when it's negative, it represents January 1st 0001, 01:00:00 AM UTC
        ticks = (self.replay.timestamp.timestamp() + shift) * 10_000_000

        return PackFormat.Long(int(ticks))

    def _dump_replay_data(self, events):
        replay_data = ""
        for event in events:
            if isinstance(event, ReplayEventOsu): # gonna work on other modes later
                replay_data += f"{event.time_delta}|{event.x}|{event.y}|{event.keys.value},"
            elif isinstance(event, ReplayEventTaiko):
                replay_data += f"{event.time_delta}|{event.x}|0|{event.keys.value},"
            elif isinstance(event, ReplayEventCatch):
                replay_data += f"{event.time_delta}|{event.x}|0|{int(event.dashing)},"
            elif isinstance(event, ReplayEventMania):
                replay_data += f"{event.time_delta}|{event.keys}|0|0,"

        filters = [{"id": lzma.FILTER_LZMA1, "dict_size": 2097152, "mode": lzma.MODE_FAST}]
        compressed = lzma.compress(replay_data.encode("ascii"), format=lzma.FORMAT_ALONE, filters=filters)

        self._hash = hashlib.md5(compressed).hexdigest()
        self._play_data = PackFormat.Integer(len(compressed)) + compressed

def dump_replay(replay: Replay):
    dumper = ReplayDumper(replay)
    return dumper.dump()

def dump_replay_file(replay: Replay, file_name: str):
    with open(file_name, "wb") as f:
        f.write(dump_replay(replay))
