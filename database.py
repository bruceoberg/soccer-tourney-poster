#!/usr/bin/env python3

"""
soccer tournament roster data from wikipedia
"""

from __future__ import annotations  # Forward refs without quotes

from bs4 import BeautifulSoup, Tag
from dateutil import parser as dateutil_parser
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from tqdm import tqdm
from typing import Literal

import re
import requests
import sys
import time
import urllib.parse
import yaml

from .common import strSquadsPage
from .util import CMpStrInjected

g_strUrlWikipedia = "https://en.wikipedia.org"

# Persistent data store. The "load" step rewrites squads.yaml every run (rosters change
# often) and maintains two sidecar caches for data that needs an HTTP lookup:
#
#   countries.yaml — country name -> flag URL + 3-letter FIFA code
#   coaches.yaml   — coach name -> coach record (home of the coming per-coach data)
#
# A normal run makes a single network call (the squads page); the sidecars supply
# everything else. See LoadDatabase for the populate-vs-normal caching policy.

g_pathDatabase = Path("database")
s_pathDatabaseFile    = g_pathDatabase / "db.yaml"

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

# database classes

class SPlayer(BaseModel): # tag = playero
	"""One player row from a squad wikitable."""

	model_config = ConfigDict(populate_by_name=True)

	strName:	str				= Field(exclude=True)	# injected on load by CMpStrInjected
	strNumber:	str				= Field(alias='jersey_number')
	strPos:   	str				= Field(alias='position')
	fCaptain: 	bool			= Field(alias='is_captain')		# team captain (parsed from a "(captain)" suffix on the name)
	strDob:   	str				= Field(alias='birthdate')		# compact ISO date "1995-03-12" (age parenthetical stripped)
	strCaps:  	str				= Field(alias='caps')
	strClub:  	str				= Field(alias='club')
	strCountry: str				= Field(alias='club_country')	# the club's country name ("" if the club cell carried no flag); flag URL lives in countries.yaml

type SPlayers = CMpStrInjected[SPlayer, Literal["strName"]] # tag = players

class SSquad(BaseModel): # tag = squado
	"""One national team's full tournament squad."""

	model_config = ConfigDict(populate_by_name=True)

	strTeam:	str				= Field(exclude=True)	# injected on load by CMpStrInjected
	strCoach:	str				= Field(alias='coach')
	strUrl:		str				= Field(alias='url')
	players:	SPlayers		= Field(alias='players')

type SGroup = CMpStrInjected[SSquad, Literal["strTeam"]] # tag = group

class SCoach(BaseModel): # tag = coach
	"""One team's head coach, with nationality inferred from the squad page."""

	model_config = ConfigDict(populate_by_name=True)

	strName:	str				= Field(exclude=True)	# injected on load by CMpStrInjected
	strCountry: str				= Field(alias='country')
	lStrPrevJobs: list[str]		= Field(alias='previous_jobs')

class SCountry(BaseModel): # tag = country
	"""A country's flag and FIFA code, cached in countries.yaml so a normal run needs no lookup."""

	model_config = ConfigDict(populate_by_name=True)

	strName:	str				= Field(exclude=True)	# injected on load by CMpStrInjected
	strUrlFlag:  str			= Field(alias='flag_url')
	strFifaCode: str			= Field(alias='fifa_code')

type SGroups = dict[str, SGroup] # tag = groups
type SCoaches = CMpStrInjected[SCoach, Literal["strName"]] # tag = coaches
type SCountries = CMpStrInjected[SCountry, Literal["strName"]] # tag = countries

class SDatabase(BaseModel): # tag = db
	
	model_config = ConfigDict(populate_by_name=True)

	groups:		SGroups		= Field(alias='groups')
	coaches:	SCoaches	= Field(alias='coaches')
	countries:	SCountries	= Field(alias='countries')


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


def StrUrlFlagFromImg(tagImg: Tag) -> str:
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
	strSrc = tagImg.get("src", "")
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


