import copy
import dataclasses
import gc
import pickle
import weakref
from pathlib import Path

import pytest

from osrparse import (
    GameMode,
    Key,
    KeyMania,
    KeyTaiko,
    Mod,
    Replay,
    ReplayEvent,
    ReplayEventCatch,
    ReplayEventMania,
    ReplayEventOsu,
    ReplayEventTaiko,
    parse_replay_data,
)

RES = Path(__file__).parent / "resources"


@pytest.mark.parametrize(
    "filename, mode",
    [
        ("replay.osr", GameMode.STD),
        ("taiko.osr", GameMode.TAIKO),
        ("ctb.osr", GameMode.CTB),
        ("mania.osr", GameMode.MANIA),
    ],
)
def test_parsed_mode_and_mod_identity(filename, mode):
    replay = Replay.from_path(RES / filename)
    assert replay.mode is mode
    assert replay.mods is Mod(replay.mods.value)
    assert Replay.from_string(replay.pack()).mode is mode
    for event in replay.replay_data:
        assert isinstance(event, ReplayEvent)
        if hasattr(event, "keys"):
            assert event.keys is type(event.keys)(event.keys.value)


@pytest.mark.parametrize(
    "mode, key_class",
    [
        (GameMode.STD, Key),
        (GameMode.TAIKO, KeyTaiko),
        (GameMode.MANIA, KeyMania),
    ],
)
@pytest.mark.parametrize("mask", [0, 1, 3, 4, 7, -1, 1 << 30, (1 << 90) | 3])
def test_key_identity_for_members_combinations_and_unknown_bits(mode, key_class, mask):
    text = f"0|{mask if mode is GameMode.MANIA else 320}|0|{mask},"
    first = parse_replay_data(text, decompressed=True, mode=mode)[0]
    second = parse_replay_data(text, decompressed=True, mode=mode)[0]
    assert first.keys is key_class(mask)
    assert second.keys is first.keys
    assert pickle.loads(pickle.dumps(first)).keys is first.keys
    assert copy.deepcopy(first).keys is first.keys
    assert dataclasses.replace(first).keys is first.keys


def test_combined_mod_identity_after_edit_and_round_trip():
    replay = Replay.from_path(RES / "replay.osr")
    replay.mods = Mod.Hidden | Mod.HardRock
    assert Replay.from_string(replay.pack()).mods is (Mod.Hidden | Mod.HardRock)


def test_parsing_allocates_native_events_without_python_initializers(monkeypatch):
    def unexpected_init(*args, **kwargs):
        raise AssertionError("common replay parsing called a Python event initializer")

    for cls in (ReplayEventOsu, ReplayEventTaiko, ReplayEventCatch, ReplayEventMania):
        monkeypatch.setattr(cls, "__init__", unexpected_init)
    for filename in ("replay.osr", "taiko.osr", "ctb.osr", "mania.osr"):
        assert len(Replay.from_path(RES / filename).replay_data) > 10000


def test_native_dictionary_edits_are_live_and_preserve_identity():
    replay = Replay.from_path(RES / "replay.osr")
    event = replay.replay_data[0]
    state = vars(event)
    state["keys"] = Key.K1
    state["x"] = 123.5
    assert event.keys is Key.K1
    assert event.x == 123.5
    event.x = 456.0
    assert state["x"] == 456.0
    assert vars(event) is state
    reread = Replay.from_string(replay.pack())
    assert reread.replay_data[0].keys is Key.K1
    assert reread.replay_data[0].x == 456.0
    del event.x
    assert "x" not in state
    with pytest.raises(AttributeError):
        _ = event.x


def test_native_subclass_dictionary_and_copy():
    class Child(ReplayEventOsu):
        pass

    event = Child(10, 1.0, 2.0, Key.K2)
    assert vars(event) == dataclasses.asdict(event)
    vars(event)["x"] = 42.0
    assert event.x == 42.0
    event.note = "editable"
    assert vars(event)["note"] == "editable"
    copied = copy.deepcopy(event)
    assert copied == event
    assert copied.keys is Key.K2
    assert copied.note == "editable"


def test_native_event_cycles_are_collected():
    event = Replay.from_path(RES / "replay.osr").replay_data[0]
    event.cycle = event
    ref = weakref.ref(event)
    del event
    gc.collect()
    assert ref() is None


@pytest.mark.parametrize("coordinate", ["nan", "inf", "-inf"])
def test_nonfinite_coordinates_keep_dataclass_equality_and_enum_identity(coordinate):
    @dataclasses.dataclass
    class PythonEvent:
        x: float

    reference = PythonEvent(float(coordinate))
    event = parse_replay_data(f"0|{coordinate}|0|1,", decompressed=True)[0]
    # Dataclass NaN equality differs between Python versions; match the active
    # interpreter's generated dataclass behavior, including copied objects.
    assert (event == event) == (reference == reference)
    assert (copy.deepcopy(event) == event) == (copy.deepcopy(reference) == reference)
    assert (dataclasses.replace(event) == event) == (
        dataclasses.replace(reference) == reference
    )
    assert event.keys is Key.M1
