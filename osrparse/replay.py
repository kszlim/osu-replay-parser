import lzma
import struct
from datetime import datetime, timezone, timedelta
from typing import List

from osrparse.utils import (Mod, GameMode, ReplayEvent, ReplayEventOsu,
    ReplayEventCatch, ReplayEventMania, ReplayEventTaiko)
from osrparse.dump import dump_replay

class Replay:
    # first version with rng seed value added as the last frame in the lzma data
    LAST_FRAME_SEED_VERSION = 20130319
    _BYTE = 1
    _SHORT = 2
    _INT = 4
    _LONG = 8

    def __init__(self, replay_data: List[ReplayEvent], pure_lzma: bool, decompressed_lzma: bool):
        self.offset = 0
        self.game_mode = None
        self.game_version = None
        self.beatmap_hash = None
        self.player_name = None
        self.replay_hash = None
        self.number_300s = None
        self.number_100s = None
        self.number_50s = None
        self.gekis = None
        self.katus = None
        self.misses = None
        self.score = None
        self.max_combo = None
        self.is_perfect_combo = None
        self.mod_combination = None
        self.life_bar_graph = None
        self.timestamp = None
        self.play_data = None
        self.replay_id = None
        self.replay_length = None
        self._parse_replay_and_initialize_fields(replay_data, pure_lzma, decompressed_lzma)

    def _parse_replay_and_initialize_fields(self, replay_data, pure_lzma, decompressed_lzma):
        if pure_lzma:
            self.data_from_lmza(replay_data, decompressed_lzma)
            return
        self._parse_game_mode_and_version(replay_data)
        self._parse_beatmap_hash(replay_data)
        self._parse_player_name(replay_data)
        self._parse_replay_hash(replay_data)
        self._parse_score_stats(replay_data)
        self._parse_life_bar_graph(replay_data)
        self._parse_timestamp_and_replay_length(replay_data)
        self._parse_play_data(replay_data)
        self._parse_replay_id(replay_data)

    def _parse_game_mode_and_version(self, replay_data):
        format_specifier = "<bi"
        data = struct.unpack_from(format_specifier, replay_data, self.offset)
        self.offset += struct.calcsize(format_specifier)
        self.game_mode, self.game_version = (GameMode(data[0]), data[1])

    def _unpack_game_stats(self, game_stats):
        (self.number_300s, self.number_100s, self.number_50s, self.gekis,
         self.katus, self.misses, self.score, self.max_combo,
         self.is_perfect_combo, mod_combination) = game_stats

        self.mod_combination = Mod(mod_combination)

    def _parse_score_stats(self, replay_data):
        format_specifier = "<hhhhhhih?i"
        data = struct.unpack_from(format_specifier, replay_data, self.offset)
        self._unpack_game_stats(data)
        self.offset += struct.calcsize(format_specifier)

    def _decode(self, binarystream):
        result = 0
        shift = 0
        while True:
            byte = binarystream[self.offset]
            self.offset += 1
            result = result |((byte & 0b01111111) << shift)
            if (byte & 0b10000000) == 0x00:
                break
            shift += 7
        return result

    def _parse_player_name(self, replay_data):
        self.player_name = self._parse_string(replay_data)

    def _parse_string(self, replay_data):
        if replay_data[self.offset] == 0x00:
            self.offset += Replay._BYTE
        elif replay_data[self.offset] == 0x0b:
            self.offset += Replay._BYTE
            string_length = self._decode(replay_data)
            offset_end = self.offset + string_length
            string = replay_data[self.offset:offset_end].decode("utf-8")
            self.offset = offset_end
            return string
        else:
            raise ValueError("Expected the first byte of a string to be 0x00 "
                f"or 0x0b, but got {replay_data[self.offset]}")

    def _parse_beatmap_hash(self, replay_data):
        self.beatmap_hash = self._parse_string(replay_data)

    def _parse_replay_hash(self, replay_data):
        self.replay_hash = self._parse_string(replay_data)

    def _parse_life_bar_graph(self, replay_data):
        self.life_bar_graph = self._parse_string(replay_data)

    def _parse_timestamp_and_replay_length(self, replay_data):
        format_specifier = "<qi"
        (t, self.replay_length) = struct.unpack_from(format_specifier, replay_data, self.offset)
        self.timestamp = datetime.min + timedelta(microseconds=t/10)
        self.timestamp = self.timestamp.replace(tzinfo=timezone.utc)
        self.offset += struct.calcsize(format_specifier)

    def _parse_play_data(self, replay_data):
        offset_end = self.offset+self.replay_length
        datastring = lzma.decompress(replay_data[self.offset:offset_end], format=lzma.FORMAT_AUTO).decode('ascii')[:-1]
        events = [eventstring.split('|') for eventstring in datastring.split(',')]

        if self.game_mode is GameMode.STD:
            self.play_data = [ReplayEventOsu(int(event[0]), float(event[1]), float(event[2]), int(event[3])) for event in events]
        if self.game_mode is GameMode.TAIKO:
            self.play_data = [ReplayEventTaiko(int(event[0]), float(event[1]), int(event[3])) for event in events]
        if self.game_mode is GameMode.CTB:
            self.play_data = [ReplayEventCatch(int(event[0]), float(event[1]), int(event[3])) for event in events]
        if self.game_mode is GameMode.MANIA:
            self.play_data = [ReplayEventMania(int(event[0]), int(event[1])) for event in events]

        self.offset = offset_end

        if self.game_version >= self.LAST_FRAME_SEED_VERSION and self.play_data:
            if self.play_data[-1].time_delta != -12345:
                pass
                # I've disabled this warning temporarily as it turns out that
                # many replays (perhaps all replays in non-std gamemodes?) don't
                # have an RNG seed value even after the expected version, so
                # this was more of an annoying false positive than anything.

                # print("The RNG seed value was expected in the last frame, but was not found. "
                #       f"\nGame Version: {self.game_version}, version threshold: "
                #       f"{self.LAST_FRAME_SEED_VERSION}, replay hash: {self.replay_hash}")
            else:
                del self.play_data[-1]

    def data_from_lmza(self, lzma_string, decompressed_lzma):
        if decompressed_lzma:
            # replay data is already decompressed and decoded.
            # Remove last character (comma) so splitting works, same below
            datastring = lzma_string[:-1]
        else:
            datastring = lzma.decompress(lzma_string, format=lzma.FORMAT_AUTO).decode('ascii')[:-1]
        events = [eventstring.split('|') for eventstring in datastring.split(',')]
        self.play_data = [ReplayEventOsu(int(event[0]), float(event[1]), float(event[2]), int(event[3])) for event in events]

        if self.play_data[-1].time_delta == -12345:
            del self.play_data[-1]

    def _parse_replay_id(self, replay_data):
        format_specifier = "<q"
        try:
            replay_id = struct.unpack_from(format_specifier, replay_data, self.offset)
        # old replays had replay_id stored as a short (4 bytes) instead of a
        # long (8 bytes), so fall back to short if necessary.
        # lazer checks against the gameversion before trying to parse as a
        # short, but there may be some weirdness with replays that were set
        # during this time but downloaded later having actually correct (long)
        # replay_ids, since they were likely manually migrated at some point
        # after the switch to long took place.
        # See:
        # https://github.com/ppy/osu/blob/84e1ff79a0736aa6c7a44804b585ab1c54a84399/
        # osu.Game/Scoring/Legacy/LegacyScoreDecoder.cs#L78-L81
        except struct.error:
            format_specifier = "<l"
            replay_id = struct.unpack_from(format_specifier, replay_data, self.offset)
        self.replay_id = replay_id[0]

    def dump(self, file=None):
        dumped = dump_replay(self)

        if file:
            file.write(dumped)
        
        return dumped