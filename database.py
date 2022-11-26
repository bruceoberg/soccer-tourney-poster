import arrow
import copy
import datetime
import openpyxl
import re

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
			lStrKey: Optional[list[str]] = None
			xls: TExcelSheet = []
			for row in ws.rows:
				if not lStrKey:
					lStrKey = [cell.value.lower() for cell in row]
				else:
					lStrValue: list[str] = [cell.value for cell in row]
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

class CTeam:
	def __init__(self, xlrow: TExcelRow) -> None:
		self.strSeed: str = xlrow['seed']
		self.strTeam: str = xlrow['team']

class SColors: # tag = colors
	s_dSDarker = 0.5

	s_rVLighter = 1.5
	s_rSLighter = 0.5

	def __init__(self, strColor: str) -> None:
		self.color: SColor = ColorFromStr(strColor)
		self.colorDarker: SColor = ColorResaturate(self.color, dS=self.s_dSDarker)
		self.colorLighter: SColor = ColorResaturate(self.color, rV=self.s_rVLighter, rS=self.s_rSLighter)

class CGroup:
	def __init__(self, loc: CLocalizationDataBase, strGroup: str, lTeam: list[CTeam]) -> None:
		self.strName: str = strGroup
		self.colors: SColors = SColors(loc.StrTranslation('colors.' + strGroup, 'en')) # BB (bruceo) delay this until necessary?
		self.mpStrSeedTeam: dict[str, CTeam] = {team.strSeed:team for team in lTeam}

class CMatch:
	s_patAlphaNum = re.compile('([a-zA-Z]+)([0-9]+)')
	s_patNumAlpha = re.compile('([0-9]+)([a-zA-Z]+)')

	def __init__(self, tourn: 'CTournamentDataBase', xlrow: TExcelRow) -> None:
		self.tourn = tourn
		self.id = int(xlrow['match'])
		self.venue: int = int(xlrow['venue'])
		self.strHome: str = xlrow['home']
		self.strAway: str = xlrow['away']
		self.tStart: arrow.Arrow = arrow.get(xlrow['time'])

		self.scoreHome: int = int(xlrow['home']) if xlrow['home-score'] else -1
		self.scoreAway: int = int(xlrow['away']) if xlrow['away-score'] else -1

		self.scoreHomeTiebreaker: int = int(xlrow['home-tiebreaker']) if xlrow['home-tiebreaker'] else -1
		self.scoreAwayTiebreaker: int = int(xlrow['away-tiebreaker']) if xlrow['away-tiebreaker'] else -1

		self.stage: Optional[STAGE] = None
		self.lStrGroup: list[str] = []
		self.lIdFeeders: list[int] = []

		if matHome := self.s_patNumAlpha.match(self.strHome):
			matAway = self.s_patNumAlpha.match(self.strAway)
			assert matAway
			self.stage = STAGE.Round1
			self.lStrGroup = [matHome[2], matAway[2]]
		elif matHome := self.s_patAlphaNum.match(self.strHome):
			matAway = self.s_patAlphaNum.match(self.strAway)
			assert matAway
			assert matHome[1] == matAway[1]
			
			if matHome[1] in tourn.setStrGroup:
				self.stage = STAGE.Group
				self.lStrGroup = [matHome[1]]
				self.strHome = tourn.mpStrSeedTeam[self.strHome].strTeam
				self.strAway = tourn.mpStrSeedTeam[self.strAway].strTeam
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

	s_strKeyTournPrefix = 'tournament'

	def __init__(self, pathFile: Path, loc: CLocalizationDataBase) -> None:

		super().__init__(pathFile)

		self.loc = loc
		assert self.s_strKeyTournPrefix not in loc.mpStrSectionSetStrSubkey

		xlb: TExcelBook = self.XlbLoad()
		
		# both MpStrGroupGroup() and CMatch.__init__() depend on self.mpStrSeedTeam existing

		self.mpStrSeedTeam: dict[str, CTeam] = {xlrow['seed']:CTeam(xlrow) for xlrow in xlb['seeds']}

		self.mpStrGroupGroup: dict[str, CGroup] = self.MpStrGroupGroup()
		self.lStrGroup: list[str] = sorted(self.mpStrGroupGroup.keys())
		self.setStrGroup: set[str] = set(self.lStrGroup)

		self.mpIdMatch: dict[int, CMatch] = {int(xlrow['match']):CMatch(self, xlrow) for xlrow in xlb['matches']}

		# translations come from both the tranlsations table (mostly unchanging) and the tournament table (new per contest)

		self.mpStrKeyStrLocaleStrText: dict[str, dict[str, str]] = {(self.s_strKeyTournPrefix + '.' + xlrow['key']).lower():xlrow for xlrow in xlb['tournament']}

		self.mpDateSetMatch: dict[datetime.date, set[CMatch]] = self.MpDateSetMatch()
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
		
		self.setMatchLeft: set[CMatch] = self.SetMatchLeft()

	def MpStrGroupGroup(self) -> dict[str, CGroup]:
		""" build list of groups from team seedings. """
		mpStrGroupGroup: dict[str, CGroup] = {}

		setStrGroup: set[str] = {strSeed[:1] for strSeed in self.mpStrSeedTeam}
		assert len(setStrGroup) <= 16
		assert 'ABCDEFGHIJKLMNOP'[:len(setStrGroup)] == ''.join(sorted(setStrGroup))

		for strGroup in setStrGroup:
			lTeam: list[CTeam] = [team for strSeed, team in self.mpStrSeedTeam.items() if strSeed[0] == strGroup]
			mpStrGroupGroup[strGroup] = CGroup(self, strGroup, lTeam)

		return mpStrGroupGroup

	def MpDateSetMatch(self) -> dict[datetime.date, set[CMatch]]:
		""" map dates to matches. """

		mpDateSetMatch: dict[datetime.date, set[CMatch]] = {}

		for match in self.mpIdMatch.values():
			mpDateSetMatch.setdefault(match.tStart.date(), set()).add(match)

		return mpDateSetMatch

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

	def SetMatchLeft(self) -> set[CMatch]:
		""" return matches that are on the left side of the elimination bracket. """

		setIdLeft: set[int] = set(self.matchFinal.lIdFeeders[:1])
		setIdVisit: set[int] = copy.copy(setIdLeft)

		while setIdVisit:
			match = self.mpIdMatch[setIdVisit.pop()]

			# NOTE (bruceo) setIdFeeders will be empty for group and round1 matches

			setIdFeeders: set[int] = set(match.lIdFeeders)
			setIdLeft |= setIdFeeders
			setIdVisit |= setIdFeeders

		return {self.mpIdMatch[id] for id in setIdLeft}

	def StrTranslation(self, strKey: str, strLocale: str) -> str:
		if strKey.startswith(self.s_strKeyTournPrefix + '.'):
			assert strKey not in self.loc.mpStrKeyStrLocaleStrText
			return super().StrTranslation(strKey, strLocale)

		return self.loc.StrTranslation(strKey, strLocale)

