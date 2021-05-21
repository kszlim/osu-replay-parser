import os
from typing import Union

from osrparse.replay import Replay

def parse_replay(replay_data: str, pure_lzma: bool = False, decompressed_lzma: bool = False,
                 allow_unsupported_play_data: bool = False) -> Replay:
    """
    Parses a Replay from the given replay data.

    Args:
        String replay_data: The replay data from either parsing an osr file or from the api get_replay endpoint.
        Boolean pure_lzma: Whether replay_data conatins the entirety of an osr file, or only the lzma compressed
                data containing the cursor movements and keyboard presses of the player.
                If replay data was loaded from an osr, this value should be False, as an osr contains
                more information than just the lzma, such as username and game version (see
                https://osu.ppy.sh/help/wiki/osu!_File_Formats/Osr_(file_format)). If replay data
                was retrieved from the api, this value should be True, as the api only
                returns the lzma data (see https://github.com/ppy/osu-api/wiki#apiget_replay)
        Boolean decompressed_lzma: Whether replay_data is compressed lzma, or decompressed
                (and decoded to ascii) lzma. For example, the following calls are equivalent:
                ```
                >>> osrparse.parse_replay(lzma_string, pure_lzma=True)
                ```
                and
                ```
                >>> lzma_string = lzma.decompress(lzma_string).decode("ascii")
                >>> osrparse.parse_replay(lzma_string, pure_lzma=True, decompressed_lzma=True)
                ```
                This parameter only has an affect if ``pure_lzma`` is ``True``.
        Boolean allow_unsupported_play_data: Whether to allow non-Standard Modes to parse data.
    Returns:
        A Replay object with the fields specific in the Replay's init method. If pure_lzma is False, all fields will
        be filled (nonnull). If pure_lzma is True, only the play_data will be filled.
    """

    return Replay(replay_data, pure_lzma, decompressed_lzma, allow_unsupported_play_data)

def parse_replay_file(replay_path: Union[os.PathLike, str], pure_lzma: bool = False,
                      allow_unsupported_play_data: bool = False) -> Replay:
    """
    Parses a Replay from the file at the given path.

    Args:
        [String or Path]: A pathlike object representing the absolute path to the file to parse data from.
        Boolean pure_lzma: False if the file contains data equivalent to an osr file (or is itself an osr file),
                           and True if the file contains only lzma data. See parse_replay documentation for
                           more information on the difference between these two and how each affect the
                           fields in the final Replay object.
        Boolean allow_unsupported_play_data: Whether to allow non-Standard Modes to parse data.
    """

    with open(replay_path, 'rb') as f:
        data = f.read()
    return parse_replay(data, pure_lzma, allow_unsupported_play_data=allow_unsupported_play_data)
