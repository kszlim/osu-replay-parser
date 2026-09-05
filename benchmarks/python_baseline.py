"""Load the frozen Python codec with frozen Python model classes.

The differential tests intentionally use the public models. Benchmarks must
instead retain the original pure-Python models to avoid overstating speedups.
"""

import importlib.util
import sys
from pathlib import Path

from benchmarks import python_baseline_utils

_source = Path(__file__).resolve().parents[1] / "tests/reference/python_replay.py"
_spec = importlib.util.spec_from_file_location("_osrparse_python_baseline", _source)
_module = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _module
_spec.loader.exec_module(_module)
for _name in (
    "GameMode",
    "Mod",
    "Key",
    "KeyMania",
    "KeyTaiko",
    "LifeBarState",
    "ReplayEvent",
    "ReplayEventOsu",
    "ReplayEventTaiko",
    "ReplayEventCatch",
    "ReplayEventMania",
):
    setattr(_module, _name, getattr(python_baseline_utils, _name))

Replay = _module.Replay
