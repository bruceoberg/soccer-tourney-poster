#!/usr/bin/env python3

from __future__ import annotations  # Forward refs without quotes (eg foo: CFoo, not foo: 'CFoo')

import arrow
import babel.dates
import datetime
import fpdf
import logging
import math
import platform
import sys

from babel import Locale
from dataclasses import dataclass
from dateutil import tz
from pathlib import Path
from typing import Optional, Iterable, Type, cast

from bolay import SFontKey, CFontInstance, CPdf, CBlot
from bolay import JH, JV, SPoint, SRect, RectBoundingBox, SHaloArgs
from bolay import ColorFromStr, SColor
from bolay import colorBlack, colorWhite, colorGrey, colorDarkSlateGrey, colorLightGrey

from .config import PAGEK, SPageArgs, SDocumentArgs, IterDoca
from .loc import StrTzAbbrev, StrFmtBestFit
from .versioning import g_repover
from .database import g_loc, CTournamentDataBase, CGroup, CMatch, STAGE

g_pathCode = Path(__file__).parent

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

			oltbAbbrev = self.Oltb(rectTeam, self.page.Fontkey('group.team.abbrev'), dYTeam)
			rectAbbrev = oltbAbbrev.RectDrawText(strTeam, colorBlack, self.page.JhEnd())

			if fLtR:
				rectName = rectTeam.Copy().Stretch(dXRight = -(rectAbbrev.dX + oltbAbbrev.dSMargin))
			else:
				rectName = rectTeam.Copy().Stretch(dXLeft = (rectAbbrev.dX + oltbAbbrev.dSMargin))

			uTeamText = 0.75
			oltbName = self.Oltb(rectName, self.page.Fontkey('group.team.name'), dYTeam * uTeamText, dSMargin = oltbAbbrev.dSMargin)
			strTeam = self.page.StrTeam(strTeam)
			oltbName.DrawText(strTeam, colorDarkSlateGrey, self.page.JhStart(), fShrinkToFit = True) #, JV.Top)

		# dividers for team/points/gf/ga

		dXRank = (rectInside.dX - rectTeam.dX) / 7.0
		dXStats = dXRank * 2

		if fLtR:
			rectPoints = rectHeading.Copy(x=rectTeam.xMax, dX=dXStats)
			rectGoalsFor = rectHeading.Copy(x=rectPoints.xMax, dX=dXStats)
			rectGoalsAgainst = rectHeading.Copy(x=rectGoalsFor.xMax, dX=dXStats)
			rectRank = rectHeading.Copy(x=rectGoalsAgainst.xMax, dX=dXRank)
		else:
			rectPoints = rectHeading.Copy(x=rectTeam.xMin - dXStats, dX=dXStats)
			rectGoalsFor = rectHeading.Copy(x=rectPoints.xMin - dXStats, dX=dXStats)
			rectGoalsAgainst = rectHeading.Copy(x=rectGoalsFor.xMin - dXStats, dX=dXStats)
			rectRank = rectHeading.Copy(x=rectGoalsAgainst.xMin - dXRank, dX=dXRank)

		self.pdf.set_line_width(self.s_dSLineStats)
		self.pdf.set_draw_color(0) # black

		if fLtR:
			self.pdf.line(rectPoints.xMin, rectHeading.yMax, rectPoints.xMin, rectInside.yMax)
			self.pdf.line(rectGoalsFor.xMin, rectHeading.yMax, rectGoalsFor.xMin, rectInside.yMax)
			self.pdf.line(rectGoalsAgainst.xMin, rectHeading.yMax, rectGoalsAgainst.xMin, rectInside.yMax)
			self.pdf.line(rectRank.xMin, rectHeading.yMax, rectRank.xMin, rectInside.yMax)
		else:
			self.pdf.line(rectPoints.xMax, rectHeading.yMax, rectPoints.xMax, rectInside.yMax)
			self.pdf.line(rectGoalsFor.xMax, rectHeading.yMax, rectGoalsFor.xMax, rectInside.yMax)
			self.pdf.line(rectGoalsAgainst.xMax, rectHeading.yMax, rectGoalsAgainst.xMax, rectInside.yMax)
			self.pdf.line(rectRank.xMax, rectHeading.yMax, rectRank.xMax, rectInside.yMax)

		# heading labels

		lTuRectStr = (
			#(rectTeam, "COUNTRY"),
			(rectPoints,		self.page.StrTranslation('group.points')),
			(rectGoalsFor,		self.page.StrTranslation('group.goals-for')),
			(rectGoalsAgainst,	self.page.StrTranslation('group.goals-against')),
			 # RIGHT/LEFT-POINTING DOUBLE ANGLE QUOTATION MARK
			(rectRank,			"\u00bb" if fLtR else "\u00ab"),
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

			if self.page.pagea.fResults and self.match.FHasResults():
				strTime = self.page.StrTranslation(self.tourn.StrKeyVenue(self.match.venue))
			else:
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

		haloaScore = SHaloArgs(colorBlack, 0.1)

		if self.page.pagea.fResults and self.match.scoreHome != -1:
			oltbHomeScore = self.Oltb(rectHomeBox, self.page.Fontkey('match.score'), self.dayb.s_dSScore)
			oltbHomeScore.DrawText(str(self.match.scoreHome), colorWhite, JH.Center, haloa = haloaScore)
		else:
			self.DrawBox(rectHomeBox, self.dayb.s_dSLineScore, colorBlack, colorWhite)

		xAwayBox = self.rect.x + (self.rect.dX / 2.0) + (dXLineGap / 2.0 )
		rectAwayBox = SRect(xAwayBox, yScore, self.dayb.s_dSScore, self.dayb.s_dSScore)

		if self.page.pagea.fResults and self.match.scoreAway != -1:
			oltbAwayScore = self.Oltb(rectAwayBox, self.page.Fontkey('match.score'), self.dayb.s_dSScore)
			oltbAwayScore.DrawText(str(self.match.scoreAway), colorWhite, JH.Center, haloa = haloaScore)
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
			oltbTiebreaker.DrawText(strTiebreaker, colorWhite, JH.Center, haloa = haloaScore)

		if self.fElimination and not (self.page.pagea.fResults and self.match.strTeamHome and self.match.strTeamAway):

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
					self.match.stage is not None and
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

				def TuStrFontStrLabelForm(strLabel: str) -> tuple[str, str]:
					setStrLabelChars: set[str] = { ch for ch in strLabel }
					if setStrLabelChars == self.tourn.setStrGroup:
						return ('match.form.label', '·')
					
					if not setStrLabelChars.issubset(self.tourn.setStrGroup):
						return ('match.form.label', strLabel)
					   
					if len(setStrLabelChars) <= len(self.tourn.setStrGroup) // 2:
						return ('match.form.label', strLabel)
						
					strLabelInverse = '~' + ''.join(sorted(self.tourn.setStrGroup - setStrLabelChars)) + '~'
					return ('match.form.label-inverse', strLabelInverse)

				for xLineFormMin, strLabel in ((xLineFormLeftMin, strHome), (xLineFormRightMin, strAway)):
					strFont, strLabelForm = TuStrFontStrLabelForm(strLabel)
					rectLabelForm = SRect(xLineFormMin, yLineForm, self.dayb.s_dXLineForm, dYFontForm)
					oltbLabelForm = self.Oltb(rectLabelForm, self.page.Fontkey(strFont), dYFontForm)
					oltbLabelForm.DrawText(strLabelForm, colorBlack, JH.Center)

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

			# team names

			if self.match.stage == STAGE.Third:

				# (full) team names

				strHome = self.page.StrTeam(self.match.strTeamHome)
				rectHomeTeam = SRect(self.rect.x, rectHomeBox.y, rectHomeBox.xMin - self.rect.x, rectHomeBox.dY)
				oltbHomeTeam = self.Oltb(rectHomeTeam, self.page.Fontkey('match.team.abbrev'), rectHomeBox.dY)
				oltbHomeTeam.DrawText(strHome, colorBlack, JH.Right)

				strAway = self.page.StrTeam(self.match.strTeamAway)
				rectAwayTeam = SRect(rectAwayBox.xMax, rectAwayBox.y, self.rect.xMax - rectAwayBox.xMax, rectAwayBox.dY)
				oltbAwayTeam = self.Oltb(rectAwayTeam, self.page.Fontkey('match.team.abbrev'), rectAwayBox.dY)
				oltbAwayTeam.DrawText(strAway, colorBlack, JH.Left)

			else:

				dXTeams = self.rect.dX - (2 * self.dayb.s_dSScore) - dXLineGap
				dXTeam = dXTeams / 2.0

				rectHomeTeam = SRect(self.rect.x, yScore, dXTeam, self.dayb.s_dSScore)
				oltbHomeTeam = self.Oltb(rectHomeTeam, self.page.Fontkey('match.team.abbrev'), self.dayb.s_dSScore)
				oltbHomeTeam.DrawText(self.match.strTeamHome, colorBlack, JH.Center)

				rectAwayTeam = SRect(self.rect.xMax - dXTeam, yScore, dXTeam, self.dayb.s_dSScore)
				oltbAwayTeam = self.Oltb(rectAwayTeam, self.page.Fontkey('match.team.abbrev'), self.dayb.s_dSScore)
				oltbAwayTeam.DrawText(self.match.strTeamAway, colorBlack, JH.Center)

			# group name, subtly

			if self.page.pagea.fGroupHints and self.dYTimeAndGap:
				strGroup = self.match.lStrGroup[0]
				colorGroup = self.tourn.mpStrGroupGroup[strGroup].colors.colorDarker
				oltbGroup = self.Oltb(self.rect, self.page.Fontkey('group.name'), self.dayb.s_dYFontTime, dSMargin = oltbAwayScore.dSMargin)
				oltbGroup.DrawText(strGroup, colorGroup, JH.Right, JV.Top)

class CDayBlot(CBlot): # tag = dayb

	s_dXMin = 2.25
	s_dYMin = s_dXMin # square

	s_dSLineOuter = 0.02
	s_dSLineScore = 0.01

	s_uYDate = 0.06
	s_dYDate = s_dYMin * s_uYDate

	s_uYTime = 0.075
	s_dYFontTime = s_dYMin * s_uYTime
	s_dYTimeGapMax = s_dYFontTime / 2.0
	# scores are square, so we use dS

	s_uSScore = 0.147
	s_dSScore = s_dYMin * s_uSScore
	s_dSScoreGap = s_dSScore / 2.0

	s_dSPens = s_dSScore / 2.0
	s_dSPensNudge = 0.02

	s_dXLineForm = s_dSScore * 1.32
	s_dYFontForm = s_dYFontTime

	s_dYFontLabel = s_dYFontTime * 1.3

	def __init__(self, page: CPage, tDay: arrow.Arrow, iterMatch: Optional[Iterable[CMatch]] = None) -> None:
		self.page = page
		self.tourn = page.tourn
		self.doc = page.doc
		self.pdf = page.pdf

		self.tDay = tDay

		super().__init__(self.pdf)

		if iterMatch:
			self.lMatch = sorted(iterMatch, key=lambda match: (match.tStart, match.strSeedHome))

			for match in self.lMatch:
				assert self.tDay.date() == self.page.DateDisplay(match)
		else:
			self.lMatch = []

		self.dYTime = CFontInstance(self.pdf, self.page.Fontkey('match.time'), self.s_dYFontTime).dYCap

	def Draw(self, pos: SPoint, daybl: CDayBlotList, tPrev: Optional[arrow.Arrow] = None) -> None:

		rectBorder = SRect(pos.x, pos.y, daybl.dXDayb, daybl.dYDayb)
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
			if self.page.pagea.fResults and matchbTop.match.FHasResults() and matchbTop.match.FHasResults():
				continue

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

class CDayBlotList: # tag = daybl
	def __init__(self, lDayb: list[CDayBlot]):
		self.lDayb = lDayb

		self.dXDayb = CDayBlot.s_dXMin
		self.dYDayb = CDayBlot.s_dYMin

		cMatchMax = max([len(dayb.lMatch) for dayb in lDayb])

		if cMatchMax >= 5:
			self.dXDayb *= 1.1
			self.dYDayb *= 1.3
		elif cMatchMax <= 2:
			self.dYDayb *= 0.60

class CElimBlot(CDayBlot): # tag = elimb

	s_dX = CDayBlot.s_dXMin
	s_dY = (CDayBlot.s_dYMin / 2) + (CDayBlot.s_dYTimeGapMax * 2)

	s_dYDate = CDayBlot.s_dYFontTime

	def __init__(self, page: CPage, match: CMatch) -> None:
		self.page = page
		self.tourn = page.tourn
		self.doc = page.doc
		self.pdf = page.pdf

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

		if self.page.pagea.fMainBorders and self.page.pagea.fEliminationBorders and matchb.match.stage is not None:
			try:
				colorBorder = self.page.s_mpStageColorBorder[matchb.match.stage]
			except KeyError:
				pass
			else:
				self.DrawBox(rectAll, self.s_dSLineOuter, colorBorder)

class CFinalBlot(CBlot): # tag = finalb

	s_dX = CDayBlot.s_dXMin * 3.0
	s_dY = CDayBlot.s_dYMin

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
		self.tourn = page.tourn
		self.doc = page.doc
		self.pdf = page.pdf

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

		if self.page.pagea.fResults and self.match.FHasResults():
			strTime = self.page.StrTranslation(self.tourn.StrKeyVenue(self.match.venue))
		else:
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

		haloaScore = SHaloArgs(colorBlack, 0.1)

		if self.page.pagea.fResults and self.match.scoreHome != -1:
			oltbHomeScore = self.Oltb(rectHomeBox, self.page.Fontkey('match.score'), self.s_dSScore)
			oltbHomeScore.DrawText(str(self.match.scoreHome), colorWhite, JH.Center, haloa = haloaScore)
		else:
			self.DrawBox(rectHomeBox, self.s_dSLineScore, colorBlack, colorWhite)

		xAwayBox = rectScore.x + (rectScore.dX / 2.0) + (dXLineGap / 2.0 )
		rectAwayBox = SRect(xAwayBox, rectScore.y, self.s_dSScore, self.s_dSScore)

		if self.page.pagea.fResults and self.match.scoreAway != -1:
			oltbAwayScore = self.Oltb(rectAwayBox, self.page.Fontkey('match.score'), self.s_dSScore)
			oltbAwayScore.DrawText(str(self.match.scoreAway), colorWhite, JH.Center, haloa = haloaScore)
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
			oltbTiebreaker.DrawText(strTiebreaker, colorBlack, JH.Center)

		if self.page.pagea.fResults and self.match.strTeamHome and self.match.strTeamAway:

			# (full) team names

			strHome = self.page.StrTeam(self.match.strTeamHome)
			rectHomeTeam = SRect(rectAll.x, rectHomeBox.y, rectHomeBox.xMin - rectAll.x, rectHomeBox.dY)
			oltbHomeTeam = self.Oltb(rectHomeTeam, self.page.Fontkey('match.team.abbrev'), rectHomeBox.dY)
			oltbHomeTeam.DrawText(strHome, colorBlack, JH.Right)

			strAway = self.page.StrTeam(self.match.strTeamAway)
			rectAwayTeam = SRect(rectAwayBox.xMax, rectAwayBox.y, rectAll.xMax - rectAwayBox.xMax, rectAwayBox.dY)
			oltbAwayTeam = self.Oltb(rectAwayTeam, self.page.Fontkey('match.team.abbrev'), rectAwayBox.dY)
			oltbAwayTeam.DrawText(strAway, colorBlack, JH.Left)

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
		self.pdf = doc.pdf
		self.pagea = pagea

		if pagea.strNameTourn:
			self.tourn = CTournamentDataBase.TournFromStrName(pagea.strNameTourn)
		else:
			assert(doc.tourn)
			self.tourn = cast(CTournamentDataBase, doc.tourn)

		self.strOrientation = self.pagea.strOrientation
		self.strTz = self.pagea.strTz
		tzinfoOptional = cast(datetime.tzinfo, tz.gettz(self.strTz))
		assert(tzinfoOptional is not None)
		self.tzinfo = tzinfoOptional
		self.strLocale = self.pagea.strLocale
		self.locale = Locale.parse(self.strLocale)
		self.strDateMMMMEEEEd = StrPatternDateMMMMEEEEd(self.locale)
		if self.pagea.fmt is None:
			assert(self.pagea.fmtCrop == None)
			self.fmt = StrFmtBestFit(len(self.tourn.mpStrTeamGroup), self.locale)
		else: 
			self.fmt = self.pagea.fmt
		self.fmtCrop = self.pagea.fmtCrop

		self.BuildDisplayDatesTimes()

		self.mpDateSetMatch: dict[datetime.date, set[CMatch]] = self.MpDateSetMatch()

		# with our dates set, we can calucate out short timezone name

		tMin = arrow.get(min(self.mpDateSetMatch))
		tTz = tMin.to(self.tzinfo)
		self.strTzAbbrev = StrTzAbbrev(self.strTz, tTz.datetime)

		if self.strTzAbbrev.startswith('+'):
			self.strTzHeader = f'UTC{self.strTzAbbrev}'
		else:
			dT = tTz.utcoffset()
			assert(dT)
			if cSec := int(dT.total_seconds()):
				if (cSec % (60*60)) == 0:
					cHour = cSec // (60*60)
					self.strTzHeader = f'{self.strTzAbbrev} (UTC{cHour:+d})'
				else:
					cHour = cSec // (60*60)
					cMin = (cSec % (60*60)) // 60
					self.strTzHeader = f'{self.strTzAbbrev} (UTC{cHour:+d}:{cMin:02d})'
	
		# if self.pagea.fmt is None:
		# 	print(f"{self.tourn.strName} ({str(self.locale).lower()}/{self.strTzAbbrev}): choosing {self.fmt}")

		# using "type: ignore" here because fpdf's typing stubs are known to be janky.

		self.pdf.add_page(orientation=self.strOrientation, format=self.fmt)	# type: ignore[arg-type]
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
		return g_loc.StrTranslation(strKey, self.strLocale)

	def StrTeam(self, strKey: str) -> str:
		return self.StrTranslation(self.tourn.StrKeyTeam(strKey))

	def StrTitle(self):
		tMin = arrow.get(min(self.mpDateSetMatch))
		strYear = tMin.strftime('%Y')
		strName = self.StrTranslation(self.tourn.StrKeyCompetition())
		strLabel = self.StrTranslation('page.title.results' if self.pagea.fResults else 'page.title.fixtures')
		strFormatTitle = self.StrTranslation('page.format.title')
		return strFormatTitle.format(year=strYear, name=strName, label=strLabel)

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

		# map all matches into the day that they are played in the tournament's timezone.
		# the goal here is to have same-day matches appear on the same calendar day for all
		# pages regardless of the page timezone.

		strTzTourney: str = self.tourn.StrTimezone()
		tzinfoTourney = tz.gettz(strTzTourney)
		assert(tzinfoTourney)
		mpIdDateTourney: dict[int, datetime.date] = { id: match.tStart.to(tzinfoTourney).date() for id, match in self.tourn.mpIdMatch.items() }

		# if all the matches are one day off their display dates, then reset the display dates

		fAllGroupMatchesAhead = True

		for match in self.tourn.mpIdMatch.values():
			if match.stage != STAGE.Group:
				continue
			tTimeTz = match.tStart.to(self.tzinfo)
			dateDisplay = mpIdDateTourney[match.id]
			if dateDisplay.day == tTimeTz.day:
				fAllGroupMatchesAhead = False
				break

		if fAllGroupMatchesAhead:
			mpIdDateTourneyAdjusted: dict[int, datetime.date] = {id: dateTourney + datetime.timedelta(days=1) for id, dateTourney in mpIdDateTourney.items() }
			mpIdDateTourney = mpIdDateTourneyAdjusted

		for match in self.tourn.mpIdMatch.values():
			tTimeTz = match.tStart.to(self.tzinfo)
			strTime = babel.dates.format_time(tTimeTz.time(), 'short', locale=self.locale)

			if match.stage == STAGE.Group:
				dateDisplay = mpIdDateTourney[match.id]
				if dateDisplay.day != tTimeTz.day:
					strHour, strRest = strTime.split(':', 1)
					hourNew = 24 if tTimeTz.hour == 0 else int(strHour) + 24 # correct for 12am not always being "00"
					strTime = f'{hourNew}:{strRest}'
			else:
				dateDisplay = tTimeTz.date()
			
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

		# lIdMatch = (49,57)
		# setDate: set[datetime.date] = {doc.tourn.mpIdMatch[idMatch].tStart.date() for idMatch in lIdMatch}
		setDate: set[datetime.date] = set(self.mpDateSetMatch.keys())

		daybl = CDayBlotList([CDayBlot(self, arrow.get(date), self.mpDateSetMatch.get(date)) for date in sorted(setDate)])

		dXCell = daybl.dXDayb + dSMargin
		dYCell = daybl.dYDayb + dSMargin

		for row in range(4):
			for col in range(7):
				try:
					dayb = daybl.lDayb[row * 7 + col]
				except IndexError:
					continue
				pos = SPoint(
						dSMargin + col * dXCell,
						dSMargin + row * dYCell)
				dayb.Draw(pos, daybl)

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

class CHeaderBlot(CBlot): # tag = headerb

	s_dY = CDayBlot.s_dYMin * 0.6

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
		strTitle = self.page.StrTitle()
		rectTitle = oltbTitle.RectDrawText(strTitle, colorWhite, JH.Center, JV.Middle)
		dSMarginSides = rectAll.yMax - rectTitle.yMax

		# dates

		tMin = arrow.get(min(self.page.mpDateSetMatch))
		tMax = arrow.get(max(self.page.mpDateSetMatch))
		strDateRange = self.page.StrDateRangeForHeader(tMin, tMax)
		strLocation = self.page.StrTranslation(self.page.tourn.StrKeyHost())
		strFormatDates = self.page.StrTranslation('page.format.dates-and-location')
		strDatesLocation = strFormatDates.format(dates=strDateRange, location=strLocation)

		# time zone

		strLabelTimeZone = self.page.StrTranslation('page.timezone.label')
		strFormatTimeZone = self.page.StrTranslation('page.format.timezone')
		strTimeZone = strFormatTimeZone.format(label=strLabelTimeZone, timezone=self.page.strTzHeader)

		# notes left and right

		if self.page.pagea.fResults:
			strNoteLeft = strDateRange
			strNoteRight = strLocation
		else:
			strNoteLeft = strDatesLocation
			strNoteRight = strTimeZone

		# swapping for RtL

		if not self.page.FIsLeftToRight():
			strNoteLeft, strNoteRight = strNoteRight, strNoteLeft

		rectNoteLeft = rectAll.Copy().Stretch(dXLeft = self.s_dY) # yes, using height as left space
		oltbNoteLeft = self.Oltb(rectNoteLeft, self.page.Fontkey('page.header.title'), self.s_dYFontSides, dSMargin = dSMarginSides)
		oltbNoteLeft.DrawText(strNoteLeft, colorWhite, JH.Left, JV.Bottom)

		rectNoteRight = rectAll.Copy().Stretch(dXRight = -self.s_dY) # ditto
		oltbNoteRight = self.Oltb(rectNoteRight, self.page.Fontkey('page.header.title'), self.s_dYFontSides, dSMargin = dSMarginSides)
		oltbNoteRight.DrawText(strNoteRight, colorWhite, JH.Right, JV.Bottom)

class CFooterBlot(CBlot): # tag = headerb

	s_dY = CDayBlot.s_dYMin * 0.2

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
			'BRUCE@OBERG.ORG',
			'MADE IN PYTHON WITH FPDF2',
			'GITHUB.COM/BRUCEOBERG/SOCCER-TOURNEY-POSTER',
			g_repover.StrVersionShort(),
			self.page.strLocale.lower(),
			str(self.page.fmt),
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

	s_dYFontStage = CDayBlot.s_dYFontTime
	s_dYStageLabel = s_dYFontStage * 2.0

	def __init__(self, page: CPage, setMatch: set[CMatch]) -> None:
		self.page = page
		self.tourn = page.tourn
		self.doc = page.doc
		self.pdf = page.pdf

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

		lDayb: list[CDayBlot] = []

		for tDay in arrow.Arrow.range('day', arrow.get(dateMin), arrow.get(dateMax)):
			setMatchDate = self.page.mpDateSetMatch.get(tDay.date(), set()).intersection(setMatch)
			lDayb.append(CDayBlot(self.page, tDay, iterMatch = setMatchDate))

		self.daybl = CDayBlotList(lDayb)

		self.dX = 7 * self.daybl.dXDayb
		self.dY = self.s_dYStageLabel + self.s_dYDayOfWeek + cWeek * self.daybl.dYDayb

		# build a list of all day blots and their relative positions

		self.lTuDPosDayb: list[tuple[SPoint, CDayBlot]] = []

		for iDay, dayb in enumerate(self.daybl.lDayb):
			iWeekday = iDay % 7
			iWeek = iDay // 7

			if not self.page.FIsLeftToRight():
				iWeekday = 6 - iWeekday

			dPosDayb = SPoint(iWeekday * self.daybl.dXDayb, iWeek * self.daybl.dYDayb)
			self.lTuDPosDayb.append((dPosDayb, dayb))

	def Draw(self, pos: SPoint) -> None:

		yStageTextMin = pos.y
		yDaysOfWeekMin = yStageTextMin + self.s_dYStageLabel
		yDaysMin = yDaysOfWeekMin + self.s_dYDayOfWeek
		yDaysMax = pos.y + self.dY
		dYDays = yDaysMax - yDaysMin

		# stage heading

		rectStageText = SRect(pos.x, yStageTextMin, self.dX, self.s_dYFontStage)
		oltbStageText = self.Oltb(rectStageText, self.page.Fontkey('elim.stage'), rectStageText.dY)
		strStageText = self.page.StrTranslation('stage.group').upper()
		rectStageTextDrawn = oltbStageText.RectDrawText(strStageText, colorLightGrey, JH.Center)

		yStageTextMiddle = rectStageTextDrawn.yMin + rectStageTextDrawn.dY / 2 # middle of text
		dSStageGap = (yDaysOfWeekMin - yStageTextMiddle) / 2

		xStageLineLeftMin = rectStageText.xMin
		xStageLineLeftMax = rectStageTextDrawn.xMin - dSStageGap

		xStageLineRightMin = rectStageTextDrawn.xMax + dSStageGap
		xStageLineRightMax = rectStageText.xMax

		self.pdf.set_line_width(CGroupBlot.s_dSLineStats)
		self.pdf.set_draw_color(0) # black

		self.pdf.line(xStageLineLeftMin, yStageTextMiddle, xStageLineLeftMax, yStageTextMiddle)
		self.pdf.line(xStageLineRightMin, yStageTextMiddle, xStageLineRightMax, yStageTextMiddle)

		# self.pdf.line(xLeftMin, yTitleTextMiddle, xLeftMin, yTitleTextMiddle + dSTitleGap)
		# self.pdf.line(xRightMax, yTitleTextMiddle, xRightMax, yTitleTextMiddle + dSTitleGap)

		# days of week

		mpIdayStrDayOfWeek = babel.dates.get_day_names('abbreviated', locale=self.page.locale)

		if self.page.FIsLeftToRight():
			rectDayOfWeek = SRect(x = pos.x, y = yDaysOfWeekMin, dX = self.daybl.dXDayb, dY = self.s_dYDayOfWeek)
			dXShift = self.daybl.dXDayb
		else:
			rectDayOfWeek = SRect(x = pos.x + self.dX - self.daybl.dXDayb, y = yDaysOfWeekMin, dX = self.daybl.dXDayb, dY = self.s_dYDayOfWeek)
			dXShift = -self.daybl.dXDayb

		for iDay in range(7):
			strDayOfWeek = mpIdayStrDayOfWeek[(iDay + self.weekdayFirst) % 7]
			oltbDayOfWeek = self.Oltb(rectDayOfWeek, self.page.Fontkey('calendar.day-of-week'), rectDayOfWeek.dY)
			oltbDayOfWeek.DrawText(strDayOfWeek, colorBlack, JH.Center)
			rectDayOfWeek.Shift(dX = dXShift)

		# days

		rectDays = SRect(x = pos.x, y = yDaysMin, dX = self.dX, dY = dYDays)

		tPrev: Optional[arrow.Arrow] = None
		for dPosDayb, dayb in self.lTuDPosDayb:

			posDayb = SPoint(rectDays.x + dPosDayb.x, rectDays.y + dPosDayb.y)

			dayb.Draw(posDayb, self.daybl, tPrev)

			tPrev = dayb.tDay

		# border

		if self.page.pagea.fMainBorders:
			self.DrawBox(rectDays, CDayBlot.s_dSLineOuter, colorBlack)

class CBracketBlot(CBlot): # tag = bracketb

	s_dXStageGap = CElimBlot.s_dX / 8
	s_dYStageGap = CElimBlot.s_dY / 8

	s_dYFontStage = CElimBlot.s_dYDate
	s_dYStageLabel = s_dYFontStage * 2.0

	def __init__(self, page: CPage, setMatch: set[CMatch]) -> None:
		self.page = page
		self.tourn = page.tourn
		self.doc = page.doc
		self.pdf = page.pdf

		super().__init__(self.pdf)

		lStage: list[STAGE] = list(sorted(set([match.stage for match in setMatch])))
		mpStageCRow: dict[STAGE, int] = {stage:len(self.tourn.mpStageSetMatch[stage].intersection(setMatch)) // 2 for stage in lStage}

		self.cCol: int = len(lStage) * 2
		self.cRow: int = max(mpStageCRow.values())

		dXGrid = self.cCol * CElimBlot.s_dX + (self.cCol - 1) * self.s_dXStageGap
		dYGrid = self.cRow * CElimBlot.s_dY + (self.cRow - 1) * self.s_dYStageGap

		self.dX = dXGrid
		self.dY = self.s_dYStageLabel + dYGrid				# earliest stage label pops up above grid
		self.dYMidGrid = self.s_dYStageLabel + dYGrid / 2.0	# so CCalElim can center bracket with groups

		# figure out offsets for bracket layout

		dXCell = CElimBlot.s_dX + self.s_dXStageGap
		dYCell = CElimBlot.s_dY + self.s_dYStageGap

		mpColX: dict[int, float] = {col : col * dXCell for col in range(self.cCol)}

		mpStageRowY: dict[tuple[STAGE, int], float] = {}
		dYElimbGridMax = (dYGrid - CElimBlot.s_dY) / 2
		dYElimbGridPerStage = dYElimbGridMax / (len(lStage) - 1)

		for iStage, (stage, cRowStage) in enumerate(mpStageCRow.items()):
			if cRowStage >= self.cRow:
				dYStageMin = 0
				dYGridStage = dYCell
			else:
				dYStageMin = iStage * dYElimbGridPerStage

				if cRowStage > 1:
					dYGridBlots = cRowStage * CElimBlot.s_dY
					dYGridUnused = dYGrid - (dYGridBlots + 2 * dYStageMin)
					dYMarginGap = dYGridUnused / (cRowStage - 1)
					dYGridStage = dYMarginGap + CElimBlot.s_dY
				else:
					dYGridStage = 0

			for row in range(cRowStage):
				mpStageRowY[(stage, row)] = self.s_dYStageLabel + dYStageMin + row * dYGridStage

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

			# center directly below semis, with vertical midpoint even with
			# bottom of last quarters row.

			xThird = (dXGrid - elimbThird.s_dX) / 2
			yThird = mpStageRowY[(STAGE.Quarters, 1)] + (CElimBlot.s_dY / 2)

			# small tournaments may need top push the third place match down further.
			# bottom of semis (plus margin for the label) is a hard limit.

			yThird = max(yThird, mpStageRowY[(STAGE.Semis, 0)] + CElimBlot.s_dY + 2 * self.s_dYStageLabel)

			# be honest

			self.dY = max(self.dY, yThird + CElimBlot.s_dY)

			self.lTuXYElimb.append((xThird, yThird, elimbThird))

			rectElimbThird = SRect(xThird, yThird, elimbThird.s_dX, elimbThird.s_dY)
			mpStageLRect.setdefault(STAGE.Third, []).append(rectElimbThird)

		self.mpStageTuRectStr: dict[STAGE, tuple[SRect, str]] = {}

		for stage, lRect in mpStageLRect.items():
			rectStage = RectBoundingBox(lRect)
			strKey = 'stage.' + stage.name.lower()
			strStage = self.page.StrTranslation(strKey).upper()

			self.mpStageTuRectStr[stage] = (rectStage, strStage)

	def Draw(self, pos: SPoint) -> None:

		for x, y, elimb in self.lTuXYElimb:

			posDayb = SPoint(pos.x + x, pos.y + y)

			elimb.Draw(posDayb)

		for stage, (rectStageLocal, strStage) in self.mpStageTuRectStr.items():

			rectStageGlobal = rectStageLocal.Copy().Shift(dX = pos.x, dY = pos.y)
			rectStageText = SRect(rectStageGlobal.x, rectStageGlobal.y - self.s_dYStageLabel, rectStageGlobal.dX, self.s_dYFontStage)

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

		# header/footer

		headerb = CHeaderBlot(self)
		rectHeader = self.rectInside.Copy().Set(dY=headerb.s_dY)

		footerb = CFooterBlot(self)
		rectFooter = self.rectInside.Copy().Stretch(dYTop = (self.rectInside.dY - footerb.s_dY))

		rectCanvas = self.rectInside.Copy()
		rectCanvas.yMin = rectHeader.yMax
		rectCanvas.yMax = rectFooter.yMin

		# groups on either side

		cGroupHalf = len(self.tourn.lStrGroup) // 2

		lGroupbLeft = [CGroupBlot(self, self.tourn.mpStrGroupGroup[strGroup]) for strGroup in self.tourn.lStrGroup[:cGroupHalf]]
		gsetbLeft = CGroupSetBlot(doc, lGroupbLeft, rectCanvas, cCol = 1)

		lGroupbRight = [CGroupBlot(self, self.tourn.mpStrGroupGroup[strGroup]) for strGroup in self.tourn.lStrGroup[cGroupHalf:]]
		gsetbRight = CGroupSetBlot(doc, lGroupbRight, rectCanvas, cCol = 1)

		setMatchCalendar = self.tourn.setMatchGroup | self.tourn.setMatchElimination

		if self.tourn.matchThird:
			setMatchCalendar.add(self.tourn.matchThird)

		calb = CCalendarBlot(self, setMatchCalendar)
		finalb = CFinalBlot(self)

		dXUnused = rectCanvas.dX - (calb.dX + gsetbLeft.dX + gsetbRight.dX)
		dXGap = dXUnused / 4.0 # both margins and both gaps between groups and calendar. same gap vertically for calendar/final

		dYUnused = rectCanvas.dY - (calb.dY + finalb.s_dY)
		dYGap = dYUnused / 3.0

		assert gsetbLeft.dY == gsetbRight.dY
		yGroups = rectCanvas.y + (rectCanvas.dY - gsetbLeft.dY) / 2.0

		xGroupsLeft = rectCanvas.x + dXGap

		gsetbLeft.Draw(SPoint(xGroupsLeft, yGroups))

		xCalendar = xGroupsLeft + gsetbLeft.dX + dXGap
		yCalendar = rectCanvas.y + dYGap

		calb.Draw(SPoint(xCalendar, yCalendar))

		xFinal = (rectCanvas.dX - finalb.s_dX) / 2.0
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

		# header/footer

		headerb = CHeaderBlot(self)
		rectHeader = self.rectInside.Copy().Set(dY=headerb.s_dY)

		footerb = CFooterBlot(self)
		rectFooter = self.rectInside.Copy().Stretch(dYTop = (self.rectInside.dY - footerb.s_dY))

		rectCanvas = self.rectInside.Copy()
		rectCanvas.yMin = rectHeader.yMax
		rectCanvas.yMax = rectFooter.yMin

		# groups on either side

		assert len(self.tourn.lStrGroup) % 2 == 0
		cGroupHalf = len(self.tourn.lStrGroup) // 2

		if self.FIsLeftToRight():
			lStrGroupLeft = self.tourn.lStrGroup[:cGroupHalf]
			lStrGroupRight = self.tourn.lStrGroup[cGroupHalf:]
		else:
			lStrGroupLeft = self.tourn.lStrGroup[cGroupHalf:]
			lStrGroupRight = self.tourn.lStrGroup[:cGroupHalf]

		lGroupbLeft = [CGroupBlot(self, self.tourn.mpStrGroupGroup[strGroup]) for strGroup in lStrGroupLeft]
		gsetbLeft = CGroupSetBlot(self.doc, lGroupbLeft, rectCanvas, cCol = 1)

		lGroupbRight = [CGroupBlot(self, self.tourn.mpStrGroupGroup[strGroup]) for strGroup in lStrGroupRight]
		gsetbRight = CGroupSetBlot(self.doc, lGroupbRight, rectCanvas, cCol = 1)

		assert gsetbLeft.dY == gsetbRight.dY

		# cal vs bracket matches

		setMatchCalendar: set[CMatch] = self.tourn.mpStageSetMatch[STAGE.Group]
		lSetMatchBracket: list[set[CMatch]] = [setMatch for stage, setMatch in self.tourn.mpStageSetMatch.items() if stage != STAGE.Group]
		setMatchBracket: set[CMatch] = set().union(*lSetMatchBracket)

		calb = CCalendarBlot(self, setMatchCalendar)
		bracketb = CBracketBlot(self, setMatchBracket)

		finalb = CFinalBlot(self)

		dYUnused = rectCanvas.dY - (calb.dY + bracketb.dY + finalb.s_dY)
		dYGap = dYUnused / 4.0
		fVerticalOverflow = dYGap < 0

		if fVerticalOverflow:
			dYUnused = rectCanvas.dY - (calb.dY + bracketb.dY)
			dYGap = max(0.0, dYUnused / 3.0)
			dYGapFinal = 0.0
		else:
			dYGapFinal = dYGap

		dXColumns = max(calb.dX, bracketb.dX, finalb.s_dX) + gsetbLeft.dX + gsetbRight.dX
		dXUnused = rectCanvas.dX - dXColumns
		dXGap = dXUnused / 4.0 # both margins and both gaps between groups and calendar. same gap vertically for calendar/final
		fHorizontalOverflow = dXGap < 0

		if fHorizontalOverflow:
			# paper to narrow: slide the groups below the calendar and closer to the bracket.
			dXColumns = max(bracketb.dX, finalb.s_dX) + gsetbLeft.dX + gsetbRight.dX
			dXUnused = rectCanvas.dX - dXColumns

			dYUnused = rectCanvas.dY - (calb.dY + gsetbLeft.dY + finalb.s_dY)	# NOTE bruceo: could possibly move final's up

			if dYUnused < 0:
				# try shrinking group sets vertically
				rectLayout = rectCanvas.Copy(dY = 0) # zero height to force group sets to minimum gaps
				gsetbLeft.Layout(rectLayout, cCol = 1, fAddOuterMargin = False)
				gsetbRight.Layout(rectLayout, cCol = 1, fAddOuterMargin = False)
				dYUnused = rectCanvas.dY - (calb.dY + gsetbLeft.dY + finalb.s_dY)	# NOTE bruceo: could possibly move final's up
				dYGapFinal = 0.0

			if dXUnused < 0 and dYUnused < 0:
				sys.exit(f"{self.tourn.strName}: groups don't fit. x over by {-dXUnused:0.2f}. y over by {-dYUnused:0.2f}")
			if dXUnused < 0:
				sys.exit(f"{self.tourn.strName}: groups too wide; over by {-dXUnused:0.2f}.")
			if dYUnused < 0:
				sys.exit(f"{self.tourn.strName}: groups too tall; over by {-dYUnused:0.2f}")

			dXGap = dXUnused / 4.0
			dYGap = dYUnused / 3.0
			
			yGroups = rectCanvas.y + calb.dY + 2 * dYGap

		else:
			# normal: groups to either side of vertical cal/bracket/final stack

			yGroups = rectCanvas.y + (rectCanvas.dY - gsetbLeft.dY) / 2.0

		xGroupsLeft = rectCanvas.x + dXGap
		xGroupsRight = rectCanvas.xMax - (gsetbRight.dX + dXGap)

		gsetbLeft.Draw(SPoint(xGroupsLeft, yGroups))
		gsetbRight.Draw(SPoint(xGroupsRight, yGroups))

		xCalendar = rectCanvas.x + (rectCanvas.dX - calb.dX) / 2.0
		yCalendar = rectCanvas.y + dYGap

		calb.Draw(SPoint(xCalendar, yCalendar))

		xBracket = rectCanvas.x + (rectCanvas.dX - bracketb.dX) / 2.0

		if fHorizontalOverflow:
			yBracket = yGroups + (gsetbLeft.dY / 2.0) - bracketb.dYMidGrid
		else:
			yBracket = yCalendar + calb.dY + dYGap

		bracketb.Draw(SPoint(xBracket, yBracket))

		xFinal = rectCanvas.x + (rectCanvas.dX - finalb.s_dX) / 2.0

		# backwards final y calculation deals with both the /4 and /3 cases of dYUnused above.
		# when calendar + bracket are too tall, final gets skootched inside the bracket.

		yFinal = rectCanvas.yMax - (finalb.s_dY + dYGapFinal)

		finalb.Draw(SPoint(xFinal, yFinal))

		headerb.Draw(rectHeader.posMin)
		footerb.Draw(rectFooter.posMin)

		self.DrawCropLines()

		# print(' '.join([
		# 	f"cTeam: {len(self.tourn.mpStrTeamGroup)}",
		# 	f"dX2: {gsetbLeft.dX+gsetbRight.dX+max(bracketb.dX, finalb.s_dX)+1:0.3f}",
		# 	f"dX3: {gsetbLeft.dX+gsetbRight.dX+max(calb.dX, bracketb.dX, finalb.s_dX)+1:0.3f}",
		# 	f"dY2: {headerb.s_dY+footerb.s_dY+calb.dY+bracketb.dY:0.3f}",
		# 	f"dY3: {headerb.s_dY+footerb.s_dY+calb.dY+bracketb.dY+finalb.s_dY+1:0.3f}",
		# ]))

		# print(f"cTeam: {len(self.tourn.mpStrTeamGroup)} fmt: {self.StrFmtBestFit()}")

class CDocument: # tag = doc
	s_strKeyPrefixFonts = 'fonts.'
	s_pathDirFonts = g_pathCode / 'fonts'

	s_mpPagekClsPage: dict[PAGEK, Type[CPage]] = {
		PAGEK.GroupsTest:	CGroupsTestPage,
		PAGEK.DaysTest:		CDaysTestPage,
		PAGEK.CalOnly:		CCalOnlyPage,
		PAGEK.CalElim:		CCalElimPage,
	}

	def __init__(self, doca: SDocumentArgs) -> None:
		self.doca = doca
		self.pdf = CPdf()

		if doca.strNameTourn:
			strName = doca.strNameTourn
			self.tourn = CTournamentDataBase.TournFromStrName(strName)
			strSubject = strKeywords = ' '.join(strName.split('-'))
		else:
			strName = 'collection'
			self.tourn = None
			strSubject = 'collection'
			strKeywords = ''

		self.pdf.set_title(strName)
		self.pdf.set_author('bruce oberg')
		self.pdf.set_subject(strSubject)
		self.pdf.set_keywords(strKeywords)
		self.pdf.set_creator(f'python v{platform.python_version()}, fpdf2 v{fpdf.__version__}')
		self.pdf.set_lang('en')
		self.pdf.set_creation_date(arrow.now().datetime)

		# load all fonts for all languages

		setStrTtf: set[str] = set()
		setStrLocale: set[str] = {pagea.strLocale for pagea in doca.tuPagea}

		for strKey in g_loc.mpStrKeyStrLocaleStrText:
			if not strKey.startswith(self.s_strKeyPrefixFonts):
				continue
			for strLocale in setStrLocale:
				setStrTtf.add(g_loc.StrTranslation(strKey, strLocale))

		for strTtf in setStrTtf:
			assert strTtf
			self.pdf.AddFont(strTtf, '', self.s_pathDirFonts / strTtf)

		self.lPage: list[CPage] = [self.s_mpPagekClsPage[pagea.pagek](self, pagea) for pagea in self.doca.tuPagea]

		pathDirOutput = Path.cwd() / self.doca.strDirOutput if self.doca.strDirOutput else Path.cwd()

		lStrFile = [strName]
		
		if self.doca.strFileSuffix:
			lStrFile.append(self.doca.strFileSuffix)

		if self.doca.fAddLangTzSuffix:
			for page in self.lPage:
				lStrFile.append(page.strLocale.lower())
				lStrFile.append(page.strTzAbbrev.lower())

		strFile = '-'.join(lStrFile)

		pathDirOutput.mkdir(parents=True, exist_ok=True)
		pathOutput = (pathDirOutput / strFile).with_suffix('.pdf')

		print(f"writing to {pathOutput.relative_to(Path.cwd())}")

		self.pdf.output(str(pathOutput))

def main():
	for doca in IterDoca():
		CDocument(doca)

if __name__ == '__main__':
	main()
