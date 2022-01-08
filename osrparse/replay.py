# CHANGELOG:
# * number_{300, 100, 50}s -> count_{300, 100, 50}
# * {geki, katu, misses} -> {count_geki, count_katu, count_miss}
# * is_perfect_combo -> perfect
# * game_mode -> mode
# * player_name -> username
# * play_data -> replay_data
# * added rng_seed

import lzma
import struct
from datetime import datetime, timezone, timedelta
from typing import List, Optional
import base64

from osrparse.utils import (Mod, GameMode, ReplayEvent, ReplayEventOsu,
    ReplayEventCatch, ReplayEventMania, ReplayEventTaiko, Key, KeyMania,
    KeyTaiko)
from osrparse.dump import dump_replay

class _Unpacker:
    """
    Helper class for dealing with the ``.osr`` format. Not intended to be used
    by consumers.
    """
    def __init__(self, replay_data):
        self.replay_data = replay_data
        self.offset = 0

    def string_length(self, binarystream):
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

    def unpack_string(self):
        if self.replay_data[self.offset] == 0x00:
            self.offset += 1
        elif self.replay_data[self.offset] == 0x0b:
            self.offset += 1
            string_length = self.string_length(self.replay_data)
            offset_end = self.offset + string_length
            string = self.replay_data[self.offset:offset_end].decode("utf-8")
            self.offset = offset_end
            return string
        else:
            raise ValueError("Expected the first byte of a string to be 0x00 "
                f"or 0x0b, but got {self.replay_data[self.offset]}")

    def unpack_once(self, specifier):
        # always use little endian
        specifier = f"<{specifier}"
        unpacked = struct.unpack_from(specifier, self.replay_data, self.offset)
        self.offset += struct.calcsize(specifier)
        # `struct.unpack_from` always returns a tuple, even if there's only one
        # element
        return unpacked[0]

    def unpack_timestamp(self):
        ticks = self.unpack_once("q")
        timestamp = datetime.min + timedelta(microseconds=ticks/10)
        timestamp = timestamp.replace(tzinfo=timezone.utc)
        return timestamp

    def unpack_play_data(self, mode):
        replay_length = self.unpack_once("i")
        offset_end = self.offset + replay_length
        data = self.replay_data[self.offset:offset_end]
        data = lzma.decompress(data, format=lzma.FORMAT_AUTO)
        data = data.decode("ascii")
        replay_data = self.parse_replay_data(data, mode)
        self.offset = offset_end
        return replay_data

    @staticmethod
    def parse_replay_data(replay_data_str, mode):
        # remove trailing comma to make splitting easier
        replay_data_str = replay_data_str[:-1]
        events = [event.split('|') for event in replay_data_str.split(',')]

        play_data = []
        for event in events:
            time_delta = int(event[0])
            x = event[1]
            y = event[2]
            keys = int(event[3])

            if mode is GameMode.STD:
                keys = Key(keys)
                event = ReplayEventOsu(time_delta, float(x), float(y), keys)
            if mode is GameMode.TAIKO:
                event = ReplayEventTaiko(time_delta, int(x), KeyTaiko(keys))
            if mode is GameMode.CTB:
                event = ReplayEventCatch(time_delta, float(x), int(keys) == 1)
            if mode is GameMode.MANIA:
                event = ReplayEventMania(time_delta, KeyMania(keys))
            play_data.append(event)

        return play_data

    def unpack_replay_id(self):
        # old replays had replay_id stored as a short (4 bytes) instead of a
        # long (8 bytes), so fall back to short if necessary.
        # lazer checks against the gameversion before trying to parse as a
        # short, but there may be some weirdness with replays that were set
        # during this time but downloaded later having actually correct (long)
        # replay_ids, since they were likely manually migrated at some point
        # after the switch to long took place.
        # See:
        # https://github.com/ppy/osu/blob/84e1ff79a0736aa6c7a44804b585ab1c54a843
        # 99/osu.Game/Scoring/Legacy/LegacyScoreDecoder.cs#L78-L81
        try:
            replay_id = self.unpack_once("q")
        except struct.error:
            replay_id = self.unpack_once("l")
        return replay_id

    def unpack(self):
        mode = GameMode(self.unpack_once("b"))
        game_version = self.unpack_once("i")
        beatmap_hash = self.unpack_string()
        username = self.unpack_string()
        replay_hash = self.unpack_string()
        count_300 = self.unpack_once("h")
        count_100 = self.unpack_once("h")
        count_50 = self.unpack_once("h")
        count_geki = self.unpack_once("h")
        count_katu = self.unpack_once("h")
        count_miss = self.unpack_once("h")
        score = self.unpack_once("i")
        max_combo = self.unpack_once("h")
        perfect = self.unpack_once("?")
        mods = Mod(self.unpack_once("i"))
        life_bar_graph = self.unpack_string()
        timestamp = self.unpack_timestamp()
        play_data = self.unpack_play_data(mode)
        replay_id = self.unpack_replay_id()

        rng_seed = None
        if play_data[-1].time_delta == -12345:
            rng_seed = play_data[-1]
            del play_data[-1]

        return Replay(mode, game_version, beatmap_hash, username,
            replay_hash, count_300, count_100, count_50, count_geki, count_katu,
            count_miss, score, max_combo, perfect, mods, life_bar_graph,
            timestamp, play_data, replay_id, rng_seed)



