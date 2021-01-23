import lzma
import struct
import datetime
from enum import Enum, IntFlag

# the first build with rng seed value added as the last frame in the lzma data.
VERSION_THRESHOLD = 20130319

class GameMode(Enum):
    STD    = 0
    TAIKO  = 1
    CTB    = 2
    MANIA  = 3

class Mod(IntFlag):
	NoMod       =  0,
	NoFail      =  1 << 0,
	Easy        =  1 << 1,
	TouchDevice =  1 << 2,
	Hidden      =  1 << 3,
	HardRock    =  1 << 4,
	SuddenDeath =  1 << 5,
	DoubleTime  =  1 << 6,
	Relax       =  1 << 7,
	HalfTime    =  1 << 8,
	Nightcore   =  1 << 9,
	Flashlight  =  1 << 10,
	Autoplay    =  1 << 11,
	SpunOut     =  1 << 12,
	Autopilot   =  1 << 13,
	Perfect     =  1 << 14,
	Key4        =  1 << 15,
	Key5        =  1 << 16,
	Key6        =  1 << 17,
	Key7        =  1 << 18,
	Key8        =  1 << 19,
	FadeIn      =  1 << 20,
	Random      =  1 << 21,
	Cinema      =  1 << 22,
	Target      =  1 << 23,
	Key9        =  1 << 24,
	KeyCoop     =  1 << 25,
	Key1        =  1 << 26,
	Key3        =  1 << 27,
	Key2        =  1 << 28,
	ScoreV2     =  1 << 29,
	Mirror      =  1 << 30


class ReplayEvent(object):
    def __init__(self, time_since_previous_action, x, y, keys_pressed):
        self.time_since_previous_action = time_since_previous_action
        self.x = x
        self.y = y
        self.keys_pressed = keys_pressed

    def __str__(self):
        return f"{self.time_since_previous_action} ({self.x}, {self.y}) {self.keys_pressed}"

    def __eq__(self, other):
        if not isinstance(other, ReplayEvent):
            return False
        return (self.time_since_previous_action == other.time_since_previous_action
            and self.x == other.x and self.y == other.y and self.keys_pressed == other.keys_pressed)

    def __hash__(self):
        return hash((self.time_since_previous_action, self.x, self.y, self.keys_pressed))

class Replay(object):
    _BYTE = 1
    _SHORT = 2
    _INT = 4
    _LONG = 8

    def __init__(self, replay_data, pure_lzma, decompressed_lzma):
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
        self.timestamp = datetime.datetime.min + datetime.timedelta(microseconds=t/10)
        self.offset += struct.calcsize(format_specifier)

    def _parse_play_data(self, replay_data):
        offset_end = self.offset+self.replay_length
        if self.game_mode != GameMode.STD:
            self.play_data = None
        else:
            datastring = lzma.decompress(replay_data[self.offset:offset_end], format=lzma.FORMAT_AUTO).decode('ascii')[:-1]
            events = [eventstring.split('|') for eventstring in datastring.split(',')]
            self.play_data = [ReplayEvent(int(event[0]), float(event[1]), float(event[2]), int(event[3])) for event in events]
        self.offset = offset_end

        if self.game_version >= VERSION_THRESHOLD and self.play_data:
            if self.play_data[-1].time_since_previous_action != -12345:
                print("The RNG seed value was expected in the last frame, but was not found. "
                      "\nGame Version: {}, version threshold: {}, replay hash: {}, mode: {}".format(self.game_version, VERSION_THRESHOLD, self.replay_hash, "osr"))
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
        self.play_data = [ReplayEvent(int(event[0]), float(event[1]), float(event[2]), int(event[3])) for event in events]

        if self.play_data[-1].time_since_previous_action == -12345:
            del self.play_data[-1]

    def _parse_replay_id(self, replay_data):
        format_specifier = "<q"
        self.replay_id = struct.unpack_from(format_specifier, replay_data, self.offset)[0]

def parse_replay(replay_data, pure_lzma=False, decompressed_lzma=False):
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
    Returns:
        A Replay object with the fields specific in the Replay's init method. If pure_lzma is False, all fields will
        be filled (nonnull). If pure_lzma is True, only the play_data will be filled.
    """

    return Replay(replay_data, pure_lzma, decompressed_lzma)

def parse_replay_file(replay_path, pure_lzma=False):
    """
    Parses a Replay from the file at the given path.

    Args:
        [String or Path]: A pathlike object representing the absolute path to the file to parse data from.
        Boolean pure_lzma: False if the file contains data equivalent to an osr file (or is itself an osr file),
                           and True if the file contains only lzma data. See parse_replay documentation for
                           more information on the difference between these two and how each affect the
                           fields in the final Replay object.
    """

    with open(replay_path, 'rb') as f:
        data = f.read()
    return parse_replay(data, pure_lzma)
