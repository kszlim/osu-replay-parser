from importlib import metadata

from osrparse.replay import Replay, ReplayData, parse_replay_data
from osrparse.utils import (
    GameMode,
    Key,
    KeyMania,
    KeyTaiko,
    LifeBarState,
    Mod,
    ReplayEvent,
    ReplayEventCatch,
    ReplayEventMania,
    ReplayEventOsu,
    ReplayEventTaiko,
)

__version__ = metadata.version(__package__)

__all__ = [
    "GameMode",
    "Mod",
    "Replay",
    "ReplayData",
    "ReplayEvent",
    "Key",
    "ReplayEventOsu",
    "ReplayEventTaiko",
    "ReplayEventMania",
    "ReplayEventCatch",
    "KeyTaiko",
    "KeyMania",
    "parse_replay_data",
    "LifeBarState",
]
