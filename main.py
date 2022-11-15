import calendar
import datetime
import logging
import math

from dataclasses import dataclass
from dateutil import tz
from pathlib import Path
from typing import Optional

from database import *
from pdf import *

logging.getLogger("fontTools.subset").setLevel(logging.ERROR)

class CGroupBlot(CBlot): # tag = groupb

	s_dX = 4.5
	s_dY = s_dX / (16.0 / 9.0) # HDTV ratio
	s_dSLineOuter = 0.04
	s_dSLineInner = 0.008
	s_dSLineStats = 0.01

	# width to height ratios

	s_rSGroup = 5.0
	s_rSTeamName = 6.0

	def __init__(self, doc: 'CDocument', group: CGroup) -> None:
		super().__init__(doc.pdf)
		self.doc = doc
		self.group = group

	def Draw(self, pos: SPoint) -> None:

		rectBorder = SRect(pos.x, pos.y, self.s_dX, self.s_dY)
		rectInside = rectBorder.Copy().Inset(self.s_dSLineOuter / 2.0)

		# title

		#dYTitle = dY * self.s_uYTitle
		dYTitle = rectInside.dX / self.s_rSGroup
		rectTitle = rectInside.Copy(dY=dYTitle)

		self.FillBox(rectTitle, self.group.colors.color)

		dYGroupName = dYTitle * 1.3
		oltbGroupName = self.Oltb(rectTitle, self.doc.fontkeyGroupName, dYGroupName)
		rectGroupName = oltbGroupName.RectDrawText(
										self.group.strName,
										self.group.colors.colorDarker,
										JH.Right,
										JV.Middle)

		rectGroupLabel = rectTitle.Copy(dX=rectGroupName.x - rectTitle.x)

		uGroupLabel = 0.65
		oltbGroupLabel = self.Oltb(rectGroupLabel, self.doc.fontkeyGroupLabel, dYTitle * uGroupLabel, dSMargin=oltbGroupName.dSMargin)
		oltbGroupLabel.DrawText('Group', colorWhite, JH.Right) #, JV.Top)

		# heading

		#dYHeading = dY * self.s_uYHeading
		dYHeading = dYTitle / 4.0
		rectHeading = rectInside.Copy(y=rectTitle.yMax, dY=dYHeading)

		self.FillBox(rectHeading, colorBlack)

		# teams

		dYTeams = rectInside.dY - (dYTitle + dYHeading)
		dYTeam = dYTeams / len(self.group.mpStrSeedTeam)
		rectTeam = rectHeading.Copy(y=rectHeading.yMax, dY=dYTeam)

		for i in range(len(self.group.mpStrSeedTeam)):
			color = self.group.colors.colorLighter if (i & 1) else colorWhite
			self.FillBox(rectTeam, color)
			rectTeam.Shift(dY=dYTeam)

		rectTeam.dX = dYTeam * self.s_rSTeamName

		for i, strSeed in enumerate(sorted(self.group.mpStrSeedTeam)):
			rectTeam.y = rectHeading.y + rectHeading.dY + i * dYTeam
			team = self.group.mpStrSeedTeam[strSeed]

			oltbAbbrev = self.Oltb(rectTeam, self.doc.fontkeyGroupTeamAbbrev, dYTeam)
			oltbAbbrev.DrawText(team.strAbbrev, colorBlack, JH.Right)

			uTeamText = 0.75
			oltbName = self.Oltb(rectTeam, self.doc.fontkeyGroupTeamAbbrev, dYTeam * uTeamText, dSMargin=oltbAbbrev.dSMargin)
			oltbName.DrawText(team.strName, colorDarkgrey, JH.Left) #, JV.Top)

		# dividers for team/points/gf/ga

		dXStats = (rectInside.dX - rectTeam.dX) / 3.0

		rectPoints = rectHeading.Copy(x=rectTeam.xMax, dX=dXStats)
		rectGoalsFor = rectHeading.Copy(x=rectPoints.xMax, dX=dXStats)
		rectGoalsAgainst = rectHeading.Copy(x=rectGoalsFor.xMax, dX=dXStats)

		self.pdf.set_line_width(self.s_dSLineStats)
		self.pdf.set_draw_color(0) # black
	
		self.pdf.line(rectPoints.xMin, rectHeading.yMax, rectPoints.xMin, rectInside.yMax)
		self.pdf.line(rectGoalsFor.xMin, rectHeading.yMax, rectGoalsFor.xMin, rectInside.yMax)
		self.pdf.line(rectGoalsAgainst.xMin, rectHeading.yMax, rectGoalsAgainst.xMin, rectInside.yMax)

		# heading labels

		lTuRectStr = (
			#(rectTeam, "COUNTRY"),
			(rectPoints,		"PTS"),
			(rectGoalsFor,		"GF"),
			(rectGoalsAgainst,	"GA"),
		)

		for rectHeading, strHeading in lTuRectStr:
			oltbHeading = self.Oltb(rectHeading, self.doc.fontkeyGroupHeading, rectHeading.dY)
			oltbHeading.DrawText(strHeading, colorWhite, JH.Center)

		# draw border last to cover any alignment weirdness

		self.DrawBox(rectBorder, self.s_dSLineOuter, colorBlack)
		self.DrawBox(rectBorder, self.s_dSLineInner, self.group.colors.color)

