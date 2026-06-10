#!/usr/bin/env python3

"""
soccer tournament roster page handling
"""

from __future__ import annotations  # Forward refs without quotes

import sys

from typing import TYPE_CHECKING, Type, Callable, Iterable, Generator
from dataclasses import dataclass, replace
from dateutil import parser as dateutil_parser
from dateutil.relativedelta import relativedelta
from bolay import CBlot, SRect, SPoint, SFontKey, JH, JV
from bolay import SColor, ColorFromStr, ColorResaturate, ColorResaturateDarker, FIsSaturated
from bolay import colorWhite, colorBlack, colorLightGrey, colorDarkgrey

from .database import SGroup, SSquad, SPlayer
from .common import mpStrGroupStrColor, mpStrFifaCodeStrSeed, strDateStart

from . import metrics

if TYPE_CHECKING:
	from .doc import CDocument

# starting date

s_tTourney = dateutil_parser.parse(strDateStart)

def StrAge(player: SPlayer) -> str:
	tDob = dateutil_parser.parse(player.strDob)
	return str(abs(relativedelta(tDob, s_tTourney).years))

def StrCaptain(player: SPlayer) -> str:
	# U+F04D2: nerdfont md-star_outline
	return '\U000f04d2' if player.fCaptain else ''

def StrGoals(player: SPlayer) -> str:
	return player.strGoals if int(player.strGoals) > 0 else ''

def StrCaps(player: SPlayer) -> str:
	return player.strCaps if int(player.strCaps) > 0 else ''


@dataclass(frozen=True, slots=True)
class SCellSpec(): # tag = cellsp
	dX: float | None = None
	jh: JH | None = None
	clsCell: Type[CCellBlot] | None = None
	fnField: Callable[[SPlayer], str] | None = None

type TRowSpec = list[SCellSpec | None] # tag = rowsp

def IterCellsp(dXTotal: float, rowsp: TRowSpec, rowspWidths: TRowSpec | None = None) -> Generator[SCellSpec]:
	# collect and distribute widths
	rowspCollect = rowspWidths if rowspWidths else rowsp
	assert rowspCollect
	assert all([cellsp is not None for cellsp in rowspCollect])
	lDX = [cellsp.dX for cellsp in rowspCollect]

	# collect

	dXRemaining = dXTotal
	dXNegativeSum = 0

	for dX in lDX:
		if dX == 0:
			continue

		if dX < 0:
			dXNegativeSum += dX
		else:
			dXRemaining -= dX
			dXRemaining = max(dXRemaining, 0)

	# distribute

	for iDX in range(len(lDX)):
		if lDX[iDX] < 0:
			uRemaining = lDX[iDX] / dXNegativeSum # undoes negativeness
			assert uRemaining >= 0
			lDX[iDX] = dXRemaining * uRemaining

	iDXCur = 0
	for cellsp in rowsp:
		if cellsp is None:
			yield SCellSpec(lDX[iDXCur])
		else:
			yield replace(cellsp, dX = lDX[iDXCur])
		iDXCur += 1

class CCellBlot(CBlot):
	def __init__(self, doc: CDocument, rect: SRect):
		super().__init__(doc.pdf)

		self.doc = doc
		self.rect = rect

class CTextCell(CCellBlot):
	s_uYText = 0.60

	def __init__(self, doc: CDocument, rect: SRect, strText: str, jh: JH):
		super().__init__(doc, rect)

		self.strText = strText
		self.jh = jh

	def Draw(self, colorText: SColor = colorBlack):
		dYText = self.rect.dY * self.s_uYText
		oltbText = self.Oltb(self.rect, SFontKey('NotoSans', ''), dYText, dSMargin=0.0)
		oltbText.DrawText(
					self.strText,
					colorText,
					self.jh,
					JV.Middle,
					fShrinkToFit=(len(self.strText)>=10))

class CImageCell(CCellBlot):
	s_uSRectImage = CTextCell.s_uYText

	def __init__(self, doc: CDocument, rect: SRect, strCountry: str, jh: JH):
		# sad that SRect.Inset() is in absolute units, not relative.
		rectImage = rect.Copy(
							dX = rect.dX * self.s_uSRectImage,
							dY = rect.dY * self.s_uSRectImage)
		rectImage.Shift(
					dX = (rect.dX - rectImage.dX) / 2.0,
					dY = (rect.dY - rectImage.dY) / 2.0)

		super().__init__(doc, rectImage)

		self.jh = jh
		self.img = doc.imgc.ImgFlagFromStrCountry(strCountry, rectImage)

	def Draw(self, colorText: SColor = colorBlack):
		if self.img is None:
			return

		# the image already fits the cell with correct aspect; justify horizontally per jh
		# and center vertically (matching the text cells' JV.Middle)

		if self.jh == JH.Left:
			x = self.rect.xMin
		elif self.jh == JH.Center:
			x = self.rect.xMin + (self.rect.dX - self.img.dXIn) / 2.0
		else:
			assert self.jh == JH.Right
			x = self.rect.xMax - self.img.dXIn

		y = self.rect.yMin + (self.rect.dY - self.img.dYIn) / 2.0

		rectFlag = SRect(x, y, self.img.dXIn, self.img.dYIn)

		self.pdf.image(str(self.img.path), rectFlag.x, rectFlag.y, w=rectFlag.dX, h=rectFlag.dY)

		dSLine = min(self.img.dXIn, self.img.dYIn) / 30.0

		self.DrawBox(rectFlag, dSLine, colorLightGrey)

