"""Boundary regressions for the consolidated codec and sequence adapters."""

import pytest

from osrparse import Key, ReplayData, ReplayEventOsu, parse_replay_data
from osrparse.utils import _restore_event


def test_index_conversion_can_mutate_sequence():
    data = ReplayData([1])

    class Index:
        def __index__(self):
            data.append(2)
            return -1

    assert data[Index()] == 2
    assert data == [1, 2]


def test_slice_conversion_uses_length_after_callbacks():
    data = ReplayData([1])

    class Start:
        def __index__(self):
            data.append(2)
            return 0

    assert data[Start() :] == [1, 2]


def test_clear_allows_reentrant_finalizers():
    data = ReplayData()

    class Item:
        def __del__(self):
            data.append("from finalizer")

    data.append(Item())
    data.clear()
    assert data == ["from finalizer"]


def test_old_pickle_restore_entry_point_remains_available():
    expected = ReplayEventOsu(1, 2.0, 3.0, Key.K1)
    assert _restore_event(ReplayEventOsu, vars(expected)) == expected


def test_invalid_mode_is_rejected_explicitly():
    with pytest.raises(TypeError, match="GameMode"):
        parse_replay_data("0|0|0|0,", decompressed=True, mode=0)
