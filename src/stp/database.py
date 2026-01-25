#!/usr/bin/env python3

from __future__ import annotations  # Forward refs without quotes (eg foo: CFoo, not foo: 'CFoo')

import arrow
import copy
import openpyxl
import re

from babel import Locale
from enum import IntEnum, auto
from pathlib import Path
from typing import Optional, cast

from bolay import SColor, ColorFromStr, ColorResaturate, FIsSaturated

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
		self.mpStrKeyStrLocaleStrText: dict[str, dict[str, str]] = {}

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

	def StrTranslation(self, strKey: str, strLocale: str) -> str:
		strKey = strKey.lower()

		mpStrLocaleStrText = self.mpStrKeyStrLocaleStrText[strKey]

		try:
			if strText := mpStrLocaleStrText[strLocale]:
				return strText
		except KeyError:
			pass

		strLanguage = Locale.parse(strLocale).language

		try:
			if strText := mpStrLocaleStrText[strLanguage]:
				return strText
		except KeyError:
			pass

		return mpStrLocaleStrText['en']


class CLocalizationDataBase(CDataBase): # tag = loc

	def __init__(self) -> None:

		super().__init__('localization')

		self.mpStrSectionSetStrSubkey: dict[str, set[str]] = {}

		xlb: TExcelBook = self.XlbLoad()

		for strSection, xls in xlb.items():
			setStrSubkey = self.mpStrSectionSetStrSubkey.setdefault(strSection, set())
			for xlrow in xls:
				strSubkey = xlrow['key'].lower()
				del xlrow['key']
				
				setStrSubkey.add(strSubkey)

				strKey = strSection + '.' + strSubkey
				strKey = strKey.lower()

				self.mpStrKeyStrLocaleStrText[strKey] = xlrow

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
