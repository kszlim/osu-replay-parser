from distutils.core import setup

version = '0.1.2'

setup(
    name = 'osrparse',
    version = version,
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
    download_url = 'https://github.com/kszlim/osu-replay-parser/tarball/0.1.2',
    license = 'MIT',
    packages = ['osrparse']
)
