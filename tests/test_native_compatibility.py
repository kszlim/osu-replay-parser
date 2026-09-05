"""Golden format contracts, generated round trips, and malformed-input tests."""

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
from hypothesis import assume, given, settings

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
from tests._wire import GOLDEN, packed_fingerprint, packed_sections, replay_fingerprint

RES = Path(__file__).parent / "resources"


@pytest.mark.parametrize("path", sorted(RES.glob("*.osr")), ids=lambda p: p.name)
def test_all_fixture_fields_and_packed_wire_match_golden_results(path):
    expected_fields, expected_wire, expected_round_trip = GOLDEN[path.name]
    replay = Replay.from_path(path)
    assert replay_fingerprint(replay) == expected_fields
    packed = replay.pack()
    assert packed_fingerprint(packed) == expected_wire
    assert replay_fingerprint(Replay.from_string(packed)) == expected_round_trip


@given(replays())
@settings(max_examples=150, deadline=None)
def test_generated_replays_round_trip_all_fields(replay):
    # These values are reserved control records rather than playable events.
    assume(all(event.time_delta != -12345 for event in replay.replay_data))
    assume(
        not any(
            isinstance(event, ReplayEventOsu) and event.x == 256 and event.y == -500
            for event in replay.replay_data[:2]
        )
    )
    expected = vars(replay).copy()
    expected["rng_seed"] = replay.rng_seed or None
    assert vars(Replay.from_string(replay.pack())) == expected


@pytest.mark.parametrize("mode", list(GameMode))
@pytest.mark.parametrize(
    "text, records",
    [
        ("0|256|-500|0,0|256|-500|0,16|320|64|5,-12345|0|0|0,", [(16, 320, 64, 5)]),
        ("0|0|0|0,16|320|64|1", [(0, 0, 0, 0), (16, 320, 64, 1)]),
        ("0|0|0|0,16|320|64|1,", [(0, 0, 0, 0), (16, 320, 64, 1)]),
        ("-12345|320|0|0,16|320|64|1", [(-12345, 320, 0, 0), (16, 320, 64, 1)]),
        (
            "0|0|0|0,0|0|0|0,0|256|-500|0,",
            [(0, 0, 0, 0), (0, 0, 0, 0), (0, 256, -500, 0)],
        ),
        (
            "999999999999999999999999999999|999999999999999999999999999999|0|999999999999999999999999999999,",
            [(10**30 - 1, 10**30 - 1, 0, 10**30 - 1)],
        ),
        (
            "-10|-999999999999999999999999999999|0|-999999999999999999999999999999,",
            [(-10, -(10**30 - 1), 0, -(10**30 - 1))],
        ),
        (" 1_0 | ３２０ |64| 0_1 ,", [(10, 320, 64, 1)]),
    ],
)
def test_event_stream_contract_in_every_mode(mode, text, records):
    constructors = {
        GameMode.STD: lambda time, x, y, keys: ReplayEventOsu(
            time, float(x), float(y), Key(keys)
        ),
        GameMode.TAIKO: lambda time, x, y, keys: ReplayEventTaiko(
            time, int(x), KeyTaiko(keys)
        ),
        GameMode.CTB: lambda time, x, y, keys: ReplayEventCatch(
            time, float(x), keys == 1
        ),
        GameMode.MANIA: lambda time, x, y, keys: ReplayEventMania(
            time, KeyMania(int(x))
        ),
    }
    expected = [constructors[mode](*record) for record in records]
    assert parse_replay_data(text, decompressed=True, mode=mode) == expected
    if text.isascii():
        compressed = lzma.compress(text.encode("ascii"))
        assert parse_replay_data(compressed, decoded=True, mode=mode) == expected
        assert parse_replay_data(base64.b64encode(compressed), mode=mode) == expected
        assert (
            parse_replay_data(base64.b64encode(compressed).decode(), mode=mode)
            == expected
        )


@pytest.mark.parametrize("mode", [GameMode.STD, GameMode.CTB])
def test_native_coordinates_preserve_binary64_precision(mode):
    data = parse_replay_data(
        "16|0.10000000000000002|0.20000000000000004|1,",
        decompressed=True,
        mode=mode,
    )
    assert data._cached_event_count == 0
    assert data[0].x == 0.10000000000000002
    if mode is GameMode.STD:
        assert data[0].y == 0.20000000000000004


@pytest.mark.parametrize("format", [lzma.FORMAT_ALONE, lzma.FORMAT_XZ])
def test_concatenated_lzma_streams_and_trailing_junk(format):
    a = lzma.compress(b"0|0|0|0,", format=format)
    b = lzma.compress(b"16|320|64|1,", format=format)
    first = ReplayEventOsu(0, 0.0, 0.0, Key(0))
    second = ReplayEventOsu(16, 320.0, 64.0, Key.M1)
    for data, expected in [
        (a, [first]),
        (a + b, [first, second]),
        (a + b"junk", [first]),
    ]:
        assert parse_replay_data(data, decoded=True) == expected


