#!/usr/bin/env python3

from __future__ import annotations  # Forward refs without quotes (eg foo: CFoo, not foo: 'CFoo')

import arrow
import copy
import openpyxl
import polib
import re

from babel import Locale
from datetime import datetime, timezone
from enum import IntEnum, auto
from pathlib import Path
from typing import Optional, cast

from bolay import IntEnum0, EnumTuple, SColor, ColorFromStr, ColorResaturate, FIsSaturated

from . import __project__, __version__, __author_email__

TExcelRow = dict[str, str]				# tag = xlrow
TExcelSheet = list[TExcelRow]			# tag = xls
TExcelBook = dict[str, TExcelSheet]		# tag = xlb

g_pathCode = Path(__file__).parent

class CDataBase: # tag = db

	s_pathDir = g_pathCode / 'database'

	@classmethod
	def LStrNameTournament(cls) -> list[str]:
		lPath = cls.s_pathDir.glob('*.xlsx')
		return [path.stem for path in sorted(lPath) if path.stem != 'localization' and path.stem[0].isdigit()]

	def __init__(self, strName: str) -> None:

		self.strName = strName
		self.pathFile = self.s_pathDir / (strName + '.xlsx')

	def XlbLoad(self) -> TExcelBook:
		wb = openpyxl.load_workbook(filename = str(self.pathFile), data_only=True)
		
		xlb: TExcelBook = {}
		
		for ws in wb.worksheets:
			# skip worksheets starting with pound sign... so we can have scratch sheets for conversion work
			if str(ws.title).startswith('#'):
				continue
			lStrKey: list[str] = []
			lStrFill: list[str] = []
			xls: TExcelSheet = []
			for row in ws.rows:
				lValRow = [cell.value for cell in row]
				# skip empty rows and rows starting with a '#'
				if not lValRow:
					continue
				valStart = lValRow[0]
				strStart = '' if valStart is None else str(valStart)
				if strStart.startswith('#'):
					continue
				if not lStrKey:
					while not lValRow[-1]:
						del lValRow[-1]
					assert all(lValRow), f'header row has an empty value: {lValRow}'
					lStrKey = [cast(str, val).lower() for val in lValRow]
					assert lStrKey
					lStrFill = [''] * len(lStrKey)
				else:
					lStrValue: list[str] = ['' if val is None else str(val) for val in lValRow] + lStrFill
					xlrow: TExcelRow = dict(zip(lStrKey, lStrValue))
					xls.append(xlrow)
			xlb[str(ws.title).lower()] = xls

		return xlb


def StrFromLocale(locale: Locale) -> str:
	assert(locale.language)

	lStr = [locale.language]

	if locale.script:
		lStr.append(locale.script)

	if locale.territory:
		lStr.append(locale.territory)

	return '_'.join(lStr).lower()

