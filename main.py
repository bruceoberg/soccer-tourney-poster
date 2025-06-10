# 'annotations' allow typing hints to forward reference.
#	e.g. Fn(fwd: CFwd) instead of Fn(fwd: 'CFwd')
#	when CFwd is later in file.
from __future__ import annotations

import babel.dates
import babel.numbers
import datetime
import logging
import math
import platform

from babel import Locale
from dataclasses import dataclass
from dateutil import tz
from pathlib import Path
from typing import Optional, Type, Iterable

from database import *
from bolay import *

g_pathHere = Path(__file__).parent
g_pathLocalization = g_pathHere / 'fonts' / 'localization.xlsx'
g_loc = CLocalizationDataBase(g_pathLocalization)
#g_pathTourn = g_pathHere / 'tournaments' / '2018-mens-world-cup.xlsx'
#g_pathTourn = g_pathHere / 'tournaments' / '2022-mens-world-cup.xlsx'
#g_pathTourn = g_pathHere / 'tournaments' / '2023-womens-world-cup.xlsx'
#g_pathTourn = g_pathHere / 'tournaments' / '2024-mens-euro.xlsx'
#g_pathTourn = g_pathHere / 'tournaments' / '2024-mens-copa-america.xlsx'
g_pathTourn = g_pathHere / 'tournaments' / '2025-mens-club-world-cup.xlsx'
g_tourn = CTournamentDataBase(g_pathTourn, g_loc)

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

	def __init__(self, page: CPage, group: CGroup) -> None:
		self.page = page
		self.doc = self.page.doc
		self.pdf = self.doc.pdf
		self.tourn = self.doc.tourn

		super().__init__(self.pdf)

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
		oltbGroupName = self.Oltb(rectTitle, self.page.Fontkey('group.name'), dYGroupName)
		rectGroupName = oltbGroupName.RectDrawText(
										self.group.strName,
										self.group.colors.colorDarker,
										JH.Right,
										JV.Middle)

		rectGroupLabel = rectTitle.Copy(dX=rectGroupName.x - rectTitle.x)

		uGroupLabel = 0.65
		strGroupTitle = self.page.StrTranslation('group.title')
		oltbGroupLabel = self.Oltb(rectGroupLabel, self.page.Fontkey('group.label'), dYTitle * uGroupLabel, dSMargin = oltbGroupName.dSMargin)
		oltbGroupLabel.DrawText(strGroupTitle, colorWhite, JH.Right) #, JV.Top)

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

		for i, strSeed in enumerate(sorted(self.group.mpStrSeedStrTeam)):
			rectTeam.y = rectHeading.y + rectHeading.dY + i * dYTeam
			strTeam = self.group.mpStrSeedStrTeam[strSeed]

			oltbAbbrev = self.Oltb(rectTeam, self.page.Fontkey('group.team.abbrev'), dYTeam)
			rectAbbrev = oltbAbbrev.RectDrawText(strTeam, colorBlack, JH.Right)

			rectName = rectTeam.Copy().Stretch(dXRight = -(rectAbbrev.dX + oltbAbbrev.dSMargin))

			uTeamText = 0.75
			oltbName = self.Oltb(rectName, self.page.Fontkey('group.team.name'), dYTeam * uTeamText, dSMargin = oltbAbbrev.dSMargin)
			strTeam = self.page.StrTeam(strTeam)
			oltbName.DrawText(strTeam, colorDarkSlateGrey, self.page.JhStart(), fShrinkToFit = True) #, JV.Top)

		# dividers for team/points/gf/ga

		dXRank = (rectInside.dX - rectTeam.dX) / 7.0
		dXStats = dXRank * 2

		rectPoints = rectHeading.Copy(x=rectTeam.xMax, dX=dXStats)
		rectGoalsFor = rectHeading.Copy(x=rectPoints.xMax, dX=dXStats)
		rectGoalsAgainst = rectHeading.Copy(x=rectGoalsFor.xMax, dX=dXStats)
		rectRank = rectHeading.Copy(x=rectGoalsAgainst.xMax, dX=dXRank)

		self.pdf.set_line_width(self.s_dSLineStats)
		self.pdf.set_draw_color(0) # black

		self.pdf.line(rectPoints.xMin, rectHeading.yMax, rectPoints.xMin, rectInside.yMax)
		self.pdf.line(rectGoalsFor.xMin, rectHeading.yMax, rectGoalsFor.xMin, rectInside.yMax)
		self.pdf.line(rectGoalsAgainst.xMin, rectHeading.yMax, rectGoalsAgainst.xMin, rectInside.yMax)
		self.pdf.line(rectRank.xMin, rectHeading.yMax, rectRank.xMin, rectInside.yMax)

		# heading labels

		lTuRectStr = (
			#(rectTeam, "COUNTRY"),
			(rectPoints,		self.page.StrTranslation('group.points')),
			(rectGoalsFor,		self.page.StrTranslation('group.goals-for')),
			(rectGoalsAgainst,	self.page.StrTranslation('group.goals-against')),
			(rectRank,			"\u00bb"), # RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK
		)

		for rectHeading, strHeading in lTuRectStr:
			oltbHeading = self.Oltb(rectHeading, self.page.Fontkey('group.heading'), rectHeading.dY)
			oltbHeading.DrawText(strHeading, colorWhite, JH.Center)

		if self.page.pagea.fGroupDots:
			cDotDown = 3
			cDotPtsAcross = 3
			cDotGoalsAcross = 5
			dSDot = dXStats / (2 * cDotGoalsAcross + 1)
			dYTeamDotUnused = dYTeam - (cDotDown * dSDot)
			dYTeamDotGap = dYTeamDotUnused / (cDotDown + 1)
			dYTeamDotGrid = dSDot + dYTeamDotGap
			dYTeamDotMin = dYTeamDotGap

			for iTeam in range(len(self.group.mpStrSeedStrTeam)):
				yTeam = rectHeading.yMax + iTeam * dYTeam

				for xStat, cDotAcross in ((rectPoints.xMin, cDotPtsAcross), (rectGoalsFor.xMin, cDotGoalsAcross), (rectGoalsAgainst.xMin, cDotGoalsAcross)):
					dXStatDotUnused = dXStats - (cDotAcross * dSDot)
					dXStatDotGap = dXStatDotUnused / (cDotAcross + 1)
					dXStatDotGrid = dSDot + dXStatDotGap
					dXStatDotMin = dXStatDotGap

					for col in range(cDotAcross):
						for row in range(cDotDown):
							xDot = xStat + dXStatDotMin + dXStatDotGrid * col
							yDot = yTeam + dYTeamDotMin + dYTeamDotGrid * row

							with self.pdf.local_context(fill_opacity=0.05):
								self.pdf.set_fill_color(0) # black
								self.pdf.rect(xDot, yDot, dSDot, dSDot, style='F')


		# draw border last to cover any alignment weirdness

		if self.page.pagea.fMainBorders:

			self.DrawBox(rectBorder, self.s_dSLineOuter, colorBlack)
			self.DrawBox(rectBorder, self.s_dSLineInner, self.group.colors.color)