class CHeaderBlot(CBlot):

	s_rowsp: TRowSpec = [
		None,															# number
		None,															# captain
		None,															# name
		SCellSpec(None,	JH.Center,	CTextCell,	lambda: '\uef0c'),		# pos		(nerdfont nf-fa-person_running)
		SCellSpec(None,	JH.Right,	CTextCell,	lambda: '\uf1fd'),		# age		(nerdfont nf-fa-cake_candles)
		SCellSpec(None,	JH.Right,	CTextCell,	lambda: '\U000f0499'),	# caps		(nerdfont nf-md-shield_outline)
		SCellSpec(None,	JH.Right,	CTextCell,	lambda: '\uf4de'),		# goals		(nerdfont nf-oct-goal)
		None,															# flag
		SCellSpec(None,	JH.Left,	CTextCell,	lambda: '\uf155'),		# club		(nerdfont nf-fa-dollar)
	]

	def __init__(self, doc: CDocument, rect: SRect):
		super().__init__(doc.pdf)

		self.doc = doc
		self.rect = rect
		self.lCellb: list[CCellBlot] = []

		xCur = rect.x
		for cellp in IterCellsp(rect.dX, self.s_rowsp, CPlayerBlot.s_rowsp):
			rectCell = self.rect.Copy(x=xCur, dX=cellp.dX)
			xCur += rectCell.dX

			if cellp.clsCell is None:
				continue

			self.lCellb.append(cellp.clsCell(doc, rectCell, cellp.fnField(), cellp.jh))

	def Draw(self):
		for cellb in self.lCellb:
			cellb.Draw()

class CPlayerBlot(CBlot):

	s_rowsp: TRowSpec = [
		SCellSpec(0.15,	JH.Right,	CTextCell,	lambda player: player.strNumber),		# number
		SCellSpec(0.1,	JH.Right,	CTextCell,	lambda player: StrCaptain(player)),		# captain
		SCellSpec(1.4,	JH.Left,	CTextCell,	lambda player: player.strName),			# name
		SCellSpec(0.12,	JH.Center,	CTextCell,	lambda player: player.strPos[0]),		# pos
		SCellSpec(0.16,	JH.Right,	CTextCell,	lambda player: StrAge(player)),			# age
		SCellSpec(0.21,	JH.Right,	CTextCell,	lambda player: StrCaps(player)),		# caps
		SCellSpec(0.21,	JH.Right,	CTextCell,	lambda player: StrGoals(player)),		# goals
		SCellSpec(0.3,	JH.Right,	CImageCell,	lambda player: player.strClubCountry),	# club flag
		SCellSpec(-1,	JH.Left,	CTextCell,	lambda player: player.strClub),			# club
	]

	def __init__(self, doc: CDocument, rect: SRect, player: SPlayer):
		super().__init__(doc.pdf)

		self.doc = doc
		self.rect = rect
		self.player = player
		self.dSLine = (1.0 - CTextCell.s_uYText) * rect.dY * 0.0625
		self.lCellb: list[CCellBlot] = []

		xCur = rect.x
		for cellp in IterCellsp(rect.dX, self.s_rowsp):
			rectCell = self.rect.Copy(x=xCur, dX=cellp.dX)
			xCur += rectCell.dX

			if cellp.clsCell is None:
				continue

			self.lCellb.append(cellp.clsCell(doc, rectCell, cellp.fnField(self.player), cellp.jh))

	def Draw(self):
		self.pdf.set_line_width(self.dSLine)
		self.pdf.SetDrawColor(colorLightGrey)
		self.pdf.line(
					self.rect.xMin,
					self.rect.yMin,
					self.rect.xMax,
					self.rect.yMin)
		
		for cellb in self.lCellb:
			cellb.Draw()