class CLocalizationDataBase(CDataBase): # tag = loc

	s_pathDirPotPo = g_pathCode / 'localization'

	def __init__(self) -> None:

		super().__init__('localization')

		self.mpStrSectionSetStrSubkey: dict[str, set[str]] = {}
		self.setLocale: set[Locale] = set()
		self.mpStrKeyStrLocaleStrText: dict[str, dict[str, str]] = {}

		xlb: TExcelBook = self.XlbLoad()

		for strSection, xls in xlb.items():
			setStrSubkey = self.mpStrSectionSetStrSubkey.setdefault(strSection, set())
			for xlrow in xls:
				strSubkey = xlrow['key'].lower()
				del xlrow['key']

				
				for strLocale in xlrow.keys():
					self.setLocale.add(Locale.parse(strLocale))
				
				setStrSubkey.add(strSubkey)

				strKey = strSection + '.' + strSubkey
				strKey = strKey.lower()

				self.mpStrKeyStrLocaleStrText[strKey] = xlrow

		# used to create our pot/po files.
		#self.DumpPotPos()

	def StrTranslation(self, strKey: str, locale: Locale) -> str:
		strKey = strKey.lower()

		mpStrLocaleStrText = self.mpStrKeyStrLocaleStrText[strKey]

		lStrLocale = [
			str(locale),		# full name... en_US or zh_Hans_CN
		]

		if locale.script:
			lStrLocale.append(f"{locale.language}_{locale.script}")

		if locale.language != 'en':
			lStrLocale.append(locale.language)

		for strLocale in lStrLocale:
			try:
				if strText := mpStrLocaleStrText[strLocale.lower()]:
					return strText
			except KeyError:
				pass

		return mpStrLocaleStrText['en']
	
	def DumpPotPos(self):
		# write to a pot and pos for each locale

		mpLocalePof = { locale: polib.POFile() for locale in self.setLocale }
		localeEn = Locale.parse('en')
		assert(localeEn in mpLocalePof)
		dtUtcNow = datetime.now(timezone.utc)
		strDateUtcNow = dtUtcNow.strftime('%Y-%m-%d %H:%M+0000')
		strYearUtcNow = dtUtcNow.strftime('%Y')

		setStrLangUntranslated = set(('nb', 'sv', 'cs', 'hr', 'pl', 'el', 'sw', 'uz'))

		# header

		strHeader = '\n'.join((
			f"Soccer Tournament Poster localization template.",
			f"©️ {strYearUtcNow} {__author_email__}",
			f"This file is distributed under the same license as the {__project__} package."))
		# metadata

		objMetadata = {
			'Content-Type': 'text/plain; charset=UTF-8',
			'Content-Transfer-Encoding': '8bit', # vestigal, but some tools complain if it's missing
			'Project-Id-Version': f"{__project__} {__version__}",
			'POT-Creation-Date': strDateUtcNow,
			'PO-Revision-Date': strDateUtcNow,
			'Last-Translator': __author_email__,
			'Language-Team': __author_email__,
			'MIME-Version': '1.0',
			'X-Generator': 'stp.CLocalizationDatabase.DumpPotPos()',
			'X-Poedit-SourceCharset': 'UTF-8',
		}

		strOverview = ' '.join((
			f"This project supports a poster showing the fixtures or results of a football (soccer) tournament.",
			f"In all cases, shorter translations are preferred. Country names will be shrunk to fit, but",
			f"many other fields will just overflow. In general, the translation approach should match",
			f"that of a newspaper or sports page. Be brief and colloquial, not vebose or technical.",
			f"We're aiming for a casual readership."))

		poeOverview = polib.POEntry(
			msgid=f"### overview - see notes ###",
			msgstr='',
			comment=strOverview,
			flags=['read-only'])
		
		for locale, pof in mpLocalePof.items():
			pof.metadata = copy.deepcopy(objMetadata)
			pof.metadata['Language'] = StrFromLocale(locale)
			pof.append(poeOverview)

		# section

		mpStrSectionStrComment: dict[str, str] = {
			'competition':	"Name of the poster- shown in the poster header. Inserted into the {name} field of page.format-title. Year goes before or after, according to that key.",
			'host':			"Host country or region - shown in poster header, but in limited space. Inserted into the {location} field of page.format.dates-and-location. Date range goes before or after, according to that key.",
			'venue':		"Venues where matches are held. Most often a city, but sometimes an arena name when a city had multiple locations.",
			'page':			"Title text and layout. If in doubt, leave alone.",
			'stage':		"Names of the stages of a soccer tournament.",
			'group':		"Abbreviations for the group stage sections of the poster.",
			'country':		"Country names, keyed by their 3 letter FIFA code.",
			'club':			"Club names, keyed by their 3 letter FIFA code. Resist translating terms - the whole name from the original language is almost always used. Leave off acronyms (eg FC) unless they disambiguate.",
		}

		mpStrKeyStrComment: dict[str, str] = {
			'match.format.label':				"How to format an ordinal match number.",
			'match.after-extra-time':			"How to abbreviate the term 'After Extra Time'.",
			'page.timezone.label':				"Inserted into the {label} of page.format.timezone.",
			'page.format.dates-and-location':	"Date range is built and inserted into {dates} field. Country from 'host' section is inserted into {location} field.",
			'page.format.timezone':				"Timezone is build and inserted into {timezone} field. Text from page.timezone.label is inserted into {label} field. Farsi version includes an invisible RtL character so that parenthesis apprear correctly.",
			'page.title.fixtures':				"Inserted into page.format.title when poster shows upcoming matches with no scores.",
			'page.title.results':				"Inserted into page.format.title when poster shows completed matches with scores.",
			'page.format.title':				"Layout of the poster title (centered, on top). Specifies order of year, competition title (from competition section), and poster label (fixtures/results)",
			'stage.round64':					"Caution. A literal translation of 'Round of' may be inappropriate. Some languages use forms like 'eighths final' or 'sixteenths final'.",
			'stage.round32':					"Caution. A literal translation of 'Round of' may be inappropriate. Some languages use forms like 'eighths final' or 'sixteenths final'.",
			'stage.round16':					"Caution. A literal translation of 'Round of' may be inappropriate. Some languages use forms like 'eighths final' or 'sixteenths final'.",
			'stage.quarters':					"Caution. A literal translation of 'Round of' may be inappropriate. Some languages use forms like 'eighths final' or 'sixteenths final'.",
			'group.points':						"ABBREVIATION. Shown in a very small area. Indicates the 'points' of football standings (win=3pts, tie=1pt). Not related to goals.",
			'group.goals-for':					"ABBREVIATION. Shown in a very small area. Indicates goals the team scored. Not related to 'points'.",
			'group.goals-against':				"ABBREVIATION. Shown in a very small area. Indicates goals scored against the team. Not related to 'points'.",
		}

		for strSection, setStrSubkey in self.mpStrSectionSetStrSubkey.items():
			poeSection = polib.POEntry(
				msgid=f"### section: {strSection} - see notes ###",
				msgstr='',
				comment=mpStrSectionStrComment.get(strSection, ''),
				flags=['read-only'])

			for pof in mpLocalePof.values():
				pof.append(poeSection)

			for strSubkey in sorted(setStrSubkey):
				strKey = f"{strSection.lower()}.{strSubkey.lower()}"

				for locale, pof in mpLocalePof.items():
					strId = self.StrTranslation(strKey, localeEn)
					if locale != localeEn and locale.language not in setStrLangUntranslated:
						strMsg = self.StrTranslation(strKey, locale)
					else:
						strMsg = ''
					lStrFlags = ['fuzzy'] if locale.language in setStrLangUntranslated else []
					pof.append(
							polib.POEntry(
								msgctxt=strKey,
								msgid=strId,
								msgstr=strMsg,
								comment=mpStrKeyStrComment.get(strKey, ''),
								flags=lStrFlags))

		print("writing localizations")

		self.s_pathDirPotPo.mkdir(parents=True, exist_ok=True)

		mpLocalePof[localeEn].save(str(self.s_pathDirPotPo / f"{__project__}.pot"))
		for locale, pof in mpLocalePof.items():
			if locale != localeEn:
				pof.save(str(self.s_pathDirPotPo / f"{__project__}-{StrFromLocale(locale)}.po"))