class CMatchBlot(CBlot): # tag = dayb
	def __init__(self, dayb: CDayBlot, match: CMatch, rect: SRect) -> None:
		super().__init__(dayb.pdf)
		self.doc = dayb.doc
		self.tourn = dayb.tourn
		self.page = dayb.page
		self.dayb = dayb
		self.match = match
		self.rect = rect
		self.fElimination = match.stage != STAGE.Group

		self.dYInfo = dayb.dYTime + dayb.s_dSScore

		if self.fElimination and not self.page.pagea.fResults:
			self.dYInfo += self.dayb.s_dYFontLabel + (self.dayb.s_dSPens / 2.0) - self.dayb.s_dSPensNudge

		dYGaps = (self.rect.dY - self.dYInfo)
		dYTimeGap = min(self.dayb.s_dYTimeGapMax, dYGaps / 3.0)
		self.dYOuterGap = (dYGaps - dYTimeGap) / 2.0
		# self.dYTimeAndGap may be cleared if we coalesce times
		self.dYTimeAndGap = self.dayb.dYTime + dYTimeGap

	def DrawFill(self) -> None:

		if self.match.stage == STAGE.Final:
			return

		if self.match.stage == STAGE.Third and isinstance(self.dayb, CElimBlot):
			return

		lStrGroup = self.match.lStrGroup if self.match.lStrGroup else self.tourn.lStrGroup
		lGroup = [self.tourn.mpStrGroupGroup[strGroup] for strGroup in lStrGroup]
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
		elif self.match.stage == self.tourn.stageElimFirst:
			rectLeft = self.rect.Copy(dX=self.rect.dX / 2.0)
			lRc.append(SRectColor(rectLeft, lColor[0]))
			rectRight = rectLeft.Copy().Shift(dX=rectLeft.dX)

			if len(lColor) == 2:
				lRc.append(SRectColor(rectRight, lColor[1]))
			else:
				assert len(lColor) > 2
				rectStripe = rectRight.Copy(dX=rectRight.dX / (len(lColor) - 1))
				for color in lColor[1:]:
					lRc.append(SRectColor(rectStripe, color))
					rectStripe = rectStripe.Copy().Shift(dX=rectStripe.dX)
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

			strTime = self.page.StrTimeDisplay(self.match)
			rectTime = SRect(self.rect.x, yTime, self.rect.dX, self.dayb.dYTime)
			oltbTime = self.Oltb(rectTime, self.page.Fontkey('match.time'), self.dayb.s_dYFontTime)
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

		haloaScore = SHaloArgs(colorLightGrey, 0.1)

		if self.page.pagea.fResults and self.match.scoreHome != -1:
			oltbHomeScore = self.Oltb(rectHomeBox, self.page.Fontkey('match.score'), self.dayb.s_dSScore)
			oltbHomeScore.DrawText(str(self.match.scoreHome), colorBlack, JH.Center, haloa = haloaScore)
		else:
			self.DrawBox(rectHomeBox, self.dayb.s_dSLineScore, colorBlack, colorWhite)

		xAwayBox = self.rect.x + (self.rect.dX / 2.0) + (dXLineGap / 2.0 )
		rectAwayBox = SRect(xAwayBox, yScore, self.dayb.s_dSScore, self.dayb.s_dSScore)

		if self.page.pagea.fResults and self.match.scoreAway != -1:
			oltbAwayScore = self.Oltb(rectAwayBox, self.page.Fontkey('match.score'), self.dayb.s_dSScore)
			oltbAwayScore.DrawText(str(self.match.scoreAway), colorBlack, JH.Center, haloa = haloaScore)
		else:
			self.DrawBox(rectAwayBox, self.dayb.s_dSLineScore, colorBlack, colorWhite)

		rectHomePens = SRect(rectHomeBox.xMax, rectHomeBox.yMax)
		rectHomePens.Outset(self.dayb.s_dSPens / 2)
		rectHomePens.Shift(dX=-self.dayb.s_dSPensNudge, dY=-self.dayb.s_dSPensNudge)

		rectAwayPens = SRect(rectAwayBox.xMin, rectAwayBox.yMax)
		rectAwayPens.Outset(self.dayb.s_dSPens / 2)
		rectAwayPens.Shift(dX=self.dayb.s_dSPensNudge, dY=-self.dayb.s_dSPensNudge)

		if self.page.pagea.fResults and self.match.scoreHomeTiebreaker != -1:
			assert self.match.scoreAwayTiebreaker != -1
			strTiebreaker = f'({self.match.scoreHomeTiebreaker}-{self.match.scoreAwayTiebreaker})'
			rectTiebreaker = SRect(rectHomePens.xMin, rectHomePens.yMin, rectAwayPens.xMax - rectHomePens.xMin, rectHomePens.dY)
			oltbTiebreaker = self.Oltb(rectTiebreaker, self.page.Fontkey('match.score'), rectHomePens.dY)
			oltbTiebreaker.DrawText(strTiebreaker, colorBlack, JH.Center, haloa = haloaScore)

		if self.fElimination and not self.page.pagea.fResults:

			# PK boxes

			self.DrawBox(rectHomePens, self.dayb.s_dSLineScore, colorBlack, colorWhite)
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

			# round 1 gets them otherwise honor pref

			fDrawFormLabels = self.page.pagea.fMatchNumbers or self.match.stage == self.tourn.stageElimFirst

			# elimination hint pref can turn them back on

			if fDrawFormLabels:
				strHome = self.match.strSeedHome
				strAway = self.match.strSeedAway
				dYFontForm = self.dayb.s_dYFontForm
			elif (
					self.page.pagea.fEliminationHints and
					isinstance(self.dayb, CElimBlot) and
					self.match.stage > self.tourn.stageElimFirst and
					self.match.stage < STAGE.Third
			     ):
				assert len(self.match.lIdFeeders) == 2
				matchFeedLeft = self.tourn.mpIdMatch[self.match.lIdFeeders[0]]
				matchFeedRight = self.tourn.mpIdMatch[self.match.lIdFeeders[1]]

				fDrawFormLabels = True
				strHome = ''.join(sorted(matchFeedLeft.lStrGroup))
				strAway = ''.join(sorted(matchFeedRight.lStrGroup))
				dYFontForm = self.dayb.s_dYFontForm * 0.8

			if fDrawFormLabels:

				for xLineFormMin, strLabel in ((xLineFormLeftMin, strHome), (xLineFormRightMin, strAway)):
					rectLabelForm = SRect(xLineFormMin, yLineForm, self.dayb.s_dXLineForm, dYFontForm)
					oltbLabelForm = self.Oltb(rectLabelForm, self.page.Fontkey('match.form.label'), dYFontForm)
					oltbLabelForm.DrawText(strLabel, colorBlack, JH.Center)

			# match label

			if self.page.pagea.fMatchNumbers:

				if isinstance(self.dayb, CElimBlot):
					strFontLabel = 'elim.label'
				else:
					strFontLabel = 'match.label'

				strFormatLabel = self.page.StrTranslation('match.format.label')
				strLabel = strFormatLabel.format(id=self.match.id)

				rectLabel = self.rect.Copy(y=rectHomePens.yMax, dY=self.dayb.s_dYFontLabel + self.dayb.s_dYTimeGapMax)
				oltbLabel = self.Oltb(rectLabel, self.page.Fontkey(strFontLabel), self.dayb.s_dYFontLabel)
				oltbLabel.DrawText(strLabel, colorBlack, JH.Center)

		else:

			haloaHome: Optional[SHaloArgs] = None
			haloaAway: Optional[SHaloArgs] = None

			if self.page.pagea.fResults and self.fElimination:
				groupHome = self.tourn.mpStrTeamGroup[self.match.strTeamHome]
				haloaHome = SHaloArgs(groupHome.colors.colorDarker, 0.05)
				groupAway = self.tourn.mpStrTeamGroup[self.match.strTeamAway]
				haloaAway = SHaloArgs(groupAway.colors.colorDarker, 0.05)

			# team names

			dXTeams = self.rect.dX - (2 * self.dayb.s_dSScore) - dXLineGap
			dXTeam = dXTeams / 2.0

			rectHomeTeam = SRect(self.rect.x, yScore, dXTeam, self.dayb.s_dSScore)
			oltbHomeTeam = self.Oltb(rectHomeTeam, self.page.Fontkey('match.team.abbrev'), self.dayb.s_dSScore)
			oltbHomeTeam.DrawText(self.match.strTeamHome, colorBlack, JH.Center, haloa = haloaHome)

			rectAwayTeam = SRect(self.rect.xMax - dXTeam, yScore, dXTeam, self.dayb.s_dSScore)
			oltbAwayTeam = self.Oltb(rectAwayTeam, self.page.Fontkey('match.team.abbrev'), self.dayb.s_dSScore)
			oltbAwayTeam.DrawText(self.match.strTeamAway, colorBlack, JH.Center, haloa = haloaAway)

			# group name, subtly

			if self.page.pagea.fGroupHints and self.dYTimeAndGap:
				strGroup = self.match.lStrGroup[0]
				colorGroup = self.tourn.mpStrGroupGroup[strGroup].colors.colorDarker
				oltbGroup = self.Oltb(self.rect, self.page.Fontkey('group.name'), self.dayb.s_dYFontTime, dSMargin = oltbAwayScore.dSMargin)
				oltbGroup.DrawText(strGroup, colorGroup, JH.Right, JV.Top)

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

	def __init__(self, page: CPage, tDay: arrow.Arrow, iterMatch: Optional[Iterable[CMatch]] = None) -> None:
		self.page = page
		self.doc = self.page.doc
		self.pdf = self.doc.pdf
		self.tourn = self.doc.tourn

		self.tDay = tDay

		super().__init__(self.pdf)

		if iterMatch:
			self.lMatch = sorted(iterMatch, key=lambda match: (match.tStart, match.strSeedHome))

			for match in self.lMatch:
				assert self.tDay.date() == self.page.DateDisplay(match)
		else:
			self.lMatch = []

		self.dYTime = CFontInstance(self.pdf, self.page.Fontkey('match.time'), self.s_dYFontTime).dYCap

	def Draw(self, pos: SPoint, tPrev: Optional[arrow.Arrow] = None) -> None:

		rectBorder = SRect(pos.x, pos.y, self.s_dX, self.s_dY)
		rectInside = rectBorder.Copy().Inset(self.s_dSLineOuter / 2.0)

		# Date

		strDate = self.page.StrDateForCalendar(self.tDay, tPrev)
		rectDate = rectInside.Copy(dY=self.s_dYDate)
		oltbDate = self.Oltb(rectDate, self.page.Fontkey('day.date'), rectDate.dY)
		oltbDate.DrawText(strDate, colorBlack, self.page.JhStart())

		# matchless days get a bottom border and nothing else

		if not self.lMatch:

			if self.page.pagea.fMainBorders:
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

		if self.page.pagea.fMainBorders:
			self.DrawBox(rectBorder, self.s_dSLineOuter, colorBlack)

