Parsing Replays
===============

Creating a Replay
-----------------

Depending on the type of data you have, a |Replay| can be created multiple ways, using either one of |from_path|, |from_file|, or |from_string|:

.. code-block:: python

    from osrparse import Replay
    # from a path
    replay = Replay.from_path("path/to/osr.osr")

    # or from an opened file object
    with open("path/to/osr.osr") as f:
        replay = Replay.from_file(f)

    # or from a string
    with open("path/to/osr.osr") as f:
        replay_string = f.read()
    replay = Replay.from_string(replay_string)

Most likely, you will be using |from_path| to create a |Replay|.

Parsing Just Replay Data
------------------------

Unfortunately, the `/get_replay <https://github.com/ppy/osu-api/wiki#apiget_replay>`__ endpoint of `osu!api v1 <https://github.com/ppy/osu-api/wiki>`__ does not return the full contents of a replay, but only the replay data potion. This means that you cannot create a full replay from the response of this endpoint.

For this, we provide |parse_replay_data|, a function that takes the response of this endpoint and returns List[:class:`~osrparse.utils.ReplayEvent`] (ie, the parsed replay data):

.. code-block:: python

    from osrparse import parse_replay_data
    import base64
    import lzma

    lzma_string = retrieve_from_api()
    replay_data = parse_replay_data(lzma_string)
    assert isinstance(replay_data[0], ReplayEvent)

    # or parse an already decoded lzma string
    lzma_string = retrieve_from_api()
    lzma_string = base64.b64decode(lzma_string)
    replay_data = parse_replay_data(lzma_string, decoded=True)

    # or parse an already decoded and decompressed lzma string
    lzma_string = retrieve_from_api()
    lzma_string = base64.b64decode(lzma_string)
    lzma_string = lzma.decompress(lzma_string).decode("ascii")
    replay_data = parse_replay_data(lzma_string, decompressed=True)
