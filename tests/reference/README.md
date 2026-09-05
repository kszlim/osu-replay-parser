`python_replay.py` is the unmodified `osrparse/replay.py` from the modernization
baseline, commit `17d2315b4934bc9da14e6965211444b16ad4affd` (MIT licensed).
It is the differential-test and benchmark oracle, not a runtime fallback.
Keep it frozen; add compatibility cases to `tests/test_native_compatibility.py`.
