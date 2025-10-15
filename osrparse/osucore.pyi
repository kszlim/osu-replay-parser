from typing import List

def parse_replay_from_bytes(data: bytes, header_only: bool = False):
    ...

def parse_replay_data(data: bytes, game_mode: GameMode):
    ...

def parse_replay_from_path(path: str,):
    ...

def parse_replays_from_paths(paths: List[str], header_only: bool = False):
    ...

class GameMode:
    """
    An osu! game mode.
    """
    STD: int
    TAIKO : int
    CTB: int
    MANIA: int

class Mod:
    """
    An osu! mod, or combination of mods.
    """
    NoMod: int
    NoFail: int
    Easy: int
    TouchDevice: int
    Hidden: int
    HardRock: int
    SuddenDeath: int
    DoubleTime: int
    Relax: int
    HalfTime: int
    Nightcore: int
    Flashlight: int
    Autoplay: int
    SpunOut: int
    Autopilot: int
    Perfect: int
    Key4: int
    Key5: int
    Key6: int
    Key7: int
    Key8: int
    FadeIn: int
    Random: int
    Cinema: int
    Target: int
    Key9: int
    KeyCoop: int
    Key1: int
    Key3: int
    Key2: int
    ScoreV2: int
    Mirror: int

class Key:
    """
    A key that can be pressed during osu!standard gameplay - mouse 1 and 2, key
    1 and 2, and smoke.
    """
    M1: int
    M2: int
    K1: int
    K2: int
    SMOKE: int

class KeyTaiko:
    """
    A key that can be pressed during osu!taiko gameplay.
    """
    LEFT_DON: int
    LEFT_KAT: int
    RIGHT_DON: int
    RIGHT_KAT: int

class KeyMania:
    """
    A key that can be pressed during osu!mania gameplay
    """
    K1: int
    K2: int
    K3: int
    K4: int
    K5: int
    K6: int
    K7: int
    K8: int
    K9: int
    K10: int
    K11: int
    K12: int
    K13: int
    K14: int
    K15: int
    K16: int
    K17: int
    K18: int

# the osr format for non-std gamemodes isn't document on the wiki. Here's
# the reference I used for non-std replay events below:
# https://github.com/kszlim/osu-replay-parser/pull/27#issuecomment-845679072.

class ReplayEventOsu:
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

class ReplayEventTaiko:
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

class ReplayEventCatch:
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

class ReplayEventMania:
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
