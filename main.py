#!/usr/bin/env python3

"""
generates roster cheat sheets
"""

from __future__ import annotations  # Forward refs without quotes

import argparse

from .database import DbEnsure
from .doc import WritePdf

def main() -> None:
	parser = argparse.ArgumentParser(prog="rcs", description="generate roster cheat sheets")
	parser.add_argument(
		"--rescrape-squads",
		action="store_true",
		help="only re-scrape squads",
	)
	parser.add_argument(
		"--rescrape-all",
		action="store_true",
		help="re-scrape everything",
	)
	args = parser.parse_args()

	WritePdf(DbEnsure(args.rescrape_squads, args.rescrape_all))

	# group = next(iter(db.groups.values()))
	# squad = next(iter(group.values()))
	# print(f"{repr(squad)}")
	# player = next(iter(group.playerso))
	# print(f"{repr(player)}")

if __name__ == '__main__':
	main()
