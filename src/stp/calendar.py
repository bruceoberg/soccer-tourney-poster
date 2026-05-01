from __future__ import annotations  # Forward refs without quotes (eg foo: CFoo, not foo: 'CFoo')

import arrow
import babel.dates
import datetime

from typing import TYPE_CHECKING, Optional, Iterable, NamedTuple

from bolay import SFontKey, VEK, CFontInstance, CBlot
from bolay import JH, JV, SPoint, SRect, SHaloArgs
from bolay import SColor
from bolay import colorBlack, colorWhite, colorLightGrey

from .database import CMatch, STAGE
from .group import CGroupBlot

if TYPE_CHECKING:
	from .page import CPage

class SRectColor(NamedTuple):
	rect: SRect
	color: SColor

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

		# elimination rounds get extra height for penalties/labels

		if self.fElimination:
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

			if self.page.FMatchHasResults(self.match):
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

		if self.page.FMatchHasResults(self.match):
			oltbHomeScore = self.Oltb(rectHomeBox, self.page.Fontkey('match.score'), self.dayb.s_dSScore)
			oltbHomeScore.DrawText(str(self.match.scoreHome), colorWhite, JH.Center, haloa = haloaScore)
		else:
			self.DrawBox(rectHomeBox, self.dayb.s_dSLineScore, colorBlack, colorWhite)

		xAwayBox = self.rect.x + (self.rect.dX / 2.0) + (dXLineGap / 2.0 )
		rectAwayBox = SRect(xAwayBox, yScore, self.dayb.s_dSScore, self.dayb.s_dSScore)

		if self.page.FMatchHasResults(self.match):
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

		if self.page.FMatchHasResults(self.match):
			if self.match.scoreHomeTiebreaker != -1 or self.match.fAfterExtraTime:

				dYBelowBox = self.rect.yMax - rectHomeBox.yMax
				yExtraTime = rectHomeBox.yMax - self.dayb.s_dSPensNudge
				dYExtraTime = dYBelowBox
				dYFontExtraTime = dYBelowBox # * 0.9

				if self.match.scoreHomeTiebreaker != -1:
					assert self.match.scoreAwayTiebreaker != -1

					# line between penalties

					yLine = yExtraTime + dYExtraTime / 2.0
					self.pdf.set_line_width(self.dayb.s_dSLineScore)
					self.pdf.set_draw_color(0) # black
					self.pdf.line(rectHomePens.xMax, yLine, rectAwayPens.xMin, yLine)

					# penalties on either side

					strHomeTiebreaker = f'({self.match.scoreHomeTiebreaker}'
					rectHomeTiebreaker = SRect(rectHomePens.xMin, yExtraTime, rectHomePens.dX, dYExtraTime)
					oltbHomeTiebreaker = self.Oltb(rectHomeTiebreaker, self.page.Fontkey('match.score'), dYFontExtraTime)
					oltbHomeTiebreaker.DrawText(strHomeTiebreaker, colorWhite, JH.Right, JV.Bottom, haloa = haloaScore)

					strAwayTiebreaker = f'{self.match.scoreAwayTiebreaker})'
					rectAwayTiebreaker = SRect(rectAwayPens.xMin, yExtraTime, rectAwayPens.dX, dYExtraTime)
					oltbAwayTiebreaker = self.Oltb(rectAwayTiebreaker, self.page.Fontkey('match.score'), dYFontExtraTime)
					oltbAwayTiebreaker.DrawText(strAwayTiebreaker, colorWhite, JH.Left, JV.Bottom, haloa = haloaScore)

				elif self.match.fAfterExtraTime:
					strExtraTime = self.page.StrTranslation('match.after-extra-time')
					rectExtraTime = SRect(rectHomePens.xMin, yExtraTime, rectAwayPens.xMax - rectHomePens.xMin, dYExtraTime)
					oltbExtraTime = self.Oltb(rectExtraTime, self.page.Fontkey('match.score'), dYFontExtraTime)
					oltbExtraTime.DrawText(strExtraTime, colorWhite, JH.Center, JV.Bottom, haloa = haloaScore)

		if self.fElimination and not self.page.FMatchHasResults(self.match):

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
				assert self.match.idFeederHome is not None
				matchFeederHome = self.tourn.mpIdMatch[self.match.idFeederHome]
				assert self.match.idFeederAway is not None
				matchFeederAway = self.tourn.mpIdMatch[self.match.idFeederAway]

				fDrawFormLabels = True
				strHome = ''.join(sorted(matchFeederHome.lStrGroup))
				strAway = ''.join(sorted(matchFeederAway.lStrGroup))
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
				oltbHomeTeam = self.Oltb(rectHomeTeam, self.page.Fontkey('third.team.name'), rectHomeBox.dY)
				oltbHomeTeam.DrawText(strHome, colorBlack, JH.Right)

				strAway = self.page.StrTeam(self.match.strTeamAway)
				rectAwayTeam = SRect(rectAwayBox.xMax, rectAwayBox.y, self.rect.xMax - rectAwayBox.xMax, rectAwayBox.dY)
				oltbAwayTeam = self.Oltb(rectAwayTeam, self.page.Fontkey('third.team.name'), rectAwayBox.dY)
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

		vekTime = VEK.BaseCap # assuming times across all languages are within the baseline ... cap height

		self.dYTime = CFontInstance(self.pdf, self.page.Fontkey('match.time'), self.s_dYFontTime, vekTime).dYGlyphs

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
			if self.page.FMatchHasResults(matchbTop.match) or self.page.FMatchHasResults(matchbTop.match):
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

