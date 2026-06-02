#!/usr/bin/env python3

"""
generates roster cheat sheets
"""

from __future__ import annotations  # Forward refs without quotes

from bs4 import BeautifulSoup, Tag
from pathlib import Path

import json
import requests

G_STR_SQUADS_URL = "https://en.wikipedia.org/wiki/2026_FIFA_World_Cup_squads"


class SPlayer:  # tag = plyr
	"""One player row from a squad wikitable."""

	strNo:   str
	strPos:  str
	strName: str
	strDob:  str    # raw "12 March 1995 (age 31)" — caller strips if needed
	strCaps: str
	strClub: str

	def __init__(
		self,
		strNo:   str,
		strPos:  str,
		strName: str,
		strDob:  str,
		strCaps: str,
		strClub: str,
	) -> None:
		self.strNo   = strNo
		self.strPos  = strPos
		self.strName = strName
		self.strDob  = strDob
		self.strCaps = strCaps
		self.strClub = strClub


class SSquad:  # tag = sqd
	"""One national team's full tournament squad."""

	strGroup: str    # group-stage group, e.g. "Group A"
	strTeam:  str
	strCoach: str
	lPlyr:    list[SPlayer]

	def __init__(self, strGroup: str, strTeam: str, strCoach: str, lPlyr: list[SPlayer]) -> None:
		self.strGroup = strGroup
		self.strTeam  = strTeam
		self.strCoach = strCoach
		self.lPlyr    = lPlyr


def StrCellText(tag: Tag) -> str:
	"""
	Return clean whitespace-collapsed cell text.

	Drops footnote <sup> references, plus the hidden (display:none) spans the
	wikitables use for sort keys and the machine-readable ISO birthdate — e.g.
	the Pos. cell <span style="display:none">1</span><a>GK</a> would otherwise
	read as "1 GK", and the DOB cell would prepend "(2000-05-17)".
	"""
	for sup in tag.find_all("sup"):
		sup.decompose()
	for span in tag.find_all("span", style=lambda s: bool(s) and "display:none" in s.replace(" ", "")):
		span.decompose()
	return tag.get_text(separator=" ", strip=True)


def PlyrFromRow(row: Tag) -> SPlayer | None:
	"""
	Parse one <tr> into an SPlayer.
	Returns None for header rows and position-group subheaders (GK/DF/MF/FW).
	"""
	# Columns: No. | Pos. | Player | Date of birth (age) | Caps | Goals | Club
	lCols = row.find_all(["td", "th"])
	if len(lCols) < 7:
		return None

	# Position-group subheader rows span multiple columns — skip them
	if lCols[0].get("colspan"):
		return None

	return SPlayer(
		strNo   = StrCellText(lCols[0]),
		strPos  = StrCellText(lCols[1]),
		strName = StrCellText(lCols[2]),
		strDob  = StrCellText(lCols[3]),
		strCaps = StrCellText(lCols[4]),
		# lCols[5] is the Goals column — not captured in SPlayer
		strClub = StrCellText(lCols[6]),
	)


def LPlyrFromTable(table: Tag) -> list[SPlayer]:
	"""Parse a squad wikitable into a list of players, skipping the header row."""
	lPlyr: list[SPlayer] = []
	for row in table.find_all("tr")[1:]:  # [1:] skips the column header row
		plyr = PlyrFromRow(row)
		if plyr is not None:
			lPlyr.append(plyr)
	return lPlyr


def StrCoachFromP(p: Tag) -> str:
	"""
	Extract coach name from a <p>Coach: [flag] <a>Name</a></p> paragraph.

	A leading flagicon (present when the coach's nationality differs from the
	team's) is dropped first — otherwise its country link is the first <a> and
	we'd pick up e.g. "Belgium" instead of the coach's name.
	"""
	for flag in p.find_all("span", {"class": "flagicon"}):
		flag.decompose()
	link = p.find("a")
	if link:
		return link.get_text(strip=True)
	return p.get_text(strip=True).removeprefix("Coach:").strip()


def TagHeadingFromNode(node: Tag) -> Tag | None:
	"""
	Return the <h2>/<h3> heading element if node is a heading, else None.

	Modern MediaWiki wraps headings in a div:

		<div class="mw-heading mw-heading3"><h3>Czech Republic</h3>
			<span class="mw-editsection">…</span></div>

	A bare <h2>/<h3> is also accepted for older markup. Returning the inner
	heading gives clean text — the "[edit]" editsection is a sibling span of
	the heading, not a child, so it never leaks into get_text().
	"""
	if node.name in ("h2", "h3"):
		return node
	if node.name == "div" and "mw-heading" in (node.get("class") or []):
		return node.find(["h2", "h3"])
	return None