class CElimBlot(CDayBlot): # tag = elimb

	s_dY = (CDayBlot.s_dY / 2) + (CDayBlot.s_dYTimeGapMax * 2)

	s_dYDate = CDayBlot.s_dYFontTime

	def __init__(self, page: CPage, match: CMatch) -> None:
		self.page = page
		self.doc = page.doc
		self.pdf = page.doc.pdf
		self.tourn = page.doc.tourn

		super().__init__(page, arrow.get(self.page.DateDisplay(match)), set([match]))

		self.stage = match.stage
		assert len(self.lMatch) == 1
		self.match = self.lMatch[0]

	def Draw(self, pos: SPoint) -> None:

		rectAll = SRect(pos.x, pos.y, self.s_dX, self.s_dY)

		# lay out match in our rect

		matchb = CMatchBlot(self, self.match, rectAll)

		# tweak match positioning to account for our date on top

		dYAdjust = self.s_dYDate / 2

		if not self.page.pagea.fMatchNumbers:
			dYAdjust += self.s_dYFontLabel / 2

		matchb.dYOuterGap += dYAdjust
		matchb.dYTimeAndGap += dYAdjust / 2

		matchb.DrawFill()

		# Date

		strDate = self.page.StrDateForElimination(self.match)
		rectDate = rectAll.Copy(dY = self.s_dYDate).Shift(dY = (matchb.dYOuterGap - self.s_dYDate) / 2)
		oltbDate = self.Oltb(rectDate, self.page.Fontkey('elim.date'), rectDate.dY)
		oltbDate.DrawText(strDate, colorBlack, JH.Center)

		# info

		matchb.DrawInfo()

		# draw border last to cover any alignment weirdness

		if self.page.pagea.fMainBorders and self.page.pagea.fEliminationBorders:
			try:
				colorBorder = self.page.s_mpStageColorBorder[matchb.match.stage]
			except KeyError:
				pass
			else:
				self.DrawBox(rectAll, self.s_dSLineOuter, colorBorder)

class CFinalBlot(CBlot): # tag = finalb

	s_dX = CDayBlot.s_dX * 3.0
	s_dY = CDayBlot.s_dY

	s_dYFontTitle = CDayBlot.s_dYFontLabel * 1.7
	s_dYFontDate = s_dYFontTitle * 0.66
	s_dYFontTime = s_dYFontDate
	s_dYFontForm = s_dYFontDate

	s_dYTextGap = s_dYFontTitle / 4.0

	s_dSLineScore = CDayBlot.s_dSLineOuter

	s_dSScore = CDayBlot.s_dSScore * 1.6
	s_dSScoreGap = s_dSScore

	s_dSPens = s_dSScore / 2.0
	s_dSPensNudge = 0

	s_dXLineForm = s_dSScore * 4

	def __init__(self, page: CPage) -> None:
		self.page = page
		self.doc = page.doc
		self.pdf = page.doc.pdf
		self.tourn = page.doc.tourn

		super().__init__(self.pdf)

		self.match: CMatch = self.tourn.matchFinal
		self.tDay = arrow.get(self.page.DateDisplay(self.match))

	def Draw(self, pos: SPoint) -> None:

		rectAll = SRect(pos.x, pos.y, self.s_dX, self.s_dY)

		# title

		rectTitle = rectAll.Copy(dY=self.s_dYFontTitle)
		oltbTitle = self.Oltb(rectTitle, self.page.Fontkey('final.title'), rectTitle.dY)
		strTitle = self.page.StrTranslation('stage.final').upper()
		oltbTitle.DrawText(strTitle, colorBlack, JH.Center)

		# date

		strDate = self.page.StrDateForFinal(self.match)
		rectDate = rectTitle.Copy(dY = self.s_dYFontDate).Shift(dY = rectTitle.dY + self.s_dYTextGap)
		oltbDate = self.Oltb(rectDate, self.page.Fontkey('final.date'), rectDate.dY)
		oltbDate.DrawText(strDate, colorBlack, JH.Center)

		# time

		strTime = self.page.StrTimeDisplay(self.match)
		rectTime = rectDate.Copy(dY=self.s_dYFontTime).Shift(dY = rectDate.dY + self.s_dYTextGap)
		oltbTime = self.Oltb(rectTime, self.page.Fontkey('final.time'), rectTime.dY)
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

		haloaScore = SHaloArgs(colorLightGrey, 0.1)

		if self.page.pagea.fResults and self.match.scoreHome != -1:
			oltbHomeScore = self.Oltb(rectHomeBox, self.page.Fontkey('match.score'), self.s_dSScore)
			oltbHomeScore.DrawText(str(self.match.scoreHome), colorBlack, JH.Center, haloa = haloaScore)
		else:
			self.DrawBox(rectHomeBox, self.s_dSLineScore, colorBlack, colorWhite)

		xAwayBox = rectScore.x + (rectScore.dX / 2.0) + (dXLineGap / 2.0 )
		rectAwayBox = SRect(xAwayBox, rectScore.y, self.s_dSScore, self.s_dSScore)

		if self.page.pagea.fResults and self.match.scoreAway != -1:
			oltbAwayScore = self.Oltb(rectAwayBox, self.page.Fontkey('match.score'), self.s_dSScore)
			oltbAwayScore.DrawText(str(self.match.scoreAway), colorBlack, JH.Center, haloa = haloaScore)
		else:
			self.DrawBox(rectAwayBox, self.s_dSLineScore, colorBlack, colorWhite)

		# PK boxes

		rectHomePens = SRect(rectHomeBox.xMax, rectHomeBox.yMax)
		rectHomePens.Outset(self.s_dSPens / 2)
		rectHomePens.Shift(dX=-self.s_dSPensNudge, dY=-self.s_dSPensNudge)

		rectAwayPens = SRect(rectAwayBox.xMin, rectAwayBox.yMax)
		rectAwayPens.Outset(self.s_dSPens / 2)
		rectAwayPens.Shift(dX=self.s_dSPensNudge, dY=-self.s_dSPensNudge)

		if self.page.pagea.fResults and self.match.scoreHomeTiebreaker != -1:
			assert self.match.scoreAwayTiebreaker != -1
			strTiebreaker = f'({self.match.scoreHomeTiebreaker}-{self.match.scoreAwayTiebreaker})'
			rectTiebreaker = SRect(rectHomePens.xMin, rectHomePens.yMin, rectAwayPens.xMax - rectHomePens.xMin, rectHomePens.dY)
			oltbTiebreaker = self.Oltb(rectTiebreaker, self.page.Fontkey('match.score'), rectHomePens.dY)
			oltbTiebreaker.DrawText(strTiebreaker, colorBlack, JH.Center, haloa = haloaScore)

		if self.page.pagea.fResults:

			# (full) team names

			strHome = self.page.StrTeam(self.match.strTeamHome)
			groupHome = self.tourn.mpStrTeamGroup[self.match.strTeamHome]
			haloaHome = SHaloArgs(groupHome.colors.colorLighter, 0.05)
			rectHomeTeam = SRect(rectAll.x, rectHomeBox.y, rectHomeBox.xMin - rectAll.x, rectHomeBox.dY)
			oltbHomeTeam = self.Oltb(rectHomeTeam, self.page.Fontkey('match.team.abbrev'), rectHomeBox.dY)
			oltbHomeTeam.DrawText(strHome, colorBlack, JH.Right, haloa = haloaHome)

			strAway = self.page.StrTeam(self.match.strTeamAway)
			groupAway = self.tourn.mpStrTeamGroup[self.match.strTeamAway]
			haloaAway = SHaloArgs(groupAway.colors.colorLighter, 0.05)
			rectAwayTeam = SRect(rectAwayBox.xMax, rectAwayBox.y, rectAll.xMax - rectAwayBox.xMax, rectAwayBox.dY)
			oltbAwayTeam = self.Oltb(rectAwayTeam, self.page.Fontkey('match.team.abbrev'), rectAwayBox.dY)
			oltbAwayTeam.DrawText(strAway, colorBlack, JH.Left, haloa = haloaAway)

		else:

			self.DrawBox(rectHomePens, self.s_dSLineScore, colorBlack, colorWhite)
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

			if self.page.pagea.fMatchNumbers:
				for xLineFormMin, strLabel in ((xLineFormLeftMin, self.match.strSeedHome), (xLineFormRightMin, self.match.strSeedAway)):
					rectLabelForm = SRect(xLineFormMin, yLineForm + self.s_dYTextGap / 2, self.s_dXLineForm, self.s_dYFontForm)
					oltbLabelForm = self.Oltb(rectLabelForm, self.page.Fontkey('final.form.label'), self.s_dYFontForm)
					oltbLabelForm.DrawText(strLabel, colorBlack, JH.Center)

