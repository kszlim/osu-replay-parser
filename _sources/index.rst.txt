osrparse
==========

osrparse is a parser for the ``.osr`` format, as described `on the osu! wiki <https://osu.ppy.sh/wiki/en/Client/File_formats/Osr_%28file_format%29>`__.

osrparse is maintained by:

* `tybug <https://github.com/tybug>`__
* `kszlim <https://github.com/kszlim>`__

Installation
------------

osrparse can be installed from pip:

.. code-block:: console

    $ pip install osrparse

Links
-----

| Github: https://github.com/kszlim/osu-replay-parser
| Documentation: https://kevin-lim.ca/osu-replay-parser/


..
    couple notes about these toctrees - the first toctree is so our sidebar has
    a link back to the index page. the ``self`` keyword comes with its share of
    issues (https://github.com/sphinx-doc/sphinx/issues/2103), but none that matter
    that much to us. It's better than using ``index`` which works but generates
    many warnings when building.

    Hidden toctrees appear on the sidebar but not as text on the table of contents
    displayed on this page.

Contents
--------

.. toctree::
    :hidden:

    self

.. toctree::
    :maxdepth: 2

    parsing-replays
    writing-replays
    appendix
