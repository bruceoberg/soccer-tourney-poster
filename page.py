#!/usr/bin/env python3

"""
soccer tournament roster page handling
"""

from __future__ import annotations  # Forward refs without quotes

from typing import TYPE_CHECKING, Type, Callable, Iterable, Generator
from dataclasses import dataclass
from dateutil import parser as dateutil_parser
from dateutil.relativedelta import relativedelta
from bolay import CBlot, SRect, SPoint, SFontKey, JH, JV
from bolay import SColor, ColorFromStr, ColorResaturate, ColorResaturateDarker, FIsSaturated
from bolay import colorWhite, colorBlack, colorLightGrey, colorDarkgrey

from .database import SGroup, SSquad, SPlayer
from .common import mpStrGroupStrColor, strDateStart

from . import metrics

if TYPE_CHECKING:
	from .doc import CDocument

# cell widths

s_tuDXCells: tuple[float] = (
	0.1,	# captain
	0.2,	# number
	0.2,	# pos
	1.5,	# name
	0.2,	# age
	0.2,	# caps
)

# starting date

s_tTourney = dateutil_parser.parse(strDateStart)

def StrAge(player: SPlayer) -> str:
	tDob = dateutil_parser.parse(player.strDob)
	return str(abs(relativedelta(tDob, s_tTourney).years))

def StrCaptain(player: SPlayer) -> str:
	return 'C' if player.fCaptain else ''

@dataclass(frozen=True, slots=True)
class SCellSpec():
	clsCell: Type[CCellBlot] | None
	fnField: Callable[[SPlayer], str] | None

@dataclass(frozen=True, slots=True)
class SCellParam(SCellSpec):
	dX: float

def IterCellp(dXTotal: float, iterCellsp: Iterable[SCellSpec | None]) -> Generator[SCellParam]:
	dXRemaining = dXTotal
	itor = iter(iterCellsp)
	for dX in s_tuDXCells:
		try:
			cellsp = next(itor)
		except StopIteration:
			break
		dXRemaining -= dX

		if cellsp is None:
			yield SCellParam(None, None, dX)
		else:
			yield SCellParam(cellsp.clsCell, cellsp.fnField, dX)

	if lCellsp := list(itor):
		dX = dXRemaining / len(lCellsp)
		for cellsp in lCellsp:

			if cellsp is None:
				yield SCellParam(None, None, dX)
			else:
				yield SCellParam(cellsp.clsCell, cellsp.fnField, dX)


class CCellBlot(CBlot):
	def __init__(self, doc: CDocument, rect: SRect):
		super().__init__(doc.pdf)

		self.doc = doc
		self.rect = rect

class CTextCell(CCellBlot):
	def __init__(self, doc: CDocument, rect: SRect, strText: str):
		super().__init__(doc, rect)

		self.strText = strText

	def Draw(self):
		dYText = self.rect.dY * 0.60
		oltbPlayer = self.Oltb(self.rect, SFontKey('NotoSans', ''), dYText)
		oltbPlayer.DrawText(
						self.strText,
						colorBlack,
						JH.Left,
						JV.Middle)

class CPlayerBlot(CBlot):

	s_tuCellsp: tuple[SCellParam | None] = (
		SCellSpec(CTextCell, lambda player: StrCaptain(player)),
		SCellSpec(CTextCell, lambda player: player.strNumber),
		SCellSpec(CTextCell, lambda player: player.strPos),
		SCellSpec(CTextCell, lambda player: player.strName),
		SCellSpec(CTextCell, lambda player: StrAge(player)),
		SCellSpec(CTextCell, lambda player: player.strCaps),
		SCellSpec(CTextCell, lambda player: player.strClub),
	)

	def __init__(self, doc: CDocument, rect: SRect, player: SPlayer):
		super().__init__(doc.pdf)

		self.doc = doc
		self.rect = rect
		self.player = player
		self.lCellb: list[CCellBlot] = []

		xCur = rect.x
		for cellp in IterCellp(rect.dX, self.s_tuCellsp):
			rectCell = self.rect.Copy(x=xCur, dX=cellp.dX)
			xCur += rectCell.dX

			if cellp.clsCell is None:
				continue

			self.lCellb.append(cellp.clsCell(doc, rectCell, cellp.fnField(self.player)))

	def Draw(self):
		for cellb in self.lCellb:
			cellb.Draw()

