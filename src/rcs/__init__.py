#!/usr/bin/env python3
"""Roster Cheat Sheet Generator."""

from importlib.metadata import version, metadata
from pathlib import Path

__project__ = 'rcs'
__version__ = version(__project__)
__author_email__ = metadata('rcs')['Author-email']

g_pathCode = Path(__file__).parent
