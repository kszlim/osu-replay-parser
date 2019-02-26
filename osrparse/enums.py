from enum import Enum


class GameMode(Enum):
    Standard = 0
    Taiko = 1
    CatchTheBeat = 2
    Osumania = 3

# see https://github.com/ppy/osu-api/wiki#mods
class Mod(Enum):
    NoMod          = 0
    NoFail         = 1
    Easy           = 2
    TouchDevice    = 4
    Hidden         = 8
    HardRock       = 16
    SuddenDeath    = 32
    DoubleTime     = 64
    Relax          = 128
    HalfTime       = 256
    Nightcore      = 512
    Flashlight     = 1024
    Autoplay       = 2048
    SpunOut        = 4096
    Autopilot      = 8192
    Perfect        = 16384
    Key4           = 32768
    Key5           = 65536
    Key6           = 131072
    Key7           = 262144
    Key8           = 524288
    keyMod         = 1015808
    FadeIn         = 1048576
    Random         = 2097152
    Cinema         = 4194304
    Target         = 8388608
    Key9           = 16777216
    KeyCoop        = 33554432
    Key1           = 67108864
    Key3           = 134217728
    Key2           = 268435456
    ScoreV2        = 536870912
    LastMod        = 1073741824
