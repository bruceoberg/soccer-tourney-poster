from __future__ import annotations  # Forward refs without quotes (eg foo: CFoo, not foo: 'CFoo')

import math

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bolay import VEK, UVekLm, CBlot
from bolay import JH, JV, SPoint, SRect
from bolay import colorBlack, colorWhite, colorDarkSlateGrey, colorLightGrey
from bolay import EnumTuple

from .database import CGroup, MATCHSTAT

if TYPE_CHECKING:
	from .page import CPage
	from .main import CDocument

g_sRadiusArea1 = math.sqrt(1 / math.pi)

class CGroupBlot(CBlot): # tag = groupb

	s_dX = 4.5
	s_dY = s_dX / (16.0 / 9.0) # HDTV ratio
	s_dSLineOuter = 0.04
	s_dSLineInner = 0.008
	s_dSLineStats = 0.01

	# width to height ratios

	s_rSGroup = 5.0
	s_rSTeamName = 6.0

	def __init__(self, page: CPage, group: CGroup) -> None:
		self.page = page
		self.tourn = page.tourn
		self.doc = page.doc
		self.pdf = page.pdf

		super().__init__(self.pdf)

		self.group = group

	def Draw(self, pos: SPoint) -> None:

		fLtR = self.page.FIsLeftToRight()

		rectBorder = SRect(pos.x, pos.y, self.s_dX, self.s_dY)
		rectInside = rectBorder.Copy().Inset(self.s_dSLineOuter / 2.0)

		# title

		#dYTitle = dY * self.s_uYTitle
		dYTitle = rectInside.dX / self.s_rSGroup
		rectTitle = rectInside.Copy(dY=dYTitle)

		self.FillBox(rectTitle, self.group.colors.color)

		dYGroupName = dYTitle * 1.3
		oltbGroupName = self.Oltb(rectTitle, self.page.Fontkey('group.name'), dYGroupName)
		rectGroupName = oltbGroupName.RectDrawText(
										self.group.strName,
										self.group.colors.colorDarker,
										self.page.JhEnd(),
										JV.Middle)

		rectGroupLabel = rectTitle.Copy(dX=rectGroupName.x - rectTitle.x)
		if not fLtR:
			rectGroupLabel = rectTitle.Shift(dX=rectGroupName.dX)

		uGroupLabel = 0.65
		strGroupTitle = self.page.StrTranslation('group.title')
		oltbGroupLabel = self.Oltb(rectGroupLabel, self.page.Fontkey('group.label'), dYTitle * uGroupLabel, dSMargin = oltbGroupName.dSMargin)
		oltbGroupLabel.DrawText(strGroupTitle, colorWhite, self.page.JhEnd()) #, JV.Top)

		# heading

		#dYHeading = dY * self.s_uYHeading
		dYHeading = dYTitle / 4.0
		rectHeading = rectInside.Copy(y=rectTitle.yMax, dY=dYHeading)

		self.FillBox(rectHeading, colorBlack)

		# teams

		dYTeams = rectInside.dY - (dYTitle + dYHeading)
		dYTeam = dYTeams / len(self.group.mpStrSeedStrTeam)
		rectTeam = rectHeading.Copy(y=rectHeading.yMax, dY=dYTeam)

		for i in range(len(self.group.mpStrSeedStrTeam)):
			color = self.group.colors.colorLighter if (i & 1) else colorWhite
			self.FillBox(rectTeam, color)
			rectTeam.Shift(dY=dYTeam)

		rectTeam.dX = dYTeam * self.s_rSTeamName
		if not fLtR:
			rectTeam.Shift(dX=rectHeading.dX - rectTeam.dX)

		for i, strSeed in enumerate(sorted(self.group.mpStrSeedStrTeam)):
			rectTeam.y = rectHeading.y + rectHeading.dY + i * dYTeam
			strTeam = self.group.mpStrSeedStrTeam[strSeed]

			oltbPlace = self.Oltb(rectTeam, self.page.Fontkey('group.team.abbrev'), dYTeam)
			rectPlace = oltbPlace.RectDrawText(strTeam, colorBlack, self.page.JhEnd())

			if fLtR:
				rectName = rectTeam.Copy().Stretch(dXRight = -(rectPlace.dX + oltbPlace.dSMargin))
			else:
				rectName = rectTeam.Copy().Stretch(dXLeft = (rectPlace.dX + oltbPlace.dSMargin))

			uTeamText = 0.75
			oltbName = self.Oltb(rectName, self.page.Fontkey('group.team.name'), dYTeam * uTeamText, dSMargin = oltbPlace.dSMargin)
			strTeam = self.page.StrTeam(strTeam)
			oltbName.DrawText(strTeam, colorDarkSlateGrey, self.page.JhStart(), fShrinkToFit = True) #, JV.Top)

		# dividers for team/points/gf/ga

		dXRank = (rectInside.dX - rectTeam.dX) / 7.0
		dXStats = dXRank * 2

		if fLtR:
			rectGoalsFor = rectHeading.Copy(x=rectTeam.xMax, dX=dXStats)
			rectGoalsAgainst = rectHeading.Copy(x=rectGoalsFor.xMax, dX=dXStats)
			rectPoints = rectHeading.Copy(x=rectGoalsAgainst.xMax, dX=dXStats)
			rectRank = rectHeading.Copy(x=rectPoints.xMax, dX=dXRank)
		else:
			rectGoalsFor = rectHeading.Copy(x=rectTeam.xMin - dXStats, dX=dXStats)
			rectGoalsAgainst = rectHeading.Copy(x=rectGoalsFor.xMin - dXStats, dX=dXStats)
			rectPoints = rectHeading.Copy(x=rectGoalsAgainst.xMin - dXStats, dX=dXStats)
			rectRank = rectHeading.Copy(x=rectPoints.xMin - dXRank, dX=dXRank)

		self.pdf.set_line_width(self.s_dSLineStats)
		self.pdf.set_draw_color(0) # black

		if fLtR:
			self.pdf.line(rectGoalsFor.xMin, rectHeading.yMax, rectGoalsFor.xMin, rectInside.yMax)
			self.pdf.line(rectGoalsAgainst.xMin, rectHeading.yMax, rectGoalsAgainst.xMin, rectInside.yMax)
			self.pdf.line(rectPoints.xMin, rectHeading.yMax, rectPoints.xMin, rectInside.yMax)
			self.pdf.line(rectRank.xMin, rectHeading.yMax, rectRank.xMin, rectInside.yMax)
		else:
			self.pdf.line(rectGoalsFor.xMax, rectHeading.yMax, rectGoalsFor.xMax, rectInside.yMax)
			self.pdf.line(rectGoalsAgainst.xMax, rectHeading.yMax, rectGoalsAgainst.xMax, rectInside.yMax)
			self.pdf.line(rectPoints.xMax, rectHeading.yMax, rectPoints.xMax, rectInside.yMax)
			self.pdf.line(rectRank.xMax, rectHeading.yMax, rectRank.xMax, rectInside.yMax)

		# heading labels

		@dataclass
		class SHeadingLabel: # tag = headlab
			rect: SRect
			strLabel: str

		lHeadlab = [
			SHeadingLabel(rectGoalsFor,		self.page.StrTranslation('group.goals-for')),
			SHeadingLabel(rectGoalsAgainst,	self.page.StrTranslation('group.goals-against')),
			SHeadingLabel(rectPoints,		self.page.StrTranslation('group.points')),
			 # RIGHT/LEFT-POINTING DOUBLE ANGLE QUOTATION MARK
			SHeadingLabel(rectRank,			"»" if fLtR else "«"),
		]

		fontkeyHeading = self.page.Fontkey('group.heading')
		lStrLabel = [headlab.strLabel for headlab in lHeadlab]
		veklmEm: UVekLm = self.pdf.LmEmFromText(fontkeyHeading, VEK.DescendCap, lStrLabel)

		for headlab in lHeadlab:
			oltbHeading = self.Oltb(headlab.rect, fontkeyHeading, rectHeading.dY, veklmEm=veklmEm)
			oltbHeading.DrawText(headlab.strLabel, colorWhite, JH.Center)

		if self.page.pagea.fGroupDots:
			cDotDown = 3
			cDotPtsAcross = 3
			cDotGoalsAcross = 5
			cDotAcrossMax = max(cDotPtsAcross, cDotGoalsAcross)
			dSDot = dXStats / (2 * cDotGoalsAcross + 1)
			dYTeamDotUnused = dYTeam - (cDotDown * dSDot)
			dYTeamDotGap = dYTeamDotUnused / (cDotDown + 1)
			dYTeamDotGrid = dSDot + dYTeamDotGap
			dYTeamDotMin = dYTeamDotGap

			for iTeam, strTeam in enumerate(self.group.mpStrSeedStrTeam.values()):
				yTeam = rectHeading.yMax + iTeam * dYTeam
				results = None if self.page.pagea.fFixturesOnly else self.tourn.mpStrTeamResults.get(strTeam)

				# group rank

				if results and results.strPlace:
					rectPlace = rectRank.Copy(y = yTeam, dY=dYTeam)
					oltbPlace = self.Oltb(rectPlace, self.page.Fontkey('group.team.place'), dYTeam)
					oltbPlace.DrawText(results.strPlace, colorBlack, JH.Center)

				# total points

				if results and results.cPoint:
					dXDotsPoints = ((cDotPtsAcross * 2) + 1) * dSDot
					xPointsTotal = rectPoints.xMin + dXDotsPoints if self.page.FIsLeftToRight() else rectPoints.xMin
					dXPointsTotal =  rectPoints.dX - dXDotsPoints
					rectPointTotal = SRect(xPointsTotal, yTeam, dXPointsTotal, dYTeam)
					oltbPointTotal = self.Oltb(rectPointTotal, self.page.Fontkey('group.team.point-total'), dYTeam)
					oltbPointTotal.DrawText(f"{results.cPoint:1}", colorLightGrey, JH.Center)

				# dots

				for row in range(cDotDown):

					uOpacityDefault = 0.05
					uOpacityFilled = 1.0

					@dataclass
					class SDotBox:
						xStat: float
						mpColUOpacity: list[float]

					mpMatchstatDotbox: EnumTuple[MATCHSTAT, SDotBox] = EnumTuple(MATCHSTAT, (
						SDotBox(rectGoalsFor.xMin,		[uOpacityDefault] * cDotGoalsAcross),
						SDotBox(rectGoalsAgainst.xMin,	[uOpacityDefault] * cDotGoalsAcross),
						SDotBox(rectPoints.xMin,		[uOpacityDefault] * cDotPtsAcross),
					))

					if results and row < len(results.lResult):
						result = results.lResult[row]
						for matchstat, dotbox in mpMatchstatDotbox.items():
							cColExtra = result[matchstat] - len(dotbox.mpColUOpacity)
							if cColExtra > 0:
								dotbox.mpColUOpacity.extend([uOpacityDefault] * cColExtra)
							for col in range(result[matchstat]):
								dotbox.mpColUOpacity[col] = uOpacityFilled

					for matchstat, dotbox in mpMatchstatDotbox.items():
						xStat = dotbox.xStat
						cDotAcross = len(dotbox.mpColUOpacity)
						if cDotAcross > cDotAcrossMax:
							assert matchstat != MATCHSTAT.Points
							dXDotsAndGaps = ((2 * cDotAcrossMax) - 1) * dSDot
							dXDots = cDotAcross * dSDot
							dXGaps = dXDotsAndGaps - dXDots

							uGapsMin = 1.0 / 8.0
							if dXGaps / dXDotsAndGaps < uGapsMin:
								dXGaps = dXDotsAndGaps * dXDotsAndGaps
								dXDots = dXDotsAndGaps - dXGaps
								dXDot = dXDots / cDotAcross
							else:
								dXDot = dSDot

							dXGap = dXGaps / (cDotAcross - 1)
						else:
							dXDot = dSDot
							dXGap = dSDot

						dXStatDotGrid = dXDot + dXGap
						dXStatDotMin = dSDot

						for col in range(cDotAcross):
							dXDotMin = dXStatDotMin + dXStatDotGrid * col
							if self.page.FIsLeftToRight():
								xDot = xStat + dXDotMin
							else:
								xDot = xStat + dXStats - (dXDotMin + dXDot)
							yDot = yTeam + dYTeamDotMin + dYTeamDotGrid * row

							with self.pdf.local_context(fill_opacity=dotbox.mpColUOpacity[col]):
								self.pdf.set_fill_color(0) # black
								if matchstat == MATCHSTAT.Points:
									dSCenter = dSDot / 2.0
									dSRadius = dSDot * g_sRadiusArea1 # a circle with the same area as dSDot square
									self.pdf.circle(xDot + dSCenter, yDot + dSCenter, dSRadius, style='F')
								else:
									self.pdf.rect(xDot, yDot, dXDot, dSDot, style='F')


		# draw border last to cover any alignment weirdness

		if self.page.pagea.fMainBorders:

			self.DrawBox(rectBorder, self.s_dSLineOuter, colorBlack)
			self.DrawBox(rectBorder, self.s_dSLineInner, self.group.colors.color)

