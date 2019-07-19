from distutils.core import setup
from setuptools import find_packages
from osrparse.__init__ import __version__

with open("README.md", "r") as f:
    long_description = f.read()

setup(
    name = "circleparse",
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
    author = "Liam DeVoe",
    author_email = "orionldevoe@gmail.com",
    url = "https://github.com/circleguard/circleparse",
    download_url = "https://github.com/circleguard/circleparse/tarball/" + __version__,
    license = "MIT",
    test_suite="tests",
    packages = find_packages()
)
