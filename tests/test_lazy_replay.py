import copy
import dataclasses
import gc
import lzma
import pickle
import struct
import weakref
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from osrparse import (
    GameMode,
    Key,
    KeyMania,
    KeyTaiko,
    Replay,
    ReplayData,
    ReplayEventOsu,
    _native,
    parse_replay_data,
)
from tests._wire import GOLDEN, packed_fingerprint, packed_sections

RES = Path(__file__).parent / "resources"


def test_native_replay_and_lazy_views_preserve_identity_and_lifetime():
    replay = Replay.from_path(RES / "replay.osr")
    assert replay._cached_event_count == 0
    assert replay._cached_field_count == 0
    assert replay.mode is GameMode.STD
    assert replay.username == "Cookiezi"
    assert replay._cached_event_count == 0
    data = replay.replay_data
    assert isinstance(data, ReplayData)
    assert data._cached_event_count == 0
    assert len(data) == 17498
    first = data[0]
    assert data._cached_event_count == 1
    assert first is data[0]
    assert first.keys is Key.M1
    last = data[-1]
    assert last is data[len(data) - 1]
    assert data._cached_event_count == 2
    del replay
    gc.collect()
    first.x = 123.5
    assert data[0].x == 123.5


def test_slices_materialize_only_requested_views():
    data = Replay.from_path(RES / "replay.osr").replay_data
    assert [event.time_delta for event in data[2:6]] == [21, 125, 167, 168]
    assert data._cached_event_count == 4
    assert [event.time_delta for event in data[-1:-4:-1]] == [166, 167, 167]
    assert data._cached_event_count == 7
    with pytest.raises(ValueError):
        data[::0]
    with pytest.raises(IndexError):
        data[len(data)]


@pytest.mark.parametrize(
    "filename", ["replay.osr", "taiko.osr", "ctb.osr", "mania.osr"]
)
def test_pack_does_not_materialize_events(filename):
    replay = Replay.from_path(RES / filename)
    packed = replay.pack()
    assert replay._cached_field_count == 0
    assert replay._cached_event_count == 0
    assert packed_fingerprint(packed) == GOLDEN[filename][1]
    assert replay._cached_event_count == 0


def test_pack_merges_edited_view_with_untouched_native_frames():
    replay = Replay.from_path(RES / "replay.osr")
    expected = vars(Replay.from_path(RES / "replay.osr"))
    data = replay.replay_data
    data[3].x = expected["replay_data"][3].x = 123.5
    data[7].keys = expected["replay_data"][7].keys = Key.K2
    replay.username = expected["username"] = "編集"
    assert vars(Replay.from_string(replay.pack())) == expected
    assert data._cached_event_count == 2


def test_dataclass_materialization_preserves_existing_sequence_and_event_aliases():
    replay = Replay.from_path(RES / "replay.osr")
    data = replay.replay_data
    event = data[0]
    as_dict = dataclasses.asdict(replay)
    assert isinstance(as_dict["replay_data"], list)
    assert isinstance(as_dict["replay_data"][0], dict)
    assert event is replay.replay_data[0] is data[0]
    replay.replay_data.append(event)
    assert len(data) == len(replay.replay_data)
    data[0].x = 789.0
    assert vars(replay)["replay_data"][0].x == 789.0


def test_structural_mutation_matches_lists_and_keeps_event_references():
    data = Replay.from_path(RES / "replay.osr").replay_data
    first = data[0]
    data[:] = [first, ReplayEventOsu(2, 2.0, 3.0, Key.K1)]
    expected = list(data)
    value = ReplayEventOsu(3, 4.0, 5.0, Key.K2)
    data.insert(0, value)
    expected.insert(0, value)
    assert data[1] is first
    data.append(value)
    expected.append(value)
    data.extend([first])
    expected.extend([first])
    del data[1:3]
    del expected[1:3]
    data[::2] = [value] * len(expected[::2])
    expected[::2] = [value] * len(expected[::2])
    assert data == expected and expected == data
    assert data.pop() is expected.pop()
    data.reverse()
    expected.reverse()
    data.sort(key=lambda event: event.time_delta)
    expected.sort(key=lambda event: event.time_delta)
    assert data == expected
    data += [first]
    expected += [first]
    data *= 2
    expected *= 2
    assert data == expected
    assert data.count(first) == expected.count(first)
    assert data.index(first) == expected.index(first)
    assert data + [value] == expected + [value]
    assert [value] + data == [value] + expected
    assert 2 * data == 2 * expected
    shallow = copy.copy(data)
    assert shallow[0] is data[0]
    data.clear()
    assert len(data) == 0
    assert len(shallow) > 0


