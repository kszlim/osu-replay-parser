from .enums import GameMode, ModCombination
import lzma


class ReplayEvent(object):
    def __init__(self, time_since_previous_action, x, y, keys_pressed):
        self.time_since_previous_action = time_since_previous_action
        self.x = x
        self.y = y
        self.keys_pressed = keys_pressed


class Replay(object):
    __BYTE = 1
    __SHORT = 2
    __INT = 4
    __LONG = 8

    #Order of field initilization matters.
    def __init__(self, replay_data):
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
        self.parse_replay_and_initialize_fields(replay_data)

    def parse_replay_and_initialize_fields(self, replay_data):
        self.parse_game_mode(replay_data)
        self.parse_game_version(replay_data)
        self.parse_beatmap_hash(replay_data)
        self.parse_player_name(replay_data)
        self.parse_replay_hash(replay_data)
        self.parse_300s(replay_data)
        self.parse_100s(replay_data)
        self.parse_50s(replay_data)
        self.parse_gekis(replay_data)
        self.parse_katus(replay_data)
        self.parse_misses(replay_data)
        self.parse_score(replay_data)
        self.parse_max_combo(replay_data)
        self.parse_is_perfect_combo(replay_data)
        self.parse_mod_combination(replay_data)
        self.parse_life_bar_graph(replay_data)
        self.parse_timestamp(replay_data)
        self.parse_play_data(replay_data)

    @staticmethod
    def __parse_as_int(bytestring):
        return int.from_bytes(bytestring, byteorder='little')

    def __decode(self, binarystream):
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

    def parse_game_mode(self, replay_data):
        offset_end = self.offset + Replay.__BYTE
        self.game_mode = GameMode(self.__parse_as_int(replay_data[self.offset:offset_end]))
        self.offset = offset_end

    def parse_game_version(self, replay_data):
        offset_end = self.offset + Replay.__INT
        self.game_version = self.__parse_as_int(replay_data[self.offset:offset_end])
        self.offset = offset_end

    def parse_player_name(self, replay_data):
        self.player_name = self.parse_string(replay_data)

    def parse_string(self, replay_data):
        if replay_data[self.offset] == 0x00:
            self.offset += Replay.__BYTE
        elif replay_data[self.offset] == 0x0b:
            self.offset += Replay.__BYTE
            string_length = self.__decode(replay_data)
            offset_end = self.offset + string_length
            string = replay_data[self.offset:offset_end].decode("utf-8")
            self.offset = offset_end
            return string
        else:
            #TODO: Replace with custom exception
            raise Exception("Invalid replay")

    def parse_beatmap_hash(self, replay_data):
        self.beatmap_hash = self.parse_string(replay_data)

    def parse_replay_hash(self, replay_data):
        self.replay_hash = self.parse_string(replay_data)

    def parse_300s(self, replay_data):
        offset_end = self.offset + Replay.__SHORT
        self.number_300s = self.__parse_as_int(replay_data[self.offset:offset_end])
        self.offset = offset_end

    def parse_100s(self, replay_data):
        offset_end = self.offset + Replay.__SHORT
        self.number_100s = self.__parse_as_int(replay_data[self.offset:offset_end])
        self.offset = offset_end

    def parse_50s(self, replay_data):
        offset_end = self.offset + Replay.__SHORT
        self.number_50s = self.__parse_as_int(replay_data[self.offset:offset_end])
        self.offset = offset_end

    def parse_gekis(self, replay_data):
        offset_end = self.offset + Replay.__SHORT
        self.gekis = self.__parse_as_int(replay_data[self.offset:offset_end])
        self.offset = offset_end

    def parse_katus(self, replay_data):
        offset_end = self.offset + Replay.__SHORT
        self.katus = self.__parse_as_int(replay_data[self.offset:offset_end])
        self.offset = offset_end

    def parse_misses(self, replay_data):
        offset_end = self.offset + Replay.__SHORT
        self.misses = self.__parse_as_int(replay_data[self.offset:offset_end])
        self.offset = offset_end

    def parse_score(self, replay_data):
        offset_end = self.offset + Replay.__INT
        self.score = self.__parse_as_int(replay_data[self.offset:offset_end])
        self.offset = offset_end

    def parse_max_combo(self, replay_data):
        offset_end = self.offset + Replay.__SHORT
        self.max_combo = self.__parse_as_int(replay_data[self.offset:offset_end])
        self.offset = offset_end

    def parse_is_perfect_combo(self, replay_data):
        offset_end = self.offset + Replay.__BYTE
        self.is_perfect_combo = bool(self.__parse_as_int(replay_data[self.offset:offset_end]))
        self.offset = offset_end

    def parse_mod_combination(self, replay_data):

        # Generator yielding value of each bit in an integer if it's set + value
        # of LSB no matter what .
        def bits(n):
            if n == 0:
                yield 0
            while n:
                b = n & (~n+1)
                yield b
                n ^= b

        offset_end = self.offset + Replay.__INT
        bit_values_gen = bits(self.__parse_as_int(replay_data[self.offset:offset_end]))
        self.mod_combination = frozenset(ModCombination(mod_val) for mod_val in bit_values_gen)
        self.offset = offset_end

    def parse_life_bar_graph(self, replay_data):
        self.life_bar_graph = self.parse_string(replay_data)

    def parse_timestamp(self, replay_data):
        offset_end = self.offset + Replay.__LONG
        self.timestamp = self.__parse_as_int(replay_data[self.offset:offset_end])
        self.offset = offset_end

    def parse_replay_data_length(self, replay_data):
        offset_end = self.offset + Replay.__INT
        self.__replay_length = self.__parse_as_int(replay_data[self.offset:offset_end])
        self.offset = offset_end

    def parse_play_data(self, replay_data):
        self.parse_replay_data_length(replay_data)
        offset_end = self.offset+self.__replay_length
        datastring = lzma.decompress(replay_data[self.offset:offset_end], format=lzma.FORMAT_AUTO).decode('ascii')[:-1]
        events = [eventstring.split('|') for eventstring in datastring.split(',')]
        self.play_data = [ReplayEvent(int(event[0]), float(event[1]), float(event[2]), int(event[3])) for event in events]
        self.offset = offset_end

def parse_replay(replay_data):
    return Replay(replay_data)

def parse_replay_file(replay_path):
    with open(replay_path, 'rb') as f:
        data = f.read()
    return parse_replay(data)
