"""Independent framing checks and golden fingerprints for the bundled fixtures."""

import dataclasses
import hashlib
import json
import lzma
import struct
from datetime import datetime
from enum import Enum


def replay_fingerprint(replay):
    def encode(value):
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, datetime):
            return value.isoformat()
        raise TypeError(type(value))

    text = json.dumps(
        dataclasses.asdict(replay),
        default=encode,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(text.encode()).hexdigest()


def packed_sections(data):
    """Locate the compressed payload without decoding any replay fields/events."""
    offset = 5  # mode and version
    for skip in (0, 0, 0, 23):  # three identity strings, score block, lifebar
        offset += skip
        marker = data[offset]
        offset += 1
        if marker == 0:
            continue
        assert marker == 11
        length = shift = 0
        while True:
            byte = data[offset]
            offset += 1
            length |= (byte & 127) << shift
            if byte < 128:
                break
            shift += 7
        offset += length
    offset += 8  # timestamp
    length = struct.unpack_from("<I", data, offset)[0]
    assert offset + 4 + length + 8 == len(data)
    return data[:offset], data[offset + 4 : offset + 4 + length], data[-8:]


def packed_fingerprint(data):
    header, compressed, footer = packed_sections(data)
    # Check the encoder's bytes independently of its compressor implementation.
    return hashlib.sha256(
        header + b"\0" + lzma.decompress(compressed) + b"\0" + footer
    ).hexdigest()


# Captured once from Python commit 17d2315: complete parsed fields, uncompressed
# packed wire, and parsed fields after packing. No legacy implementation is used
# at test time. The lazer fixture's zero RNG seed is omitted during packing.
GOLDEN = {
    "ctb.osr": (
        "442fb49650790e04c0d953f36cae8f4b2fc953311bfb369695c98658ccf7413e",
        "ea081d7cd38b64af0408d7810eb84cfef9c3d611e4822f80148e2da05a4292e8",
        "442fb49650790e04c0d953f36cae8f4b2fc953311bfb369695c98658ccf7413e",
    ),
    "lazer_standard_format.osr": (
        "724af4eea603a6711b9be641f9fbb93dcbe46966f8fea77450a1148bec0e76d6",
        "2e8fb751a2db191ad7030a1f7c84d5de3787e46d8ac28afc164397f24912c32e",
        "2e597b659b8dc680557585bff306481fb8475c5436f7417e39d2139a74b1a8d8",
    ),
    "mania.osr": (
        "29818a47776f8f0bab9604fc659b41abeba5d7cac81e74574ea34f72824b7cb6",
        "95b7aefae920be27c66f4d8357fd2960c764db050c139376fed52eca91474e89",
        "29818a47776f8f0bab9604fc659b41abeba5d7cac81e74574ea34f72824b7cb6",
    ),
    "replay.osr": (
        "60c05ec3f90de51149a40933db13a9661224058634afd7c4a5c0e2e7e8be4a07",
        "745102748eccdca75447136cc2dd64d3b26df090980fb7c0dbd15ad0917d88d7",
        "60c05ec3f90de51149a40933db13a9661224058634afd7c4a5c0e2e7e8be4a07",
    ),
    "replay2.osr": (
        "a4ce95c97e44ed28808fb862863d58131344c72324da75db2a97f76ecd40b4b4",
        "6b02391ccc64d5bfda6ed63db8a9b9a027cf598223f1d9821647178da9d2a42f",
        "a4ce95c97e44ed28808fb862863d58131344c72324da75db2a97f76ecd40b4b4",
    ),
    "replay_old_replayid.osr": (
        "41e4e5b6f20dcbc31ab35d1fb158a3afba6c54395550e46134130b181a9ce728",
        "037da10fd964ca21319a2a0c4567779db9ed9ac65e0c3a2b5093a282e7f4aefe",
        "41e4e5b6f20dcbc31ab35d1fb158a3afba6c54395550e46134130b181a9ce728",
    ),
    "taiko.osr": (
        "574fae61801c3e3b756c6b040891b7596dc08c3d2e759396bde2e1f9639debd3",
        "abf2feb96cfb95e372c2cad3a8d6ace91325f93bd148f84c00a9fea0eb4cfaeb",
        "574fae61801c3e3b756c6b040891b7596dc08c3d2e759396bde2e1f9639debd3",
    ),
}
