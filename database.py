#!/usr/bin/env python3

# 'annotations' allow typing hints to forward reference.
#	e.g. Fn(fwd: CFwd) instead of Fn(fwd: 'CFwd')
#	when CFwd is later in file.
from __future__ import annotations

import arrow
import copy
import openpyxl
import re

from babel import Locale
from enum import IntEnum, auto
from pathlib import Path
from typing import Optional

from bolay import SColor, ColorFromStr, ColorResaturate, FIsSaturated
from config import g_strNameTourn

TExcelRow = dict[str, str]				# tag = xlrow
TExcelSheet = list[TExcelRow]			# tag = xls
TExcelBook = dict[str, TExcelSheet]		# tag = xlb

g_pathHere = Path(__file__).parent

class CDataBase: # tag = db

	s_pathDir = g_pathHere / 'database'

	def __init__(self, strName: str) -> None:

		self.pathFile = self.s_pathDir / (strName + '.xlsx')
		self.mpStrKeyStrLocaleStrText: dict[str, dict[str, str]] = {}

	def XlbLoad(self) -> TExcelBook:
		wb = openpyxl.load_workbook(filename = str(self.pathFile))
		
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
					lStrKey = [val.lower() for val in lValRow]
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
		self.colors: SColors = SColors(tourn.StrTranslation('colors.' + strGroup, 'en')) # BB (bruceo) delay this until necessary?
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

		self.stage: Optional[STAGE] = None
		self.lStrGroup: list[str] = []
		self.lIdFeeders: list[int] = []
		self.idFeeding: Optional[int] = None

		# this tuple is for sorting the columns of the elimination bracket.
		# as such, it starts with the most distant fed match (the final) and then
		# ids matches closer to this match, ending with the match's own id.

		self.tuIdFed: tuple[int] = ()

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
			
			if matHome[1] == 'RU' or matHome[1] == 'L':
				self.stage = STAGE.Third
				self.lIdFeeders = [int(matHome[2]), int(matAway[2])]
			else:
				# leaving self.stage as None, but setting ids so
				# we can set it based on feeders' stages
				assert matHome[1] == 'W'
				self.lIdFeeders = [int(matHome[2]), int(matAway[2])]
		else:
			assert False

	def LinkFeeders(self, mpIdMatch: dict[int, 'CMatch']) -> None:

		# both the final and thiurd place match are fed by the semis.
		# we use idFeeding for sorting the bracket, so it's ok to ign ore the third place match
		if self.stage == STAGE.Third:
			return
		
		for idFeeder in self.lIdFeeders:
			matchFeeder = mpIdMatch[idFeeder]
			assert matchFeeder.idFeeding is None
			matchFeeder.idFeeding = self.id

	def BuildTuIdFed(self, mpIdMatch: dict[int, 'CMatch']) -> None:
	
		lIdFeeding: list[int] = []
		matchFeeding: Optional[CMatch] = self

		while matchFeeding:
			lIdFeeding.append(matchFeeding.id)
			matchFeeding = mpIdMatch.get(matchFeeding.idFeeding)

		self.tuIdFed = tuple(reversed(lIdFeeding))

	def FTrySetStage(self, tourn: CTournamentDataBase, stagePrev: STAGE, stage: STAGE):
		assert self.stage is None
		assert self.lIdFeeders

		# no ordered sets in python, and we want to preserve order in this case

		setStrGroup: set[str] = set()
		lStrGroup: list[str] = []

		for id in self.lIdFeeders:
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

class CTournamentDataBase(CDataBase): # tag = tourn

	s_lStrKeyLocPrefix = ('tournament', 'colors')

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
		
		# translations come from both the tranlsations table (mostly unchanging) and the tournament table (new per contest)

		for strKeyLocPrefix in self.s_lStrKeyLocPrefix:
			assert strKeyLocPrefix not in g_loc.mpStrSectionSetStrSubkey
			for xlrow in xlb[strKeyLocPrefix]:
				self.mpStrKeyStrLocaleStrText[(strKeyLocPrefix + '.' + xlrow['key']).lower()] = xlrow

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

		for match in self.mpIdMatch.values():
			match.LinkFeeders(self.mpIdMatch)

		for match in self.mpIdMatch.values():
			match.BuildTuIdFed(self.mpIdMatch)

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
		
		self.setMatchGroup: set[CMatch] = self.mpStageSetMatch[STAGE.Group]
		self.setMatchElimination: set[CMatch] = set().union(*[setMatch for stage, setMatch in self.mpStageSetMatch.items() if stage != STAGE.Group])
		
		self.setMatchFirst: set[CMatch] = self.SetMatchElimHalfFirst()
		self.setMatchSecond: set[CMatch] = self.SetMatchElimHalfSecond()

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

	def SetMatchElimHalfFirst(self) -> set[CMatch]:
		assert len(self.matchFinal.lIdFeeders) == 2
		return self.SetMatchElimFeeding(self.matchFinal.lIdFeeders[0])
	
	def SetMatchElimHalfSecond(self) -> set[CMatch]:
		assert len(self.matchFinal.lIdFeeders) == 2
		return self.SetMatchElimFeeding(self.matchFinal.lIdFeeders[1])

	def SetMatchElimFeeding(self, id: int) -> set[CMatch]:
		""" return emlimination matches that feed a particular match id. """

		setIdFeeding: set[int] = set([id])
		setIdVisit: set[int] = copy.copy(setIdFeeding)

		while setIdVisit:
			match = self.mpIdMatch[setIdVisit.pop()]

			# NOTE (bruceo) setIdFeeders will be empty for group and first elimination round matches

			setIdFeeders: set[int] = set(match.lIdFeeders)
			setIdFeeding |= setIdFeeders
			setIdVisit |= setIdFeeders

		return {self.mpIdMatch[id] for id in setIdFeeding}

	def StrTranslation(self, strKey: str, strLocale: str) -> str:
		for strKeyLocPrefix in self.s_lStrKeyLocPrefix:
			if strKey.startswith(strKeyLocPrefix + '.'):
				assert strKey not in g_loc.mpStrKeyStrLocaleStrText
				return super().StrTranslation(strKey, strLocale)

		return g_loc.StrTranslation(strKey, strLocale)
	
	def FLocSectionHasAllKeys(self, strSection: str, setStrKeys: set[str]) -> bool:
		return setStrKeys.issubset(g_loc.mpStrSectionSetStrSubkey[strSection])

	def StrTeam(self, strKey: str, strLocale: str) -> str:
		strKeyResolved = self.strKeyTeamPrefix + strKey
		return self.StrTranslation(strKeyResolved, strLocale)

g_tourn = CTournamentDataBase(g_strNameTourn)
