from pathlib import Path
from unittest import TestCase
import datetime
from osrparse import parse_replay, parse_replay_file, ReplayEvent, GameMode, Mod

RES = Path(__file__).parent / "resources"

class TestStandardReplay(TestCase):

    @classmethod
    def setUpClass(cls):

        replay1_path =  RES / "replay.osr"
        with open(replay1_path, "rb") as f:
            data = f.read()
        cls._replays = [parse_replay(data, pure_lzma=False), parse_replay_file(replay1_path)]
        cls._combination_replay = parse_replay_file(RES / "replay2.osr")
        cls._old_replayid_replay = parse_replay_file(RES / "replay_old_replayid.osr")

    def test_replay_mode(self):
        for replay in self._replays:
            self.assertEqual(replay.game_mode, GameMode.STD, "Game mode is incorrect")

    def test_game_version(self):
        for replay in self._replays:
            self.assertEqual(replay.game_version, 20140226, "Game version is incorrect")

    def test_beatmap_hash(self):
        for replay in self._replays:
            self.assertEqual(replay.beatmap_hash, "da8aae79c8f3306b5d65ec951874a7fb", "Beatmap hash is incorrect")

    def test_player_name(self):
        for replay in self._replays:
            self.assertEqual(replay.player_name, "Cookiezi", "Player name is incorrect")

    def test_number_hits(self):
        for replay in self._replays:
            self.assertEqual(replay.number_300s, 1982, "Number of 300s is wrong")
            self.assertEqual(replay.number_100s, 1, "Number of 100s is wrong")
            self.assertEqual(replay.number_50s, 0, "Number of 50s is wrong")
            self.assertEqual(replay.gekis, 250, "Number of gekis is wrong")
            self.assertEqual(replay.katus, 1, "Number of katus is wrong")
            self.assertEqual(replay.misses, 0, "Number of misses is wrong")

    def test_max_combo(self):
        for replay in self._replays:
            self.assertEqual(replay.max_combo, 2385, "Max combo is wrong")

    def test_is_perfect_combo(self):
        for replay in self._replays:
            self.assertEqual(replay.is_perfect_combo, True, "is_perfect_combo is wrong")

    def test_nomod(self):
        for replay in self._replays:
            self.assertEqual(replay.mod_combination, Mod.NoMod, "Mod combination is wrong")

    def test_mod_combination(self):
        self.assertEqual(self._combination_replay.mod_combination, Mod.Hidden | Mod.HardRock, "Mod combination is wrong")

    def test_timestamp(self):
        for replay in self._replays:
            self.assertEqual(replay.timestamp, datetime.datetime(2013, 2, 1, 16, 31, 34), "Timestamp is wrong")

    def test_play_data(self):
        for replay in self._replays:
            self.assertIsInstance(replay.play_data[0], ReplayEvent, "Replay data is wrong")
            self.assertEqual(len(replay.play_data), 17500, "Replay data is wrong")

    def test_replay_id(self):
        for replay in self._replays:
            self.assertEqual(replay.replay_id, 1040219800)
        # old replays had game_version stored as a short, we want to make sure
        # we can parse it properly instead of erroring
        self.assertEqual(self._old_replayid_replay.replay_id, 1127598189)
