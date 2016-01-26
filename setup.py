from distutils.core import setup
from setuptools import find_packages

version = '2.1.0'

setup(
    name = 'osrparse',
    version = version,
    description = "Python implementation of osu! rhythm game replay parser.",
    classifiers = [
        'Topic :: Games/Entertainment',
        'Topic :: Software Development :: Libraries',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5'
    ],
    keywords = ['osu!, osr, replay, replays, parsing, parser, python'],
    author = 'Kevin Lim',
    author_email = 'kszlim@gmail.com',
    url = 'https://github.com/kszlim/osu-replay-parser',
    download_url = 'https://github.com/kszlim/osu-replay-parser/tarball/' + version,
    license = 'MIT',
    test_suite="tests",
    packages = find_packages()
)
