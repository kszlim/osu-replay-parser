from datetime import datetime

from osrparse.replay import Replay
from osrparse.utils import GameMode
from osrparse.utils import ReplayEvent as ReplayEvent
from osrparse.utils import ReplayEventCatch as ReplayEventCatch
from osrparse.utils import ReplayEventMania as ReplayEventMania
from osrparse.utils import ReplayEventOsu as ReplayEventOsu
from osrparse.utils import ReplayEventTaiko as ReplayEventTaiko

def unpack(data: bytes, replay_type: type[Replay]) -> Replay: ...
def unpack_timestamp(data: bytes) -> datetime: ...
def parse_events(text: str, mode: GameMode) -> tuple[list[ReplayEvent], int | None]: ...
def parse_replay_data(
    data: str | bytes,
    *,
    decoded: bool = False,
    decompressed: bool = False,
    mode: GameMode,
) -> list[ReplayEvent]: ...
def pack(
    replay: Replay, *, dict_size: int | None = None, mode: int | None = None
) -> bytes: ...
