#!/usr/bin/env python3

from __future__ import annotations  # Forward refs without quotes (eg foo: CFoo, not foo: 'CFoo')

from .database import CDataBase, CTournamentDataBase

def main():
	for strName in CDataBase.LStrNameTournament():
		tourn = CTournamentDataBase.TournFromStrName(strName)
		for match in tourn.mpIdMatch.values():
			if not match.strTeamHome:
				continue
			if not match.strTeamAway:
				continue
			if set(match.strTeamHome) != set(match.strTeamAway):
				continue

			print(f"{strName}: {match.strTeamHome}v{match.strTeamAway}... {match.tStart.strftime('%Y-%m-%d')}")