def PlayerFromRow(row: Tag) -> SPlayer | None:
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
		strName  	= strName,
		jersey_number	= StrCellText(lCols[0]),
		position   	= StrCellText(lCols[1]),
		fCaptain 	= fCaptain,
		strDob   	= StrDobCompact(StrCellText(lCols[3])),
		strCaps  	= StrCellText(lCols[4]),
		# lCols[5] is the Goals column — not captured in SPlayer
		strClub		= StrCellText(lCols[6]),
		strCountry	= StrCountryFromCell(lCols[6]),
	)


def LPlayerFromTable(table: Tag) -> list[SPlayer]:
	"""Parse a squad wikitable into a list of players, skipping the header row."""
	lPlayer: list[SPlayer] = []
	for row in table.find_all("tr")[1:]:  # [1:] skips the column header row
		player = PlayerFromRow(row)
		if player is not None:
			lPlayer.append(player)
	return lPlayer



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


# Candidate national-team article titles to probe for a country's FIFA code, most
# specific first. The bare "<country> national football team" title is frequently a
# men's/women's disambiguation page (Sweden, Australia, New Zealand, …) that carries no
# infobox at all, so we try the explicit men's titles ahead of it; the "soccer" variants
# cover the US/Canada/Australia naming. The first title whose infobox yields a code wins.

g_lStrFifaSuffix = [
	" men's national football team",
	" men's national soccer team",
	" national football team",
	" national soccer team",
]

# A FIFA code is exactly three uppercase letters. The infobox data cell may carry a
# trailing footnote marker, so we pull the first such token rather than taking the
# whole cell text.

g_reFifaCode = re.compile(r"\b[A-Z]{3}\b")


def StrFifaFromInfobox(strHtml: str) -> str:
	"""
	The FIFA code from a national-team article's infobox HTML, or "".

	We read the rendered "FIFA code" header cell and its paired data cell ("ENG") rather
	than the wikitext: the wikitext field name ("FIFA Trigramme") and its wrapping template
	vary between articles — several build the infobox indirectly, so that field never
	appears in the lead-section wikitext at all, while the rendered label is uniform.
	"""
	soup = BeautifulSoup(strHtml, "html.parser")
	for th in soup.find_all("th"):
		if th.get_text(strip=True).lower() == "fifa code":
			td = th.find_next_sibling("td")
			if td is not None:
				match = g_reFifaCode.search(td.get_text(" ", strip=True))
				if match is not None:
					return match.group(0)
	return ""


def StrFifaFromCountry(strCountry: str) -> str:
	"""
	The 3-letter FIFA code for a country (e.g. "England" -> "ENG"), or "".

	HTTP lookup against the country's men's national-team article infobox — populate path
	only, the sibling of StrUrlFlagFromTeam. We probe the candidate titles in
	g_lStrFifaSuffix (most specific first, to dodge disambiguation pages) and return the
	first article whose infobox carries a code. A missing page returns an API "error"
	object with HTTP 200, so we simply skip to the next candidate.
	"""
	for strSuffix in g_lStrFifaSuffix:
		objJson = ObjApiParse({
			"action":    "parse",
			"page":      strCountry + strSuffix,
			"prop":      "text",
			"redirects": "1",
		})
		if "error" in objJson:
			continue
		strHtml = objJson.get("parse", {}).get("text", {}).get("*", "")
		strFifa = StrFifaFromInfobox(strHtml)
		if strFifa:
			return strFifa
	return ""


# A managerial-career row's first cell is a years range that opens with a 4-digit year
# ("2021–2022", "2024–"); the medal-record and footnote rows that follow the career block
# do not, so this both recognizes career rows and marks where the block ends.

g_reCareerYears = re.compile(r"^\d{4}")

# A still-current job has an open-ended date: a year, the en-dash (or hyphen) separator,
# then nothing (or "present"). That last entry is the national team the coach holds now,
# which we drop so previous_jobs holds only prior jobs.

g_reCareerCurrent = re.compile(r"\d{4}\s*[–-]\s*(present)?\s*$", re.IGNORECASE)


