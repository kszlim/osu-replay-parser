from enum import Enum, IntFlag

class GameMode(Enum):
    STD    = 0
    TAIKO  = 1
    CTB    = 2
    MANIA  = 3

class Mod(IntFlag):
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
    M1    = 1 << 0
    M2    = 1 << 1
    K1    = 1 << 2
    K2    = 1 << 3
    SMOKE = 1 << 4

class ReplayEvent:
    def __init__(self, time_delta: int, x: float, y: float,
        keys: int):
        self.time_delta = time_delta
        self.x = x
        self.y = y
        self.keys = Key(keys)

    def __str__(self):
        return (f"{self.time_delta} ({self.x}, {self.y}) "
            f"{self.keys}")

    def __eq__(self, other):
        if not isinstance(other, ReplayEvent):
            return False
        t = self.time_delta
        other_t = other.time_delta
        return (t == other_t and self.x == other.x and self.y == other.y
            and self.keys == other.keys)

    def __hash__(self):
        return hash((self.time_delta, self.x, self.y,
            self.keys))
