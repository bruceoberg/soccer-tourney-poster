#!/usr/bin/env python3
"""Soccer Tournament Poster Database Querier."""

from importlib.metadata import version, metadata
from pathlib import Path

__project__ = 'stp'
__version__ = version(__project__)
__author_email__ = metadata(__project__)['Author-email']

g_pathCode = Path(__file__).parent
