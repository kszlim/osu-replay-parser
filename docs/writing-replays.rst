Writing Replays
===============

Writing a Replay
----------------

Just as replays can be parsed from a path, file, or string, they can also be written back to a path, file, or string, with |write_path|, |write_file|, and |pack| respectively:


.. code-block:: python

    replay.write_path("path/to/new_osr.osr")

    # or to an opened file object
    with open("path/to/new_osr.osr") as f:
        replay.write_file(f)

    # or to a string
    packed = replay.pack()

Editing a Replay
----------------

The writing facilities of osrparse can be used to parse a replay, edit some or all of its attributes, and write it back to its file. The result is an edited replay.

For instance, to change the username of a replay:

.. code-block:: python

    from osrparse import Replay

    replay = Replay.from_path("path/to/osr.osr")
    replay.username = "fake username"
    replay.write_path("path/to/osr.osr")
