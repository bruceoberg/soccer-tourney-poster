import datetime
import logging

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

	# colors

	s_dSDarker = 0.5

	s_rVLighter = 1.5
	s_rSLighter = 0.5

	def __init__(self, doc: 'CDocument', group: CGroup) -> None:
		super().__init__(doc.pdf)
		self.doc = doc
		self.group = group
		self.color: SColor = ColorFromStr(self.group.strColor)
		self.colorDarker = ColorResaturate(self.color, dS=self.s_dSDarker)
		self.colorLighter = ColorResaturate(self.color, rV=self.s_rVLighter, rS=self.s_rSLighter)

	def Draw(self, pos: SPoint) -> None:

		rectBorder = SRect(pos.x, pos.y, self.s_dX, self.s_dY)
		rectInside = rectBorder.Copy().Inset(self.s_dSLineOuter / 2.0)

		# title

		#dYTitle = dY * self.s_uYTitle
		dYTitle = rectInside.dX / self.s_rSGroup
		rectTitle = rectInside.Copy(dY=dYTitle)

		self.FillBox(rectTitle, self.color)

		dYGroupName = dYTitle * 1.3
		oltbGroupName = self.Oltb(rectTitle, 'Consolas', dYGroupName, strStyle = 'B')
		rectGroupName = oltbGroupName.RectDrawText(
										self.group.strName,
										self.colorDarker,
										JH.Right,
										JV.Middle)

		rectGroupLabel = rectTitle.Copy(dX=rectGroupName.x - rectTitle.x)

		uGroupLabel = 0.65
		oltbGroupLabel = self.Oltb(rectGroupLabel, 'Calibri', dYTitle * uGroupLabel, dSMargin=oltbGroupName.dSMargin)
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
			color = self.colorLighter if (i & 1) else colorWhite
			self.FillBox(rectTeam, color)
			rectTeam.Shift(dY=dYTeam)

		rectTeam.dX = dYTeam * self.s_rSTeamName

		for i, strSeed in enumerate(sorted(self.group.mpStrSeedTeam)):
			rectTeam.y = rectHeading.y + rectHeading.dY + i * dYTeam
			team = self.group.mpStrSeedTeam[strSeed]

			oltbAbbrev = self.Oltb(rectTeam, 'Consolas', dYTeam)
			oltbAbbrev.DrawText(team.strAbbrev, colorBlack, JH.Right)

			uTeamText = 0.75
			oltbName = self.Oltb(rectTeam, 'Calibri', dYTeam * uTeamText, dSMargin=oltbAbbrev.dSMargin)
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
			oltbHeading = self.Oltb(rectHeading, 'Calibri', rectHeading.dY)
			oltbHeading.DrawText(strHeading, colorWhite, JH.Center)

		# draw border last to cover any alignment weirdness

		self.DrawBox(rectBorder, self.s_dSLineOuter, colorBlack)
		self.DrawBox(rectBorder, self.s_dSLineInner, self.color)

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
		lGroupb = [self.doc.mpStrGroupGroupb[strGroup] for strGroup in lStrGroup] 
		if self.match.stage == STAGE.Group:
			lColor = [groupb.color for groupb in lGroupb]
		else:
			lColor = [groupb.colorLighter for groupb in lGroupb]

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
			oltbTime = self.Oltb(rectTime, self.dayb.s_strFontTime, self.dayb.s_dYFontTime)
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
				oltbLabelForm = self.Oltb(rectLabelForm, self.dayb.s_strFontForm, self.dayb.s_dYFontForm)
				oltbLabelForm.DrawText(strLabel, colorBlack, JH.Center)

			# match label

			rectLabel = self.rect.Copy(y=rectHomePens.yMax, dY=self.dayb.s_dYFontLabel + self.dayb.s_dYTimeGapMax)
			oltbLabel = self.Oltb(rectLabel, 'Calibri', self.dayb.s_dYFontLabel, strStyle='B')
			oltbLabel.DrawText(self.match.strName, colorBlack, JH.Center)

		else:

			# team names

			dXTeams = self.rect.dX - (2 * self.dayb.s_dSScore) - dXLineGap
			dXTeam = dXTeams / 2.0

			rectHomeTeam = SRect(self.rect.x, yScore, dXTeam, self.dayb.s_dSScore)
			oltbHomeTeam = self.Oltb(rectHomeTeam, 'Consolas', self.dayb.s_dSScore)
			oltbHomeTeam.DrawText(self.match.strHome, colorBlack, JH.Center)

			rectAwayTeam = SRect(self.rect.xMax - dXTeam, yScore, dXTeam, self.dayb.s_dSScore)
			oltbAwayTeam = self.Oltb(rectAwayTeam, 'Consolas', self.dayb.s_dSScore)
			oltbAwayTeam.DrawText(self.match.strAway, colorBlack, JH.Center)

