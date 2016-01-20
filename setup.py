from distutils.core import setup
from setuptools import find_packages

setup(
    name = 'osrparse',
    version = '0.2.2',
    description = "Python implementation of osu! rhythm game replay parser.",
    classifiers = [
        'Topic :: Games/Entertainment',
        'Topic :: Software Development :: Libraries',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python'
    ],
    keywords = ['osu!, osr, replay, replays, parsing, parser, python'],
    author = 'Kevin Lim',
    author_email = 'kszlim@gmail.com',
    url = 'https://github.com/kszlim/osu-replay-parser',
    download_url = 'https://github.com/kszlim/osu-replay-parser/tarball/0.2.2',
    license = 'MIT',
    test_suite="tests",
    packages = find_packages()
)