def StrTitleFromUrl(strUrl: str) -> str:
	"""Wikipedia article title from a /wiki/ URL ("…/Mauricio_Pochettino" -> "Mauricio Pochettino")."""
	return urllib.parse.unquote(strUrl.rsplit("/wiki/", 1)[-1]).replace("_", " ")


def LStrPrevJobsFromCoachUrl(strUrl: str) -> list[str]:
	"""
	A coach's two most-recent prior managerial jobs (newest first), padded to length 2.

	HTTP lookup against the coach's Wikipedia article — populate path only, the sibling of
	StrFifaFromCountry. We read the rendered infobox rather than the wikitext: each row after
	the "Managerial career" header pairs a years cell (th, "2021–2022") with a team cell (td,
	whose link names the club/country). We drop the trailing current job (open-ended date — the
	national team the coach holds now) and return the previous two team names, newest first.
	Returns ["", ""] when the article, infobox, or career section is missing.
	"""
	if not strUrl:
		return ["", ""]

	objJson = ObjApiParse({
		"action":    "parse",
		"page":      StrTitleFromUrl(strUrl),
		"prop":      "text",
		"redirects": "1",
	})
	if "error" in objJson:
		return ["", ""]

	soup = BeautifulSoup(objJson.get("parse", {}).get("text", {}).get("*", ""), "html.parser")
	infobox = soup.find("table", {"class": "infobox"})
	if infobox is None:
		return ["", ""]

	# Walk the infobox rows: skip until the "Managerial career" header, then collect each
	# (team, is-current) career row until the years cell stops looking like a year range.
	lStrTeamCareer: list[tuple[str, bool]] = []
	fInCareer = False
	for tr in infobox.find_all("tr"):
		th = tr.find("th")
		if not fInCareer:
			if th is not None and "Managerial career" in th.get_text(strip=True):
				fInCareer = True
			continue

		strYears = th.get_text(" ", strip=True) if th is not None else ""
		if strYears == "Years":
			continue  # some infoboxes carry a "Years | Team" column sub-header — skip it
		if not g_reCareerYears.match(strYears):
			break  # left the career block (medal record, footnotes, …)

		td = tr.find("td")
		if td is None:
			continue

		link = td.find("a")
		strTeam = link.get_text(strip=True) if link is not None else td.get_text(" ", strip=True)
		lStrTeamCareer.append((strTeam, bool(g_reCareerCurrent.search(strYears))))

	# Drop trailing current jobs (the national team coached now), then take the previous two
	# in chronological order and reverse to newest-first.
	while lStrTeamCareer and lStrTeamCareer[-1][1]:
		lStrTeamCareer.pop()

	lStrPrevJobs = [strTeam for strTeam, _ in lStrTeamCareer[-2:]]
	lStrPrevJobs.reverse()
	while len(lStrPrevJobs) < 2:
		lStrPrevJobs.append("")
	return lStrPrevJobs


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


def TagHeadingFromTag(node: Tag) -> Tag | None:
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