class CDayBlot(CBlot): # tag = dayb

	s_dX = 2.25
	s_dY = s_dX # square

	s_dSLineOuter = 0.02
	s_dSLineScore = 0.01

	s_uYDate = 0.06
	s_dYDate = s_dY * s_uYDate

	s_uYTime = 0.075
	s_strFontTime = 'Calibri'
	s_dYFontTime = s_dY * s_uYTime
	s_dYTimeGapMax = s_dYFontTime / 2.0	
	# scores are square, so we use dS

	s_uSScore = 0.147
	s_dSScore = s_dY * s_uSScore
	s_dSScoreGap = s_dSScore / 2.0

	s_dSPens = s_dSScore / 2.0
	s_dSPensNudge = 0.02

	s_dXLineForm = s_dSScore * 1.32

	s_strFontForm = s_strFontTime
	s_dYFontForm = s_dYFontTime

	s_dYFontLabel = s_dYFontTime * 1.3

	def __init__(self, doc: 'CDocument', setMatch: set[CMatch]) -> None:
		super().__init__(doc.pdf)
		self.doc = doc
		self.db = doc.db
		self.lMatch = sorted(setMatch, key=lambda match: (match.tStart, match.strHome))
		for match in self.lMatch[1:]:
			assert self.lMatch[0].tStart.date() == match.tStart.date()
		self.dYTime = CFontInstance(self.pdf, self.s_strFontTime, self.s_dYFontTime).dYCap

	def Draw(self, pos: SPoint, datePrev: Optional[datetime.date] = None) -> None:

		# BB (bruceo) only include year/month sometimes
		if datePrev and datePrev.month == self.lMatch[0].tStart.month:
			strFormat = "D"
		else:
			strFormat = "MMMM D"
		strDate = self.lMatch[0].tStart.format(strFormat)

		rectBorder = SRect(pos.x, pos.y, self.s_dX, self.s_dY)
		rectInside = rectBorder.Copy().Inset(self.s_dSLineOuter / 2.0)

		# Date

		rectDate = rectInside.Copy(dY=self.s_dYDate)
		oltbHeading = self.Oltb(rectDate, 'Calibri', rectDate.dY, strStyle='I')
		oltbHeading.DrawText(strDate, colorBlack)

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

class CPage:
	def __init__(self, doc: 'CDocument', strOrientation: str, fmt: str | tuple):
		self.doc = doc

		# unwind CDocument field so everyone doesn't have to use ".doc." everywhere.

		self.db = doc.db
		self.pdf = doc.pdf
		self.mpStrGroupGroupb = doc.mpStrGroupGroupb
		self.mpDateDayb = doc.mpDateDayb

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
				groupb = self.mpStrGroupGroupb[strGroup]
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
		# setDate: set[datetime.date] = {g_db.mpIdMatch[idMatch].tStart.date() for idMatch in lIdMatch}
		setDate: set[datetime.date] = set(doc.mpDateDayb.keys())

		lDayb: list[CDayBlot] = [doc.mpDateDayb[date] for date in sorted(setDate)]

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

class CPosterPage(CPage): # tag = benjyp
	def __init__(self, doc: 'CDocument'):
		super().__init__(doc, 'landscape', (22, 28))

		dYGroupsGap = 1.0
		cGroup = len(self.db.lStrGroup) // 2
		dXGroups = CGroupBlot.s_dX
		dYGroups = (cGroup * CGroupBlot.s_dY) + ((cGroup - 1) * dYGroupsGap)
		yGroups = (self.rect.dY - dYGroups) / 2.0
		lGroupbLeft = [self.mpStrGroupGroupb[strGroup] for strGroup in self.db.lStrGroup[:cGroup]]
		lGroupbRight = [self.mpStrGroupGroupb[strGroup] for strGroup in self.db.lStrGroup[cGroup:]]

		dateMin: datetime.date = min(self.db.mpDateSetMatch.keys())
		dateMax: datetime.date = max(self.db.mpDateSetMatch.keys())

		cDay = (dateMax - dateMin).days + 1
		cWeek = (cDay + 6) // 7
		if dateMin.weekday() != 6: # SUNDAY
			cWeek += 1

		dXCalendar = 7 * CDayBlot.s_dX
		dYCalendar = cWeek * CDayBlot.s_dY
		yCalendar = (self.rect.dY - dYCalendar) / 2.0

		dXUnused = self.rect.dX - (dXCalendar + 2 * dXGroups)
		dXGap = dXUnused / 4 # both margins and both gaps between groups and calendar

		xGroupsLeft = dXGap
		xCalendar = xGroupsLeft + dXGroups + dXGap
		xGroupsRight = xCalendar + dXCalendar + dXGap

		for xGroups, lGroupb in ((xGroupsLeft, lGroupbLeft), (xGroupsRight, lGroupbRight)):
			for iGroupb, groupb in enumerate(lGroupb):
				yGroup = yGroups + iGroupb * (CGroupBlot.s_dY + dYGroupsGap)
				groupb.Draw(SPoint(xGroups, yGroup))
			
		
		datePrev: Optional[datetime.date] = None
		for dateMatch in sorted(self.mpDateDayb):
			dayb = self.mpDateDayb[dateMatch]

			iDay = (dateMatch.weekday() + 1) % 7 # we want sunday as 0
			iWeek = (dateMatch - dateMin).days // 7

			xDay = xCalendar + iDay * CDayBlot.s_dX
			yDay = yCalendar + iWeek * CDayBlot.s_dY

			dayb.Draw(SPoint(xDay, yDay), datePrev)
			datePrev = dateMatch

class CDocument: # tag = doc
	def __init__(self, pathDb: Path) -> None:
		self.db = CDataBase(pathDb)
		self.pdf = CPdf()
		self.mpStrGroupGroupb: dict[str, CGroupBlot] = {strGroup:CGroupBlot(self, group) for strGroup, group in self.db.mpStrGroupGroup.items()}
		self.mpDateDayb: dict[datetime.date, CDayBlot] = {date:CDayBlot(self, setMatch) for date, setMatch in self.db.mpDateSetMatch.items()}

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


