import lzma
import struct
from datetime import datetime, timezone, timedelta
from typing import List, Optional
import base64
from dataclasses import dataclass

from osrparse.utils import (Mod, GameMode, ReplayEvent, ReplayEventOsu,
    ReplayEventCatch, ReplayEventMania, ReplayEventTaiko, Key, KeyMania,
    KeyTaiko, LifeBarState)


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
        (replay_data, rng_seed) = self.parse_replay_data(data, mode)
        self.offset = offset_end
        return (replay_data, rng_seed)

    @staticmethod
    def parse_replay_data(replay_data_str, mode):
        # remove trailing comma (if it exists) to make splitting easier.
        # stable always adds a trailing comma, but some lazer versions do not.
        replay_data_str = replay_data_str.rstrip(",")
        events = [event.split('|') for event in replay_data_str.split(',')]

        rng_seed = None
        play_data = []
        for event in events:
            time_delta = int(event[0])
            x = event[1]
            y = event[2]
            keys = int(event[3])

            if time_delta == -12345 and event == events[-1]:
                rng_seed = keys
                continue

            if mode is GameMode.STD:
                keys = Key(keys)
                event = ReplayEventOsu(time_delta, float(x), float(y), keys)
            if mode is GameMode.TAIKO:
                event = ReplayEventTaiko(time_delta, int(x), KeyTaiko(keys))
            if mode is GameMode.CTB:
                event = ReplayEventCatch(time_delta, float(x), int(keys) == 1)
            if mode is GameMode.MANIA:
                event = ReplayEventMania(time_delta, KeyMania(int(x)))

            play_data.append(event)

        return (play_data, rng_seed)

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

    def unpack_life_bar(self):
        life_bar = self.unpack_string()
        if not life_bar:
            return None

        # remove trailing comma to make splitting easier
        life_bar = life_bar[:-1]
        states = [state.split("|") for state in life_bar.split(",")]

        return [LifeBarState(int(s[0]), float(s[1])) for s in states]

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
        life_bar_graph = self.unpack_life_bar()
        timestamp = self.unpack_timestamp()
        (replay_data, rng_seed) = self.unpack_play_data(mode)
        replay_id = self.unpack_replay_id()

        return Replay(mode, game_version, beatmap_hash, username,
            replay_hash, count_300, count_100, count_50, count_geki, count_katu,
            count_miss, score, max_combo, perfect, mods, life_bar_graph,
            timestamp, replay_data, replay_id, rng_seed)


class _Packer:
    def __init__(self, replay, *, dict_size=None, mode=None):
        self.replay = replay
        self.dict_size = dict_size or 1 << 21
        self.mode = mode or lzma.MODE_FAST

    def pack_byte(self, data):
        return struct.pack("<B", data)

    def pack_short(self, data):
        return struct.pack("<H", data)

    def pack_int(self, data):
        return struct.pack("<I", data)

    def pack_long(self, data):
        return struct.pack("<Q", data)

    def pack_ULEB128(self, data):
        # https://github.com/mohanson/leb128
        r, i = [], len(data)

        while True:
            byte = i & 0x7f
            i = i >> 7

            if (i == 0 and byte & 0x40 == 0) or (i == -1 and byte & 0x40 != 0):
                r.append(byte)
                return b"".join(map(self.pack_byte, r))

            r.append(0x80 | byte)

    def pack_string(self, data):
        if data:
            return (self.pack_byte(11) + self.pack_ULEB128(data) +
                data.encode("utf-8"))
        return self.pack_byte(11) + self.pack_byte(0)

    def pack_timestamp(self):
        # windows ticks starts at year 0001, in contrast to unix time (1970).
        # 62135596800 is the number of seconds between these two years and is
        # added to account for this difference.
        # The factor of 10000000 converts seconds to ticks.

        ticks = (62135596800 + self.replay.timestamp.timestamp()) * 10000000
        ticks = int(ticks)
        return self.pack_long(ticks)

    def pack_life_bar(self):
        data = ""
        if self.replay.life_bar_graph is None:
            return self.pack_string(data)

        for state in self.replay.life_bar_graph:
            life = state.life
            # store 0 or 1 instead of 0.0 or 1.0
            if int(life) == life:
                life = int(state.life)

            data += f"{state.time}|{life},"

        return self.pack_string(data)

    def pack_replay_data(self):
        data = ""
        for event in self.replay.replay_data:
            t = event.time_delta
            if isinstance(event, ReplayEventOsu):
                data += f"{t}|{event.x}|{event.y}|{event.keys.value},"
            elif isinstance(event, ReplayEventTaiko):
                data += f"{t}|{event.x}|0|{event.keys.value},"
            elif isinstance(event, ReplayEventCatch):
                data += f"{t}|{event.x}|0|{int(event.dashing)},"
            elif isinstance(event, ReplayEventMania):
                data += f"{t}|{event.keys.value}|0|0,"

        if self.replay.rng_seed:
            data += f"-12345|0|0|{self.replay.rng_seed},"

        filters = [
            {
                "id": lzma.FILTER_LZMA1,
                "dict_size": self.dict_size,
                "mode": self.mode
            }
        ]

        data = data.encode("ascii")
        compressed = lzma.compress(data, format=lzma.FORMAT_ALONE,
            filters=filters)

        return self.pack_int(len(compressed)) + compressed

    def pack(self):
        r = self.replay
        data = b""

        data += self.pack_byte(r.mode.value)
        data += self.pack_int(r.game_version)
        data += self.pack_string(r.beatmap_hash)
        data += self.pack_string(r.username)
        data += self.pack_string(r.replay_hash)
        data += self.pack_short(r.count_300)
        data += self.pack_short(r.count_100)
        data += self.pack_short(r.count_50)
        data += self.pack_short(r.count_geki)
        data += self.pack_short(r.count_katu)
        data += self.pack_short(r.count_miss)
        data += self.pack_int(r.score)
        data += self.pack_short(r.max_combo)
        data += self.pack_byte(r.perfect)
        data += self.pack_int(r.mods.value)
        data += self.pack_life_bar()
        data += self.pack_timestamp()
        data += self.pack_replay_data()
        data += self.pack_long(r.replay_id)

        return data