@dataclass
class SPageArgs: # tag - pagea
	
	# NOTE (bruceo) strLocale is a two letter ISO 639 language code, or
	# one combined with a two letter ISO 3166-1 alpha-2 country code (e.g. en-gb vs en-us)
	#	https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes
	# more importantly, it's a code honored by arrow
	#	https://arrow.readthedocs.io/en/latest/api-guide.html#module-arrow.locales

	clsPage: Type['CPage']
	strOrientation: str = 'landscape'
	fmt: str | tuple[float, float] = (22, 28)
	strTz: str = 'US/Pacific'
	fmtCrop: Optional[str | tuple[float, float]] = (18, 27)
	strLocale: str = 'en_US'
	strVariant: str = ''
	fMainBorders: bool = True
	fEliminationBorders: bool = True
	fMatchNumbers: bool = False
	fGroupHints: bool = False
	fEliminationHints: bool = True
	fGroupDots: bool = True
	fResults: bool = False

def StrPatternDateMMMMEEEEd(locale: Locale) -> str:
	# CLDR does not provide a skeleton for 'MMMMEEEEd' (for getting 'Sunday, November 1' in any language).
	# so for western languages (e.g. not arabic/farsi/japanese), we build 'MMMMEEEEd' from the pattern provided by 'MMMEd'.

	dtfMMMEd = locale.datetime_skeletons['MMMEd']

	if locale.language in ('ja', 'ar', 'fa'):
		return dtfMMMEd.pattern

	lStrPattern = dtfMMMEd.pattern.split("'")
	lStrPatternNew = []

	for iStr, str in enumerate(lStrPattern):
		# the pattern can have single quotes denoting literals. so skip those
		if not (iStr & 1):
			str = str.replace('E', 'EEEE', 1)
			str = str.replace('MMM', 'MMMM', 1)

		lStrPatternNew.append(str)

	return ''.join(lStrPatternNew)
		
class CPage:

	s_dSLineCropMarks = 0.008
	s_colorCropMarks = colorGrey

	# "darkslategray": "#2f4f4f", (47)
	# "lightgrey": "#d3d3d3", (211)
	# (211 - 47) / 3 = 41

	s_mpStageColorBorder: dict[STAGE, SColor] = {
		STAGE.Round64: ColorFromStr("#585858"),		# 47 + 41 = 88 (0x58)
		STAGE.Round32: ColorFromStr("#585858"),		
		STAGE.Round16: ColorFromStr("#585858"),		
		STAGE.Quarters: ColorFromStr("#818181"),	# 88 + 41 = 129 (0x81)
		STAGE.Semis: ColorFromStr("#aaaaaa"),		# 129 + 41 = 170 (0xaa)
	}

	def __init__(self, doc: CDocument, pagea: SPageArgs):
		self.doc = doc
		self.pagea = pagea

		self.tourn = self.doc.tourn
		self.pdf = self.doc.pdf

		self.strOrientation = self.pagea.strOrientation
		self.fmt = self.pagea.fmt
		self.fmtCrop = self.pagea.fmtCrop
		self.strTz = self.pagea.strTz
		self.tzinfo = tz.gettz(self.strTz)
		self.strLocale = self.pagea.strLocale
		self.locale = Locale.parse(self.strLocale)
		self.strDateMMMMEEEEd = StrPatternDateMMMMEEEEd(self.locale)

		self.BuildDisplayDatesTimes()

		self.mpDateSetMatch: dict[datetime.date, set[CMatch]] = self.MpDateSetMatch()

		self.pdf.add_page(orientation=self.strOrientation, format=self.fmt)
		self.rect = SRect(0, 0, self.pdf.w, self.pdf.h)

		if tuDxDyCrop := self.pdf.TuDxDyFromOrientationFmt(self.strOrientation, self.fmtCrop):
			dX = min(self.rect.dX, tuDxDyCrop[0])
			dY = min(self.rect.dY, tuDxDyCrop[1])
			dXCropPerEdge = (self.rect.dX - dX) / 2
			dYCropPerEdge = (self.rect.dY - dY) / 2
			dSCropMarkPerEdge = min(dXCropPerEdge / 2, dYCropPerEdge / 2)

			self.rectInside = self.rect.Copy().Stretch(
												dXLeft = dXCropPerEdge,
												dYTop = dYCropPerEdge,
												dXRight = -dXCropPerEdge,
												dYBottom = -dYCropPerEdge)


			self.rectCropMarks = self.rectInside.Copy().Outset(dSCropMarkPerEdge)
		else:
			self.rectInside = self.rect
			self.rectCropMarks = self.rect

	def StrTranslation(self, strKey: str) -> str:
		return self.tourn.StrTranslation(strKey, self.strLocale)

	def StrTeam(self, strKey: str) -> str:
		return self.tourn.StrTeam(strKey, self.strLocale)

	def Fontkey(self, strFont: str) -> SFontKey:
		strTtf = self.StrTranslation(self.doc.s_strKeyPrefixFonts + strFont)

		return SFontKey(strTtf, '')

	def FIsLeftToRight(self) -> bool:
		return self.locale.character_order == 'left-to-right'

	def JhStart(self) -> JH:
		return JH.Left if self.locale.character_order == 'left-to-right' else JH.Right

	def JhEnd(self) -> JH:
		return JH.Right if self.locale.character_order == 'left-to-right' else JH.Left

	def StrDateRangeForHeader(self, tMin: arrow.Arrow, tMax: arrow.Arrow) -> str:
		if tMin.year != tMax.year:
			strDateFmt = 'yMMM' # multi year: month + year to month + year
		else:
			strDateFmt = 'MMMd' # single year: month + day to month + day
		strDateRange = babel.dates.format_interval(tMin.datetime, tMax.datetime, strDateFmt, locale=self.locale)
		strDateRange = strDateRange.translate({ord(ch):' ' for ch in '\u00a0\u2009\u202f'}) # our fonts don't have these weirdo spaces
		return strDateRange

	def StrDateForCalendar(self, tDate: arrow.Arrow, tPrev: Optional[arrow.Arrow] = None) -> str:
		# NOTE (bruceo) only include month sometimes when it is changing
		#	these formats are CLDR patterns (https://cldr.unicode.org/translation/date-time/date-time-patterns)
		#	as supported by babel.dates.format_skeleton()

		if tPrev and tPrev.month == tDate.month:
			strFormat = "d"
		else:
			strFormat = "MMMMd"

		return babel.dates.format_skeleton(strFormat, tDate.datetime, locale=self.locale)
		
	def StrDateForElimination(self, match: CMatch) -> str:
		return babel.dates.format_skeleton('MMMEd', self.DateDisplay(match), locale=self.locale)

	def StrDateForFinal(self, match: CMatch) -> str:
		return babel.dates.format_date(self.DateDisplay(match), format=self.strDateMMMMEEEEd, locale=self.locale)
	
	def BuildDisplayDatesTimes(self):

		self.mpIdDateDisplay: dict[int, datetime.date] = {}
		self.mpIdStrTimeDisplay: dict[int, str] = {}

		for match in self.tourn.mpIdMatch.values():
			tTimeTz = match.tStart.to(self.tzinfo)
			dateDisplay = tTimeTz.date()
			strTime = babel.dates.format_time(tTimeTz.time(), 'short', locale=self.locale)

			if match.stage == STAGE.Group and match.tStart.day != tTimeTz.day:
				# for timezones behind the UTC start time, return the date in that timezone.
				# for those ahead, return the UTC date, and StrTimeDidplay() will display a weirdo 48hr time.
				# BB (bruceo) may need to do this on a per-locale basis. japan knows about 48hr times, but do others?
				dSec = tTimeTz.utcoffset().total_seconds()
				if dSec > 0:
					dateDisplay = match.tStart.date()
					strHour, strRest = strTime.split(':', 1)
					hourNew = 24 if tTimeTz.hour == 0 else int(strHour) + 24 # correct for 12am not always being "00"
					strTime = f'{hourNew}:{strRest}'
			
			# hacks that probably violate the CLDR

			strTime = strTime.lower()
			strTime = strTime.translate({ord(ch):'' for ch in ' \u00a0\u2009\u202f'}) # remove spaces for very narrow times, please

			self.mpIdDateDisplay[match.id] = dateDisplay
			self.mpIdStrTimeDisplay[match.id] = strTime

	def DateDisplay(self, match: CMatch) -> datetime.date:
		return self.mpIdDateDisplay[match.id]

	def StrTimeDisplay(self, match: CMatch) -> str:
		return self.mpIdStrTimeDisplay[match.id]

	def MpDateSetMatch(self) -> dict[datetime.date, set[CMatch]]:
		""" map dates to matches. """

		mpDateSetMatch: dict[datetime.date, set[CMatch]] = {}

		for match in self.tourn.mpIdMatch.values():
			mpDateSetMatch.setdefault(self.DateDisplay(match), set()).add(match)

		return mpDateSetMatch


	def DrawCropLines(self) -> None:
		if self.rectInside is self.rect:
			return

		self.pdf.set_line_width(self.s_dSLineCropMarks)
		self.pdf.set_draw_color(self.s_colorCropMarks.r, self.s_colorCropMarks.g, self.s_colorCropMarks.b)

		self.pdf.line(self.rect.xMin, 			self.rectInside.yMin,		self.rectCropMarks.xMin,	self.rectInside.yMin) 		# top
		self.pdf.line(self.rectCropMarks.xMax,	self.rectInside.yMin,		self.rect.xMax,				self.rectInside.yMin)

		self.pdf.line(self.rect.xMin,			self.rectInside.yMax,		self.rectCropMarks.xMin,	self.rectInside.yMax) 		# bottom
		self.pdf.line(self.rectCropMarks.xMax,	self.rectInside.yMax,		self.rect.xMax,				self.rectInside.yMax)

		self.pdf.line(self.rectInside.xMin,		self.rect.yMin, 			self.rectInside.xMin,		self.rectCropMarks.yMin)	# left
		self.pdf.line(self.rectInside.xMin,		self.rectCropMarks.yMax,	self.rectInside.xMin,		self.rect.yMax)

		self.pdf.line(self.rectInside.xMax,		self.rect.yMin, 			self.rectInside.xMax,		self.rectCropMarks.yMin)	# right
		self.pdf.line(self.rectInside.xMax,		self.rectCropMarks.yMax,	self.rectInside.xMax,		self.rect.yMax)