class CGroupSetBlot(CBlot): # tag = gsetb

	s_dSGridGapMin = min(CGroupBlot.s_dX, CGroupBlot.s_dY) / 6
	s_dSGridGapMax = min(CGroupBlot.s_dX, CGroupBlot.s_dY) / 2

	def __init__(self, doc: CDocument, lGroupb: list[CGroupBlot], rectCanvas: SRect, cCol: int = 0, cRow: int = 0, fAddOuterMargin: bool = True) -> None:
		super().__init__(doc.pdf)

		self.doc = doc
		self.lGroupb = lGroupb

		self.cCol = 0
		self.cRow = 0
		self.fAddOuterMargin = fAddOuterMargin

		self.dXGridGap = 0
		self.dYGridGap = 0

		self.dX = 0
		self.dY = 0

		if not lGroupb:
			return

		self.Layout(rectCanvas, cCol, cRow, fAddOuterMargin)

	def Layout(self, rectCanvas: SRect, cCol: int = 0, cRow: int = 0, fAddOuterMargin: bool = True):

		self.fAddOuterMargin = fAddOuterMargin

		if cCol == 0 and cRow == 0:
			self.cCol = round(math.sqrt(len(self.lGroupb))) + 1
			self.cRow = cCol
		elif cCol == 0:
			self.cCol = (len(self.lGroupb) + cRow - 1) // cRow
			self.cRow = cRow
		elif cRow == 0:
			self.cCol = cCol
			self.cRow = (len(self.lGroupb) + cCol - 1) // cCol
		else:
			self.cCol = cCol
			self.cRow = cRow

		dXGroups = (self.cCol * CGroupBlot.s_dX)
		dYGroups = (self.cRow * CGroupBlot.s_dY)

		if fAddOuterMargin:
			self.dXGridGap = 0 if self.cCol <= 1 else (rectCanvas.dX - dXGroups) / self.cCol
			self.dYGridGap = 0 if self.cRow <= 1 else (rectCanvas.dY - dYGroups) / self.cRow
		else:
			self.dXGridGap = 0 if self.cCol <= 2 else (rectCanvas.dX - dXGroups) / (self.cCol - 1)
			self.dYGridGap = 0 if self.cRow <= 2 else (rectCanvas.dY - dYGroups) / (self.cRow - 1)

		# gaps could be negative if rectInside is too small

		self.dXGridGap = 0 if self.cCol <= 1 else min(max(self.s_dSGridGapMin, self.dXGridGap), self.s_dSGridGapMax)
		self.dYGridGap = 0 if self.cRow <= 1 else min(max(self.s_dSGridGapMin, self.dYGridGap), self.s_dSGridGapMax)

		if fAddOuterMargin:
			self.dX = dXGroups + (self.cCol * self.dXGridGap)
			self.dY = dYGroups + (self.cRow * self.dYGridGap)
		else:
			self.dX = dXGroups + max(0, ((self.cCol - 1) * self.dXGridGap))
			self.dY = dYGroups + max(0, ((self.cRow - 1) * self.dYGridGap))

	def Draw(self, pos: SPoint) -> None:

		# add margins if there is spacing

		xGroupOrigin = pos.x + (self.dXGridGap / 2 if self.fAddOuterMargin else 0)
		yGroupOrigin = pos.y + (self.dYGridGap / 2 if self.fAddOuterMargin else 0)
		for iGroupb, groupb in enumerate(self.lGroupb):
			iRow, iCol = divmod(iGroupb, self.cCol)
			posGroup = SPoint(
				xGroupOrigin + iCol * (CGroupBlot.s_dX + self.dXGridGap),
				yGroupOrigin + iRow * (CGroupBlot.s_dY + self.dYGridGap))
			groupb.Draw(posGroup)

		# NOTE bruceo: debug drawing for any blot?
		#self.DrawBox(SRect(pos.x, pos.y, self.dX, self.dY), CGroupBlot.s_dSLineStats, ColorFromStr('magenta'))