g_loc = CLocalizationDataBase()

class STAGE(IntEnum):
	Group = auto()
	Round64 = auto()
	Round32 = auto()	# may not be used, depending on tourney size
	Round16 = auto() # ditto
	Quarters = auto()
	Semis = auto()
	Third = auto()
	Final = auto()

class SColors: # tag = colors
	s_dSDarker = 0.5

	s_rVLighter = 1.5
	s_rSLighter = 0.5

	s_rVDarker = 0.75	# for unsaturated colors
	s_dVLighter = 0.2

	def __init__(self, strColor: str) -> None:
		self.color: SColor = ColorFromStr(strColor)
		if FIsSaturated(self.color):
			self.colorDarker: SColor = ColorResaturate(self.color, dS=self.s_dSDarker)
			self.colorLighter: SColor = ColorResaturate(self.color, rV=self.s_rVLighter, rS=self.s_rSLighter)
		else:
			self.colorDarker: SColor = ColorResaturate(self.color, rV=self.s_rVDarker)
			self.colorLighter: SColor = ColorResaturate(self.color, dV=self.s_dVLighter)

class CGroup:
	def __init__(self, tourn: CTournamentDataBase, strGroup: str, mpStrSeedStrTeam: dict[str, str]) -> None:
		self.strName: str = strGroup
		self.colors: SColors = SColors(tourn.StrColorGroup(strGroup))
		self.mpStrSeedStrTeam: dict[str, str] = {strSeed:strTeam for strSeed, strTeam in mpStrSeedStrTeam.items() if strSeed[0] == strGroup}

