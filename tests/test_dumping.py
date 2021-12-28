from pathlib import Path
from unittest import TestCase
from tempfile import TemporaryDirectory

from osrparse import parse_replay_file


RES = Path(__file__).parent / "resources"


class TestDumping(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.replay = parse_replay_file(RES / "replay.osr")

    def test_dumping(self):
        with TemporaryDirectory() as tempdir:
            r2_path = Path(tempdir) / "dumped.osr"
            self.replay.dump(r2_path)
            r2 = parse_replay_file(r2_path)

        # `replay_length` is intentionally not tested for equality here, as the
        # length of the compressed replay data may change after dumping due to
        # varying lzma settings.
        attrs = ["game_mode", "game_version", "beatmap_hash", "player_name",
            "replay_hash", "number_300s", "number_100s", "number_50s", "gekis",
            "katus", "misses", "score", "max_combo", "is_perfect_combo",
            "mod_combination", "life_bar_graph", "timestamp", "play_data",
            "replay_id"]
        for attr in attrs:
            self.assertEqual(getattr(self.replay, attr), getattr(r2, attr),
                f"{attr} is wrong")