class CMatchBlot(CBlot): # tag = dayb
	def __init__(self, dayb: 'CDayBlot', match: CMatch, rect: SRect) -> None:
		super().__init__(dayb.pdf)
		self.doc = dayb.doc
		self.db = dayb.db
		self.dayb = dayb
		self.match = match
		self.rect = rect
		self.fElimination = match.stage != STAGE.Group

		self.dYInfo = dayb.dYTime + dayb.s_dSScore
		
		if self.fElimination:
			self.dYInfo += self.dayb.s_dYFontLabel + (self.dayb.s_dSPens / 2.0) - self.dayb.s_dSPensNudge

		dYGaps = (self.rect.dY - self.dYInfo)
		dYTimeGap = min(self.dayb.s_dYTimeGapMax, dYGaps / 3.0)
		self.dYOuterGap = (dYGaps - dYTimeGap) / 2.0
		# self.dYTimeAndGap may be cleared if we coalesce times
		self.dYTimeAndGap = self.dayb.dYTime + dYTimeGap

	def DrawFill(self) -> None:
		lStrGroup = self.match.lStrGroup if self.match.lStrGroup else self.db.lStrGroup
		lGroup = [self.db.mpStrGroupGroup[strGroup] for strGroup in lStrGroup] 
		if self.match.stage == STAGE.Group:
			lColor = [group.colors.color for group in lGroup]
		else:
			lColor = [group.colors.colorLighter for group in lGroup]

		@dataclass
		class SRectColor:
			rect: SRect
			color: SColor

		lRc: list[SRectColor] = []

		if self.match.stage == STAGE.Group:
			assert len(lColor) == 1
			lRc.append(SRectColor(self.rect, lColor[0]))
		elif self.match.stage == STAGE.Round1:
			assert len(lColor) == 2
			rectLeft = self.rect.Copy(dX=self.rect.dX / 2.0)
			lRc.append(SRectColor(rectLeft, lColor[0]))

			rectRight = rectLeft.Copy().Shift(dX=rectLeft.dX)
			lRc.append(SRectColor(rectRight, lColor[1]))
		else:
			rectStripe = self.rect.Copy(dX=self.rect.dX / len(lColor))
			for color in lColor:
				lRc.append(SRectColor(rectStripe, color))
				rectStripe = rectStripe.Copy().Shift(dX=rectStripe.dX)

		for rc in lRc:
			self.FillBox(rc.rect, rc.color)

	def DrawInfo(self) -> None:

		# time

		if self.dYTimeAndGap:
			yTime = self.rect.y + self.dYOuterGap
			yScore = yTime + self.dYTimeAndGap

			rectTime = SRect(self.rect.x, yTime, self.rect.dX, self.dayb.dYTime)
			tStartPacific = self.match.tStart.to(tz.gettz('US/Pacific'))
			strTime = tStartPacific.format('h:mma')
			oltbTime = self.Oltb(rectTime, self.doc.fontkeyMatchTime, self.dayb.s_dYFontTime)
			oltbTime.DrawText(strTime, colorBlack, JH.Center)
		else:
			yScore = self.rect.y + self.dYOuterGap

		# dash between score boxes

		dXLineGap = self.dayb.s_dSScore / 2.0
		dXLine = dXLineGap / 2.0
		xLineMin = self.rect.x + (self.rect.dX / 2.0) - (dXLine / 2.0)
		xLineMax = xLineMin + dXLine
		yLine = yScore + (self.dayb.s_dSScore / 2.0)
		self.pdf.set_line_width(self.dayb.s_dSLineScore)
		self.pdf.set_draw_color(0) # black
		self.pdf.line(xLineMin, yLine, xLineMax, yLine)

		# score boxes

		xHomeBox = self.rect.x + (self.rect.dX / 2.0) - ((dXLineGap / 2.0 ) + self.dayb.s_dSScore)
		rectHomeBox = SRect(xHomeBox, yScore, self.dayb.s_dSScore, self.dayb.s_dSScore)
		self.DrawBox(rectHomeBox, self.dayb.s_dSLineScore, colorBlack, colorWhite)

		xAwayBox = self.rect.x + (self.rect.dX / 2.0) + (dXLineGap / 2.0 )
		rectAwayBox = SRect(xAwayBox, yScore, self.dayb.s_dSScore, self.dayb.s_dSScore)
		self.DrawBox(rectAwayBox, self.dayb.s_dSLineScore, colorBlack, colorWhite)

		if self.fElimination:

			# PK boxes

			rectHomePens = SRect(rectHomeBox.xMax, rectHomeBox.yMax)
			rectHomePens.Outset(self.dayb.s_dSPens)
			rectHomePens.Shift(dX=-self.dayb.s_dSPensNudge, dY=-self.dayb.s_dSPensNudge)
			self.DrawBox(rectHomePens, self.dayb.s_dSLineScore, colorBlack, colorWhite)

			rectAwayPens = SRect(rectAwayBox.xMin, rectAwayBox.yMax)
			rectAwayPens.Outset(self.dayb.s_dSPens)
			rectAwayPens.Shift(dX=self.dayb.s_dSPensNudge, dY=-self.dayb.s_dSPensNudge)
			self.DrawBox(rectAwayPens, self.dayb.s_dSLineScore, colorBlack, colorWhite)

			# form lines

			yLineForm = (rectHomeBox.yMax + rectHomePens.yMin) / 2.0
			dXLineFormGap = ((rectHomeBox.xMin - self.rect.xMin) - self.dayb.s_dXLineForm) / 2.0

			xLineFormLeftMin = self.rect.xMin + dXLineFormGap
			xLineFormRightMin =  self.rect.xMax - (dXLineFormGap + self.dayb.s_dXLineForm)

			for xLineFormMin in (xLineFormLeftMin, xLineFormRightMin):
				xLineFormMax = xLineFormMin + self.dayb.s_dXLineForm
				self.pdf.set_line_width(self.dayb.s_dSLineScore)
				self.pdf.set_draw_color(0) # black
				self.pdf.line(xLineFormMin, yLineForm, xLineFormMax, yLineForm)

			# form labels

			for xLineFormMin, strLabel in ((xLineFormLeftMin, self.match.strHome), (xLineFormRightMin, self.match.strAway)):
				rectLabelForm = SRect(xLineFormMin, yLineForm, self.dayb.s_dXLineForm, self.dayb.s_dYFontForm)
				oltbLabelForm = self.Oltb(rectLabelForm, self.doc.fontkeyMatchFormLabel, self.dayb.s_dYFontForm)
				oltbLabelForm.DrawText(strLabel, colorBlack, JH.Center)

			# match label

			rectLabel = self.rect.Copy(y=rectHomePens.yMax, dY=self.dayb.s_dYFontLabel + self.dayb.s_dYTimeGapMax)
			oltbLabel = self.Oltb(rectLabel, self.doc.fontkeyMatchLabel, self.dayb.s_dYFontLabel)
			oltbLabel.DrawText(self.match.strName, colorBlack, JH.Center)

		else:

			# team names

			dXTeams = self.rect.dX - (2 * self.dayb.s_dSScore) - dXLineGap
			dXTeam = dXTeams / 2.0

			rectHomeTeam = SRect(self.rect.x, yScore, dXTeam, self.dayb.s_dSScore)
			oltbHomeTeam = self.Oltb(rectHomeTeam, self.doc.fontkeyMatchTeamAbbrev, self.dayb.s_dSScore)
			oltbHomeTeam.DrawText(self.match.strHome, colorBlack, JH.Center)

			rectAwayTeam = SRect(self.rect.xMax - dXTeam, yScore, dXTeam, self.dayb.s_dSScore)
			oltbAwayTeam = self.Oltb(rectAwayTeam, self.doc.fontkeyMatchTeamAbbrev, self.dayb.s_dSScore)
			oltbAwayTeam.DrawText(self.match.strAway, colorBlack, JH.Center)

