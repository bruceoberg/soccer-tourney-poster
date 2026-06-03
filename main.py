#!/usr/bin/env python3

"""
generates roster cheat sheets
"""

from __future__ import annotations  # Forward refs without quotes

from bs4 import BeautifulSoup, Tag
from dataclasses import dataclass, replace
from dateutil import parser as dateutil_parser
from pathlib import Path

import argparse
import re
import requests
import sys
import time
import urllib.parse
import yaml

g_strUrlWikipedia = "https://en.wikipedia.org"

# Persistent data store. The "load" step rewrites squads.yaml every run (rosters change
# often) and maintains two sidecar caches for data that needs an HTTP lookup:
#
#   countries.yaml — country name -> flag URL (and, later, FIFA code)
#   coaches.yaml   — coach name -> coach record (home of the coming per-coach data)
#
# A normal run makes a single network call (the squads page); the sidecars supply
# everything else. See LoadDatabase for the populate-vs-normal caching policy.

g_pathDatabase = Path("database")

# Section anchor on a national-team article whose table lists the active roster;
# we link each team URL straight to it.

g_strSquadAnchor = "Current_squad"

# Wikimedia's API policy requires a descriptive User-Agent with contact info;
# the generic "Mozilla/5.0" string gets throttled aggressively (HTTP 429).

g_strUserAgent = "roster-cheat-sheet/0.1 (https://github.com/bruceoberg/roster-cheat-sheet; bruce@oberg.org)"

# Shared connection pool so the burst of per-team flag lookups reuses one
# keep-alive connection and the proper User-Agent.

g_session = requests.Session()
g_session.headers.update({"User-Agent": g_strUserAgent})


@dataclass(frozen=True)
class SPlayer:  # tag = plyr
	"""One player row from a squad wikitable."""

	strNo:    str
	strPos:   str
	strName:  str
	fCaptain: bool   # team captain (parsed from a "(captain)" suffix on the name)
	strDob:   str    # compact ISO date "1995-03-12" (age parenthetical stripped)
	strCaps:  str
	strClub:  str
	strCountry: str  # the club's country name ("" if the club cell carried no flag); flag URL lives in countries.yaml


@dataclass(frozen=True)
class SCoach:  # tag = coch
	"""One team's head coach, with nationality inferred from the squad page."""

	strName:    str
	strCountry: str  # nationality; the team's own country when no flag icon was shown


@dataclass(frozen=True)
class SCountry:  # tag = cty
	"""A country's flag, cached in countries.yaml so a normal run needs no flag lookup."""

	strCountry: str  # country name (the registry key)
	strUrlFlag: str  # source URL of the country's flag SVG
	# strFifaCode: str = ""   # FUTURE — 3-letter FIFA code; HTTP lookup, --reload-all only


@dataclass(frozen=True)
class SSquad:  # tag = sqd
	"""One national team's full tournament squad."""

	strGroup: str    # group-stage group, e.g. "Group A"
	strTeam:  str
	coach:    SCoach
	strUrl:   str    # team's own Wikipedia article URL ("" if none was found)
	lPlyr:    list[SPlayer]


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


# Trailing "(captain)" marker on a player name, with arbitrary internal/surrounding
# whitespace and any case — e.g. "Messi ( captain )" or "Messi (Captain)".

g_reCaptain = re.compile(r"\(\s*captain\s*\)\s*$", re.IGNORECASE)


def StrNameCaptain(strRaw: str) -> tuple[str, bool]:
	"""
	Split a player-name cell into (clean name, is-captain).

	Captaincy is encoded as a trailing "(captain)" suffix on the name; strip it
	and report it as a flag. The returned name is whitespace-stripped either way.
	"""
	strClean, cSub = g_reCaptain.subn("", strRaw)
	return strClean.strip(), cSub > 0


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


