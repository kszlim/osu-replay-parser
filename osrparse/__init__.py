from importlib import metadata

from osrparse.utils import (GameMode, Mod, Key, ReplayEvent, ReplayEventOsu,
    ReplayEventTaiko, ReplayEventMania, ReplayEventCatch, KeyTaiko, KeyMania)
from osrparse.replay import Replay, parse_replay_data

__version__ = metadata.version(__package__)

__all__ = ["GameMode", "Mod", "Replay", "ReplayEvent", "Key",
    "ReplayEventOsu", "ReplayEventTaiko", "ReplayEventMania",
    "ReplayEventCatch", "KeyTaiko", "KeyMania", "parse_replay_data"]