class CDayBlot(CBlot): # tag = dayb

	s_dX = 2.25
	s_dY = s_dX # square

	s_dSLineOuter = 0.02
	s_dSLineScore = 0.01

	s_uYDate = 0.06
	s_dYDate = s_dY * s_uYDate

	s_uYTime = 0.075
	s_dYFontTime = s_dY * s_uYTime
	s_dYTimeGapMax = s_dYFontTime / 2.0	
	# scores are square, so we use dS

	s_uSScore = 0.147
	s_dSScore = s_dY * s_uSScore
	s_dSScoreGap = s_dSScore / 2.0

	s_dSPens = s_dSScore / 2.0
	s_dSPensNudge = 0.02

	s_dXLineForm = s_dSScore * 1.32
	s_dYFontForm = s_dYFontTime

	s_dYFontLabel = s_dYFontTime * 1.3

	def __init__(self, doc: 'CDocument', setMatch: set[CMatch] = set(), date: Optional[datetime.date] = None) -> None:
		super().__init__(doc.pdf)
		self.doc = doc
		self.db = doc.db
		self.lMatch = sorted(setMatch, key=lambda match: (match.tStart, match.strHome))
		if self.lMatch:
			assert date is None
			self.tStart = self.lMatch[0].tStart
		else:
			assert date is not None
			self.tStart = arrow.get(date)
		self.date = self.tStart.date()
		for match in self.lMatch[1:]:
			assert self.date == match.tStart.date()
		self.dYTime = CFontInstance(self.pdf, self.doc.fontkeyDayTime, self.s_dYFontTime).dYCap

	def Draw(self, pos: SPoint, datePrev: Optional[datetime.date] = None) -> None:

		rectBorder = SRect(pos.x, pos.y, self.s_dX, self.s_dY)
		rectInside = rectBorder.Copy().Inset(self.s_dSLineOuter / 2.0)

		# Date

		# BB (bruceo) only include year/month sometimes

		if datePrev and datePrev.month == self.tStart.month:
			strFormat = "D"
		else:
			strFormat = "MMMM D"
		strDate = self.tStart.format(strFormat)

		rectDate = rectInside.Copy(dY=self.s_dYDate)
		oltbDate = self.Oltb(rectDate, self.doc.fontkeyDayDate, rectDate.dY)
		oltbDate.DrawText(strDate, colorBlack)

		# matchless days get a bottom border and nothing else

		if not self.lMatch:

			self.pdf.set_line_width(self.s_dSLineOuter)
			self.pdf.set_draw_color(0) # black
			self.pdf.line(rectBorder.xMin, rectBorder.yMax, rectBorder.xMax, rectBorder.yMax)

			return

		rectInside.Stretch(dYTop=rectDate.dY)

		# count the time segments

		dYMatch = rectInside.dY / len(self.lMatch)
		rectMatch = rectInside.Copy(dY=dYMatch)

		# lay out matches top to bottom

		lMatchb: list[CMatchBlot] = []

		for match in self.lMatch:
			lMatchb.append(CMatchBlot(self, match, rectMatch))
			rectMatch = rectMatch.Copy().Shift(dY=rectMatch.dY)

		# coalesce matches at the same time

		for matchbTop, matchbBottom in zip(lMatchb, lMatchb[1:]):
			if not matchbTop.dYTimeAndGap:
				continue

			if matchbTop.match.tStart != matchbBottom.match.tStart:
				continue

			dYToSplit = matchbBottom.dYTimeAndGap
			dYAdjust = dYToSplit / 3.0
			matchbBottom.dYOuterGap = dYAdjust
			matchbBottom.dYTimeAndGap = 0

			matchbTop.dYOuterGap += dYAdjust
			matchbTop.dYTimeAndGap += dYAdjust
			matchbTop.rect.Stretch(dYBottom=dYAdjust * 2)
			matchbBottom.rect.Stretch(dYTop=dYAdjust * 2)

		# draw fills, then boxes.text

		for matchb in lMatchb:
			matchb.DrawFill()

		for matchb in lMatchb:
			matchb.DrawInfo()

		# draw border last to cover any alignment weirdness

		self.DrawBox(rectBorder, self.s_dSLineOuter, colorBlack)

