from pathlib import Path
from unittest import TestCase
from datetime import datetime, timezone
from osrparse import (ReplayEventOsu, GameMode, Mod, ReplayEventTaiko,
    ReplayEventCatch, ReplayEventMania, Replay)
import glob


RES = Path(__file__).parent / "resources"

class TestReplay(TestCase):

    def test_complete_legacy_equivalence(self):
        replay_paths = glob.glob(str(RES / "*.osr"))
        legacy_replays = [Replay.from_path(path, use_legacy_parser=True) for path in replay_paths]
        replays = Replay.from_paths(replay_paths)
        for legacy_replay, replay in zip(legacy_replays, replays):
            self.assertEqual(legacy_replay.replay_data, replay.replay_data)

class TestStandardReplay(TestCase):

    @classmethod
    def setUpClass(cls):

        replay1_path =  RES / "replay.osr"
        with open(replay1_path, "rb") as f:
            data = f.read()
        cls._replays = [Replay.from_path(replay1_path), Replay.from_path(replay1_path, use_legacy_parser=True), Replay.from_string(data), Replay.from_string(data, use_legacy_parser=True)]
        cls._combination_replay = Replay.from_path(RES / "replay2.osr")
        cls._old_replayid_replay = Replay.from_path(RES / "replay_old_replayid.osr")
        cls._osr_replay = Replay.from_path(replay1_path, use_legacy_parser=True)
        cls._osu_core_replay = Replay.from_path(replay1_path)

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
            self.assertEqual(replay.mods.value, Mod.NoMod.value, "Mod combination is wrong")

    def test_mod_combination(self):
        self.assertEqual(self._combination_replay.mods.value, (Mod.Hidden | Mod.HardRock).value, "Mod combination is wrong")

    def test_timestamp(self):
        for replay in self._replays:
            self.assertEqual(replay.timestamp, datetime(2013, 2, 1, 16, 31, 34, tzinfo=timezone.utc), "Timestamp is wrong")

    def test_play_data(self):
        for replay in self._replays:
            self.assertIsInstance(replay.replay_data[0], ReplayEventOsu, "Replay data is wrong")
            self.assertEqual(len(replay.replay_data), 17500, "Replay data is wrong")

    def test_replay_id(self):
        for replay in self._replays:
            self.assertEqual(replay.replay_id, 1040219800)
        # old replays had game_version stored as a short, we want to make sure
        # we can parse it properly instead of erroring
        self.assertEqual(self._old_replayid_replay.replay_id, 1127598189)

    def test_legacy_equivalence(self):
        osr_replay = self._osr_replay
        core_replay = self._osu_core_replay
        for (core_replay_event, replay_event) in zip(core_replay.replay_data, osr_replay.replay_data):
            self.assertEqual(core_replay_event.time_delta, replay_event.time_delta)
            self.assertEqual(core_replay_event.x, replay_event.x)
            self.assertEqual(core_replay_event.y, replay_event.y)
            self.assertEqual(core_replay_event.keys.value, replay_event.keys.value)

class TestTaikoReplay(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.replay = Replay.from_path(RES / "taiko.osr")

    def test_play_data(self):
        replay_data = self.replay.replay_data
        self.assertIsInstance(replay_data[0], ReplayEventTaiko, "Replay data is wrong")
        self.assertEqual(len(replay_data), 17475, "Replay data is wrong")

class TestCatchReplay(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.replay = Replay.from_path(RES / "ctb.osr")
        cls.replay2 = Replay.from_path(RES / "ctb.osr", use_legacy_parser=True)

    def test_play_data(self):
        replay_data = self.replay.replay_data
        self.assertIsInstance(replay_data[0], ReplayEventCatch, "Replay data is wrong")
        self.assertEqual(len(replay_data), 10439, "Replay data is wrong")

class TestManiaReplay(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.replay = Replay.from_path(RES / "mania.osr")

    def test_play_data(self):
        replay_data = self.replay.replay_data
        self.assertIsInstance(replay_data[0], ReplayEventMania, "Replay data is wrong")
        self.assertEqual(len(replay_data), 17432, "Replay data is wrong")

class TestLazerReplay(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.replay = Replay.from_path(RES / "lazer_standard_format.osr")

    def test_play_data(self):
        # lazer replays do some unusual things with rng seeds compared to
        # stable, so make sure it parses ok
        self.assertEqual(self.replay.rng_seed, 0)
