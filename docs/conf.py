# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

from osrparse import __version__

project = "osrparse"
copyright = "2022, Kevin Lim, Liam DeVoe"
author = "Kevin Lim, Liam DeVoe"
release = "v" + __version__
version = "v" + __version__
master_doc = 'index'

# https://www.sphinx-doc.org/en/master/usage/configuration.html#confval-html_show_copyright
html_show_copyright = False
# https://www.sphinx-doc.org/en/master/usage/configuration.html#confval-html_show_sphinx
html_show_sphinx = False

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx.ext.todo"
]

intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}
# https://stackoverflow.com/a/37210251
autodoc_member_order = "bysource"

html_theme = "furo"

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# html_static_path = ["_static"]

# references that we want to use easily in any file
rst_prolog = """
.. |Replay| replace:: :class:`~osrparse.replay.Replay`
.. |from_path| replace:: :func:`Replay.from_path() <osrparse.replay.Replay.from_path>`
.. |from_file| replace:: :func:`Replay.from_file() <osrparse.replay.Replay.from_file>`
.. |from_string| replace:: :func:`Replay.from_string() <osrparse.replay.Replay.from_string>`
.. |write_path| replace:: :func:`Replay.write_path() <osrparse.replay.Replay.write_path>`
.. |write_file| replace:: :func:`Replay.write_file() <osrparse.replay.Replay.write_file>`
.. |pack| replace:: :func:`Replay.pack() <osrparse.replay.Replay.pack>`
.. |parse_replay_data| replace:: :func:`parse_replay_data() <osrparse.replay.parse_replay_data>`

.. |br| raw:: html

   <br />
"""

# linebreak workaround documented here
# https://stackoverflow.com/a/9664844/12164878