class CFinalBlot(CBlot): # tag = finalb

	s_dX = CDayBlot.s_dX * 3.0
	s_dY = CDayBlot.s_dY

	s_dYFontTitle = CDayBlot.s_dYFontLabel * 1.7
	s_dYFontDate = CDayBlot.s_dYFontLabel * 1.4
	s_dYFontTime = s_dYFontDate
	s_dYFontForm = s_dYFontDate

	s_dYTextGap = s_dYFontTitle / 4.0

	s_dSLineScore = CDayBlot.s_dSLineOuter

	s_dSScore = CDayBlot.s_dSScore * 1.6
	s_dSScoreGap = s_dSScore

	s_dSPens = s_dSScore / 2.0
	s_dSPensNudge = 0

	s_dXLineForm = s_dSScore * 4

	def __init__(self, doc: 'CDocument', match: CMatch) -> None:
		super().__init__(doc.pdf)
		self.doc = doc
		self.match = match

	def Draw(self, pos: SPoint, datePrev: Optional[datetime.date] = None) -> None:

		rectAll = SRect(pos.x, pos.y, self.s_dX, self.s_dY)

		# title

		rectTitle = rectAll.Copy(dY=self.s_dYFontTitle)
		oltbTitle = self.Oltb(rectTitle, self.doc.fontkeyFinalTitle, rectTitle.dY)
		oltbTitle.DrawText('FINAL', colorBlack, JH.Center)

		# date

		strDate = self.match.tStart.format('dddd, MMMM D')
		rectDate = rectTitle.Copy(dY=self.s_dYFontDate).Shift(dY = rectTitle.dY)
		oltbDate = self.Oltb(rectDate, self.doc.fontkeyFinalTitle, rectDate.dY)
		oltbDate.DrawText(strDate, colorBlack, JH.Center)

		# time

		strTime = self.match.tStart.format('h:mma')
		rectTime = rectDate.Copy(dY=self.s_dYFontTime).Shift(dY = rectDate.dY + self.s_dYTextGap)
		oltbTime = self.Oltb(rectTime, self.doc.fontkeyFinalTime, rectTime.dY)
		oltbTime.DrawText(strTime, colorBlack, JH.Center)

		# dash between score boxes

		rectScore = rectAll.Copy().Set(y = rectTime.yMax + 2 * self.s_dYTextGap)

		dXLineGap = self.s_dSScore
		dXLine = dXLineGap / 2.0
		xLineMin = rectScore.x + (rectScore.dX / 2.0) - (dXLine / 2.0)
		xLineMax = xLineMin + dXLine
		yLine = rectScore.y + (self.s_dSScore / 2.0)
		self.pdf.set_line_width(self.s_dSLineScore)
		self.pdf.set_draw_color(0) # black
		self.pdf.line(xLineMin, yLine, xLineMax, yLine)

		# score boxes

		xHomeBox = rectScore.x + (rectScore.dX / 2.0) - ((dXLineGap / 2.0 ) + self.s_dSScore)
		rectHomeBox = SRect(xHomeBox, rectScore.y, self.s_dSScore, self.s_dSScore)
		self.DrawBox(rectHomeBox, self.s_dSLineScore, colorBlack, colorWhite)

		xAwayBox = rectScore.x + (rectScore.dX / 2.0) + (dXLineGap / 2.0 )
		rectAwayBox = SRect(xAwayBox, rectScore.y, self.s_dSScore, self.s_dSScore)
		self.DrawBox(rectAwayBox, self.s_dSLineScore, colorBlack, colorWhite)

		# PK boxes

		rectHomePens = SRect(rectHomeBox.xMax, rectHomeBox.yMax)
		rectHomePens.Outset(self.s_dSPens)
		rectHomePens.Shift(dX=-self.s_dSPensNudge, dY=-self.s_dSPensNudge)
		self.DrawBox(rectHomePens, self.s_dSLineScore, colorBlack, colorWhite)

		rectAwayPens = SRect(rectAwayBox.xMin, rectAwayBox.yMax)
		rectAwayPens.Outset(self.s_dSPens)
		rectAwayPens.Shift(dX=self.s_dSPensNudge, dY=-self.s_dSPensNudge)
		self.DrawBox(rectAwayPens, self.s_dSLineScore, colorBlack, colorWhite)

		# form lines

		yLineForm = (rectHomeBox.yMax + rectHomePens.yMax) / 2.0
		dXLineFormGap = ((rectHomeBox.xMin - rectScore.xMin) - self.s_dXLineForm) / 2.0

		xLineFormLeftMin = rectScore.xMin + dXLineFormGap
		xLineFormRightMin =  rectScore.xMax - (dXLineFormGap + self.s_dXLineForm)

		for xLineFormMin in (xLineFormLeftMin, xLineFormRightMin):
			xLineFormMax = xLineFormMin + self.s_dXLineForm
			self.pdf.set_line_width(self.s_dSLineScore)
			self.pdf.set_draw_color(0) # black
			self.pdf.line(xLineFormMin, yLineForm, xLineFormMax, yLineForm)

		# form labels

		for xLineFormMin, strLabel in ((xLineFormLeftMin, self.match.strHome), (xLineFormRightMin, self.match.strAway)):
			rectLabelForm = SRect(xLineFormMin, yLineForm, self.s_dXLineForm, self.s_dYFontForm)
			oltbLabelForm = self.Oltb(rectLabelForm, self.doc.fontkeyDayFormLabel, self.s_dYFontForm)
			oltbLabelForm.DrawText(strLabel, colorBlack, JH.Center)

