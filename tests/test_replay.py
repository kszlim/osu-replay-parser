from pathlib import Path
from unittest import TestCase
from datetime import datetime, timezone
from osrparse import (ReplayEventOsu, GameMode, Mod, ReplayEventTaiko,
    ReplayEventCatch, ReplayEventMania, Replay)

RES = Path(__file__).parent / "resources"

class TestStandardReplay(TestCase):

    @classmethod
    def setUpClass(cls):

        replay1_path =  RES / "replay.osr"
        with open(replay1_path, "rb") as f:
            data = f.read()
        cls._replays = [Replay.from_string(data), Replay.from_path(replay1_path)]
        cls._combination_replay = Replay.from_path(RES / "replay2.osr")
        cls._old_replayid_replay = Replay.from_path(RES / "replay_old_replayid.osr")

    def test_replay_mode(self):
        for replay in self._replays:
            self.assertEqual(replay.mode, GameMode.STD, "Game mode is incorrect")

    def test_game_version(self):
        for replay in self._replays:
            self.assertEqual(replay.game_version, 20140226, "Game version is incorrect")

    def test_beatmap_hash(self):
        for replay in self._replays:
            self.assertEqual(replay.beatmap_hash, "da8aae79c8f3306b5d65ec951874a7fb", "Beatmap hash is incorrect")

    def test_player_name(self):
        for replay in self._replays:
            self.assertEqual(replay.username, "Cookiezi", "Player name is incorrect")

    def test_number_hits(self):
        for replay in self._replays:
            self.assertEqual(replay.count_300, 1982, "Number of 300s is wrong")
            self.assertEqual(replay.count_100, 1, "Number of 100s is wrong")
            self.assertEqual(replay.count_50, 0, "Number of 50s is wrong")
            self.assertEqual(replay.count_geki, 250, "Number of gekis is wrong")
            self.assertEqual(replay.count_katu, 1, "Number of katus is wrong")
            self.assertEqual(replay.count_miss, 0, "Number of misses is wrong")

    def test_max_combo(self):
        for replay in self._replays:
            self.assertEqual(replay.max_combo, 2385, "Max combo is wrong")

    def test_is_perfect_combo(self):
        for replay in self._replays:
            self.assertEqual(replay.perfect, True, "is_perfect_combo is wrong")

    def test_nomod(self):
        for replay in self._replays:
            self.assertEqual(replay.mods, Mod.NoMod, "Mod combination is wrong")

    def test_mod_combination(self):
        self.assertEqual(self._combination_replay.mods, Mod.Hidden | Mod.HardRock, "Mod combination is wrong")

    def test_timestamp(self):
        for replay in self._replays:
            self.assertEqual(replay.timestamp, datetime(2013, 2, 1, 16, 31, 34, tzinfo=timezone.utc), "Timestamp is wrong")

    def test_play_data(self):
        for replay in self._replays:
            self.assertIsInstance(replay.replay_data[0], ReplayEventOsu, "Replay data is wrong")
            self.assertEqual(len(replay.replay_data), 17498, "Replay data is wrong")

    def test_replay_id(self):
        for replay in self._replays:
            self.assertEqual(replay.replay_id, 1040219800)
        # old replays had game_version stored as a short, we want to make sure
        # we can parse it properly instead of erroring
        self.assertEqual(self._old_replayid_replay.replay_id, 1127598189)

class TestTaikoReplay(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.replay = Replay.from_path(RES / "taiko.osr")

    def test_play_data(self):
        replay_data = self.replay.replay_data
        self.assertIsInstance(replay_data[0], ReplayEventTaiko, "Replay data is wrong")
        self.assertEqual(len(replay_data), 17473, "Replay data is wrong")

class TestCatchReplay(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.replay = Replay.from_path(RES / "ctb.osr")

    def test_play_data(self):
        replay_data = self.replay.replay_data
        self.assertIsInstance(replay_data[0], ReplayEventCatch, "Replay data is wrong")
        self.assertEqual(len(replay_data), 10437, "Replay data is wrong")

class TestManiaReplay(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.replay = Replay.from_path(RES / "mania.osr")

    def test_play_data(self):
        play_data = self.replay.replay_data
        self.assertIsInstance(play_data[0], ReplayEventMania, "Replay data is wrong")
        self.assertEqual(len(play_data), 17430, "Replay data is wrong")

class TestLazerReplay(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.replay = Replay.from_path(RES / "lazer_standard_format.osr")

    def test_play_data(self):
        # lazer replays do some unusual things with rng seeds compared to
        # stable, so make sure it parses ok
        self.assertEqual(self.replay.rng_seed, 0)

    def test_score_info(self):
        self.assertEqual(self.replay.score_info, None)

class TestLazerReplayWithScoreInfo(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.replay = Replay.from_path(RES / "lazer_with_score_info.osr")

    def test_score_info(self):
        self.assertEqual(self.replay.score_info.client_version, "2024.906.2-lazer", "Client version is wrong")
        self.assertEqual(self.replay.score_info.online_id, 3510429377, "Online ID is wrong")
        self.assertEqual(self.replay.score_info.rank, "A", "Rank is wrong")
        self.assertEqual(self.replay.score_info.total_score_without_mods, 475205, "Total score without mods is wrong")
        self.assertEqual(self.replay.score_info.user_id, 9343913, "User ID is wrong")

        self.assertEqual(self.replay.score_info.mods[0]["acronym"], "HD", "First mod is wrong")
        self.assertEqual(self.replay.score_info.mods[1]["acronym"], "RX", "Second mod is wrong")

        self.assertEqual(self.replay.score_info.statistics["miss"], 55, "Miss count is wrong")
        self.assertEqual(self.replay.score_info.statistics["meh"], 2, "Meh count is wrong")
        self.assertEqual(self.replay.score_info.statistics["ok"], 25, "Ok count is wrong")
        self.assertEqual(self.replay.score_info.statistics["great"], 850, "Great count is wrong")
        self.assertEqual(self.replay.score_info.statistics["large_tick_hit"], 53, "Large tick hit count is wrong")
        self.assertEqual(self.replay.score_info.statistics["ignore_miss"], 13, "Ignore miss count is wrong")
        self.assertEqual(self.replay.score_info.statistics["ignore_hit"], 248, "Ignore hit count is wrong")
        self.assertEqual(self.replay.score_info.statistics["slider_tail_hit"], 243, "Slider tail hit count is wrong")

        self.assertEqual(self.replay.score_info.maximum_statistics["great"], 932, "Great count is wrong")
        self.assertEqual(self.replay.score_info.maximum_statistics["large_tick_hit"], 53, "Large tick hit count is wrong")
        self.assertEqual(self.replay.score_info.maximum_statistics["ignore_hit"], 252, "Ignore hit count is wrong")
        self.assertEqual(self.replay.score_info.maximum_statistics["slider_tail_hit"], 252, "Slider tail hit count is wrong")


