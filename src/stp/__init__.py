#!/usr/bin/env python3
"""Soccer Tournament Poster Generator."""

from importlib.metadata import version, metadata
from pathlib import Path

__project__ = 'stp'
__version__ = version(__project__)
__author_email__ = metadata('stp')['Author-email']

g_pathCode = Path(__file__).parent