class CPage:
	def __init__(self, doc: 'CDocument', strOrientation: str, fmt: str | tuple):
		self.doc = doc
		self.db = doc.db
		self.pdf = doc.pdf

		self.strOrientation = strOrientation
		self.fmt = fmt
		self.rect = SRect
		self.pdf.add_page(orientation=self.strOrientation, format=self.fmt)
		self.rect = SRect(0, 0, self.pdf.w, self.pdf.h)

class CGroupsTestPage(CPage): # gtp
	def __init__(self, doc: 'CDocument'):
		super().__init__(doc, 'portrait', 'c3')

		dSMargin = 0.5

		dXGrid = CGroupBlot.s_dX + dSMargin
		dYGrid = CGroupBlot.s_dY + dSMargin

		for col in range(2):
			for row in range(4):
				try:
					strGroup = self.db.lStrGroup[col * 4 + row]
				except IndexError:
					continue
				group = self.db.mpStrGroupGroup[strGroup]
				groupb = CGroupBlot(doc, group)
				pos = SPoint(
						dSMargin + col * dXGrid,
						dSMargin + row * dYGrid)
				groupb.Draw(pos)

class CDaysTestPage(CPage): # gtp
	def __init__(self, doc: 'CDocument'):
		super().__init__(doc, 'landscape', 'c3')

		dSMargin = 0.25

		dXGrid = CDayBlot.s_dX + dSMargin
		dYGrid = CDayBlot.s_dY + dSMargin

		# lIdMatch = (49,57)
		# setDate: set[datetime.date] = {doc.db.mpIdMatch[idMatch].tStart.date() for idMatch in lIdMatch}
		setDate: set[datetime.date] = set(doc.db.mpDateSetMatch.keys())

		lDayb: list[CDayBlot] = [CDayBlot(doc, self.db.mpDateSetMatch[date]) for date in sorted(setDate)]

		for row in range(4):
			for col in range(7):
				try:
					dayb = lDayb[row * 7 + col]
				except IndexError:
					continue
				pos = SPoint(
						dSMargin + col * dXGrid,
						dSMargin + row * dYGrid)
				dayb.Draw(pos)

