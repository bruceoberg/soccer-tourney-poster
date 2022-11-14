import arrow
import datetime
import openpyxl
import re

from enum import IntEnum, auto
from pathlib import Path
from typing import Optional

from pdf import SColor, ColorFromStr, ColorResaturate

TExcelRow = dict[str, str]				# tag = xlrow
TExcelTable = list[TExcelRow]			# tag = xltable
TExcelSheet = dict[str, TExcelTable]	# tag = xls

class STAGE(IntEnum):
	Group = auto()
	Round1 = auto()
	Round2 = auto()	# may not be used, depending on tourney size
	Round3 = auto() # ditto
	Quarters = auto()
	Semis = auto()
	Third = auto()
	Final = auto()

class CVenue:
	def __init__(self, xlrow: TExcelRow) -> None:
		self.strName: str = xlrow['location']

class CTeam:
	def __init__(self, xlrow: TExcelRow) -> None:
		self.strName: str = xlrow['team']
		self.strAbbrev: str = xlrow['abbrev']
		self.strSeed: Optional[str] = None
	def SetSeed(self, strSeed: str) -> None:
		self.strSeed = strSeed

class SColors: # tag = colors
	s_dSDarker = 0.5

	s_rVLighter = 1.5
	s_rSLighter = 0.5

	def __init__(self, strColor: str) -> None:
		self.color: SColor = ColorFromStr(strColor)
		self.colorDarker: SColor = ColorResaturate(self.color, dS=self.s_dSDarker)
		self.colorLighter: SColor = ColorResaturate(self.color, rV=self.s_rVLighter, rS=self.s_rSLighter)

class CGroup:
	def __init__(self, xlrow: TExcelRow) -> None:
		self.strName: str = xlrow['group']
		self.colors: SColors = SColors(xlrow['color'])
		self.mpStrSeedTeam: dict[str, CTeam] = {}
	def AddTeam(self, team: CTeam):
		self.mpStrSeedTeam[team.strSeed] = team

class CMatch:
	s_patAlphaNum = re.compile('([a-zA-Z]+)([0-9]+)')
	s_patNumAlpha = re.compile('([0-9]+)([a-zA-Z]+)')

	def __init__(self, db: 'CDataBase', xlrow: TExcelRow) -> None:
		self.strName: str = '#' + str(xlrow['match'])
		self.venue: CVenue = db.mpIdVenue[int(xlrow['venue'])]
		self.strHome: str = xlrow['home']
		self.strAway: str = xlrow['away']
		self.tStart: arrow.Arrow = arrow.get(xlrow['time'])

		self.stage: Optional[STAGE] = None
		self.lStrGroup: list[str] = []
		self.lIdFeeders = []

		if matHome := self.s_patNumAlpha.match(self.strHome):
			matAway = self.s_patNumAlpha.match(self.strAway)
			assert matAway
			self.stage = STAGE.Round1
			self.lStrGroup = [matHome[2], matAway[2]]
		elif matHome := self.s_patAlphaNum.match(self.strHome):
			matAway = self.s_patAlphaNum.match(self.strAway)
			assert matAway
			assert matHome[1] == matAway[1]
			
			if matHome[1] in db.setStrGroup:
				self.stage = STAGE.Group
				self.lStrGroup = [matHome[1]]
				self.strHome = db.mpStrSeedTeam[self.strHome].strAbbrev
				self.strAway = db.mpStrSeedTeam[self.strAway].strAbbrev
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

		lStrGroup: list[str] = []

		for id in self.lIdFeeders:
			match = mpIdMatch[id]

			if match.stage != stagePrev:
				return False

			lStrGroup += match.lStrGroup

		if stagePrev == STAGE.Round1:
			assert not self.lStrGroup
			assert len(lStrGroup) == 4
			self.lStrGroup = lStrGroup

		self.stage = stage

		return True

class CDataBase:

	def __init__(self, pathFile: Path) -> None:

		self.pathFile = pathFile

		xls: TExcelSheet = self.XlsLoad()
		
		self.mpStrGroupGroup: dict[str, CGroup] = {xlrow['group']:CGroup(xlrow) for xlrow in xls['groups']}
		self.lStrGroup: list[str] = list(self.mpStrGroupGroup.keys())
		self.setStrGroup: set[str] = set(self.lStrGroup)

		self.mpIdVenue: dict[int, CVenue] = {int(xlrow['venue']):CVenue(xlrow) for xlrow in xls['venues']}
		self.mpRankTeam: dict[int, CTeam] = {int(xlrow['rank']):CTeam(xlrow) for xlrow in xls['teams']}

		self.mpStrSeedTeam: dict[str, CTeam] = self.MpStrSeedTeam(xls)

		# CMatch.__init__ depends on self.mpStrSeedTeam existing

		self.mpIdMatch: dict[int, CMatch] = {int(xlrow['match']):CMatch(self, xlrow) for xlrow in xls['matches']}

		self.mpDateSetMatch: dict[datetime.date, set[CMatch]] = self.MpDateSetMatch()
		self.mpStageSetMatch: dict[STAGE, set[CMatch]] = self.MpStageSetMatch()

	def MpStrSeedTeam(self, xls: TExcelSheet) -> dict[str, CTeam]:
		""" load seeds and hook them up to groups. """
		mpStrSeedTeam: dict[str, CTeam] = {}

		for xlrow in xls['seeds']:
			strSeed = xlrow['seed']
			rank = int(xlrow['rank'])

			team = self.mpRankTeam[rank]
			team.SetSeed(strSeed)

			mpStrSeedTeam[strSeed] = team

			strGroup = strSeed[:1]
			group = self.mpStrGroupGroup[strGroup]
			group.AddTeam(team)

		return mpStrSeedTeam

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

	def XlsLoad(self) -> TExcelSheet:
		wb = openpyxl.load_workbook(filename = str(self.pathFile))
		
		xls: TExcelSheet = {}
		
		for ws in wb.worksheets:
			for strTable, strRange in ws.tables.items():
				lStrKey: Optional[list[str]] = None
				xltable: TExcelTable = []
				for row in ws[strRange]:
					if not lStrKey:
						lStrKey = [cell.value.lower() for cell in row]
					else:
						lStrValue: list[str] = [cell.value for cell in row]
						xlrow: TExcelRow = dict(zip(lStrKey, lStrValue))
						xltable.append(xlrow)
				xls[strTable] = xltable

		return xls