def StrUrlFlagFromImg(img: Tag) -> str:
	"""
	Canonical SVG URL behind a flagicon's <img> thumbnail, or "".

	The flagicon renders a PNG thumbnail of an SVG source — e.g.
		//upload.wikimedia.org/wikipedia/commons/thumb/1/1b/Flag_of_Croatia.svg/40px-Flag_of_Croatia.svg.png
	We recover the original vector file behind it
		https://upload.wikimedia.org/wikipedia/commons/1/1b/Flag_of_Croatia.svg
	by dropping the "/thumb/" segment and the trailing "NNpx-….png" render, so the
	future PDF step can rasterize crisply at any size. Wikimedia emits protocol-relative
	"//upload…" srcs, so we prepend https:.
	"""
	strSrc = img.get("src", "")
	if not strSrc:
		return ""
	if strSrc.startswith("//"):
		strSrc = "https:" + strSrc

	# A thumbnail src embeds the source-file path; strip the /thumb/ marker and the
	# trailing render so we point at the original file. Non-thumbnail srcs (rare)
	# already are the original and need no surgery.
	if "/thumb/" in strSrc:
		strSrc = strSrc.replace("/thumb/", "/", 1).rsplit("/", 1)[0]

	return strSrc


def ImgFlagFromCell(tag: Tag) -> Tag | None:
	"""The <img> of the flag icon inside a cell, or None when the cell has no flag."""
	flag = tag.find("span", {"class": "flagicon"})
	if flag is None:
		return None
	return flag.find("img")


def StrUrlFlagFromCell(tag: Tag) -> str:
	"""Canonical SVG URL of the flag icon in a cell, or ""."""
	img = ImgFlagFromCell(tag)
	return StrUrlFlagFromImg(img) if img is not None else ""


def StrCountryFromUrl(strUrl: str) -> str:
	"""
	Canonical country name from a flag SVG URL — the only stable country key.

	A flag icon's alt text is NOT reliable: club cells render the football-federation
	name ("Argentine Football Association", "Royal Dutch Football Association"), and one
	country appears under several alt strings. The flag *file* is stable, so we key
	countries by it: the last URL segment, percent-decoded, with the "Flag_of_"/".svg"
	wrapper and any "_(qualifier)" dropped, e.g.
		.../Flag_of_the_Netherlands.svg       -> "Netherlands"
		.../Flag_of_Belgium_%28civil%29.svg   -> "Belgium"
		.../Flag_of_C%C3%B4te_d%27Ivoire.svg  -> "Côte d'Ivoire"
	"""
	if not strUrl:
		return ""
	strFile = urllib.parse.unquote(strUrl.rsplit("/", 1)[-1])
	strName = strFile.removeprefix("Flag_of_").removesuffix(".svg").split("_(")[0]
	return strName.replace("_", " ").strip().removeprefix("the ")


def StrCountryFromCell(tag: Tag) -> str:
	"""
	Canonical country name behind a cell's flag icon (from its flag file), or "".

	The club cell's flag identifies the club's country; we store that canonical name on
	the player and resolve its flag later through countries.yaml.
	"""
	img = ImgFlagFromCell(tag)
	return StrCountryFromUrl(StrUrlFlagFromImg(img)) if img is not None else ""


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

	strName, fCaptain = StrNameCaptain(StrCellText(lCols[2]))

	return SPlayer(
		strNo    = StrCellText(lCols[0]),
		strPos   = StrCellText(lCols[1]),
		strName  = strName,
		fCaptain = fCaptain,
		strDob   = StrDobCompact(StrCellText(lCols[3])),
		strCaps  = StrCellText(lCols[4]),
		# lCols[5] is the Goals column — not captured in SPlayer
		strClub    = StrCellText(lCols[6]),
		strCountry = StrCountryFromCell(lCols[6]),
	)


def LPlyrFromTable(table: Tag) -> list[SPlayer]:
	"""Parse a squad wikitable into a list of players, skipping the header row."""
	lPlyr: list[SPlayer] = []
	for row in table.find_all("tr")[1:]:  # [1:] skips the column header row
		plyr = PlyrFromRow(row)
		if plyr is not None:
			lPlyr.append(plyr)
	return lPlyr


