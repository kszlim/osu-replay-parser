from distutils.core import setup
from setuptools import find_packages
from osrparse import __version__

with open("README.md", "r") as f:
    long_description = f.read()

setup(
    name = "osrparse",
    version = __version__,
    description = "Parser for osr files and lzma replay streams for osu!",
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers = [
        "Topic :: Games/Entertainment",
        "Topic :: Software Development :: Libraries",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3"
    ],
    keywords = ["osu!, osr, replay, replays, parsing, parser, python"],
    author = "Kevin Lim, Liam DeVoe",
    author_email = "kszlim@gmail.com, orionldevoe@gmail.com",
    url = "https://github.com/kszlim/osu-replay-parser",
    download_url = "https://github.com/kszlim/osu-replay-parser/tarball/v" + __version__,
    license = "MIT",
    test_suite="tests",
    packages = find_packages()
)
