from enum import Enum, IntFlag
from dataclasses import dataclass

class GameMode(Enum):
    """
    An osu! game mode.
    """
    STD    = 0
    TAIKO  = 1
    CTB    = 2
    MANIA  = 3

class Mod(IntFlag):
    """
    An osu! mod, or combination of mods.
    """
    NoMod       =  0
    NoFail      =  1 << 0
    Easy        =  1 << 1
    TouchDevice =  1 << 2
    Hidden      =  1 << 3
    HardRock    =  1 << 4
    SuddenDeath =  1 << 5
    DoubleTime  =  1 << 6
    Relax       =  1 << 7
    HalfTime    =  1 << 8
    Nightcore   =  1 << 9
    Flashlight  =  1 << 10
    Autoplay    =  1 << 11
    SpunOut     =  1 << 12
    Autopilot   =  1 << 13
    Perfect     =  1 << 14
    Key4        =  1 << 15
    Key5        =  1 << 16
    Key6        =  1 << 17
    Key7        =  1 << 18
    Key8        =  1 << 19
    FadeIn      =  1 << 20
    Random      =  1 << 21
    Cinema      =  1 << 22
    Target      =  1 << 23
    Key9        =  1 << 24
    KeyCoop     =  1 << 25
    Key1        =  1 << 26
    Key3        =  1 << 27
    Key2        =  1 << 28
    ScoreV2     =  1 << 29
    Mirror      =  1 << 30

class Key(IntFlag):
    """
    A key that can be pressed during osu!standard gameplay - mouse 1 and 2, key
    1 and 2, and smoke.
    """
    M1    = 1 << 0
    M2    = 1 << 1
    K1    = 1 << 2
    K2    = 1 << 3
    SMOKE = 1 << 4

class KeyTaiko(IntFlag):
    """
    A key that can be pressed during osu!taiko gameplay.
    """
    LEFT_DON  = 1 << 0
    LEFT_KAT  = 1 << 1
    RIGHT_DON = 1 << 2
    RIGHT_KAT = 1 << 3

class KeyMania(IntFlag):
    """
    A key that can be pressed during osu!mania gameplay
    """
    K1 = 1 << 0
    K2 = 1 << 1
    K3 = 1 << 2
    K4 = 1 << 3
    K5 = 1 << 4
    K6 = 1 << 5
    K7 = 1 << 6
    K8 = 1 << 7
    K9 = 1 << 8
    K10 = 1 << 9
    K11 = 1 << 10
    K12 = 1 << 11
    K13 = 1 << 12
    K14 = 1 << 13
    K15 = 1 << 14
    K16 = 1 << 15
    K17 = 1 << 16
    K18 = 1 << 17

# the osr format for non-std gamemodes isn't document on the wiki. Here's
# the reference I used for non-std replay events below:
# https://github.com/kszlim/osu-replay-parser/pull/27#issuecomment-845679072.

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

@dataclass
class ReplayEventOsu(ReplayEvent):
    """
    A single frame in an osu!standard replay.

    Attributes
    ----------
    time_delta: int
        The time since the previous event (ie frame).
    x: float
        The x position of the cursor.
    y: float
        The y position of the cursor.
    keys: Key
        The keys pressed.
    """
    x: float
    y: float
    keys: Key

@dataclass
class ReplayEventTaiko(ReplayEvent):
    """
    A single frame in an osu!taiko replay.

    Attributes
    ----------
    time_delta: int
        The time since the previous event (ie frame).
    x: int
        Unknown what this represents. Always one of 0, 320, or 640, depending on
        ``keys``.
    keys: KeyTaiko
        The keys pressed.
    """
    # we have no idea what this is supposed to represent. It's always one of 0,
    # 320, or 640, depending on `keys`. Leaving untouched for now.
    x: int
    keys: KeyTaiko

@dataclass
class ReplayEventCatch(ReplayEvent):
    """
    A single frame in an osu!catch replay.

    Attributes
    ----------
    time_delta: int
        The time since the previous event (ie frame).
    x: float
        The x position of the player.
    dashing: bool
        Whether we are dashing or not.
    """
    x: float
    dashing: bool

@dataclass
class ReplayEventMania(ReplayEvent):
    """
    A single frame in an osu!mania replay.

    Attributes
    ----------
    time_delta: int
        The time since the previous event (ie frame).
    keys: KeyMania
        The keys pressed.
    """
    keys: KeyMania

@dataclass
class LifeBarState:
    """
    A state of the lifebar shown on the results screen, at a particular point in
    time.

    Attributes
    ----------
    time: int
        The time, in ms, this life bar state corresponds to in the replay.
        The time since the previous event (ie frame).
    life: float
        The amount of life at this life bar state.
    """
    time: int
    life: float