def CoachFromP(p: Tag, strTeam: str) -> SCoach:
	"""
	Parse a <p>Coach: [flag] <a>Name</a></p> paragraph into an SCoach.

	A leading flagicon appears only when the coach's nationality differs from the
	team's; we canonicalize its country from the flag file (its alt text is unreliable,
	see StrCountryFromUrl). With no flagicon the coach shares the team's country, so
	strCountry falls back to the team heading — a raw name that MpCochResolve later maps
	to a canonical countries.yaml key (free when it already is one, else an API lookup).
	"""
	strCountry = strTeam

	flag = p.find("span", {"class": "flagicon"})
	if flag is not None:
		img = flag.find("img")
		strCountryFlag = StrCountryFromUrl(StrUrlFlagFromImg(img)) if img is not None else ""
		if strCountryFlag:
			strCountry = strCountryFlag

	for flag in p.find_all("span", {"class": "flagicon"}):
		flag.decompose()

	link = p.find("a")
	if link:
		strName = link.get_text(strip=True)
	else:
		strName = p.get_text(strip=True).removeprefix("Coach:").strip()

	return SCoach(strName=strName, strCountry=strCountry)


def StrUrlFlagFromTeam(strTeam: str) -> str:
	"""
	Canonical SVG URL of a national team's own flag, or "".

	Used at populate time for a country that never appears as a flag icon on the
	squads page — a coach shown without a flag (nationality == team) whose country
	also isn't some player's club country. We render the {{flagicon|<team>}} template
	through the parse API and pull the SVG URL out with the same StrUrlFlagFromCell
	logic the page cells use.
	"""
	objJson = ObjApiParse({
		"action":       "parse",
		"text":         "{{flagicon|" + strTeam + "}}",
		"contentmodel": "wikitext",
		"prop":         "text",
	})
	strHtml = objJson.get("parse", {}).get("text", {}).get("*", "")
	return StrUrlFlagFromCell(BeautifulSoup(strHtml, "html.parser"))


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
			coch = CoachFromP(node, strTeamCur or "")

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
						coach    = coch,
						strUrl   = strUrlTeam or "",
						lPlyr    = lPlyr,
					))

		iNode += 1

	return lSqd


def MpStrCountryUrlFromSoup(soup: BeautifulSoup) -> dict[str, str]:
	"""
	Harvest every flag icon on the squads page into country name -> flag SVG URL.

	This is the free tier: it costs no extra HTTP (the page is already fetched) and
	covers every player's club country plus every coach whose nationality differs
	from their team. countries.yaml fills its remaining entries (coaches whose
	nationality matches their team) from the API at populate time.
	"""
	mpStrCountryUrl: dict[str, str] = {}
	for flag in soup.find_all("span", {"class": "flagicon"}):
		img = flag.find("img")
		if img is None:
			continue
		strUrl     = StrUrlFlagFromImg(img)
		strCountry = StrCountryFromUrl(strUrl)
		if strCountry and strUrl:
			mpStrCountryUrl.setdefault(strCountry, strUrl)
	return mpStrCountryUrl


def ObjApiParse(mpStrParams: dict[str, str]) -> dict:
	"""
	GET the MediaWiki action=parse API and return the decoded JSON.

	Retries on HTTP 429 (rate limit) with exponential backoff, honoring a
	Retry-After header when present, so a burst of flag lookups doesn't fail the run.
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


def StrUrlSquad(sqd: SSquad) -> str:
	"""Team article URL with the current-squad anchor, or "" if no URL was found."""
	if not sqd.strUrl:
		return ""
	return f"{sqd.strUrl}#{g_strSquadAnchor}"


def ObjFromSqd(sqd: SSquad) -> dict:
	"""Serialize an SSquad to a plain dict for squads.yaml (countries by name)."""
	return {
		"team":  sqd.strTeam,
		"coach": {
			"name":    sqd.coach.strName,
			"country": sqd.coach.strCountry,
		},
		"url":    StrUrlSquad(sqd),
		"players": [
			{
				"no":      plyr.strNo,
				"pos":     plyr.strPos,
				"name":    plyr.strName,
				"captain": plyr.fCaptain,
				"dob":     plyr.strDob,
				"caps":    plyr.strCaps,
				"club":    plyr.strClub,
				"country": plyr.strCountry,
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


def ObjFromCountry(cty: SCountry) -> dict:
	"""Serialize an SCountry for countries.yaml."""
	return {"country": cty.strCountry, "flag_url": cty.strUrlFlag}


def LObjFromMpCty(mpStrCty: dict[str, SCountry]) -> list[dict]:
	"""countries.yaml body, sorted by country name for stable diffs."""
	return [ObjFromCountry(mpStrCty[strCountry]) for strCountry in sorted(mpStrCty)]


def MpCtyFromObj(objYaml: object) -> dict[str, SCountry]:
	"""Parse countries.yaml's raw object into country name -> SCountry."""
	mpStrCty: dict[str, SCountry] = {}
	for obj in objYaml or []:
		cty = SCountry(strCountry=obj["country"], strUrlFlag=obj.get("flag_url", ""))
		mpStrCty[cty.strCountry] = cty
	return mpStrCty