class CGroupSetBlot(CBlot): # tag = gsetb

	s_dSGridGap = CGroupBlot.s_dY / 2

	def __init__(self, doc: 'CDocument', lGroupb: list[CGroupBlot], cCol: int = 0, cRow: int = 0) -> None:
		super().__init__(doc.pdf)

		self.doc = doc
		self.lGroupb = lGroupb

		if cCol == 0 and cRow == 0:
			self.cCol = round(math.sqrt(len(lGroupb))) + 1
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
	
		self.dX = (self.cCol * CGroupBlot.s_dX) + ((self.cCol - 1) * self.s_dSGridGap)
		self.dY = (self.cRow * CGroupBlot.s_dY) + ((self.cRow - 1) * self.s_dSGridGap)

	def Draw(self, pos: SPoint) -> None:
		for iGroupb, groupb in enumerate(self.lGroupb):
			yGroup = pos.y + iGroupb * (CGroupBlot.s_dY + self.s_dSGridGap)
			groupb.Draw(SPoint(pos.x, yGroup))

class CCalendarBlot(CBlot): # tag = calb

	s_dYDayOfWeek = CDayBlot.s_dYDate * 2

	def __init__(self, doc: 'CDocument', lDayb: list[CDayBlot]) -> None:
		super().__init__(doc.pdf)

		self.doc = doc

		mpDateDayb: dict[datetime.date, CDayBlot] = {dayb.date:dayb for dayb in lDayb}
		dateMin: datetime.date = min(mpDateDayb)
		dateMax: datetime.date = max(mpDateDayb)

		# ensure dateMin is a sunday for proper week calculations

		if dateMin.weekday() != 6: # SUNDAY
			# arrow.shift(weekday) always goes forward in time
			dateMin = arrow.get(dateMin).shift(weeks=-1).shift(weekday=6).date()

		# and always go all the way to saturday

		if dateMax.weekday() != 5: # SATURDAY
			dateMax = arrow.get(dateMax).shift(weekday=5).date()

		cDay: int = (dateMax - dateMin).days + 1
		assert cDay % 7 == 0
		cWeek: int = cDay // 7

		self.dX = 7 * CDayBlot.s_dX
		self.dY = self.s_dYDayOfWeek + cWeek * CDayBlot.s_dY

		# build a list of all day blots and their relative positions

		self.lTuDPosDayb: list[tuple[SPoint, CDayBlot]] = []

		for tDay in arrow.Arrow.range('day', arrow.get(dateMin), arrow.get(dateMax)):
			date = tDay.date()
			
			try:
				dayb = mpDateDayb[date]
			except KeyError:
				dayb = CDayBlot(doc, date=date)

			iDay = (date.weekday() + 1) % 7 # we want sunday as 0
			iWeek = (date - dateMin).days // 7

			dPosDayb = SPoint(iDay * CDayBlot.s_dX, iWeek * CDayBlot.s_dY)
			self.lTuDPosDayb.append((dPosDayb, dayb))

	def Draw(self, pos: SPoint) -> None:

		# days of week

		rectDayOfWeek = SRect(x = pos.x, y = pos.y, dX = CDayBlot.s_dX, dY = self.s_dYDayOfWeek)

		for iDay in range(7):
			strDayOfWeek = calendar.day_abbr[(iDay + 6) % 7]
			oltbDayOfWeek = self.Oltb(rectDayOfWeek, self.doc.fontkeyCalDayOfWeek, rectDayOfWeek.dY)
			oltbDayOfWeek.DrawText(strDayOfWeek, colorBlack, JH.Center)
			rectDayOfWeek.Shift(dX=CDayBlot.s_dX)

		# days

		rectDays = SRect(x = pos.x, y = pos.y, dX = self.dX, dY = self.dY).Stretch(dYTop = rectDayOfWeek.dY)

		datePrev: Optional[datetime.date] = None
		for dPosDayb, dayb in self.lTuDPosDayb:

			posDayb = SPoint(rectDays.x + dPosDayb.x, rectDays.y + dPosDayb.y)

			dayb.Draw(posDayb, datePrev)

			datePrev = dayb.date

		# border

		self.DrawBox(rectDays, CDayBlot.s_dSLineOuter, colorBlack)