class CSquadBlot(CBlot): # tag = squadb
	s_rSName = 15.0

	def __init__(self, doc: CDocument, squad: SSquad, rectLocal: SRect):
		super().__init__(doc.pdf)

		self.doc = doc
		self.squad = squad
		self.rectLocal = rectLocal

	def Draw(self, pos: SPoint):
		rectSquad = self.rectLocal.Copy().Shift(dX=pos.x, dY=pos.y)
		dYName = rectSquad.dX / self.s_rSName
		rectName = rectSquad.Copy(dY=dYName)

		self.FillBox(rectName, colorLightGrey)

		oltbSquadName = self.Oltb(rectName, SFontKey('NotoSans', ''), dYName)
		oltbSquadName.DrawText(
						self.squad.strTeam,
						colorDarkgrey,
						JH.Left,
						JV.Middle)
		
		rectPeople = rectSquad.Copy().Stretch(dYTop = dYName)
		dYPerson = rectPeople.dY / self.doc.cPersonMax
		yCur = rectPeople.y

		if self.squad.strCoach:
			rectCoach = SRect(rectPeople.x, yCur, rectPeople.dY, dYPerson)
			yCur += dYPerson
			oltbPerson = self.Oltb(rectCoach, SFontKey('NotoSans', 'B'), dYPerson)
			oltbPerson.DrawText(
							self.squad.strCoach,
							colorBlack,
							JH.Left,
							JV.Middle)
			
		for player in self.squad.players.values():
			rectPlayer = SRect(rectPeople.x, yCur, rectPeople.dY, dYPerson)
			yCur += dYPerson

			CPlayerBlot(self.doc, rectPlayer, player).Draw()

class SColors: # tag = colors
	s_dSDarker = 0.5

	s_rVLighter = 1.5
	s_rSLighter = 0.5

	s_rVDarker = 0.75	# for unsaturated colors
	s_dVLighter = 0.2

	def __init__(self, strColor: str) -> None:
		self.color: SColor = ColorFromStr(strColor)
		if FIsSaturated(self.color):
			self.colorDarker: SColor = ColorResaturateDarker(self.color, dS=self.s_dSDarker)
			self.colorLighter: SColor = ColorResaturate(self.color, rV=self.s_rVLighter, rS=self.s_rSLighter)
		else:
			self.colorDarker: SColor = ColorResaturateDarker(self.color, rV=self.s_rVDarker)
			self.colorLighter: SColor = ColorResaturate(self.color, dV=self.s_dVLighter)

class CGroupBlot(CBlot): # tag = groupb

	s_dX = metrics.page.dXLive
	s_dY = metrics.page.dYLive

	s_rSLineOuter = 0.001
	s_rSLineInner = 0.0002
	s_dSLineOuter = s_dX * s_rSLineOuter
	s_dSLineInner = s_dX * s_rSLineInner

	s_rSGroup = 15.0

	def __init__(self, doc: CDocument, strGroup: str, group: SGroup) -> None:
		super().__init__(doc.pdf)

		self.doc = doc

		assert strGroup.startswith("Group ")
		assert len(strGroup) == len("Group ") + 1
		self.strGroup = strGroup[-1]
		self.group = group
		self.colors = SColors(mpStrGroupStrColor[self.strGroup])

		# repeating some of the layout in Draw() here

		rectBorder = SRect(0, 0, self.s_dX, self.s_dY)
		rectInside = rectBorder.Copy().Inset(self.s_dSLineOuter / 2.0)

		dYTitle = rectInside.dX / self.s_rSGroup

		dXSquads = rectInside.dX
		dYSquads = rectInside.dY - dYTitle

		assert len(group) == 4

		dXSquad = dXSquads / 2
		dYSquad = dYSquads / 2

		self.lSquadb: list[CSquadBlot] = []

		for iSquad, squad in enumerate(self.group.values()):
			row, col = divmod(iSquad, 2)
			rectLocal = SRect(row * dXSquad, col * dYSquad, dXSquad, dYSquad)

			self.lSquadb.append(CSquadBlot(self.doc, squad, rectLocal))

	def Draw(self, pos: SPoint) -> None:

		rectBorder = SRect(pos.x, pos.y, self.s_dX, self.s_dY)
		rectInside = rectBorder.Copy().Inset(self.s_dSLineOuter / 2.0)

		# title

		#dYTitle = dY * self.s_uYTitle
		dYTitle = rectInside.dX / self.s_rSGroup
		rectTitle = rectInside.Copy(dY=dYTitle)

		posSquads = SPoint(rectInside.x, rectInside.y + dYTitle)

		for squadb in self.lSquadb:
			squadb.Draw(posSquads)

		self.FillBox(rectTitle, self.colors.color)

		dYGroupName = dYTitle * 1.3
		oltbGroupName = self.Oltb(rectTitle, SFontKey('NotoSansMono', ''), dYGroupName)
		rectGroupName = oltbGroupName.RectDrawText(
										self.strGroup,
										self.colors.colorDarker,
										JH.Right,
										JV.Middle)

		rectGroupLabel = rectTitle.Copy(dX=rectGroupName.x - rectTitle.x)

		uGroupLabel = 0.65
		strGroupTitle = "Group"
		oltbGroupLabel = self.Oltb(rectGroupLabel, SFontKey('NotoSans', ''), dYTitle * uGroupLabel, dSMargin = oltbGroupName.dSMargin)
		oltbGroupLabel.DrawText(strGroupTitle, colorWhite, JH.Right) #, JV.Top)

		self.DrawBox(rectBorder, self.s_dSLineOuter, colorBlack)
		self.DrawBox(rectBorder, self.s_dSLineInner, self.colors.color)