class CGroupsTestPage(CPage): # gtp
	def __init__(self, doc: CDocument, pagea: SPageArgs):
		super().__init__(doc, pagea)

		dSMargin = 0.5

		dXGrid = CGroupBlot.s_dX + dSMargin
		dYGrid = CGroupBlot.s_dY + dSMargin

		for col in range(2):
			for row in range(4):
				try:
					strGroup = self.tourn.lStrGroup[col * 4 + row]
				except IndexError:
					continue
				group = self.tourn.mpStrGroupGroup[strGroup]
				groupb = CGroupBlot(self, group)
				pos = SPoint(
						dSMargin + col * dXGrid,
						dSMargin + row * dYGrid)
				groupb.Draw(pos)

class CDaysTestPage(CPage): # gtp
	def __init__(self, doc: CDocument, pagea: SPageArgs):
		super().__init__(doc, pagea)

		dSMargin = 0.25

		dXGrid = CDayBlot.s_dX + dSMargin
		dYGrid = CDayBlot.s_dY + dSMargin

		# lIdMatch = (49,57)
		# setDate: set[datetime.date] = {doc.tourn.mpIdMatch[idMatch].tStart.date() for idMatch in lIdMatch}
		setDate: set[datetime.date] = set(self.mpDateSetMatch.keys())

		lDayb: list[CDayBlot] = [CDayBlot(self, arrow.get(date), self.mpDateSetMatch.get(date)) for date in sorted(setDate)]

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

	def __init__(self, doc: CDocument, lGroupb: list[CGroupBlot], cCol: int = 0, cRow: int = 0) -> None:
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

class CHeaderBlot(CBlot): # tag = headerb

	s_dY = CDayBlot.s_dY * 0.6

	s_dYFontTitle = s_dY / 2
	s_dYFontSides = s_dYFontTitle / 2

	def __init__(self, page: CPage) -> None:
		super().__init__(page.pdf)
		self.page = page
		self.doc = page.doc

	def Draw(self, pos: SPoint) -> None:

		rectAll = SRect(pos.x, pos.y, self.page.rectInside.dX, self.s_dY)

		# fill with black, and bleed to crop marks above and to the sides

		rectBox = self.page.rectCropMarks.Copy()
		rectBox.yMax = rectAll.yMax
		self.FillBox(rectBox, colorBlack)

		# title

		oltbTitle = self.Oltb(rectAll, self.page.Fontkey('page.header.title'), self.s_dYFontTitle)
		strTitle = self.page.StrTranslation('tournament.title').upper()
		rectTitle = oltbTitle.RectDrawText(strTitle, colorWhite, JH.Center, JV.Middle)
		dSMarginSides = rectAll.yMax - rectTitle.yMax

		# dates

		tMin = arrow.get(min(self.page.mpDateSetMatch))
		tMax = arrow.get(max(self.page.mpDateSetMatch))
		strDateRange = self.page.StrDateRangeForHeader(tMin, tMax)
		strLocation = self.page.StrTranslation('tournament.location')
		strFormatDates = self.page.StrTranslation('page.format.dates-and-location')
		strDatesLocation = strFormatDates.format(dates=strDateRange, location=strLocation).upper()

		# time zone

		tTz = tMin.to(self.page.tzinfo)
		
		if self.page.pagea.strTz == 'Asia/Tehran':
			strTz = 'IRST'	# thanks arrow for not supporting iran
		else:
			strTz = tTz.format('ZZZ', self.page.strLocale)

		if strTz.startswith('+'):
			strTz = f'UTC{strTz}'
		else:
			dT = tTz.utcoffset()
			if cSec := int(dT.total_seconds()):
				if (cSec % (60*60)) == 0:
					cHour = cSec // (60*60)
					strTz += f' (UTC{cHour:+d})'
				else:
					cHour = cSec // (60*60)
					cMin = (cSec % (60*60)) // 60
					strTz += f' (UTC{cHour:+d}:{cMin:02d})'

		strLabelTimeZone = self.page.StrTranslation('page.timezone.label')
		strFormatTimeZone = self.page.StrTranslation('page.format.timezone')
		strTimeZone = strFormatTimeZone.format(label=strLabelTimeZone, timezone=strTz)

		# notes left and right

		if self.page.FIsLeftToRight():
			strNoteLeft = strDatesLocation
			strNoteRight = strTimeZone
		else:
			strNoteLeft = strTimeZone
			strNoteRight = strDatesLocation

		rectNoteLeft = rectAll.Copy().Stretch(dXLeft = self.s_dY) # yes, using height as left space
		oltbNoteLeft = self.Oltb(rectNoteLeft, self.page.Fontkey('page.header.title'), self.s_dYFontSides, dSMargin = dSMarginSides)
		oltbNoteLeft.DrawText(strNoteLeft, colorWhite, JH.Left, JV.Bottom)

		rectNoteRight = rectAll.Copy().Stretch(dXRight = -self.s_dY) # ditto
		oltbNoteRight = self.Oltb(rectNoteRight, self.page.Fontkey('page.header.title'), self.s_dYFontSides, dSMargin = dSMarginSides)
		oltbNoteRight.DrawText(strNoteRight, colorWhite, JH.Right, JV.Bottom)

class CFooterBlot(CBlot): # tag = headerb

	s_dY = CDayBlot.s_dY * 0.2

	s_dYFont = s_dY / 4

	def __init__(self, page: CPage) -> None:
		super().__init__(page.pdf)
		self.page = page
		self.doc = page.doc

	def Draw(self, pos: SPoint) -> None:

		rectAll = SRect(pos.x, pos.y, self.page.rectInside.dX, self.s_dY)

		# fill with black, and bleed to crop marks below and to the sides

		rectBox = self.page.rectCropMarks.Copy()
		rectBox.yMin = rectAll.yMin
		self.FillBox(rectBox, colorBlack)

		# credits

		rectCredits = rectAll.Copy().Stretch(dXLeft = CHeaderBlot.s_dY, dXRight = -CHeaderBlot.s_dY) # yes, using height as left space

		lStrCreditLeft: list[str] = [
			'DESIGN/CODE BY BRUCE OBERG',
			'BRUCE@OBERG.COM',
			'MADE IN PYTHON WITH FPDF2',
			'GITHUB.COM/BRUCEOBERG/SOCCER-TOURNEY-POSTER',
		]

		lStrCreditCenter: list[str] = [
			self.page.pagea.strVariant,
		]

		lStrCreditRight: list[str] = [
			'ORIGINAL DESIGN BY BENJY TOCZYNSKI',
			'BTOCZYNSKI@GMAIL.COM',
		]

		strSpaceDotSpace = ' \u2022 '

		for lStrCredit, jh in ((lStrCreditLeft, JH.Left), (lStrCreditCenter, JH.Center), (lStrCreditRight, JH.Right)):
			strCredit = strSpaceDotSpace.join(lStrCredit)
			oltbCredit = self.Oltb(rectCredits, self.page.Fontkey('page.header.title'), self.s_dYFont)
			oltbCredit.DrawText(strCredit, colorWhite, jh, JV.Middle)

