# 'annotations' allow typing hints to forward reference.
#	e.g. Fn(fwd: CFwd) instead of Fn(fwd: 'CFwd')
#	when CFwd is later in file.
from __future__ import annotations

import arrow
import copy
import datetime
import openpyxl
import re

from babel import Locale
from enum import IntEnum, auto
from pathlib import Path
from typing import Optional

from pdf import SColor, ColorFromStr, ColorResaturate

TExcelRow = dict[str, str]				# tag = xlrow
TExcelSheet = list[TExcelRow]			# tag = xls
TExcelBook = dict[str, TExcelSheet]		# tag = xlb

class CDataBase: # tag = db

	def __init__(self, pathFile: Path) -> None:

		self.pathFile = pathFile
		self.mpStrKeyStrLocaleStrText: dict[str, dict[str, str]] = {}

	def XlbLoad(self) -> TExcelBook:
		wb = openpyxl.load_workbook(filename = str(self.pathFile))
		
		xlb: TExcelBook = {}
		
		for ws in wb.worksheets:
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

	def __init__(self, pathFile: Path) -> None:

		super().__init__(pathFile)

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

class STAGE(IntEnum):
	# BB (bruceo) rename Round1 etc to Round64 Round32 etc
	Group = auto()
	Round1 = auto()
	Round2 = auto()	# may not be used, depending on tourney size
	Round3 = auto() # ditto
	Quarters = auto()
	Semis = auto()
	Third = auto()
	Final = auto()

class SColors: # tag = colors
	s_dSDarker = 0.5

	s_rVLighter = 1.5
	s_rSLighter = 0.5

	def __init__(self, strColor: str) -> None:
		self.color: SColor = ColorFromStr(strColor)
		self.colorDarker: SColor = ColorResaturate(self.color, dS=self.s_dSDarker)
		self.colorLighter: SColor = ColorResaturate(self.color, rV=self.s_rVLighter, rS=self.s_rSLighter)

class CGroup:
	def __init__(self, tourn: CTournamentDataBase, strGroup: str, mpStrSeedStrTeam: dict[str, str]) -> None:
		self.strName: str = strGroup
		self.colors: SColors = SColors(tourn.StrTranslation('colors.' + strGroup, 'en')) # BB (bruceo) delay this until necessary?
		self.mpStrSeedStrTeam: dict[str, str] = {strSeed:strTeam for strSeed, strTeam in mpStrSeedStrTeam.items() if strSeed[0] == strGroup}

class CMatch:
	s_patAlphaNum = re.compile('([a-zA-Z]+)([0-9]+)')
	s_patNumAlpha = re.compile('([0-9]+)([a-zA-Z]+)')

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

		if matHome := self.s_patNumAlpha.match(self.strSeedHome):
			matAway = self.s_patNumAlpha.match(self.strSeedAway)
			assert matAway
			self.stage = STAGE.Round1
			self.lStrGroup = [matHome[2], matAway[2]]
		elif matHome := self.s_patAlphaNum.match(self.strSeedHome):
			matAway = self.s_patAlphaNum.match(self.strSeedAway)
			assert matAway
			assert matHome[1] == matAway[1]
			
			if matHome[1] in tourn.setStrGroup:
				self.stage = STAGE.Group
				self.lStrGroup = [matHome[1]]
			elif matHome[1] == 'RU' or matHome[1] == 'L':
				self.stage = STAGE.Third
				self.lIdFeeders = [int(matHome[2]), int(matAway[2])]
			else:
				# leaving self.stage as None, but setting ids so
				# we can set it based on feeders' stages
				assert matHome[1] == 'W'
				self.lIdFeeders = [int(matHome[2]), int(matAway[2])]
		else:
			assert False

	def FTrySetStage(self, mpIdMatch: dict[int, 'CMatch'], stagePrev: STAGE, stage: STAGE):
		assert self.stage is None
		assert self.lIdFeeders

		# no ordered sets in python, and we want to preserve order in this case

		setStrGroup: set[str] = set()
		lStrGroup: list[str] = []

		for id in self.lIdFeeders:
			match = mpIdMatch[id]

			if match.stage != stagePrev:
				return False

			for strGroup in match.lStrGroup:
				if strGroup not in setStrGroup:
					setStrGroup.add(strGroup)
					lStrGroup += strGroup

		if stagePrev == STAGE.Round1:
			assert not self.lStrGroup
			assert len(lStrGroup) == 4
			self.lStrGroup = lStrGroup
		elif stagePrev > STAGE.Round1:
			assert not self.lStrGroup
			# revert sorting if we have everything
			self.lStrGroup = lStrGroup if len(lStrGroup) < len(self.tourn.lStrGroup) else self.tourn.lStrGroup

		self.stage = stage

		return True