class MATCHSTAT(IntEnum0):
	GoalsFor = auto()
	GoalsAgainst = auto()	# may not be used, depending on tourney size
	Points = auto()

class SResult(EnumTuple[MATCHSTAT, int]):
	def __init__(self, cGoalFor: int, cGoalAgainst: int, cPoint: int):
		super().__init__(MATCHSTAT, (cGoalFor, cGoalAgainst, cPoint))

class CResults:
	
	def __init__(self, stageElimFirst: STAGE, strTeam: str, setMatch: set[CMatch]):
		self.lResult: list[SResult] = []
		self.cPoint = 0
		self.strPlace = ''

		for match in sorted(setMatch, key=lambda match: match.tStart):
			if match.stage == stageElimFirst:
				if strTeam == match.strTeamHome:
					strSeed = match.strSeedHome
				else:
					assert strTeam == match.strTeamAway
					strSeed = match.strSeedAway

				if strSeed[0].isdigit() and not self.strPlace:
					self.strPlace = strSeed[0]

				continue
			
			elif match.stage == STAGE.Group:
				if strTeam == match.strTeamHome:
					cGoalFor, cGoalAgainst = match.scoreHome, match.scoreAway
				else:
					assert strTeam == match.strTeamAway
					cGoalFor, cGoalAgainst = match.scoreAway, match.scoreHome

				if cGoalFor > cGoalAgainst:
					cPoint = 3
				elif cGoalFor == cGoalAgainst:
					cPoint = 1
				else:
					cPoint = 0

				self.cPoint += cPoint

				assert len(self.lResult) < 3

				self.lResult.append(SResult(cGoalFor, cGoalAgainst, cPoint))