class CCalendarBlot(CBlot): # tag = calb

	s_dYDayOfWeek = CDayBlot.s_dYDate * 2

	s_dYFontTitle = CDayBlot.s_dYFontTime

	def __init__(self, page: CPage, setMatch: set[CMatch]) -> None:
		self.page = page
		self.doc = page.doc
		self.pdf = page.doc.pdf
		self.tourn = page.doc.tourn

		super().__init__(self.pdf)

		# added DateDisplay for 2025 CWC... unclear if this breaks previous tourneys (prob 2023 NZ womens WC?)

		setDate: set[datetime.date] = {self.page.DateDisplay(match) for match in setMatch}

		dateMin: datetime.date = min(setDate)
		dateMax: datetime.date = max(setDate)

		# ensure dateMin/dateMax are on week boundries

		self.weekdayFirst: int = self.page.locale.first_week_day
		self.weekdayLast = (self.weekdayFirst + 6) % 7

		if dateMin.weekday() != self.weekdayFirst:
			# arrow.shift(weekday) always goes forward in time
			dateMin = arrow.get(dateMin).shift(weeks=-1).shift(weekday=self.weekdayFirst).date()

		# and always go all the way to saturday

		if dateMax.weekday() != self.weekdayLast:
			dateMax = arrow.get(dateMax).shift(weekday=self.weekdayLast).date()

		cDay: int = (dateMax - dateMin).days + 1
		assert cDay % 7 == 0
		cWeek: int = cDay // 7

		self.dX = 7 * CDayBlot.s_dX
		self.dY = self.s_dYDayOfWeek + cWeek * CDayBlot.s_dY

		# build a list of all day blots and their relative positions

		self.lTuDPosDayb: list[tuple[SPoint, CDayBlot]] = []

		for iDay, tDay in enumerate(arrow.Arrow.range('day', arrow.get(dateMin), arrow.get(dateMax))):
			setMatchDate = self.page.mpDateSetMatch.get(tDay.date(), set()).intersection(setMatch)

			dayb = CDayBlot(self.page, tDay, iterMatch = setMatchDate)

			iWeekday = iDay % 7
			iWeek = iDay // 7

			if not self.page.FIsLeftToRight():
				iWeekday = 6 - iWeekday

			dPosDayb = SPoint(iWeekday * CDayBlot.s_dX, iWeek * CDayBlot.s_dY)
			self.lTuDPosDayb.append((dPosDayb, dayb))

	def Draw(self, pos: SPoint) -> None:

		# days of week

		mpIdayStrDayOfWeek = babel.dates.get_day_names('abbreviated', locale=self.page.locale)

		if self.page.FIsLeftToRight():
			rectDayOfWeek = SRect(x = pos.x, y = pos.y, dX = CDayBlot.s_dX, dY = self.s_dYDayOfWeek)
			dXShift = CDayBlot.s_dX
		else:
			rectDayOfWeek = SRect(x = pos.x + self.dX - CDayBlot.s_dX, y = pos.y, dX = CDayBlot.s_dX, dY = self.s_dYDayOfWeek)
			dXShift = -CDayBlot.s_dX

		for iDay in range(7):
			strDayOfWeek = mpIdayStrDayOfWeek[(iDay + self.weekdayFirst) % 7]
			oltbDayOfWeek = self.Oltb(rectDayOfWeek, self.page.Fontkey('calendar.day-of-week'), rectDayOfWeek.dY)
			oltbDayOfWeek.DrawText(strDayOfWeek, colorBlack, JH.Center)
			rectDayOfWeek.Shift(dX = dXShift)

		# days

		rectDays = SRect(x = pos.x, y = pos.y, dX = self.dX, dY = self.dY).Stretch(dYTop = rectDayOfWeek.dY)

		tPrev: Optional[arrow.Arrow] = None
		for dPosDayb, dayb in self.lTuDPosDayb:

			posDayb = SPoint(rectDays.x + dPosDayb.x, rectDays.y + dPosDayb.y)

			dayb.Draw(posDayb, tPrev)

			tPrev = dayb.tDay

		# border

		if self.page.pagea.fMainBorders:
			self.DrawBox(rectDays, CDayBlot.s_dSLineOuter, colorBlack)

	def DrawHeading(self, pos: SPoint) -> None:

		# heading

		rectAll = SRect(x = pos.x, y = pos.y, dX = self.dX, dY = self.dY)
		rectTitleText = SRect(rectAll.x, rectAll.y - (self.s_dYFontTitle * 2), rectAll.dX, self.s_dYFontTitle)
		oltbTitleText = self.Oltb(rectTitleText, self.page.Fontkey('elim.stage'), rectTitleText.dY)
		strTitleText = self.page.StrTranslation('stage.group').upper()
		rectTitleTextDrawn = oltbTitleText.RectDrawText(strTitleText, colorLightGrey, JH.Center)

		yTitleTextMiddle = rectTitleTextDrawn.yMin + rectTitleTextDrawn.dY / 2 # middle of text
		dSTitleGap = (rectAll.yMin - yTitleTextMiddle) / 2

		xLeftMin = rectTitleText.xMin
		xLeftMax = rectTitleTextDrawn.xMin - dSTitleGap

		xRightMin = rectTitleTextDrawn.xMax + dSTitleGap
		xRightMax = rectTitleText.xMax

		self.pdf.set_line_width(CGroupBlot.s_dSLineStats)
		self.pdf.set_draw_color(0) # black

		self.pdf.line(xLeftMin, yTitleTextMiddle, xLeftMax, yTitleTextMiddle)
		self.pdf.line(xRightMin, yTitleTextMiddle, xRightMax, yTitleTextMiddle)

		# self.pdf.line(xLeftMin, yTitleTextMiddle, xLeftMin, yTitleTextMiddle + dSTitleGap)
		# self.pdf.line(xRightMax, yTitleTextMiddle, xRightMax, yTitleTextMiddle + dSTitleGap)