class CTournamentDataBase(CDataBase): # tag = tourn

	s_lStrKeyLocPrefix = ('tournament', 'colors')

	def __init__(self, pathFile: Path, loc: CLocalizationDataBase) -> None:

		super().__init__(pathFile)

		self.loc = loc

		xlb: TExcelBook = self.XlbLoad()
		
		# translations come from both the tranlsations table (mostly unchanging) and the tournament table (new per contest)

		for strKeyLocPrefix in self.s_lStrKeyLocPrefix:
			assert strKeyLocPrefix not in loc.mpStrSectionSetStrSubkey
			for xlrow in xlb[strKeyLocPrefix]:
				self.mpStrKeyStrLocaleStrText[(strKeyLocPrefix + '.' + xlrow['key']).lower()] = xlrow

		# both MpStrGroupGroup() and CMatch.__init__() depend on self.mpStrSeedTeam existing

		self.mpStrSeedStrTeam: dict[str, str] = {xlrow['seed']:xlrow['team'] for xlrow in xlb['seeds']}

		self.mpStrGroupGroup: dict[str, CGroup] = self.MpStrGroupGroup()
		self.lStrGroup: list[str] = sorted(self.mpStrGroupGroup.keys())
		self.setStrGroup: set[str] = set(self.lStrGroup)
		self.mpStrTeamGroup: dict[str, CGroup] = {strTeam:group for group in self.mpStrGroupGroup.values() for strTeam in group.mpStrSeedStrTeam.values()}

		self.mpIdMatch: dict[int, CMatch] = {int(xlrow['match']):CMatch(self, xlrow) for xlrow in xlb['matches']}

		self.mpStageSetMatch: dict[STAGE, set[CMatch]] = self.MpStageSetMatch()

		setMatchFinal = self.mpStageSetMatch[STAGE.Final]
		assert len(setMatchFinal) == 1
		self.matchFinal = next(iter(setMatchFinal))
		del self.mpStageSetMatch[STAGE.Final]
		
		setMatchThird = self.mpStageSetMatch[STAGE.Third]
		assert len(setMatchThird) == 1
		self.matchThird = next(iter(setMatchThird))
		del self.mpStageSetMatch[STAGE.Third]
		
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

		stagePrev: STAGE = STAGE.Round1

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
				stageNext = stagePrev + 1

			setMatchNext: set[CMatch] = set()

			for match in setMatchNoStage:
				if match.FTrySetStage(self.mpIdMatch, stagePrev, stageNext):
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

			# NOTE (bruceo) setIdFeeders will be empty for group and round1 matches

			setIdFeeders: set[int] = set(match.lIdFeeders)
			setIdFeeding |= setIdFeeders
			setIdVisit |= setIdFeeders

		return {self.mpIdMatch[id] for id in setIdFeeding}

	def StrTranslation(self, strKey: str, strLocale: str) -> str:
		for strKeyLocPrefix in self.s_lStrKeyLocPrefix:
			if strKey.startswith(strKeyLocPrefix + '.'):
				assert strKey not in self.loc.mpStrKeyStrLocaleStrText
				return super().StrTranslation(strKey, strLocale)

		return self.loc.StrTranslation(strKey, strLocale)

