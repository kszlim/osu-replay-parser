import setuptools

version = '0.1.0'

setuptools.setup(
    name='osrparse',
    version=version,
    description="Python implementation of osu! rhythm game replays.",
    classifiers=[
        'Topic :: Games/Entertainment',
        'Topic :: Software Development :: Libraries',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python'
    ],
    keywords='osu!, osr, replay, replays, parsing, parser, python',
    author='Kevin Lim',
    author_email='kszlim@gmail.com',
    url='https://github.com/',
    license='MIT',
    packages=['osrparse']
)