class CScraper:
	def __init__(self, dbCache: SDatabase):
		self.dbCache = dbCache
		self.mpStrGroupLSquad: dict[str, list[SSquad]] = {}
		self.mpStrCoachUrl: dict[str, str] = {}
		self.mpStrCountryUrl: dict[str, str] = {}

		self.lCoach: list[SCoach] = []
		self.lCountry: list[SCountry] = []

		self.ScrapeSquads()

	def ScrapeSquads(self) -> None:
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

		soup = SoupFetchSquads()

		strTeamCur:  str | None = None
		strGroupCur: str | None = None

		tagContent = soup.find("div", {"class": "mw-parser-output"})
		lTag = list(tagContent.children)

		for iTag, tag in enumerate(lTag):

			if not isinstance(tag, Tag):
				continue

			tagHeading = TagHeadingFromTag(tag)

			if tagHeading is not None:
				if tagHeading.name == "h3":
					strTeamCur = tagHeading.get_text(strip=True)
				else:
					# h2 group heading ("Group A") — record it and clear team context
					strGroupCur = tagHeading.get_text(strip=True)
					strTeamCur  = None

			elif tag.name == "p" and "Coach" in tag.get_text():
				strCoach = self.StrCoachScrape(tag, strTeamCur or "")

				# Scan ahead for the roster table, stopping at the next heading so a
				# Coach paragraph without its own table can't grab a later team's.
				# The descriptive <p> between the Coach line and the table carries
				# the team's article link, so capture the first one we pass.
				tableSquad: Tag | None = None
				strUrlTeam: str | None = None
				for tagLook in lTag[iTag + 1:]:
					if isinstance(tagLook, Tag):
						if tagLook.name == "table":
							tableSquad = tagLook
							break
						if TagHeadingFromTag(tagLook) is not None:
							break
						if tagLook.name == "p" and strUrlTeam is None:
							strUrlTeam = StrUrlTeamFromP(tagLook)

				if tableSquad is not None and strTeamCur is not None:
					lPlayer = LPlayerFromTable(tableSquad)

					# A real squad has players; this skips trailing summary sections
					# (e.g. "Coach representation by country") that also pair a
					# "Coach" paragraph with a table.
					if lPlayer:
						players: SPlayers = {player.strName: player for player in lPlayer}
						assert strGroupCur
						assert strTeamCur
						lSquad = self.mpStrGroupLSquad.setdefault(strGroupCur, [])
						lSquad.append(
							SSquad(
								strTeam  = strTeamCur,
								strCoach = strCoach,
								strUrl   = strUrlTeam or "",
								players  = players))
						
		cSquad = sum([len(lSquad) for lSquad in self.mpStrGroupLSquad.values()])
		print(f"Scraped {cSquad} squads in {len(self.mpStrGroupLSquad)} groups")

		self.ScrapeFlags(soup)

	def ScrapeFlags(self, soup: BeautifulSoup) -> None:
		"""
		Harvest every flag icon on the squads page into country name -> flag SVG URL.

		This is the free tier: it costs no extra HTTP (the page is already fetched) and
		covers every player's club country plus every coach whose nationality differs
		from their team. countries.yaml fills its remaining entries (coaches whose
		nationality matches their team) from the API at populate time.
		"""

		for flag in soup.find_all("span", {"class": "flagicon"}):
			img = flag.find("img")
			if img is None:
				continue
			strUrl     = StrUrlFlagFromImg(img)
			strCountry = StrCountryFromUrl(strUrl)
			if strCountry and strUrl:
				self.mpStrCountryUrl.setdefault(strCountry, strUrl)
		print(f"Scraped {len(self.mpStrCountryUrl)} flags")

	def StrCoachScrape(self, tagP: Tag, strTeam: str) -> str:
		"""
		Parse a <p>Coach: [flag] <a>Name</a></p> paragraph into an SCoach.

		A leading flagicon appears only when the coach's nationality differs from the
		team's; we canonicalize its country from the flag file (its alt text is unreliable,
		see StrCountryFromUrl). With no flagicon the coach shares the team's country, so
		strCountry falls back to the team heading — a raw name that MpCochResolve later maps
		to a canonical countries.yaml key (free when it already is one, else an API lookup).
		"""
		strCountry = strTeam

		tagFlag = tagP.find("span", {"class": "flagicon"})
		if tagFlag is not None:
			tagImg = tagFlag.find("img")
			strCountryFlag = StrCountryFromUrl(StrUrlFlagFromImg(tagImg)) if tagImg is not None else ""
			if strCountryFlag:
				strCountry = strCountryFlag

		for tagFlag in tagP.find_all("span", {"class": "flagicon"}):
			tagFlag.decompose()

		tagLink = tagP.find("a")
		if tagLink:
			strName = tagLink.get_text(strip=True)
		else:
			strName = tagP.get_text(strip=True).removeprefix("Coach:").strip()

		if len(self.lCoach) >= 48:
			pass

		# The name links to the coach's own article — capture it so the populate path can
		# read their managerial-career infobox. Footnote anchors are #cite fragments, so the
		# /wiki/ prefix test skips them.
		if tagLink is not None and tagLink.get("href", "").startswith("/wiki/"):
			self.mpStrCoachUrl[strName] = g_strUrlWikipedia + tagLink.get("href", "")

			coach = SCoach(strName=strName, strCountry=strCountry, lStrPrevJobs=[])
			self.lCoach.append(coach)

			return coach.strName
		
		return "Unknown"

	def ScrapeCoachesExtras(self) -> None:
		"""
		Resolve each coach's country to a canonical countries.yaml key, keyed by coach name.

		A coach with a flag on the page is already canonical (CoachFromP read it from the
		flag file). A coach without one shares the team's country: if the team heading is
		already a known country name it's kept as-is (free); otherwise it's a genuine HTTP
		fact — resolved via the team-flag API when populating (and its URL folded into
		mpStrCountryUrl so countries.yaml gets it), served from coaches.yaml otherwise, or an
		error toward --rescrape when uncached.

		previous_jobs is never on the squads page, so it follows the cache-or-API-or-error
		policy uniformly for every coach: served from coaches.yaml when present, fetched from
		the coach's article when populating, or an error toward --rescrape otherwise.
		"""

		strBarFormat = "{desc} {n_fmt}/{total_fmt}: {percentage:3.0f}%|{bar}|{postfix[0]}"

		with tqdm(total=len(self.lCoach), desc="Scraping Coaches", bar_format=strBarFormat, postfix=[" " * 20]) as pbar:
			for coach in self.lCoach:
				pbar.postfix[0] = f"{coach.strName:<20}"
				pbar.update(0)
				strCountry = coach.strCountry
				if strCountry not in self.mpStrCountryUrl:
					strUrl     = StrUrlFlagFromTeam(strCountry)
					strCountry = StrCountryFromUrl(strUrl) or strCountry
					if strUrl:
						self.mpStrCountryUrl.setdefault(strCountry, strUrl)

				# previous_jobs — never on the page, so the cache (a populated entry is always
				# length 2), else the coach-article API when populating, else an error.
				strUrlCoach = self.mpStrCoachUrl[coach.strName]
				coach.lStrPrevJobs = LStrPrevJobsFromCoachUrl(strUrlCoach)

				pbar.update(1)

	def ScrapeCountryExtras(self) ->None:
		"""
		Resolve every referenced country to an SCountry.

		flag_url comes free from this run's page harvest (mpStrCountryUrl); fifa_code never
		appears on the page, so it is always an HTTP fact. Both follow the same policy: prefer
		this run's free data, then the cache; a value still missing is resolved via the API when
		populating, or an error toward --rescrape otherwise. On full populate the FIFA lookup
		costs one API call per country (a few when the first candidate title misses), so it runs
		only on --rescrape or a first populate, never on a normal cached run.
		"""

		setStrCountry = self.SetStrCountryRef()

		strBarFormat = "{desc} {n_fmt}/{total_fmt}: {percentage:3.0f}%|{bar}|{postfix[0]}"

		with tqdm(total=len(setStrCountry), desc="Scraping Countries", bar_format=strBarFormat, postfix=[" " * 20]) as pbar:
			for strCountry in setStrCountry:
				pbar.postfix[0] = f"{strCountry:<20}"
				pbar.update(0)
				# flag_url — free from the page harvest, else the cache, else the API / an error.
				strUrl = self.mpStrCountryUrl.get(strCountry, "")

				if not strUrl:
					strUrl = StrUrlFlagFromTeam(strCountry)   # API — populate path only

				strFifa = StrFifaFromCountry(strCountry)   # API — populate path only

				self.lCountry.append(
							SCountry(
								strName = strCountry,
								strUrlFlag = strUrl,
								strFifaCode = strFifa))
				
				pbar.update(1)

	def SetStrCountryRef(self) -> set[str]:
		"""Every country name the output references (player club countries + coaches)."""
		setStrCountry: set[str] = set()
		for lSquad in self.mpStrGroupLSquad.values():
			for squad in lSquad:
				for player in squad.players.values():
					if player.strCountry:
						setStrCountry.add(player.strCountry)

		for coach in self.lCoach:
			if coach.strCountry:
				setStrCountry.add(coach.strCountry)

		return setStrCountry

	def Groups(self) -> SGroups:
		"""
		Bucket squads into group name -> team name -> team object, first-seen order.

		The team's group is implied by its parent key and the team name is its own
		key, so ObjFromSqd omits both.
		"""
		return {
			strGroup: {
				squad.strTeam: squad
				for squad in lSquad
			}
			for strGroup, lSquad in self.mpStrGroupLSquad.items()
		}
	
	def Coaches(self) -> SCoaches:
		if self.dbCache:
			return self.dbCache.coaches
		
		self.ScrapeCoachesExtras()
		
		return {coach.strName: coach for coach in self.lCoach}
		
	def Countries(self) -> SCountries:
		if self.dbCache:
			return self.dbCache.countries
		
		self.ScrapeCountryExtras()

		return {country.strName: country for country in self.lCountry}
	
	def Db(self) -> SDatabase:
		return SDatabase(
				groups = self.Groups(),
				coaches = self.Coaches(),
				countries = self.Countries())