class CMatch:
	s_patAlphaNum = re.compile('([a-zA-Z]+)-*([0-9]+)')
	s_patNumAlpha = re.compile('([0-9]+)-*([a-zA-Z]+)')

	def __init__(self, tourn: CTournamentDataBase, xlrow: TExcelRow) -> None:
		self.tourn = tourn
		self.id = int(xlrow['match'])
		self.venue: int = int(xlrow['venue'])
		self.strSeedHome: str = xlrow['home-seed']
		self.strSeedAway: str = xlrow['away-seed']
		self.tStart: arrow.Arrow = arrow.get(xlrow['time'])

		self.strTeamHome: str = xlrow['home-team'] if xlrow['home-team'] else tourn.mpStrSeedStrTeam.get(self.strSeedHome, '')
		self.strTeamAway: str = xlrow['away-team'] if xlrow['away-team'] else tourn.mpStrSeedStrTeam.get(self.strSeedAway, '')

		self.scoreHome: int = int(xlrow['home-score']) if xlrow['home-score'] else -1
		self.scoreAway: int = int(xlrow['away-score']) if xlrow['away-score'] else -1

		self.fAfterExtraTime: bool = bool(xlrow.get('after-extra-time'))

		self.scoreHomeTiebreaker: int = int(xlrow['home-tiebreaker']) if xlrow['home-tiebreaker'] else -1
		self.scoreAwayTiebreaker: int = int(xlrow['away-tiebreaker']) if xlrow['away-tiebreaker'] else -1

		self.stage: STAGE = cast(STAGE, None)
		self.lStrGroup: list[str] = []
		self.idFeederHome: Optional[int] = None
		self.idFeederAway: Optional[int] = None
		self.idFeeding: Optional[int] = None

		# display sort order of the elimination bracket. final is in the middle, with
		# each match's home feeder being before and away feeder being after.

		self.sortElim: int = 0

		if self.strSeedHome in tourn.mpStrSeedStrTeam and \
		   self.strSeedAway in tourn.mpStrSeedStrTeam:
			self.stage = STAGE.Group
			assert self.strSeedHome[0] == self.strSeedAway[0]
			self.lStrGroup = [self.strSeedHome[0]]
		elif matHome := self.s_patNumAlpha.match(self.strSeedHome):
			matAway = self.s_patNumAlpha.match(self.strSeedAway)
			assert matAway
			self.stage = tourn.stageElimFirst
			self.lStrGroup = [ch for ch in matHome[2]] + [ch for ch in matAway[2]]
		elif matHome := self.s_patAlphaNum.match(self.strSeedHome):
			matAway = self.s_patAlphaNum.match(self.strSeedAway)
			assert matAway
			assert matHome[1] == matAway[1]

			self.idFeederHome = int(matHome[2])
			self.idFeederAway = int(matAway[2])

			if matHome[1] != 'W':
				assert matHome[1] == 'RU' or matHome[1] == 'L'
				self.stage = STAGE.Third
			else:
				# leaving self.stage as None. we'll set it based on feeders' stages
				pass
		else:
			assert False

	def LinkFeeders(self, mpIdMatch: dict[int, 'CMatch']) -> None:

		# both the final and thiurd place match are fed by the semis.
		# we use idFeeding for sorting the bracket, so it's ok to ignore the third place match
		if self.stage == STAGE.Third:
			return
		
		for idFeeder in (self.idFeederHome, self.idFeederAway):
			if idFeeder is None:
				continue
			matchFeeder = mpIdMatch[idFeeder]
			assert matchFeeder.idFeeding is None
			matchFeeder.idFeeding = self.id

	def FTrySetStage(self, tourn: CTournamentDataBase, stagePrev: STAGE, stage: STAGE):
		assert self.stage is None
		assert self.idFeederHome is not None
		assert self.idFeederAway is not None

		# no ordered sets in python, and we want to preserve order in this case

		setStrGroup: set[str] = set()
		lStrGroup: list[str] = []

		for id in (self.idFeederHome, self.idFeederAway):
			match = tourn.mpIdMatch[id]

			if match.stage != stagePrev:
				return False

			for strGroup in match.lStrGroup:
				if strGroup not in setStrGroup:
					setStrGroup.add(strGroup)
					lStrGroup += strGroup

		if stagePrev == tourn.stageElimFirst:
			assert not self.lStrGroup
			#assert len(lStrGroup) >= 4
			self.lStrGroup = lStrGroup
		elif stagePrev > tourn.stageElimFirst:
			assert not self.lStrGroup
			# revert sorting if we have everything
			self.lStrGroup = lStrGroup if len(lStrGroup) < len(self.tourn.lStrGroup) else self.tourn.lStrGroup

		self.stage = stage

		return True
	
	def FHasResults(self) -> bool:
		return self.strTeamHome and self.strTeamAway and self.scoreHome != -1 and self.scoreAway != -1