class CPosterPage(CPage): # tag = posterp
	def __init__(self, doc: 'CDocument'):
		super().__init__(doc, 'landscape', (22, 28))

		lDaybCalendar: list[CDayBlot] = []
		finalb: Optional[CFinalBlot] = None

		for setMatch in self.db.mpDateSetMatch.values():
			if len(setMatch) == 1:
				match = next(iter(setMatch))
				if match.stage == STAGE.Final:
					finalb = CFinalBlot(doc, match)
					continue

			lDaybCalendar.append(CDayBlot(doc, setMatch))

		cGroupHalf = len(self.db.lStrGroup) // 2
		
		lGroupbLeft = [CGroupBlot(doc, self.db.mpStrGroupGroup[strGroup]) for strGroup in self.db.lStrGroup[:cGroupHalf]]
		gsetbLeft = CGroupSetBlot(doc, lGroupbLeft, cCol = 1)
		
		lGroupbRight = [CGroupBlot(doc, self.db.mpStrGroupGroup[strGroup]) for strGroup in self.db.lStrGroup[cGroupHalf:]]
		gsetbRight = CGroupSetBlot(doc, lGroupbRight, cCol = 1)

		calb = CCalendarBlot(doc, lDaybCalendar)

		dXUnused = self.rect.dX - (calb.dX + gsetbLeft.dX + gsetbRight.dX)
		dSGap = dXUnused / 4.0 # both margins and both gaps between groups and calendar. same gap vertically for calendar/final

		assert gsetbLeft.dY == gsetbRight.dY
		yGroups = (self.rect.dY - gsetbLeft.dY) / 2.0

		xGroupsLeft = dSGap

		gsetbLeft.Draw(SPoint(xGroupsLeft, yGroups))

		xCalendar = xGroupsLeft + gsetbLeft.dX + dSGap
		if finalb:
			yCalendar = (self.rect.dY - (calb.dY + dSGap + finalb.s_dY)) / 2.0
		else:
			yCalendar = (self.rect.dY - calb.dY) / 2.0

		calb.Draw(SPoint(xCalendar, yCalendar))

		if finalb:
			xFinal = (self.rect.dX - finalb.s_dX) / 2.0
			yFinal = yCalendar + calb.dY + dSGap

			finalb.Draw(SPoint(xFinal, yFinal))

		xGroupsRight = xCalendar + calb.dX + dSGap

		gsetbRight.Draw(SPoint(xGroupsRight, yGroups))
	