def ObjApiParse(mpStrParams: dict[str, str]) -> dict:
	"""
	GET the MediaWiki action=parse API and return the decoded JSON.

	Retries with exponential backoff on HTTP 429 (rate limit) and on transient network
	failures (read/connect timeouts, dropped connections), honoring a Retry-After header
	when present, so the populate path's burst of per-country lookups doesn't fail the
	whole run on a single hiccup. A missing page is not an error here — the API returns
	HTTP 200 with an {"error": …} body, which we hand back for the caller to interpret.
	"""
	dTBackoff = 1.0
	cTry = 5
	for iTry in range(cTry):
		try:
			resp = g_session.get(
				"https://en.wikipedia.org/w/api.php",
				params={**mpStrParams, "format": "json"},
				timeout=15,
			)
		except requests.exceptions.RequestException:
			# Transient network error — back off and retry; re-raise on the last attempt.
			if iTry + 1 == cTry:
				raise
			time.sleep(dTBackoff)
			dTBackoff *= 2
			continue
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


def SoupFetchSquads() -> BeautifulSoup:
	objJson = ObjApiParse({
		"action": "parse",
		"page":   strSquadsPage,
		"prop":   "text",
	})
	strHtml = objJson["parse"]["text"]["*"]
	return BeautifulSoup(strHtml, "html.parser")


def StrUrlSquad(sqd: SSquad) -> str:
	"""Team article URL with the current-squad anchor, or "" if no URL was found."""
	if not sqd.strUrl:
		return ""
	return f"{sqd.strUrl}#{g_strSquadAnchor}"


def DbEnsure(fRescapeSquads: bool, fRescrapeAll: bool) -> SDatabase:
	if not s_pathDatabaseFile.exists():
		fRescrapeAll = True

	if fRescrapeAll:
		dbCache = None
	else:
		strYaml = s_pathDatabaseFile.read_text(encoding="utf-8")
		print(f"Reading {s_pathDatabaseFile.stem}...")
		objDb = yaml.safe_load(strYaml)
		dbCache = SDatabase.model_validate(objDb)

	if dbCache and not fRescapeSquads:
		db = dbCache
	else:
		db = CScraper(dbCache).Db()

		print(f"Writing {s_pathDatabaseFile.stem}...")

		s_pathDatabaseFile.write_text(
			yaml.dump(
        		db.model_dump(mode="json", by_alias=True),
				allow_unicode=True,   		# don't escape non-ASCII
				sort_keys=False,      		# preserve field declaration order
				default_flow_style=False))	# prettier?
		
	return db