def ObjFromCoach(coch: SCoach) -> dict:
	"""Serialize an SCoach for coaches.yaml."""
	return {"name": coch.strName, "country": coch.strCountry}


def LObjFromMpCoch(mpStrCoch: dict[str, SCoach]) -> list[dict]:
	"""coaches.yaml body, sorted by coach name for stable diffs."""
	return [ObjFromCoach(mpStrCoch[strName]) for strName in sorted(mpStrCoch)]


def MpCochFromObj(objYaml: object) -> dict[str, SCoach]:
	"""Parse coaches.yaml's raw object into coach name -> SCoach."""
	mpStrCoch: dict[str, SCoach] = {}
	for obj in objYaml or []:
		coch = SCoach(strName=obj["name"], strCountry=obj.get("country", ""))
		mpStrCoch[coch.strName] = coch
	return mpStrCoch


def WriteYaml(path: Path, obj: object) -> None:
	"""Write obj to path as readable YAML (accents intact, our field order kept)."""
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(
		yaml.dump(obj, allow_unicode=True, sort_keys=False, default_flow_style=False),
		encoding="utf-8",
	)


def ObjLoadYaml(path: Path) -> object:
	"""
	Parse a sidecar YAML to its raw object, or None when the file is absent.

	A present-but-unparseable file is a hand-editing mistake, not a cache miss, so we
	stop rather than silently overwrite it.
	"""
	if not path.exists():
		return None
	try:
		return yaml.safe_load(path.read_text(encoding="utf-8"))
	except yaml.YAMLError as err:
		sys.exit(f"ERROR: {path} is unreadable ({err}); fix it or run: rcs --reload-all")


def SetStrCountryRef(lSqd: list[SSquad]) -> set[str]:
	"""Every country name the output references (player club countries + coaches)."""
	setStrCountry: set[str] = set()
	for sqd in lSqd:
		if sqd.coach.strCountry:
			setStrCountry.add(sqd.coach.strCountry)
		for plyr in sqd.lPlyr:
			if plyr.strCountry:
				setStrCountry.add(plyr.strCountry)
	return setStrCountry


def MpCtyBuild(
	lSqd:            list[SSquad],
	mpStrCountryUrl: dict[str, str],
	mpCtyCached:     dict[str, SCountry],
	fPopulate:       bool,
) -> dict[str, SCountry]:
	"""
	Resolve every referenced country to an SCountry for countries.yaml.

	flag_url comes free from this run's page harvest (mpStrCountryUrl). A country
	absent from the page is a coach whose nationality matches their team: when
	populating we resolve it via the API; on a normal run we reuse the cached URL,
	or error toward --reload-all when it isn't cached either. (FIFA codes will plug
	in here the same way — populate-only, gated otherwise.)
	"""
	mpStrCty: dict[str, SCountry] = {}
	for strCountry in SetStrCountryRef(lSqd):
		strUrl = mpStrCountryUrl.get(strCountry, "")
		if not strUrl:
			ctyCached = mpCtyCached.get(strCountry)
			if ctyCached is not None:
				strUrl = ctyCached.strUrlFlag
		if not strUrl:
			if fPopulate:
				strUrl = StrUrlFlagFromTeam(strCountry)   # API — populate path only
			else:
				sys.exit(f"ERROR: no cached flag for country {strCountry!r}; run: rcs --reload-all")
		mpStrCty[strCountry] = SCountry(strCountry=strCountry, strUrlFlag=strUrl)
	return mpStrCty


