#!/usr/bin/env python3

"""
generates roster cheat sheets
"""

from __future__ import annotations  # Forward refs without quotes

from bs4 import BeautifulSoup, Tag
from dateutil import parser as dateutil_parser
from pathlib import Path

import json
import requests
import sys
import time
import urllib.parse

g_strUrlWikipedia  = "https://en.wikipedia.org"
g_strUrlSquads = g_strUrlWikipedia + "/wiki/2026_FIFA_World_Cup_squads"

# Section anchor on a national-team article whose table lists the active roster;
# we link each team URL straight to it.

g_strSquadAnchor = "Current_squad"

# Wikimedia's API policy requires a descriptive User-Agent with contact info;
# the generic "Mozilla/5.0" string gets throttled aggressively (HTTP 429).

g_strUserAgent = "roster-cheat-sheet/0.1 (https://github.com/bruceoberg/roster-cheat-sheet; bruce@oberg.org)"

# Shared connection pool so the burst of per-team section checks reuses one
# keep-alive connection and the proper User-Agent.

g_session = requests.Session()
g_session.headers.update({"User-Agent": g_strUserAgent})


class SPlayer:  # tag = plyr
	"""One player row from a squad wikitable."""

	strNo:   str
	strPos:  str
	strName: str
	strDob:  str    # compact ISO date "1995-03-12" (age parenthetical stripped)
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
	strUrl:   str    # team's own Wikipedia article URL ("" if none was found)
	lPlyr:    list[SPlayer]

	def __init__(self, strGroup: str, strTeam: str, strCoach: str, strUrl: str, lPlyr: list[SPlayer]) -> None:
		self.strGroup = strGroup
		self.strTeam  = strTeam
		self.strCoach = strCoach
		self.strUrl   = strUrl
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


def StrDobCompact(strRaw: str) -> str:
	"""
	Convert a wikitable birthdate cell to a compact ISO date "YYYY-MM-DD".

	The raw cell reads "March 12, 1995 (age 31)"; we drop the parenthetical age,
	then let dateutil parse the remaining date string flexibly — it handles both
	"March 12, 1995" and "12 March 1995" without us tracking Wikipedia's format.

	On a parse failure we warn and return the raw string, so an unexpected format
	is visible in both the output and stderr rather than silently dropped.
	"""
	strDate = strRaw.split(" (")[0]
	try:
		t = dateutil_parser.parse(strDate)
	except (ValueError, OverflowError):
		print(f"WARNING: could not parse date of birth {strRaw!r}", file=sys.stderr)
		return strRaw
	return t.date().isoformat()


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
		strDob  = StrDobCompact(StrCellText(lCols[3])),
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


def StrUrlTeamFromP(p: Tag) -> str | None:
	"""
	Return the absolute URL of the team's own Wikipedia article, or None.

	The descriptive paragraph following the Coach line opens with a link to the
	national-team article — e.g. "The <a href="/wiki/Czech_Republic_national_football_team">Czech Republic</a> announced a 54-man preliminary squad …". We take the first
	/wiki/ link; footnote markers are #cite_note fragments, not /wiki/ paths, so
	the prefix test skips them.
	"""
	for link in p.find_all("a"):
		strHref = link.get("href", "")
		if strHref.startswith("/wiki/"):
			return g_strUrlWikipedia + strHref
	return None


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
			# The descriptive <p> between the Coach line and the table carries
			# the team's article link, so capture the first one we pass.
			tableSquad: Tag | None = None
			strUrlTeam: str | None = None
			iLook = iNode + 1
			while iLook < cNodes:
				candidate = lNodes[iLook]
				if isinstance(candidate, Tag):
					if candidate.name == "table":
						tableSquad = candidate
						break
					if TagHeadingFromNode(candidate) is not None:
						break
					if candidate.name == "p" and strUrlTeam is None:
						strUrlTeam = StrUrlTeamFromP(candidate)
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
						strUrl   = strUrlTeam or "",
						lPlyr    = lPlyr,
					))

		iNode += 1

	return lSqd