def test_cyclic_copy_pickle_and_gc():
    replay = Replay.from_path(RES / "replay.osr")
    data = replay.replay_data
    data[:] = [data[0]]
    data[0].owner = data
    cloned = copy.deepcopy(data)
    assert cloned[0].owner is cloned
    loaded = pickle.loads(pickle.dumps(data))
    assert loaded[0].owner is loaded
    replay.replay_data[0].owner = replay
    cloned_replay = copy.deepcopy(replay)
    assert cloned_replay.replay_data[0].owner is cloned_replay
    loaded_replay = pickle.loads(pickle.dumps(replay))
    assert loaded_replay.replay_data[0].owner is loaded_replay
    weak = weakref.ref(replay)
    del replay, data
    gc.collect()
    assert weak() is None


@settings(max_examples=2000, deadline=None)
@given(st.integers(0, (1 << 64) - 1))
def test_native_float_format_matches_python(bits):
    value = struct.unpack("<d", struct.pack("<Q", bits))[0]
    assert _native._format_float(value) == str(value)


def test_float_tie_regression():
    assert _native._format_float(-664742861425528.2) == str(-664742861425528.2)


@pytest.mark.parametrize("mask", [-1, -16, -32, -33, -64, -65, -(1 << 63), 1 << 62])
@pytest.mark.parametrize("mode", [GameMode.STD, GameMode.TAIKO, GameMode.MANIA])
def test_negative_native_flags_pack_like_python(mask, mode):
    replay = Replay.from_path(RES / "replay.osr")
    replay.mode = mode
    replay.rng_seed = None
    text = f"16|{mask if mode is GameMode.MANIA else 320}|64|{mask},"
    replay.replay_data = parse_replay_data(text, decompressed=True, mode=mode)
    actual = replay.pack()
    assert replay.replay_data._cached_event_count == 0
    enum = {GameMode.STD: Key, GameMode.TAIKO: KeyTaiko, GameMode.MANIA: KeyMania}[mode]
    keys = enum(mask).value
    expected = {
        GameMode.STD: f"16|320.0|64.0|{keys},",
        GameMode.TAIKO: f"16|320|0|{keys},",
        GameMode.MANIA: f"16|{keys}|0|0,",
    }[mode]
    _, compressed, _ = packed_sections(actual)
    assert lzma.decompress(compressed).decode() == expected


def test_sequence_comparisons_and_index_protocol():
    data = ReplayData([1, 2])
    assert data < [3]
    assert [0] < data
    assert data <= [1, 2]
    assert data != (1, 2)
    with pytest.raises(TypeError):
        hash(data)
    with pytest.raises(IndexError):
        _ = data[1 << 100]


@pytest.mark.parametrize("value", ["+", "-", "12x", "0_1x", "9223372036854775808"])
def test_checked_integer_parser_keeps_python_semantics(value):
    text = f"{value}|0|0|0,"
    try:
        time = int(value)
    except ValueError:
        with pytest.raises(ValueError):
            parse_replay_data(text, decompressed=True)
    else:
        assert parse_replay_data(text, decompressed=True) == [
            ReplayEventOsu(time, 0.0, 0.0, Key(0))
        ]


def test_exhausted_iterator_stays_exhausted_and_releases_sequence():
    data = ReplayData([1])
    iterator = iter(data)
    assert iterator.__length_hint__() == 1
    assert next(iterator) == 1
    with pytest.raises(StopIteration):
        next(iterator)
    data.append(2)
    with pytest.raises(StopIteration):
        next(iterator)
    assert iterator.__length_hint__() == 0
    weak = weakref.ref(data)
    del data
    assert weak() is None


def test_common_parse_uses_no_python_model_or_enum_constructors(monkeypatch):
    import osrparse.utils as utils

    def unexpected(*args, **kwargs):
        raise AssertionError("normal decoding used a Python constructor")

    with monkeypatch.context() as context:
        context.setattr(Replay, "__init__", unexpected)
        for name in ("GameMode", "Mod", "Key", "KeyMania", "KeyTaiko"):
            context.setattr(utils, name, unexpected)
        replay = Replay.from_path(RES / "replay.osr")
        assert replay._cached_field_count == 0
        assert replay._cached_event_count == 0
    assert replay.mode is GameMode.STD
    assert replay.replay_data[0].keys is Key.M1


def test_cached_header_reads_do_not_force_python_packing():
    replay = Replay.from_path(RES / "replay.osr")
    assert replay.mode is GameMode.STD
    assert replay._cached_field_count == 1
    first = replay.replay_data[0]
    assert first.keys is Key.M1
    count = replay._cached_field_count
    packed = replay.pack()
    assert replay._cached_field_count == count
    assert replay._cached_event_count == 1
    assert packed_fingerprint(packed) == GOLDEN["replay.osr"][1]


def test_lifebar_edits_are_not_hidden_by_native_header_storage():
    from osrparse import LifeBarState

    replay = Replay.from_path(RES / "replay.osr")
    replay.life_bar_graph = [LifeBarState(10, 0.5)]
    replay = Replay.from_string(replay.pack())
    replay.life_bar_graph[0].life = 0.75
    assert Replay.from_string(replay.pack()).life_bar_graph == [LifeBarState(10, 0.75)]