def MpCochResolve(
	lSqd:            list[SSquad],
	mpStrCountryUrl: dict[str, str],
	mpCochCached:    dict[str, SCoach],
	fPopulate:       bool,
) -> dict[str, SCoach]:
	"""
	Resolve each coach's country to a canonical countries.yaml key, keyed by coach name.

	A coach with a flag on the page is already canonical (CoachFromP read it from the
	flag file). A coach without one shares the team's country: if the team heading is
	already a known country name it's kept as-is (free); otherwise it's a genuine HTTP
	fact — resolved via the team-flag API when populating (and its URL folded into
	mpStrCountryUrl so countries.yaml gets it), served from coaches.yaml otherwise, or an
	error toward --reload-all when uncached. This is where the coming per-coach article
	fetch slots in: another populate-only lookup, gated the same way.
	"""
	mpStrCoch: dict[str, SCoach] = {}
	for sqd in lSqd:
		coch       = sqd.coach
		strCountry = coch.strCountry
		if strCountry not in mpStrCountryUrl:
			cochCached = mpCochCached.get(coch.strName)
			if cochCached is not None:
				strCountry = cochCached.strCountry
			elif fPopulate:
				strUrl     = StrUrlFlagFromTeam(strCountry)      # API — populate path only
				strCountry = StrCountryFromUrl(strUrl) or strCountry
				if strUrl:
					mpStrCountryUrl.setdefault(strCountry, strUrl)
			else:
				sys.exit(f"ERROR: no cached country for coach {coch.strName!r}; run: rcs --reload-all")
		mpStrCoch[coch.strName] = replace(coch, strCountry=strCountry)
	return mpStrCoch


def LoadDatabase(fReloadAll: bool) -> None:
	"""
	"Load" mode: fetch the latest squads page, refresh the sidecar caches, and write
	database/squads.yaml. A future "PDF" mode reads squads.yaml + countries.yaml.
	"""
	pathSquads    = g_pathDatabase / "squads.yaml"
	pathCountries = g_pathDatabase / "countries.yaml"
	pathCoaches   = g_pathDatabase / "coaches.yaml"

	soup = FetchSquadsPage()
	lSqd = LSqdFromSoup(soup)
	print(f"Parsed {len(lSqd)} teams")

	mpStrCountryUrl = MpStrCountryUrlFromSoup(soup)

	# coaches.yaml — resolve each coach's country to a canonical key. Populate (allow the
	# team-flag API for a non-canonical team heading) on --reload-all or when the file is
	# absent; otherwise serve cached coaches and error on an uncached HTTP-needing one.
	fPopulateCoaches = fReloadAll or not pathCoaches.exists()
	mpCochCached = {} if fPopulateCoaches else MpCochFromObj(ObjLoadYaml(pathCoaches))
	mpStrCoch = MpCochResolve(lSqd, mpStrCountryUrl, mpCochCached, fPopulateCoaches)
	WriteYaml(pathCoaches, LObjFromMpCoch(mpStrCoch))
	print(f"Wrote {pathCoaches} ({len(mpStrCoch)} coaches)")

	# Fold the resolved coach countries back onto the squads for squads.yaml.
	lSqd = [replace(sqd, coach=mpStrCoch[sqd.coach.strName]) for sqd in lSqd]

	# countries.yaml — assemble every referenced country's flag URL. Free URLs come from
	# this run's harvest; a country missing from it is resolved via the API at populate
	# time, served from the cache otherwise, or an error toward --reload-all.
	fPopulateCountries = fReloadAll or not pathCountries.exists()
	mpCtyCached = {} if fPopulateCountries else MpCtyFromObj(ObjLoadYaml(pathCountries))
	mpStrCty = MpCtyBuild(lSqd, mpStrCountryUrl, mpCtyCached, fPopulateCountries)
	WriteYaml(pathCountries, LObjFromMpCty(mpStrCty))
	print(f"Wrote {pathCountries} ({len(mpStrCty)} countries)")

	WriteYaml(pathSquads, LObjGroupFromLSqd(lSqd))
	print(f"Wrote {pathSquads}")


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
