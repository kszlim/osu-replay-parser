from datetime import timezone

from hypothesis.strategies import (integers, text, booleans,
    composite, from_type, lists, just, datetimes, floats)

from osrparse import (Replay, GameMode, Mod, ReplayEventOsu, ReplayEventMania,
    ReplayEventCatch, ReplayEventTaiko, KeyTaiko, KeyMania, Key)
from osrparse.utils import LifeBarState

def utf8():
    return text("utf-8")

def shorts():
    return integers(0, 2 ** 16 - 1)

def ints():
    return integers(0, 2 ** 32 - 1)

def longs():
    return integers(0, 2 ** 64 - 1)

def representable_float():
    # lzma format only allows sane floats, ie no nan or inf.
    return floats(allow_nan=False, allow_infinity=False)

@composite
def life_bar_states(draw):
    return LifeBarState(
        time=draw(integers()),
        life=draw(representable_float())
    )

@composite
def replay_events_osu(draw):
    return ReplayEventOsu(
        time_delta=draw(integers()),
        x=draw(representable_float()),
        y=draw(representable_float()),
        keys=draw(from_type(Key))
    )

@composite
def replay_events_taiko(draw):
    return ReplayEventTaiko(
        time_delta=draw(integers()),
        x=draw(integers()),
        keys=draw(from_type(KeyTaiko))
    )

@composite
def replay_events_mania(draw):
    return ReplayEventMania(
        time_delta=draw(integers()),
        keys=draw(from_type(KeyMania)),
    )

@composite
def replay_events_catch(draw):
    return ReplayEventCatch(
        time_delta=draw(integers()),
        x=draw(representable_float()),
        dashing=draw(booleans())
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
        game_version=draw(ints()),
        beatmap_hash=draw(utf8()),
        username=draw(utf8()),
        replay_hash=draw(utf8()),
        count_300=draw(shorts()),
        count_100=draw(shorts()),
        count_50=draw(shorts()),
        count_geki=draw(shorts()),
        count_katu=draw(shorts()),
        count_miss=draw(shorts()),
        score=draw(ints()),
        max_combo=draw(shorts()),
        perfect=draw(booleans()),
        # TODO mod combinations
        mods=draw(from_type(Mod)),
        # TODO bug serializing empty life bar state, None vs []
        life_bar_graph=draw(lists(life_bar_states(), min_size=1) | just(None)),
        timestamp=draw(datetimes(timezones=just(timezone.utc))),
        # TODO bug serializing empty replay_data. might be valid by osr spec?
        replay_data=draw(lists(replay_events(), min_size=1)),
        replay_id=draw(longs()),
        rng_seed=draw(ints() | just(None))
    )