def LSqdFromSoup(soup: BeautifulSoup) -> list[SSquad]:
	"""
	Walk the mw-parser-output div linearly. The repeating pattern is:

		<div class="mw-heading mw-heading2"><h2>Group A</h2></div>   — group
		<div class="mw-heading mw-heading3"><h3>Czech Republic</h3></div>  — team
		<p>Coach: <a>Name</a></p>
		<table class="wikitable">  — 26-player roster

	Team names come from <h3> headings; the enclosing <h2> ("Group A") is the
	current group. A <h2> heading clears the current team so a stray table under
	a non-team section can't be misattributed, and resets the group context.
	"""
	lSqd: list[SSquad] = []
	strTeamCur:  str | None = None
	strGroupCur: str | None = None

	content = soup.find("div", {"class": "mw-parser-output"})
	lNodes = list(content.children)
	cNodes = len(lNodes)

	iNode = 0
	while iNode < cNodes:
		node = lNodes[iNode]

		if not isinstance(node, Tag):
			iNode += 1
			continue

		heading = TagHeadingFromNode(node)

		if heading is not None:
			if heading.name == "h3":
				strTeamCur = heading.get_text(strip=True)
			else:
				# h2 group heading ("Group A") — record it and clear team context
				strGroupCur = heading.get_text(strip=True)
				strTeamCur  = None

		elif node.name == "p" and "Coach" in node.get_text():
			strCoach = StrCoachFromP(node)

			# Scan ahead for the roster table, stopping at the next heading so a
			# Coach paragraph without its own table can't grab a later team's.
			tableSquad: Tag | None = None
			iLook = iNode + 1
			while iLook < cNodes:
				candidate = lNodes[iLook]
				if isinstance(candidate, Tag):
					if candidate.name == "table":
						tableSquad = candidate
						break
					if TagHeadingFromNode(candidate) is not None:
						break
				iLook += 1

			if tableSquad is not None and strTeamCur is not None:
				lPlyr = LPlyrFromTable(tableSquad)

				# A real squad has players; this skips trailing summary sections
				# (e.g. "Coach representation by country") that also pair a
				# "Coach" paragraph with a table.
				if lPlyr:
					lSqd.append(SSquad(
						strGroup = strGroupCur or "",
						strTeam  = strTeamCur,
						strCoach = strCoach,
						lPlyr    = lPlyr,
					))

		iNode += 1

	return lSqd


def FetchSquadsPage() -> BeautifulSoup:
    resp = requests.get(
        "https://en.wikipedia.org/w/api.php",
        params={
            "action": "parse",
            "page":   "2026_FIFA_World_Cup_squads",
            "prop":   "text",
            "format": "json",
        },
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=15,
    )
    resp.raise_for_status()
    strHtml = resp.json()["parse"]["text"]["*"]
    return BeautifulSoup(strHtml, "html.parser")


def ObjFromSqd(sqd: SSquad) -> dict:
	"""Serialize an SSquad to a plain dict suitable for JSON output."""
	return {
		"team":   sqd.strTeam,
		"coach":  sqd.strCoach,
		"players": [
			{
				"no":   plyr.strNo,
				"pos":  plyr.strPos,
				"name": plyr.strName,
				"dob":  plyr.strDob,
				"caps": plyr.strCaps,
				"club": plyr.strClub,
			}
			for plyr in sqd.lPlyr
		],
	}


def LObjGroupFromLSqd(lSqd: list[SSquad]) -> list[dict]:
	"""
	Bucket squads into group objects, preserving first-seen group order.

	Each output object is {"group": "Group A", "teams": [ ... ]}; the team's
	group is implied by its parent so ObjFromSqd omits it.
	"""
	mpStrLObj: dict[str, list[dict]] = {}
	for sqd in lSqd:
		mpStrLObj.setdefault(sqd.strGroup, []).append(ObjFromSqd(sqd))

	return [
		{"group": strGroup, "teams": lObjTeam}
		for strGroup, lObjTeam in mpStrLObj.items()
	]


def main() -> None:
	soup   = FetchSquadsPage()
	lSqd   = LSqdFromSoup(soup)
	cTeams = len(lSqd)
	print(f"Parsed {cTeams} teams")

	# Spot-check first team
	if lSqd:
		sqd = lSqd[0]
		print(f"\n{sqd.strGroup} — {sqd.strTeam} — Coach: {sqd.strCoach}")
		for plyr in sqd.lPlyr[:3]:
			print(f"  {plyr.strNo:>2}  {plyr.strPos}  {plyr.strName:<25}  {plyr.strClub}")

	pathOut = Path("playground/squads.json")
	pathOut.parent.mkdir(parents=True, exist_ok=True)

	pathOut.write_text(
		json.dumps(LObjGroupFromLSqd(lSqd), ensure_ascii=False, indent=2),
		encoding="utf-8",
	)
	print(f"\nWrote {pathOut}")
	
if __name__ == '__main__':
	main()
