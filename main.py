#!/usr/bin/env python3

"""
generates roster cheat sheets
"""

from __future__ import annotations  # Forward refs without quotes

import argparse

from .database import LoadDatabase

def main() -> None:
	parser = argparse.ArgumentParser(prog="rcs", description="generate roster cheat sheets")
	parser.add_argument(
		"--reload-all",
		action="store_true",
		help="re-resolve the cached sidecars (countries.yaml, coaches.yaml) via HTTP",
	)
	args = parser.parse_args()
	LoadDatabase(fReloadAll=args.reload_all)

if __name__ == '__main__':
	main()
