`python_replay.py` and `python_utils.py` are the unmodified Python codec and
models from commit `17d2315b4934bc9da14e6965211444b16ad4affd` (MIT licensed).

Differential tests use the frozen codec with the current public models.
`baseline.py` loads a separate copy with frozen models for honest performance
comparisons. This directory is test support and is never shipped in wheels.
