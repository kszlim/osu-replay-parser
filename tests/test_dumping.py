from pathlib import Path
from unittest import TestCase
from tempfile import TemporaryDirectory

from osrparse import Replay


RES = Path(__file__).parent / "resources"


class TestDumping(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.replay = Replay.from_path(RES / "replay.osr")

    def test_dumping(self):
        packed = self.replay.pack()
        r2 = Replay.from_string(packed)

        # `replay_length` is intentionally not tested for equality here, as the
        # length of the compressed replay data may change after dumping due to
        # varying lzma settings.
        attrs = ["mode", "game_version", "beatmap_hash", "username",
            "replay_hash", "count_300", "count_100", "count_50", "count_geki",
            "count_katu", "count_miss", "score", "max_combo", "perfect",
            "mods", "life_bar_graph", "timestamp", "replay_data",
            "replay_id"]
        for attr in attrs:
            self.assertEqual(getattr(self.replay, attr), getattr(r2, attr), attr)