class Replay:
    """
    A replay found in a ``.osr`` file, or following the osr format. To create a
    replay, you likely want ``Replay.from_path``, ``Replay.from_file``, or
    ``Replay.from_string``.
    """
    def __init__(self,
        mode: GameMode,
        game_version: int,
        beatmap_hash: str,
        username: str,
        replay_hash: str,
        count_300: int,
        count_100: int,
        count_50: int,
        count_geki: int,
        count_katu: int,
        count_miss: int,
        score: int,
        max_combo: int,
        perfect: bool,
        mods: Mod,
        life_bar_graph: Optional[str],
        timestamp: datetime,
        replay_data: List[ReplayEvent],
        replay_id: int,
        rng_seed: Optional[int]
    ):
        self.mode = mode
        self.game_version = game_version
        self.beatmap_hash = beatmap_hash
        self.username = username
        self.replay_hash = replay_hash
        self.count_300 = count_300
        self.count_100 = count_100
        self.count_50 = count_50
        self.count_geki = count_geki
        self.count_katu = count_katu
        self.count_miss = count_miss
        self.score = score
        self.max_combo = max_combo
        self.perfect = perfect
        self.mods = mods
        self.life_bar_graph = life_bar_graph
        self.timestamp = timestamp
        self.replay_data = replay_data
        self.replay_id = replay_id
        self.rng_seed = rng_seed

    @staticmethod
    def from_path(path):
        """
        Creates a new ``Replay`` object from the ``.osr`` file at the given
        ``path``.

        Parameters
        ----------
        path: str or os.PathLike
            The path to the osr file to read from.

        Returns
        -------
        Replay
            The parsed replay object.
        """
        with open(path, "rb") as f:
            return Replay.from_file(f)

    @staticmethod
    def from_file(file):
        """
        Creates a new ``Replay`` object from an open file object.

        Parameters
        ----------
        file: file-like
           The file object to read from.

        Returns
        -------
        Replay
            The parsed replay object.
        """
        data = file.read()
        return Replay.from_string(data)

    @staticmethod
    def from_string(data):
        """
        Creates a new ``Replay`` object from a string containing ``.osr`` data.

        Parameters
        ----------
        data: str
           The data to parse.

        Returns
        -------
        Replay
            The parsed replay object.
        """
        return _Unpacker(data).unpack()

    def write_path(self, path):
        """
        Writes the replay to the given ``path``.

        Parameters
        ----------
        path: str or os.PathLike
           The path to where to write the replay.

        Notes
        -----
        This uses the current values of any attributes, and so can be used to
        create an edited version of a replay, by first reading a replay, editing
        an attribute, then writing the replay back to its file.
        """
        with open(path, "wb") as f:
            self.write_file(f)

    def write_file(self, file):
        """
        Writes the replay to an open file object.

        Parameters
        ----------
        file: file-like
           The file object to write to.
        """
        dumped = self.dump()
        file.write(dumped)

    def dump(self):
        """
        Returns the text representing this ``Replay``, in ``.osr`` format.
        The text returned by this method is suitable for writing to a file as a
        valid ``.osr`` file.

        Returns
        -------
        str
            The text representing this ``Replay``, in ``.osr`` format.
        """
        return dump_replay(self)


def parse_replay_data(data_string, *, decoded=False, decompressed=False,
    mode=GameMode.STD) -> List[ReplayEvent]:
    """
    Parses the replay data portion of a replay from a string. This method is
    siutable for use with the replay data returned by api v1's ``/get_replay``
    endpoint, for instance.

    Parameters
    ----------
    data_string: str or bytes
        The replay data to parse.
    decoded: bool
        Whether ``data_string`` has already been decoded from a b64
        representation. Api v1 returns a base 64 encoded string, for instance.
    decompressed: bool
        Whether ``data_string`` has already been both decompressed from lzma,
        and decoded to ascii.
        |br|
        For instance, the following two calls are equivalent:
        ```
        >>> parse_replay_data(lzma_string, decoded=True)
        >>> ...
        >>> lzma_string = lzma.decompress(lzma_string).decode("ascii")
        >>> parse_replay_data(lzma_string, decompressed=True)
        ```
        |br|
        If ``decompressed`` is ``True``, ``decoded`` is automatically set to
        ``True`` as well (ie, if ``decompressed`` is ``True``, we will assume
        ``data_string`` is not base 64 encoded).
    mode: GameMode
        What mode to parse the replay data as.
    """
    # assume the data is already decoded if it's been decompressed
    if not decoded and not decompressed:
        data_string = base64.b64decode(data_string)
    if not decompressed:
        data_string = lzma.decompress(data_string, format=lzma.FORMAT_AUTO)
        data_string = data_string.decode("ascii")
    return _Unpacker.parse_replay_data(data_string, mode)
