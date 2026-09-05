from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from os import PathLike
from typing import BinaryIO

from osrparse import _native
from osrparse.utils import GameMode, LifeBarState, Mod, ReplayEvent
from osrparse.utils import Key as Key
from osrparse.utils import KeyMania as KeyMania
from osrparse.utils import KeyTaiko as KeyTaiko
from osrparse.utils import ReplayEventCatch as ReplayEventCatch
from osrparse.utils import ReplayEventMania as ReplayEventMania
from osrparse.utils import ReplayEventOsu as ReplayEventOsu
from osrparse.utils import ReplayEventTaiko as ReplayEventTaiko


class _Unpacker:
    """Compatibility adapter for the former private unpacker helpers."""

    def __init__(self, replay_data):
        self.replay_data = replay_data
        self.offset = 0

    def unpack(self):
        return _native.unpack(bytes(self.replay_data), Replay)

    def unpack_timestamp(self):
        timestamp = _native.unpack_timestamp(bytes(self.replay_data[self.offset :]))
        self.offset += 8
        return timestamp

    @staticmethod
    def parse_replay_data(replay_data_str, mode):
        return _native.parse_events(replay_data_str, mode)


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
    life_bar_graph: list[LifeBarState] | None
        The life bar of this replay over time.
    replay_data: list[ReplayEvent]
        The replay data of the replay, including cursor position and keys
        pressed.
    replay_id: int
        The replay id of this replay, or 0 if not submitted.
    rng_seed: int | None
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
    life_bar_graph: list[LifeBarState] | None
    timestamp: datetime
    replay_data: list[ReplayEvent]
    replay_id: int
    rng_seed: int | None

    @staticmethod
    def from_path(path: str | bytes | PathLike[str] | PathLike[bytes]) -> Replay:
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
    def from_file(file: BinaryIO) -> Replay:
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
    def from_string(data: bytes | bytearray) -> Replay:
        """
        Creates a new ``Replay`` object from bytes containing ``.osr`` data.

        Parameters
        ----------
        data: bytes or bytearray
           The binary data to parse.

        Returns
        -------
        Replay
            The parsed replay object.
        """
        return _native.unpack(
            bytes(data) if isinstance(data, bytearray) else data, Replay
        )

    def write_path(
        self,
        path: str | bytes | PathLike[str] | PathLike[bytes],
        *,
        dict_size: int | None = None,
        mode: int | None = None,
    ) -> None:
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

    def write_file(
        self,
        file: BinaryIO,
        *,
        dict_size: int | None = None,
        mode: int | None = None,
    ) -> None:
        """
        Writes the replay to an open file object.

        Parameters
        ----------
        file: file-like
           The file object to write to.
        """
        packed = self.pack(dict_size=dict_size, mode=mode)
        file.write(packed)

    def pack(self, *, dict_size: int | None = None, mode: int | None = None) -> bytes:
        """
        Returns the bytes representing this ``Replay``, in ``.osr`` format.
        The bytes returned by this method are suitable for writing to a file as a
        valid ``.osr`` file.

        Returns
        -------
        bytes
            The bytes representing this ``Replay``, in ``.osr`` format.
        """
        return _native.pack(self, dict_size=dict_size, mode=mode)


def parse_replay_data(
    data_string: str | bytes,
    *,
    decoded: bool = False,
    decompressed: bool = False,
    mode: GameMode = GameMode.STD,
) -> list[ReplayEvent]:
    """
    Parses the replay data portion of a replay from a string. This method is
    suitable for use with the replay data returned by api v1's ``/get_replay``
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
    return _native.parse_replay_data(
        data_string, decoded=bool(decoded), decompressed=bool(decompressed), mode=mode
    )