class CTournamentDataBase(CDataBase): # tag = tourn

	s_mpCSeedStageElimFirst = {
		8:	STAGE.Semis,
		12:	STAGE.Quarters,
		16:	STAGE.Quarters,
		24:	STAGE.Round16,
		32:	STAGE.Round16,
		48:	STAGE.Round32,
		64:	STAGE.Round32,
	}

	s_mpStrNameTourn: dict[str, CTournamentDataBase] = {}

	@classmethod
	def TournFromStrName(cls, strName: str) -> CTournamentDataBase:
		tourn = cls.s_mpStrNameTourn.get(strName)
		
		if tourn is None:
			tourn = cls(strName)
			cls.s_mpStrNameTourn[strName] = tourn

		return tourn
	
	def __init__(self, strName: str):

		super().__init__(strName)

		xlb: TExcelBook = self.XlbLoad()

		# properties come from the properties table

		self.objProperties: dict[str, str] = {xlrow['key']:xlrow['value'] for xlrow in xlb['properties']}
		
		# both MpStrGroupGroup() and CMatch.__init__() depend on self.mpStrSeedTeam existing

		self.mpStrSeedStrTeam: dict[str, str] = {xlrow['seed']:xlrow['team'] for xlrow in xlb['seeds']}

		setStrTeam: set[str] = set(map(lambda s: s.lower(), self.mpStrSeedStrTeam.values()))
		fAllCountries: bool = self.FLocSectionHasAllKeys('country', setStrTeam)
		fAllClubs: bool = self.FLocSectionHasAllKeys('club', setStrTeam)

		self.strKeyTeamPrefix: str = 'country.' if fAllCountries or not fAllClubs else 'club.'	

		self.stageElimFirst = self.s_mpCSeedStageElimFirst[len(self.mpStrSeedStrTeam)]

		self.mpStrGroupGroup: dict[str, CGroup] = self.MpStrGroupGroup()
		self.lStrGroup: list[str] = sorted(self.mpStrGroupGroup.keys())
		self.setStrGroup: set[str] = set(self.lStrGroup)
		self.mpStrTeamGroup: dict[str, CGroup] = {strTeam:group for group in self.mpStrGroupGroup.values() for strTeam in group.mpStrSeedStrTeam.values()}

		self.mpIdMatch: dict[int, CMatch] = {int(xlrow['match']):CMatch(self, xlrow) for xlrow in xlb['matches']}

		self.fHasAllResults = all([match.FHasResults() for match in self.mpIdMatch.values()])

		for match in self.mpIdMatch.values():
			match.LinkFeeders(self.mpIdMatch)

		self.mpStageSetMatch: dict[STAGE, set[CMatch]] = self.MpStageSetMatch()
		self.mpStrTeamResults: dict[str, CResults] = self.MpStrTeamResults()

		setMatchFinal = self.mpStageSetMatch[STAGE.Final]
		assert len(setMatchFinal) == 1
		self.matchFinal = next(iter(setMatchFinal))
		del self.mpStageSetMatch[STAGE.Final]

		self.matchThird: Optional[CMatch] = None
		
		try:
			setMatchThird = self.mpStageSetMatch[STAGE.Third]
			assert len(setMatchThird) == 1
			self.matchThird = next(iter(setMatchThird))
			del self.mpStageSetMatch[STAGE.Third]
		except KeyError:
			pass

		self.AssignSortElim()
		
		self.setMatchGroup: set[CMatch] = self.mpStageSetMatch[STAGE.Group]
		self.setMatchElimination: set[CMatch] = set().union(*[setMatch for stage, setMatch in self.mpStageSetMatch.items() if stage != STAGE.Group])
		
		self.setMatchElimHalfHome: set[CMatch] = self.SetMatchElimHalfHome()
		self.setMatchElimHalfAway: set[CMatch] = self.SetMatchElimHalfAway()

	def MpStrGroupGroup(self) -> dict[str, CGroup]:
		""" build list of groups from team seedings. """
		mpStrGroupGroup: dict[str, CGroup] = {}

		setStrGroup: set[str] = {strSeed[:1] for strSeed in self.mpStrSeedStrTeam}
		assert len(setStrGroup) <= 16
		assert 'ABCDEFGHIJKLMNOP'[:len(setStrGroup)] == ''.join(sorted(setStrGroup))

		for strGroup in setStrGroup:
			mpStrGroupGroup[strGroup] = CGroup(self, strGroup, self.mpStrSeedStrTeam)

		return mpStrGroupGroup

	def MpStageSetMatch(self) -> dict[STAGE, set[CMatch]]:
		""" allot matches to stages. """

		mpStageSetMatch: dict[STAGE, set[CMatch]] = {}
		setMatchNoStage: set[CMatch] = set()

		for match in self.mpIdMatch.values():
			if match.stage is not None:
				mpStageSetMatch.setdefault(match.stage, set()).add(match)
			else:
				setMatchNoStage.add(match)

		stagePrev: STAGE = self.stageElimFirst

		while setMatchNoStage:
			setMatchPrev = mpStageSetMatch[stagePrev]

			if len(setMatchPrev) == 8:
				assert len(setMatchNoStage) == 7
				stageNext = STAGE.Quarters
			elif len(setMatchPrev) == 4:
				assert stagePrev == STAGE.Quarters
				assert len(setMatchNoStage) == 3
				stageNext = STAGE.Semis
			elif len(setMatchPrev) == 2:
				assert stagePrev == STAGE.Semis
				assert len(setMatchNoStage) == 1
				stageNext = STAGE.Final
			else:
				stageNext = STAGE(stagePrev + 1)

			setMatchNext: set[CMatch] = set()

			for match in setMatchNoStage:
				if match.FTrySetStage(self, stagePrev, stageNext):
					setMatchNext.add(match)
			
			assert setMatchNext

			setMatchNoStage -= setMatchNext
			mpStageSetMatch[stageNext] = setMatchNext

			stagePrev = stageNext

		return mpStageSetMatch
	
	def MpStrTeamResults(self) -> dict[str, CResults]:
		""" allot matches to stages. """

		mpStrTeamSetMatch: dict[str, set[CMatch]] = {}

		for match in self.mpIdMatch.values():
			if not match.FHasResults():
				continue

			mpStrTeamSetMatch.setdefault(match.strTeamHome, set()).add(match)
			mpStrTeamSetMatch.setdefault(match.strTeamAway, set()).add(match)

		return {
			strTeam: CResults(self.stageElimFirst, strTeam, setMatch)
				for strTeam, setMatch in mpStrTeamSetMatch.items()
		}

	def AssignSortElim(self):
		sortElimNext: int = 1
		lIdStack: list[int] = [self.matchFinal.id]
		setIdVisited: set[int] = set()

		while lIdStack:
			idCur = lIdStack.pop()
			matchCur = self.mpIdMatch[idCur]
			assert matchCur.sortElim == 0

			if matchCur.id in setIdVisited:
				matchCur.sortElim = sortElimNext
				sortElimNext += 1
			else:
				setIdVisited.add(idCur)

				if matchCur.idFeederAway is not None:
					lIdStack.append(matchCur.idFeederAway)
				lIdStack.append(idCur)
				if matchCur.idFeederHome is not None:
					lIdStack.append(matchCur.idFeederHome)

	def SetMatchElimHalfHome(self) -> set[CMatch]:
		assert self.matchFinal.idFeederHome is not None
		return self.SetMatchElimFeeding(self.matchFinal.idFeederHome)
	
	def SetMatchElimHalfAway(self) -> set[CMatch]:
		assert self.matchFinal.idFeederAway is not None
		return self.SetMatchElimFeeding(self.matchFinal.idFeederAway)

	def SetMatchElimFeeding(self, id: int) -> set[CMatch]:
		""" return emlimination matches that feed a particular match id. """

		setIdFeeding: set[int] = set([id])
		setIdVisit: set[int] = copy.copy(setIdFeeding)

		while setIdVisit:
			match = self.mpIdMatch[setIdVisit.pop()]

			for idFeeder in (match.idFeederHome, match.idFeederAway):
				if idFeeder is None:
					continue

				setIdFeeding.add(idFeeder)
				setIdVisit.add(idFeeder)

		return {self.mpIdMatch[id] for id in setIdFeeding}

	def FLocSectionHasAllKeys(self, strSection: str, setStrKeys: set[str]) -> bool:
		return setStrKeys.issubset(g_loc.mpStrSectionSetStrSubkey[strSection])

	def StrKeyTeam(self, strKey: str) -> str:
		return self.strKeyTeamPrefix + strKey
	
	def StrKeyCompetition(self) -> str:
		return 'competition.' + self.objProperties['competition']

	def StrKeyHost(self) -> str:
		return 'host.' + self.objProperties['host']

	def StrTimezone(self) -> str:
		return self.objProperties['timezone']
	
	def StrColorGroup(self, strGroup: str) -> str:
		return self.objProperties[f"color.{strGroup.lower()}"]
	
	def StrKeyVenue(self, venue: int) -> str:
		return 'venue.' + self.objProperties[f"venue.{venue:02}"]
