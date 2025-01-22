from datetime import timezone

from hypothesis.strategies import (integers, characters, text, booleans,
    composite, from_type, lists, just, datetimes, floats, builds, one_of)

from osrparse import (Replay, GameMode, Mod, ReplayEventOsu, ReplayEventMania,
    ReplayEventCatch, ReplayEventTaiko, KeyTaiko, KeyMania, Key)
from osrparse.utils import LifeBarState

def utf8():
    return text(characters(codec='utf-8'))

def shorts():
    return integers(0, 2 ** 16 - 1)

def uints():
    return integers(0, 2 ** 32 - 1)

def ints():
    return integers(-2 ** 31, 2 ** 31 - 1)

def longs():
    r = 2**63 - 1
    return integers(-r, r)

def keys_taiko():
    return one_of(*[just(key) for key in KeyTaiko])

def keys_mania():
    return one_of(*[just(key) for key in KeyMania])

def keys_osu():
    return one_of(*[just(key) for key in Key])

def representable_floats():
    # lzma format only allows sane floats, ie no nan or inf.
    return floats(allow_nan=False, allow_infinity=False)

life_bar_states = builds(
    LifeBarState,
    time=uints(),
    life=representable_floats()
)

replay_events_osu = builds(
    ReplayEventOsu,
    time_delta=ints(),
    x=representable_floats(),
    y=representable_floats(),
    keys=keys_osu(),
)
replay_events_taiko = builds(
    ReplayEventTaiko,
    time_delta=ints(),
    x=ints(),
    keys=keys_taiko()
)

replay_events_mania = builds(
    ReplayEventMania,
    time_delta=ints(),
    keys=keys_mania()
)

replay_events_catch = builds(
    ReplayEventCatch,
    time_delta=ints(),
    x=representable_floats()
)


@composite
def replays(draw):
    mode = draw(from_type(GameMode))
    replay_events = {
        GameMode.STD: replay_events_osu,
        GameMode.MANIA: replay_events_mania,
        GameMode.CTB: replay_events_catch,
        GameMode.TAIKO: replay_events_taiko
    }[mode]

    return Replay(
        mode=mode,
        game_version=draw(uints()),
        beatmap_hash=draw(utf8()),
        username=draw(utf8()),
        replay_hash=draw(utf8()),
        count_300=draw(shorts()),
        count_100=draw(shorts()),
        count_50=draw(shorts()),
        count_geki=draw(shorts()),
        count_katu=draw(shorts()),
        count_miss=draw(shorts()),
        score=draw(uints()),
        max_combo=draw(shorts()),
        perfect=draw(booleans()),
        # TODO mod combinations
        mods=draw(from_type(Mod)),
        # TODO issue with empty life bar state, None vs []
        life_bar_graph=draw(lists(life_bar_states, min_size=1) | just(None)),
        timestamp=draw(datetimes(timezones=just(timezone.utc))),
        # TODO issue with empty replay_data. might be valid by osr spec?
        replay_data=draw(lists(replay_events, min_size=1)),
        replay_id=draw(longs()),
        rng_seed=draw(ints() | just(None))
    )