def ObjApiParse(mpStrParams: dict[str, str]) -> dict:
	"""
	GET the MediaWiki action=parse API and return the decoded JSON.

	Retries on HTTP 429 (rate limit) with exponential backoff, honoring a
	Retry-After header when present, so a burst of section checks doesn't fail
	the run.
	"""
	dTBackoff = 1.0
	cTry = 5
	for _ in range(cTry):
		resp = g_session.get(
			"https://en.wikipedia.org/w/api.php",
			params={**mpStrParams, "format": "json"},
			timeout=15,
		)
		if resp.status_code == 429:
			dTWait = float(resp.headers.get("Retry-After", dTBackoff))
			time.sleep(dTWait)
			dTBackoff *= 2
			continue
		resp.raise_for_status()
		return resp.json()

	# Exhausted retries — surface the last 429 as an error.
	resp.raise_for_status()
	return {}


def FetchSquadsPage() -> BeautifulSoup:
	objJson = ObjApiParse({
		"action": "parse",
		"page":   "2026_FIFA_World_Cup_squads",
		"prop":   "text",
	})
	strHtml = objJson["parse"]["text"]["*"]
	return BeautifulSoup(strHtml, "html.parser")


def FSquadAnchorExists(strUrlTeam: str) -> bool:
	"""
	True if the team article has a section anchored G_STR_SQUAD_ANCHOR, so that
	<url>#Current_squad actually resolves to the current-squad table.

	Uses the lightweight parse&prop=sections API (anchors only) instead of
	fetching and scanning the whole article HTML. The title is percent-decoded
	first — hrefs arrive encoded (e.g. "Canada_men%27s_national_soccer_team"),
	and the API rejects the raw form as an invalidtitle.
	"""
	strTitle = urllib.parse.unquote(strUrlTeam.removeprefix(g_strUrlWikipedia + "/wiki/"))
	objJson = ObjApiParse({
		"action": "parse",
		"page":   strTitle,
		"prop":   "sections",
	})
	lObjSec = objJson.get("parse", {}).get("sections", [])
	return any(objSec.get("anchor") == g_strSquadAnchor for objSec in lObjSec)


def StrUrlSquad(sqd: SSquad) -> str:
	"""Team article URL with the current-squad anchor, or "" if no URL was found."""
	if not sqd.strUrl:
		return ""
	return f"{sqd.strUrl}#{g_strSquadAnchor}"


def ObjFromSqd(sqd: SSquad) -> dict:
	"""Serialize an SSquad to a plain dict suitable for JSON output."""
	return {
		"team":   sqd.strTeam,
		"coach":  sqd.strCoach,
		"url":    StrUrlSquad(sqd),
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

	if False:
		print(f"Verifying current squad URLs...")
		# Verify each team URL resolves with the #Current_squad anchor; warn (but
		# don't fail) so a renamed/missing section is visible without stopping the run.
		for sqd in lSqd:
			if not sqd.strUrl:
				print(f"WARNING: no Wikipedia URL found for {sqd.strTeam}", file=sys.stderr)
			elif not FSquadAnchorExists(sqd.strUrl):
				print(
					f"WARNING: {sqd.strUrl} has no #{g_strSquadAnchor} section",
					file=sys.stderr,
				)

	# Spot-check first team
	if lSqd:
		sqd = lSqd[0]
		print(f"\n{sqd.strGroup} — {sqd.strTeam} — Coach: {sqd.strCoach}")
		for plyr in sqd.lPlyr[:3]:
			print(f"  {plyr.strNo:>2}  {plyr.strPos}  {plyr.strName:<25}  {plyr.strClub}")

	pathOut = Path("playground/squads.json")

	print(f"Writing {pathOut}...")

	pathOut.parent.mkdir(parents=True, exist_ok=True)
	pathOut.write_text(
		json.dumps(LObjGroupFromLSqd(lSqd), ensure_ascii=False, indent=2),
		encoding="utf-8",
	)
	
if __name__ == '__main__':
	main()
