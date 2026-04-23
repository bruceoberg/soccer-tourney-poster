#!/usr/bin/env python3

from __future__ import annotations  # Forward refs without quotes (eg foo: CFoo, not foo: 'CFoo')

import argparse

from pathlib import Path

from .profiling import DiffProfiles


def Main() -> None:
	parser = argparse.ArgumentParser(description="Diff two cProfile .prof files by absolute delta in cumulative time.")
	parser.add_argument('pathBefore', type=Path, help="Baseline .prof file")
	parser.add_argument('pathAfter', type=Path, help="Comparison .prof file")
	parser.add_argument('-n', '--lines', type=int, default=30, help="Rows to print (default 30)")

	args = parser.parse_args()

	DiffProfiles(args.pathBefore, args.pathAfter, cLines=args.lines)


if __name__ == '__main__':
	Main()
