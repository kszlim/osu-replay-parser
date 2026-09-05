"""Contract tests against the frozen Python codec at commit 17d2315."""

import base64
import copy
import dataclasses
import io
import lzma
import pickle
import struct
import weakref
from pathlib import Path

import pytest
from hypothesis import given, settings

from osrparse import (
    GameMode,
    Key,
    KeyMania,
    KeyTaiko,
    LifeBarState,
    Mod,
    Replay,
    ReplayEvent,
    ReplayEventCatch,
    ReplayEventMania,
    ReplayEventOsu,
    ReplayEventTaiko,
    parse_replay_data,
)
from osrparse.strategies import replays
from tests.reference import python_replay as reference

RES = Path(__file__).parent / "resources"


@pytest.mark.parametrize("path", sorted(RES.glob("*.osr")), ids=lambda p: p.name)
def test_all_fixture_fields_and_packed_bytes_match_python(path):
    data = path.read_bytes()
    actual = Replay.from_string(data)
    expected = reference.Replay.from_string(data)
    assert vars(actual) == vars(expected)
    assert actual.pack() == expected.pack()
    assert vars(Replay.from_string(expected.pack())) == vars(
        reference.Replay.from_string(actual.pack())
    )


@given(replays())
@settings(max_examples=150, deadline=None)
def test_generated_wire_bytes_and_cross_engine_round_trips(replay):
    actual = replay.pack()
    expected = reference._Packer(replay).pack()
    assert actual == expected
    assert vars(Replay.from_string(expected)) == vars(
        reference.Replay.from_string(actual)
    )


@pytest.mark.parametrize("mode", list(GameMode))
@pytest.mark.parametrize(
    "text",
    [
        "0|256|-500|0,0|256|-500|0,16|320|64|5,-12345|0|0|0,",
        "0|0|0|0,16|320|64|1",
        "0|0|0|0,16|320|64|1,",
        "-12345|320|0|0,16|320|64|1",
        "0|0|0|0,0|0|0|0,0|256|-500|0,",
        "999999999999999999999999999999|999999999999999999999999999999|0|999999999999999999999999999999,",
        "-10|-999999999999999999999999999999|0|-999999999999999999999999999999,",
        " 1_0 | ３２０ |64| 0_1 ,",
    ],
)
def test_event_streams_match_in_every_mode(mode, text):
    assert parse_replay_data(
        text, decompressed=True, mode=mode
    ) == reference.parse_replay_data(text, decompressed=True, mode=mode)
    compressed = lzma.compress(text.encode("ascii")) if text.isascii() else None
    if compressed:
        expected = reference.parse_replay_data(compressed, decoded=True, mode=mode)
        assert parse_replay_data(compressed, decoded=True, mode=mode) == expected
        assert parse_replay_data(base64.b64encode(compressed), mode=mode) == expected
        assert (
            parse_replay_data(base64.b64encode(compressed).decode(), mode=mode)
            == expected
        )


@pytest.mark.parametrize("format", [lzma.FORMAT_ALONE, lzma.FORMAT_XZ])
def test_concatenated_lzma_streams_and_trailing_junk(format):
    a = lzma.compress(b"0|0|0|0,", format=format)
    b = lzma.compress(b"16|320|64|1,", format=format)
    for data in [a, a + b, a + b"junk"]:
        assert parse_replay_data(data, decoded=True) == reference.parse_replay_data(
            data, decoded=True
        )


@pytest.mark.parametrize(
    "dict_size, mode", [(None, None), (0, 0), (1 << 16, 1), (1 << 22, 2)]
)
def test_compression_options_match_python(dict_size, mode):
    replay = Replay.from_path(RES / "replay.osr")
    assert (
        replay.pack(dict_size=dict_size, mode=mode)
        == reference._Packer(replay, dict_size=dict_size, mode=mode).pack()
    )


def test_files_paths_bytearray_and_mutation(tmp_path):
    path = RES / "replay.osr"
    data = path.read_bytes()
    replay = Replay.from_string(bytearray(data))
    assert Replay.from_path(bytes(path)) == replay
    file = io.BytesIO(data)
    assert Replay.from_file(file) == replay
    assert not file.closed
    replay.username = "プレイヤー 🎮"
    replay.replay_data[0].x = -123.5
    replay.replay_data.append(ReplayEventOsu(10, 0.0, -0.0, Key.K1))
    replay.life_bar_graph = [LifeBarState(0, 1.0)]
    target = tmp_path / "edited.osr"
    replay.write_path(target)
    assert Replay.from_path(target) == replay
    output = io.BytesIO()
    assert replay.write_file(output) is None
    assert not output.closed
    assert Replay.from_string(output.getvalue()) == replay