class CBracketBlot(CBlot): # tag = bracketb

	s_dXStageGap = CElimBlot.s_dX / 8
	s_dYStageGap = CElimBlot.s_dY / 8

	s_dYFontStage = CElimBlot.s_dYDate

	def __init__(self, page: CPage, setMatch: set[CMatch]) -> None:
		self.page = page
		self.doc = page.doc
		self.pdf = page.doc.pdf
		self.tourn = page.doc.tourn

		super().__init__(self.pdf)

		lStage: list[STAGE] = list(sorted(set([match.stage for match in setMatch])))
		mpStageCRow: dict[STAGE, int] = {stage:len(self.tourn.mpStageSetMatch[stage].intersection(setMatch)) // 2 for stage in lStage}

		self.cCol: int = len(lStage) * 2
		self.cRow: int = max(mpStageCRow.values())

		self.dX = self.cCol * CElimBlot.s_dX + (self.cCol - 1) * self.s_dXStageGap
		self.dY = self.cRow * CElimBlot.s_dY + (self.cRow - 1) * self.s_dYStageGap

		# figure out offsets for bracket layout

		dXGrid = CElimBlot.s_dX + self.s_dXStageGap
		dYGrid = CElimBlot.s_dY + self.s_dYStageGap

		mpColX: dict[int, float] = {col : col * dXGrid for col in range(self.cCol)}

		mpStageRowY: dict[tuple[STAGE, int], float] = {}
		yElimbGridMax = (self.dY - CElimBlot.s_dY) / 2
		dYElimbGridPerStage = yElimbGridMax / (len(lStage) - 1)

		for iStage, (stage, cRowStage) in enumerate(mpStageCRow.items()):
			if cRowStage >= self.cRow:
				dYStageMin = 0
				dYGridStage = dYGrid
			else:
				dYStageMin = iStage * dYElimbGridPerStage

				if cRowStage > 1:
					dYGridBlots = cRowStage * CElimBlot.s_dY
					dYGridUnused = self.dY - (dYGridBlots + 2 * dYStageMin)
					dYMarginGap = dYGridUnused / (cRowStage - 1)
					dYGridStage = dYMarginGap + CElimBlot.s_dY
				else:
					dYGridStage = 0

			for row in range(cRowStage):
				mpStageRowY[(stage, row)] = dYStageMin + row * dYGridStage

		# allot blots to rows and columns

		setMatchElimLeft = self.tourn.setMatchFirst if self.page.FIsLeftToRight() else self.tourn.setMatchSecond

		self.lTuXYElimb: list[tuple[float, float, CElimBlot]] = []
		mpStageLRect: dict[STAGE, list[SRect]] = {}

		for colLeft, stage in enumerate(lStage):
			setMatch = self.tourn.mpStageSetMatch[stage]
			setMatchLeft = setMatch.intersection(setMatchElimLeft)
			setMatchRight = setMatch - setMatchLeft
			tuTuColSetMatchCol = ((colLeft, setMatchLeft), (self.cCol-(1+colLeft), setMatchRight))
			for col, setMatchCol in tuTuColSetMatchCol:
				x = mpColX[col]
				for row, matchCol in enumerate(sorted(setMatchCol, key=lambda match: match.tuIdFed)):
					y = mpStageRowY[(stage, row)]
					elimb = CElimBlot(self.page, matchCol)
					self.lTuXYElimb.append((x, y, elimb))
					rectElimb = SRect(x, y, elimb.s_dX, elimb.s_dY)
					mpStageLRect.setdefault(stage, []).append(rectElimb)

		if self.tourn.matchThird:
			elimbThird = CElimBlot(self.page, self.tourn.matchThird)

			xThird = (self.dX - elimbThird.s_dX) / 2

			# add extra space for small bracket with a third place match

			if lStage[0] == STAGE.Quarters:
				yThird = self.dY
				self.dY += elimbThird.s_dY
			else:
				yThird = (self.dY - elimbThird.s_dY)

			self.lTuXYElimb.append((xThird, yThird, elimbThird))

			rectElimbThird = SRect(xThird, yThird, elimbThird.s_dX, elimbThird.s_dY)
			mpStageLRect.setdefault(STAGE.Third, []).append(rectElimbThird)

		self.mpStageTuRectStr: dict[STAGE, tuple[SRect, str]] = {}

		for stage, lRect in mpStageLRect.items():
			rectStage = lRect[0]
			strKey = 'stage.' + stage.name.lower()
			strStage = self.page.StrTranslation(strKey).upper()
			for rect in lRect[1:]:
				# BB (bruceo) put this in SRect
				rectStage.xMin = min(rectStage.xMin, rect.xMin)
				rectStage.yMin = min(rectStage.yMin, rect.yMin)
				rectStage.xMax = max(rectStage.xMax, rect.xMax)
				rectStage.yMax = max(rectStage.yMax, rect.yMax)

			self.mpStageTuRectStr[stage] = (rectStage, strStage)

	def Draw(self, pos: SPoint) -> None:

		for x, y, elimb in self.lTuXYElimb:

			posDayb = SPoint(pos.x + x, pos.y + y)

			elimb.Draw(posDayb)

		for stage, (rectStageLocal, strStage) in self.mpStageTuRectStr.items():

			rectStageGlobal = rectStageLocal.Copy().Shift(dX = pos.x, dY = pos.y)
			rectStageText = SRect(rectStageGlobal.x, rectStageGlobal.y - (self.s_dYFontStage * 2), rectStageGlobal.dX, self.s_dYFontStage)

			if stage == STAGE.Third:
				rectStageText.Shift(dY = self.s_dYFontStage)

			oltbStageText = self.Oltb(rectStageText, self.page.Fontkey('elim.stage'), rectStageText.dY)
			rectStageTextDrawn = oltbStageText.RectDrawText(strStage.upper(), colorLightGrey, JH.Center)

			try:
				colorBorder = self.page.s_mpStageColorBorder[stage]
			except KeyError:
				pass
			else:

				yStageTextMiddle = rectStageTextDrawn.yMin + rectStageTextDrawn.dY / 2 # middle of text
				dSStageGap = (rectStageGlobal.yMin - yStageTextMiddle) / 2

				xLeftMin = rectStageText.xMin + CElimBlot.s_dX / 2
				xLeftMax = rectStageTextDrawn.xMin - dSStageGap

				xRightMin = rectStageTextDrawn.xMax + dSStageGap
				xRightMax = rectStageText.xMax - (CElimBlot.s_dX / 2)

				self.pdf.set_line_width(CGroupBlot.s_dSLineStats)
				self.pdf.set_draw_color(colorBorder.r, colorBorder.g, colorBorder.b)

				self.pdf.line(xLeftMin, yStageTextMiddle, xLeftMax, yStageTextMiddle)
				self.pdf.line(xRightMin, yStageTextMiddle, xRightMax, yStageTextMiddle)

				self.pdf.line(xLeftMin, yStageTextMiddle, xLeftMin, yStageTextMiddle + dSStageGap)
				self.pdf.line(xRightMax, yStageTextMiddle, xRightMax, yStageTextMiddle + dSStageGap)

class CCalOnlyPage(CPage): # tag = calonlyp
	def __init__(self, doc: CDocument, pagea: SPageArgs):
		super().__init__(doc, pagea)

		cGroupHalf = len(self.tourn.lStrGroup) // 2

		lGroupbLeft = [CGroupBlot(self, self.tourn.mpStrGroupGroup[strGroup]) for strGroup in self.tourn.lStrGroup[:cGroupHalf]]
		gsetbLeft = CGroupSetBlot(doc, lGroupbLeft, cCol = 1)

		lGroupbRight = [CGroupBlot(self, self.tourn.mpStrGroupGroup[strGroup]) for strGroup in self.tourn.lStrGroup[cGroupHalf:]]
		gsetbRight = CGroupSetBlot(doc, lGroupbRight, cCol = 1)

		setMatchCalendar = self.tourn.setMatchGroup | self.tourn.setMatchElimination

		if self.tourn.matchThird:
			setMatchCalendar.add(self.tourn.matchThird)

		calb = CCalendarBlot(self, setMatchCalendar)
		finalb = CFinalBlot(self)

		headerb = CHeaderBlot(self)
		rectHeader = self.rectInside.Copy().Set(dY=headerb.s_dY)

		footerb = CFooterBlot(self)
		rectFooter = self.rectInside.Copy().Stretch(dYTop = (self.rectInside.dY - footerb.s_dY))

		rectInside = self.rectInside.Copy()
		rectInside.yMin = rectHeader.yMax
		rectInside.yMax = rectFooter.yMin

		dXUnused = rectInside.dX - (calb.dX + gsetbLeft.dX + gsetbRight.dX)
		dXGap = dXUnused / 4.0 # both margins and both gaps between groups and calendar. same gap vertically for calendar/final

		dYUnused = rectInside.dY - (calb.dY + finalb.s_dY)
		dYGap = dYUnused / 3.0

		assert gsetbLeft.dY == gsetbRight.dY
		yGroups = rectInside.y + (rectInside.dY - gsetbLeft.dY) / 2.0

		xGroupsLeft = rectInside.x + dXGap

		gsetbLeft.Draw(SPoint(xGroupsLeft, yGroups))

		xCalendar = xGroupsLeft + gsetbLeft.dX + dXGap
		yCalendar = rectInside.y + dYGap

		calb.Draw(SPoint(xCalendar, yCalendar))

		xFinal = (rectInside.dX - finalb.s_dX) / 2.0
		yFinal = yCalendar + calb.dY + dYGap

		finalb.Draw(SPoint(xFinal, yFinal))

		xGroupsRight = xCalendar + calb.dX + dXGap

		gsetbRight.Draw(SPoint(xGroupsRight, yGroups))

		headerb.Draw(rectHeader.posMin)
		footerb.Draw(rectFooter.posMin)

		self.DrawCropLines()

class CCalElimPage(CPage): # tag = calelimp
	def __init__(self, doc: CDocument, pagea: SPageArgs):
		super().__init__(doc, pagea)

		setMatchCalendar: set[CMatch] = self.tourn.mpStageSetMatch[STAGE.Group]
		lSetMatchBracket: list[set[CMatch]] = [setMatch for stage, setMatch in self.tourn.mpStageSetMatch.items() if stage != STAGE.Group]
		setMatchBracket: set[CMatch] = set().union(*lSetMatchBracket)

		assert len(self.tourn.lStrGroup) % 2 == 0
		cGroupHalf = len(self.tourn.lStrGroup) // 2

		if self.FIsLeftToRight():
			lStrGroupLeft = self.tourn.lStrGroup[:cGroupHalf]
			lStrGroupRight = self.tourn.lStrGroup[cGroupHalf:]
		else:
			lStrGroupLeft = self.tourn.lStrGroup[cGroupHalf:]
			lStrGroupRight = self.tourn.lStrGroup[:cGroupHalf]

		lGroupbLeft = [CGroupBlot(self, self.tourn.mpStrGroupGroup[strGroup]) for strGroup in lStrGroupLeft]
		gsetbLeft = CGroupSetBlot(self.doc, lGroupbLeft, cCol = 1)

		lGroupbRight = [CGroupBlot(self, self.tourn.mpStrGroupGroup[strGroup]) for strGroup in lStrGroupRight]
		gsetbRight = CGroupSetBlot(self.doc, lGroupbRight, cCol = 1)

		calb = CCalendarBlot(self, setMatchCalendar)

		bracketb = CBracketBlot(self, setMatchBracket)

		finalb = CFinalBlot(self)

		headerb = CHeaderBlot(self)
		rectHeader = self.rectInside.Copy().Set(dY=headerb.s_dY)

		footerb = CFooterBlot(self)
		rectFooter = self.rectInside.Copy().Stretch(dYTop = (self.rectInside.dY - footerb.s_dY))

		rectInside = self.rectInside.Copy()
		rectInside.yMin = rectHeader.yMax
		rectInside.yMax = rectFooter.yMin

		dXUnused = rectInside.dX - (calb.dX + gsetbLeft.dX + gsetbRight.dX)
		dXGap = dXUnused / 4.0 # both margins and both gaps between groups and calendar. same gap vertically for calendar/final

		dYUnused = rectInside.dY - (calb.dY + bracketb.dY + finalb.s_dY)
		dYGap = dYUnused / 4.0

		assert gsetbLeft.dY == gsetbRight.dY
		yGroups = rectInside.y + (rectInside.dY - gsetbLeft.dY) / 2.0

		xGroupsLeft = rectInside.x + dXGap

		gsetbLeft.Draw(SPoint(xGroupsLeft, yGroups))

		xCalendar = xGroupsLeft + gsetbLeft.dX + dXGap
		yCalendar = rectInside.y + dYGap

		calb.Draw(SPoint(xCalendar, yCalendar))
		calb.DrawHeading(SPoint(xCalendar, yCalendar))

		xBracket = rectInside.x + (rectInside.dX - bracketb.dX) / 2
		yBracket = yCalendar + calb.dY + dYGap

		bracketb.Draw(SPoint(xBracket, yBracket))

		xFinal = rectInside.x + (rectInside.dX - finalb.s_dX) / 2.0
		yFinal = yBracket + bracketb.dY + dYGap

		finalb.Draw(SPoint(xFinal, yFinal))

		xGroupsRight = xCalendar + calb.dX + dXGap

		gsetbRight.Draw(SPoint(xGroupsRight, yGroups))

		headerb.Draw(rectHeader.posMin)
		footerb.Draw(rectFooter.posMin)

		self.DrawCropLines()

@dataclass
class SDocumentArgs: # tag = doca
	iterPagea: Iterable[SPageArgs]
	strDestDir: str = ''
	strFileSuffix: str = ''

class CDocument: # tag = doc
	s_strKeyPrefixFonts = 'fonts.'
	s_pathDirFonts = Path('fonts')

	def __init__(self, tourn: CTournamentDataBase, doca: SDocumentArgs) -> None:
		self.tourn = tourn
		self.doca = doca
		self.pdf = CPdf()

		strSubject = tourn.StrTranslation('tournament.name', 'en')
		lStrKeywords = strSubject.split() + self.tourn.pathFile.stem.split('-')
		strKeywords = ' '.join(lStrKeywords)

		self.pdf.set_title(self.tourn.pathFile.stem)
		self.pdf.set_author('bruce oberg')
		self.pdf.set_subject(strSubject)
		self.pdf.set_keywords(strKeywords)
		self.pdf.set_creator(f'python v{platform.python_version()}, fpdf2 v{fpdf.__version__}')
		self.pdf.set_lang('en')
		self.pdf.set_creation_date(arrow.now().datetime)

		# load all fonts for all languages

		setStrTtf: set[str] = set()
		setStrLocale: set[str] = {pagea.strLocale for pagea in doca.iterPagea}

		for strKey in tourn.loc.mpStrKeyStrLocaleStrText:
			if not strKey.startswith(self.s_strKeyPrefixFonts):
				continue
			for strLocale in setStrLocale:
				setStrTtf.add(tourn.StrTranslation(strKey, strLocale))

		for strTtf in setStrTtf:
			assert strTtf
			self.pdf.AddFont(strTtf, '', self.s_pathDirFonts / strTtf)

		for pagea in self.doca.iterPagea:
			pagea.clsPage(self, pagea)

		pathDirOutput = g_pathHere / self.doca.strDestDir if self.doca.strDestDir else g_pathHere
		strFile = self.tourn.pathFile.stem + '-' + self.doca.strFileSuffix if self.doca.strFileSuffix else self.tourn.pathFile.stem

		pathDirOutput.mkdir(parents=True, exist_ok=True)
		pathOutput = (pathDirOutput / strFile).with_suffix('.pdf')

		self.pdf.output(str(pathOutput))

if True:

	docaDefault = SDocumentArgs(
		strDestDir = 'playground',
		iterPagea = (
			# SPageArgs(CCalOnlyPage, fmt=(18, 27), fmtCrop=None, strVariant = 'benjy orig', fMatchNumbers = True, fEliminationHints = False, fGroupDots = False),
			SPageArgs(CCalElimPage, fmt=(20, 27), fmtCrop=None, strTz='US/Pacific'),
			SPageArgs(CCalElimPage, fmt=(20, 27), fmtCrop=None, strLocale='nl', strTz='Europe/Amsterdam'),
			SPageArgs(CCalElimPage, fmt=(20, 27), fmtCrop=None, strTz='Asia/Qatar'),
			SPageArgs(CCalElimPage, fmt=(20, 27), fmtCrop=None, strLocale='ja', strTz='Asia/Tokyo'),
			# SPageArgs(CCalElimPage, fmt=(20, 27), fmtCrop=None, strLocale='fa', strTz='Asia/Tehran'),
			SPageArgs(CCalElimPage, fmt=(20, 27), fmtCrop=None, strTz='Australia/Sydney'),
		))

	docaTests = SDocumentArgs(
		strDestDir = 'playground',
		iterPagea = (
			SPageArgs(CGroupsTestPage),
			SPageArgs(CDaysTestPage),
		))

	docaDesigns = SDocumentArgs(
		strDestDir = 'playground',
		strFileSuffix = 'designs',
		iterPagea = (
			SPageArgs(CCalOnlyPage, fmt=(18, 27), fmtCrop=None, strVariant = 'alpha', fMatchNumbers = True, fEliminationHints = False, fGroupDots = False),
			SPageArgs(CCalElimPage, fmt=(18, 27), fmtCrop=None, strVariant = 'beta', fEliminationBorders = False, fMatchNumbers = True, fEliminationHints = False, fGroupDots = False),
			SPageArgs(CCalElimPage, fmt=(18, 27), fmtCrop=None, strVariant = 'borderless', fMainBorders = False),
			SPageArgs(CCalElimPage, fmt=(18, 27), fmtCrop=None, strVariant = 'gold master'),
		))

	docaRelease = SDocumentArgs(
		#strDestDir = str(Path('releases') / (g_pathTourn.stem + '-patch1' )),
		strDestDir = str(Path('releases') / g_pathTourn.stem),
		strFileSuffix = 'all',
		iterPagea = (
			SPageArgs(CCalElimPage, fmt=(20, 27), fmtCrop=None),
			SPageArgs(CCalElimPage, strTz='US/Pacific'),
			SPageArgs(CCalElimPage, strTz='US/Mountain'),
			SPageArgs(CCalElimPage, strTz='US/Central'),
			SPageArgs(CCalElimPage, strTz='US/Eastern'),
			SPageArgs(CCalElimPage, fmt='a1', fmtCrop=None, strTz='Europe/London', strLocale='en'),
			SPageArgs(CCalElimPage, fmt='a1', fmtCrop=None, strTz='Europe/Paris', strLocale='fr'),
			SPageArgs(CCalElimPage, fmt='a1', fmtCrop=None, strTz='Europe/Rome', strLocale='it'),
			SPageArgs(CCalElimPage, fmt='a1', fmtCrop=None, strTz='Europe/Berlin', strLocale='de'),
			SPageArgs(CCalElimPage, fmt='a1', fmtCrop=None, strTz='Europe/Madrid', strLocale='es'),
			SPageArgs(CCalElimPage, fmt='a1', fmtCrop=None, strTz='Europe/Amsterdam', strLocale='nl'),
			SPageArgs(CCalElimPage, fmt='a1', fmtCrop=None, strTz='Asia/Tehran', strLocale='fa'),
			SPageArgs(CCalElimPage, fmt='a1', fmtCrop=None, strTz='Asia/Tokyo', strLocale='ja'),
			SPageArgs(CCalElimPage, fmt='a1', fmtCrop=None, strTz='Australia/Sydney', strLocale='en'),
		))

	lDocaRelease: list[SDocumentArgs] = []

	for pagea in docaRelease.iterPagea:
		
		if pagea.fmt == (20, 27) and pagea.fmtCrop == None:	# BB (bruceo) somehow glean this from the pagea more explicitly
			lStrFileSuffix = []
		else:
			lStrFileSuffix = [Locale.parse(pagea.strLocale).language.lower()]

			if pagea.strTz == 'Asia/Tehran':
				lStrFileSuffix.append('irst')	# thanks arrow for not supporting iran
			else:
				tTz = arrow.utcnow().to(tz.gettz(pagea.strTz))
				strTz = tTz.format('ZZZ') # GMT, PST, etc
				lStrFileSuffix.append(strTz.lower())


		strFileSuffix = '-'.join(lStrFileSuffix)

		lDocaRelease.append(SDocumentArgs(strDestDir = docaRelease.strDestDir, strFileSuffix = strFileSuffix, iterPagea=(pagea,)))

	llDocaTodo = [
		[
			#docaDefault,
			# docaTests,
			# docaDesigns,
			docaRelease,
		],
		lDocaRelease,
	]

	for lDoca in llDocaTodo:
		for doca in lDoca:
			doc = CDocument(g_tourn, doca)

else:

	pass