@dataclass
class Replay:
    """
    A replay found in a ``.osr`` file, or following the osr format. To create a
    replay, you likely want ``Replay.from_path``, ``Replay.from_file``, or
    ``Replay.from_string``.

    Attributes
    ----------
    mode: GameMode
        The game mode this replay was played on.
    game_version: int
        The game version this replay was played on.
    beatmap_hash: str
        The hash of the beatmap this replay was played on.
    username: str
        The user that played this replay.
    replay_hash:
        The hash of this replay.
    count_300: int
        The number of 300 judgments in this replay.
    count_100: int
        The number of 100 judgments in this replay.
    count_50: int
        The number of 50 judgments in this replay.
    count_geki: int
        The number of geki judgments in this replay.
    count_katu: int
        The number of katu judgments in this replay.
    count_miss: int
        The number of misses in this replay.
    score: int
        The score of this replay.
    max_combo: int
        The maximum combo attained in this replay.
    perfect: bool
        Whether this replay was perfect or not.
    mods: Mod
        The mods this replay was played with.
    life_bar_graph: Optional[List[LifeBarState]]
        The life bar of this replay over time.
    replay_data: List[ReplayEvent]
        The replay data of the replay, including cursor position and keys
        pressed.
    replay_id: int
        The replay id of this replay, or 0 if not submitted.
    rng_seed: Optional[int]
        The rng seed of this replay, or ``None`` if not present (typically not
        present on older replays).
    """
    mode: GameMode
    game_version: int
    beatmap_hash: str
    username: str
    replay_hash: str
    count_300: int
    count_100: int
    count_50: int
    count_geki: int
    count_katu: int
    count_miss: int
    score: int
    max_combo: int
    perfect: bool
    mods: Mod
    life_bar_graph: Optional[List[LifeBarState]]
    timestamp: datetime
    replay_data: List[ReplayEvent]
    replay_id: int
    rng_seed: Optional[int]

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

    def write_path(self, path, *, dict_size=None, mode=None):
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
            self.write_file(f, dict_size=dict_size, mode=mode)

    def write_file(self, file, *, dict_size=None, mode=None):
        """
        Writes the replay to an open file object.

        Parameters
        ----------
        file: file-like
           The file object to write to.
        """
        packed = self.pack(dict_size=dict_size, mode=mode)
        file.write(packed)

    def pack(self, *, dict_size=None, mode=None):
        """
        Returns the text representing this ``Replay``, in ``.osr`` format.
        The text returned by this method is suitable for writing to a file as a
        valid ``.osr`` file.

        Returns
        -------
        str
            The text representing this ``Replay``, in ``.osr`` format.
        """
        return _Packer(self, dict_size=dict_size, mode=mode).pack()


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
    (replay_data, _seed) = _Unpacker.parse_replay_data(data_string, mode)
    return replay_data