@pytest.mark.parametrize(
    "cls, args",
    [
        (ReplayEvent, (10,)),
        (ReplayEventOsu, (10, 1.0, 2.0, Key.M1)),
        (ReplayEventTaiko, (10, 320, KeyTaiko.LEFT_DON)),
        (ReplayEventCatch, (10, 1.0, True)),
        (ReplayEventMania, (10, KeyMania.K1)),
        (LifeBarState, (10, 0.5)),
    ],
)
def test_model_protocols(cls, args):
    value = cls(*args)
    assert dataclasses.is_dataclass(value)
    assert pickle.loads(pickle.dumps(value)) == value
    assert copy.deepcopy(value) == value
    assert dataclasses.replace(value) == value
    assert dataclasses.asdict(value) == vars(value)
    assert weakref.ref(value)() is value
    assert value == cls(**vars(value))
    assert repr(value).startswith(cls.__name__ + "(")
    with pytest.raises(TypeError):
        hash(value)
    value.custom_attribute = "supported"
    assert value.__dict__["custom_attribute"] == "supported"

    class Child(cls):
        pass

    assert isinstance(Child(*args), cls)


def test_replay_protocols_and_enum_identity():
    replay = Replay.from_path(RES / "replay.osr")
    assert replay.mode is GameMode.STD
    assert replay.mods is Mod.NoMod
    assert pickle.loads(pickle.dumps(replay)) == replay
    assert dataclasses.replace(replay) == replay
    assert copy.deepcopy(replay) == replay
    assert weakref.ref(replay)() is replay
    assert Replay(**vars(replay)) == replay
    with pytest.raises(TypeError):
        hash(replay)
    assert dataclasses.asdict(replay)["replay_data"][0] == dataclasses.asdict(
        replay.replay_data[0]
    )


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"\xff",
        b"\x00",
        b"\x00\0\0\0\0\x01",
        b"\x00\0\0\0\0\x0b\x80",
        b"\x00\0\0\0\0\x0b\x01\xff",
    ],
)
def test_malformed_headers_preserve_exception_class(data):
    with pytest.raises(Exception) as expected:
        reference.Replay.from_string(data)
    with pytest.raises(type(expected.value)):
        Replay.from_string(data)


@pytest.mark.parametrize(
    "text", ["", ",", "a|0|0|0", "1|0", "1|a|0|0", "1|0|0|a", "1|0|0|0,broken"]
)
def test_malformed_events_preserve_exception_class(text):
    with pytest.raises(Exception) as expected:
        reference.parse_replay_data(text, decompressed=True)
    with pytest.raises(type(expected.value)):
        parse_replay_data(text, decompressed=True)


@pytest.mark.parametrize(
    "field, value",
    [
        ("score", -1),
        ("count_300", 1 << 16),
        ("replay_id", 1 << 64),
        ("game_version", "wrong"),
    ],
)
def test_invalid_header_fields_raise_struct_error(field, value):
    replay = Replay.from_path(RES / "replay.osr")
    setattr(replay, field, value)
    with pytest.raises(struct.error):
        replay.pack()


def test_native_extension_is_required():
    from osrparse import _native

    assert _native.__file__.endswith((".so", ".pyd"))


@pytest.mark.parametrize(
    "options",
    [
        {"dict_size": -1},
        {"dict_size": 3.5},
        {"mode": 1 << 40},
        {"mode": 99},
        {"dict_size": 1},
    ],
)
def test_invalid_compression_options_preserve_error_class(options):
    replay = Replay.from_path(RES / "replay.osr")
    with pytest.raises(Exception) as expected:
        reference._Packer(replay, **options).pack()
    with pytest.raises(type(expected.value)):
        replay.pack(**options)


def test_truthy_decoding_flags():
    text = "0|0|0|0,16|320|64|1,"
    assert parse_replay_data(text, decompressed=1) == reference.parse_replay_data(
        text, decompressed=1
    )
    data = lzma.compress(text.encode())
    assert parse_replay_data(data, decoded=1) == reference.parse_replay_data(
        data, decoded=1
    )


def test_truncated_fixture_error_classes():
    data = (RES / "replay.osr").read_bytes()
    for length in [*range(400), *range(len(data) - 20, len(data))]:
        try:
            expected = reference.Replay.from_string(data[:length])
        except Exception as error:
            with pytest.raises(type(error)):
                Replay.from_string(data[:length])
        else:
            # Removing four ID bytes invokes the supported legacy-ID fallback.
            assert vars(Replay.from_string(data[:length])) == vars(expected)


@pytest.mark.parametrize(
    "payload", [b"", b"bad lzma", b"\xfd7zXZ\0", lzma.compress(b"0|0|0|0,")[:-1]]
)
def test_invalid_compressed_data_preserves_error_class(payload):
    with pytest.raises(Exception) as expected:
        reference.parse_replay_data(payload, decoded=True)
    with pytest.raises(type(expected.value)):
        parse_replay_data(payload, decoded=True)


def test_submodule_reexports_keep_class_identity():
    import osrparse
    import osrparse.replay
    import osrparse.utils

    for name in [
        "ReplayEventOsu",
        "ReplayEventCatch",
        "ReplayEventTaiko",
        "ReplayEventMania",
        "Key",
        "KeyMania",
        "KeyTaiko",
    ]:
        assert getattr(osrparse, name) is getattr(osrparse.replay, name)
        assert getattr(osrparse, name) is getattr(osrparse.utils, name)