@pytest.mark.parametrize("format", [lzma.FORMAT_ALONE, lzma.FORMAT_XZ])
def test_truncated_concatenated_streams_follow_stdlib_lzma(format):
    a = lzma.compress(b"0|0|0|0,", format=format)
    b = lzma.compress(b"16|320|64|1,", format=format)
    for length in range(1, len(b)):
        payload = a + b[:length]
        with pytest.raises(lzma.LZMAError):
            lzma.decompress(payload)
        with pytest.raises(lzma.LZMAError):
            parse_replay_data(payload, decoded=True)


@pytest.mark.parametrize(
    "dict_size, mode", [(None, None), (0, 0), (1 << 16, 1), (1 << 22, 2)]
)
def test_compression_options_match_stdlib_lzma(dict_size, mode):
    replay = Replay.from_path(RES / "replay.osr")
    packed = replay.pack(dict_size=dict_size, mode=mode)
    _, compressed, _ = packed_sections(packed)
    assert packed_fingerprint(packed) == GOLDEN["replay.osr"][1]
    assert compressed == lzma.compress(
        lzma.decompress(compressed),
        format=lzma.FORMAT_ALONE,
        filters=[
            {
                "id": lzma.FILTER_LZMA1,
                "dict_size": dict_size or 1 << 21,
                "mode": mode or lzma.MODE_FAST,
            }
        ],
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
    "data, error",
    [
        (b"", struct.error),
        (b"\xff", ValueError),
        (b"\x00", struct.error),
        (b"\x00\0\0\0\0\x01", ValueError),
        (b"\x00\0\0\0\0\x0b\x80", IndexError),
        (b"\x00\0\0\0\0\x0b\x01\xff", UnicodeDecodeError),
    ],
)
def test_malformed_headers_preserve_exception_class(data, error):
    with pytest.raises(error):
        Replay.from_string(data)


@pytest.mark.parametrize(
    "text, error",
    [
        ("", ValueError),
        (",", ValueError),
        ("a|0|0|0", ValueError),
        ("1|0", IndexError),
        ("1|a|0|0", ValueError),
        ("1|0|0|a", ValueError),
        ("1|0|0|0,broken", ValueError),
    ],
)
def test_malformed_events_preserve_exception_class(text, error):
    with pytest.raises(error):
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
    "options, error",
    [
        ({"dict_size": -1}, ValueError),
        ({"dict_size": 3.5}, ValueError),
        ({"mode": 1 << 40}, ValueError),
        ({"mode": 99}, lzma.LZMAError),
        ({"dict_size": 1}, lzma.LZMAError),
    ],
)
def test_invalid_compression_options_preserve_error_class(options, error):
    replay = Replay.from_path(RES / "replay.osr")
    with pytest.raises(error):
        replay.pack(**options)


def test_truthy_decoding_flags():
    text = "0|0|0|0,16|320|64|1,"
    expected = [
        ReplayEventOsu(0, 0.0, 0.0, Key(0)),
        ReplayEventOsu(16, 320.0, 64.0, Key.M1),
    ]
    assert parse_replay_data(text, decompressed=1) == expected
    assert parse_replay_data(lzma.compress(text.encode()), decoded=1) == expected


def test_truncated_fixture_error_classes():
    data = (RES / "replay.osr").read_bytes()
    # Golden boundaries include strings, fixed fields, compressed data, and ID.
    for start, stop, error in [
        (0, 5, struct.error),
        (5, 51, IndexError),
        (51, 106, struct.error),
        (106, 108, IndexError),
        (108, 120, struct.error),
        (120, 400, lzma.LZMAError),
        (len(data) - 20, len(data) - 8, lzma.LZMAError),
        (len(data) - 8, len(data) - 4, struct.error),
    ]:
        for length in range(start, stop):
            with pytest.raises(error):
                Replay.from_string(data[:length])
    for length in range(len(data) - 4, len(data)):
        # Four-byte IDs remain accepted even when trailing high bytes are absent.
        assert (
            replay_fingerprint(Replay.from_string(data[:length]))
            == GOLDEN["replay.osr"][0]
        )


@pytest.mark.parametrize(
    "payload", [b"", b"bad lzma", b"\xfd7zXZ\0", lzma.compress(b"0|0|0|0,")[:-1]]
)
def test_invalid_compressed_data_preserves_error_class(payload):
    with pytest.raises(lzma.LZMAError):
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