class CDocument: # tag = doc
	s_pathDirFonts = Path('fonts')

	def __init__(self, pathDb: Path) -> None:
		self.db = CDataBase(pathDb)
		self.pdf = CPdf()

		self.pdf.AddFont('Consolas',	'',		self.s_pathDirFonts / 'consola.ttf')
		self.pdf.AddFont('Consolas',	'B',	self.s_pathDirFonts / 'consolab.ttf')
		self.pdf.AddFont('Calibri',		'',		self.s_pathDirFonts / 'calibri.ttf')
		self.pdf.AddFont('Calibri',		'B',	self.s_pathDirFonts / 'calibrib.ttf')
		self.pdf.AddFont('Calibri', 	'I',	self.s_pathDirFonts / 'calibrili.ttf')

		self.fontkeyGroupName		= SFontKey('Consolas',	'B')
		self.fontkeyGroupLabel		= SFontKey('Calibri',	'')
		self.fontkeyGroupHeading	= SFontKey('Calibri',	'')
		self.fontkeyGroupTeamName	= SFontKey('Calibri',	'')
		self.fontkeyGroupTeamAbbrev	= SFontKey('Consolas',	'')

		self.fontkeyDayDate			= SFontKey('Calibri',	'I')
		self.fontkeyDayTime			= SFontKey('Calibri',	'')
		self.fontkeyDayFormLabel	= SFontKey('Calibri',	'')

		self.fontkeyMatchTime		= SFontKey('Calibri',	'')
		self.fontkeyMatchTeamAbbrev	= SFontKey('Consolas',	'')
		self.fontkeyMatchFormLabel	= SFontKey('Calibri',	'')
		self.fontkeyMatchLabel		= SFontKey('Calibri',	'B')

		self.fontkeyFinalTitle		= SFontKey('Calibri',	'B')
		self.fontkeyFinalTime		= SFontKey('Calibri',	'')

		self.fontkeyCalDayOfWeek	= SFontKey('Calibri',	'I')

		lPage: list[CPage] = [
			# CGroupsTestPage(self),
			# CDaysTestPage(self),
			CPosterPage(self),
		]

		pathOutput = self.db.pathFile.with_suffix('.pdf')
		self.pdf.output(str(pathOutput))

g_pathHere = Path(__file__).parent
g_pathDb = g_pathHere / '2022-world-cup.xlsx'
g_doc = CDocument(g_pathDb)