class SDayInstance(NamedTuple): # tag = dayinst
	dPos: SPoint
	dayb: CDayBlot

class SDayHeader(NamedTuple): # tag = dayhead
	x: float
	strWeekday: str
	fontkey: SFontKey

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

		dateMatchesMin: datetime.date = min(setDate)
		dateMatchesMax: datetime.date = max(setDate)
		cDayMatches: int = (dateMatchesMax - dateMatchesMin).days + 1
		cWeekMatches: int = (cDayMatches + 6) // 7

		dateCalMin = dateMatchesMin
		dateCalMax = dateMatchesMax

		# ensure dateMin/dateMax are on week boundries

		self.weekdayFirst: int = self.page.locale.first_week_day
		self.weekdayLast = (self.weekdayFirst + 6) % 7
		self.colBreak: int = 0
		self.dXBreak: float = 0

		if dateCalMin.weekday() != self.weekdayFirst:
			# arrow.shift(weekday) always goes forward in time
			dateCalMin = arrow.get(dateCalMin).shift(weeks=-1).shift(weekday=self.weekdayFirst).date()

		# and always go all the way to saturday

		if dateCalMax.weekday() != self.weekdayLast:
			dateCalMax = arrow.get(dateCalMax).shift(weekday=self.weekdayLast).date()

		cDayCal: int = (dateCalMax - dateCalMin).days + 1
		assert cDayCal % 7 == 0
		cWeekCal: int = cDayCal // 7

		if cWeekCal > cWeekMatches:
			assert(cWeekCal - cWeekMatches == 1)

			# to minimize vertical size, we will "rotate" the days of the week on our calendar to
			# eliminate a weeks worth of match-less days. the first match of the tournament will be
			# in the far left column no matter what day its on.

			self.weekdayFirst = dateMatchesMin.weekday()
			self.weekdayLast = (self.weekdayFirst + 6) % 7
			self.colBreak = (7 + self.page.locale.first_week_day - self.weekdayFirst) % 7
			assert(self.colBreak)
			self.dXBreak = 8 * CDayBlot.s_dSLineOuter

			dateCalMin = dateMatchesMin
			dateCalMax = dateMatchesMax

			if dateCalMax.weekday() != self.weekdayLast:
				dateCalMax = arrow.get(dateCalMax).shift(weekday=self.weekdayLast).date()

			cDayCal = (dateCalMax - dateCalMin).days + 1
			assert cDayCal % 7 == 0
			cWeekCal = cDayCal // 7
			assert cWeekCal == cWeekMatches

		lDayb: list[CDayBlot] = []

		for tDay in arrow.Arrow.range('day', arrow.get(dateCalMin), arrow.get(dateCalMax)):
			setMatchDate = self.page.mpDateSetMatch.get(tDay.date(), set()).intersection(setMatch)
			lDayb.append(CDayBlot(self.page, tDay, iterMatch = setMatchDate))

		self.daybl = CDayBlotList(lDayb)

		self.dX = self.dXBreak + 7 * self.daybl.dXDayb
		self.dY = self.s_dYStageLabel + self.s_dYDayOfWeek + cWeekCal * self.daybl.dYDayb

		# build a list of the days of the week and their positions/fonts

		self.lDayhead: list[SDayHeader] = []

		mpWeekdayStr = babel.dates.get_day_names('abbreviated', locale=self.page.locale)

		for col in range(7):
			x = col * self.daybl.dXDayb

			if col >= self.colBreak:
				x += self.dXBreak

			if self.page.FIsRightToLeft():
				x = self.dX - (x + self.daybl.dXDayb)

			strDayOfWeek = mpWeekdayStr[(col + self.weekdayFirst) % 7]
			strFontkey = 'calendar.day-of-week'
			if self.colBreak and (col == self.colBreak or col == self.colBreak - 1):
				strFontkey = 'calendar.day-of-week-broken'
			fontkey = self.page.Fontkey(strFontkey)

			self.lDayhead.append(SDayHeader(x, strDayOfWeek, fontkey))

		# build a list of all day blots and their relative positions


		self.lDayinst: list[SDayInstance] = []
		for iDay, dayb in enumerate(self.daybl.lDayb):
			col = iDay % 7
			row = iDay // 7

			dPos = SPoint(self.lDayhead[col].x, row * self.daybl.dYDayb)
			self.lDayinst.append(SDayInstance(dPos, dayb))

	def Draw(self, pos: SPoint) -> None:

		yStageTextMin = pos.y
		yDaysOfWeekMin = yStageTextMin + self.s_dYStageLabel
		yDaysMin = yDaysOfWeekMin + self.s_dYDayOfWeek
		yDaysMax = pos.y + self.dY
		dYDays = yDaysMax - yDaysMin

		# stage heading

		rectStageText = SRect(pos.x, yStageTextMin, self.dX, self.s_dYFontStage)
		oltbStageText = self.Oltb(rectStageText, self.page.Fontkey('elim.stage'), rectStageText.dY)
		strStageText = self.page.StrTranslation('stage.group')
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

		for dayhead in self.lDayhead:
			rectDayOfWeek = SRect(x = pos.x + dayhead.x, y = yDaysOfWeekMin, dX = self.daybl.dXDayb, dY = self.s_dYDayOfWeek)
			oltbDayOfWeek = self.Oltb(rectDayOfWeek, dayhead.fontkey, rectDayOfWeek.dY, veklmEm = VEK.DescendCap)
			oltbDayOfWeek.DrawText(dayhead.strWeekday, colorBlack, JH.Center)

		# days

		rectDays = SRect(x = pos.x, y = yDaysMin, dX = self.dX, dY = dYDays)

		tPrev: Optional[arrow.Arrow] = None
		for dayinst in self.lDayinst:

			posDayb = SPoint(rectDays.x + dayinst.dPos.x, rectDays.y + dayinst.dPos.y)

			dayinst.dayb.Draw(posDayb, self.daybl, tPrev)

			tPrev = dayinst.dayb.tDay

		# border

		if self.page.pagea.fMainBorders:
			if self.colBreak:
				# draw boxes around two sets of days on either side of break

				rectDaysBefore = rectDays.Copy(dX = self.colBreak * self.daybl.dXDayb)
				rectDaysAfter = rectDays.Copy(dX = (7 - self.colBreak) * self.daybl.dXDayb)

				if self.page.FIsLeftToRight():
					rectDaysAfter.x = rectDaysBefore.xMax + self.dXBreak
					xWeekdayBreak = (rectDaysBefore.xMax + rectDaysAfter.xMin) / 2
				else:
					rectDaysBefore.x = rectDaysAfter.xMax + self.dXBreak
					xWeekdayBreak = (rectDaysAfter.xMax + rectDaysBefore.xMin) / 2

				self.DrawBox(rectDaysBefore, CDayBlot.s_dSLineOuter, colorBlack)
				self.DrawBox(rectDaysAfter, CDayBlot.s_dSLineOuter, colorBlack)

				# draw break line

				colorWeekdayBreak = colorLightGrey

				self.pdf.set_line_width(CDayBlot.s_dSLineOuter)
				self.pdf.set_draw_color(colorWeekdayBreak.r, colorWeekdayBreak.g, colorWeekdayBreak.b)

				yWeekdayBreakMin = rectDayOfWeek.yMin
				yWeekdayBreakMax = rectDays.yMax

				self.pdf.line(xWeekdayBreak, yWeekdayBreakMin, xWeekdayBreak, yWeekdayBreakMax)

			else:
				self.DrawBox(rectDays, CDayBlot.s_dSLineOuter, colorBlack)