class CSquadBlot(CBlot): # tag = squadb
	s_rSCountry = 15.0

	def __init__(self, group: CGroupBlot, squad: SSquad):
		super().__init__(group.doc.pdf)

		self.group = group
		self.squad = squad
		country = group.doc.db.countries[self.squad.strCountry]
		self.strSeed = mpStrFifaCodeStrSeed[country.strFifaCode]

		self.rowspCountry: TRowSpec = [
			SCellSpec(0.37,	JH.Center,	CImageCell,		lambda: country.strName),
			SCellSpec(-1,	JH.Left,	CTextCell,		lambda: f"{country.strName} #{country.strFifaRank}"),
			SCellSpec(-1,	JH.Right,	CTextCell,		lambda: country.strFifaCode),
#			SCellSpec(0.6,	JH.Right,	CQRCodeCell,	lambda: country.strName),	# club flag
		]

		coach = group.doc.db.coaches[self.squad.strCoach]
		lStrJobPrevious = [strJob for strJob in coach.lStrJobPrevious if strJob]
		strJobs = f"[{','.join(lStrJobPrevious)}]" if lStrJobPrevious else ""

		self.rowspCoach: TRowSpec = [
			SCellSpec(0.10),
			SCellSpec(1.1,	JH.Left,	CTextCell,		lambda: self.squad.strCoach),
			SCellSpec(1.15,	JH.Right,	CTextCell,		lambda: strJobs),
			SCellSpec(0.3,	JH.Right,	CImageCell,		lambda: coach.strCountry),
			SCellSpec(-1,	JH.Left,	CTextCell,		lambda: coach.strCountry),
		]


	def Draw(self, pos: SPoint):
		rectSquad = SRect(pos.x, pos.y, self.group.dXSquad, self.group.dYSquad)
		dYCountry = rectSquad.dX / self.s_rSCountry
		rectCountry = rectSquad.Copy(dY=dYCountry)

		self.FillBox(rectCountry, colorLightGrey)

		xCur = rectCountry.x
		for cellp in IterCellsp(rectCountry.dX, self.rowspCountry):
			rectCell = rectCountry.Copy(x=xCur, dX=cellp.dX)
			xCur += rectCell.dX

			if cellp.clsCell is None:
				continue

			cellp.clsCell(self.group.doc, rectCell, cellp.fnField(), cellp.jh).Draw(colorDarkgrey)

		rectPeople = rectSquad.Copy().Stretch(dYTop = dYCountry)
		dYPerson = rectPeople.dY / (self.group.doc.cPersonMax + 1)
		yCur = rectPeople.y

		if self.squad.strCoach:
			rectCoach = SRect(rectPeople.x, yCur, rectPeople.dY, dYPerson)
			yCur += dYPerson

			xCur = rectCoach.x
			for cellp in IterCellsp(rectCoach.dX, self.rowspCoach):
				rectCell = rectCoach.Copy(x=xCur, dX=cellp.dX)
				xCur += rectCell.dX

				if cellp.clsCell is None:
					continue

				cellp.clsCell(self.group.doc, rectCell, cellp.fnField(), cellp.jh).Draw(colorDarkgrey)


		rectPlayer = SRect(rectPeople.x, yCur, rectPeople.dY, dYPerson)
		yCur += dYPerson

		CHeaderBlot(self.group.doc, rectPlayer).Draw()

		for player in self.squad.players.values():
			rectPlayer = SRect(rectPeople.x, yCur, rectPeople.dX, dYPerson)
			yCur += dYPerson

			CPlayerBlot(self.group.doc, rectPlayer, player).Draw()

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

		self.dXSquad = dXSquads / 2
		self.dYSquad = dYSquads / 2

		self.lSquadb: list[CSquadBlot] = [CSquadBlot(self, squad) for squad in self.group.values()]
		self.lSquadb.sort(key=lambda squadb: squadb.strSeed)

	def Draw(self, pos: SPoint) -> None:

		rectBorder = SRect(pos.x, pos.y, self.s_dX, self.s_dY)
		rectInside = rectBorder.Copy().Inset(self.s_dSLineOuter / 2.0)

		# title

		#dYTitle = dY * self.s_uYTitle
		dYTitle = rectInside.dX / self.s_rSGroup
		rectTitle = rectInside.Copy(dY=dYTitle)

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

		# squads

		posSquads = SPoint(rectInside.x, rectInside.y + dYTitle)

		for iSquadb, squadb in enumerate(self.lSquadb):
			row, col = divmod(iSquadb, 2)
			squadb.Draw(SPoint(posSquads.x + col * self.dXSquad, posSquads.y + row * self.dYSquad))

		# borders

		self.pdf.set_line_width(.25 / 72.0)
		self.pdf.SetDrawColor(colorBlack)
		xLine = rectInside.x + self.dXSquad
		self.pdf.line(
					xLine,
					rectGroupLabel.yMax,
					xLine,
					rectInside.yMax)
		
		self.DrawBox(rectBorder, self.s_dSLineOuter, colorBlack)
		self.DrawBox(rectBorder, self.s_dSLineInner, self.colors.color)
