from osucore import GameMode, Mod, Key, KeyMania, KeyTaiko, ReplayEventOsu, ReplayEventTaiko, ReplayEventMania, ReplayEventCatch, LifeBarState
from dataclasses import dataclass

@dataclass
class ReplayEvent:
    """
    Base class for an event (ie a frame) in a replay.

    Attributes
    ----------
    time_delta: int
        The time since the previous event (ie frame).
    """
    time_delta: int
