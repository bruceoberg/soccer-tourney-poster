from __future__ import annotations  # Forward refs without quotes (eg foo: CFoo, not foo: 'CFoo')

import arrow

from typing import TYPE_CHECKING

from bolay import CBlot
from bolay import JH, JV, SPoint, SRect, RectBoundingBox, SHaloArgs
from bolay import colorBlack, colorWhite, colorLightGrey

from .database import CMatch, STAGE
from .group import CGroupBlot
from .calendar import CDayBlot, CElimBlot

if TYPE_CHECKING:
	from .page import CPage

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
		strTitle = self.page.StrTranslation('stage.final')
		oltbTitle.DrawText(strTitle, colorBlack, JH.Center)

		# date

		strDate = self.page.StrDateForFinal(self.match)
		rectDate = rectTitle.Copy(dY = self.s_dYFontDate).Shift(dY = rectTitle.dY + self.s_dYTextGap)
		oltbDate = self.Oltb(rectDate, self.page.Fontkey('final.date'), rectDate.dY)
		oltbDate.DrawText(strDate, colorBlack, JH.Center)

		# time

		if self.page.FMatchHasResults(self.match):
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

		if self.page.FMatchHasResults(self.match):
			oltbHomeScore = self.Oltb(rectHomeBox, self.page.Fontkey('match.score'), self.s_dSScore)
			oltbHomeScore.DrawText(str(self.match.scoreHome), colorWhite, JH.Center, haloa = haloaScore)
		else:
			self.DrawBox(rectHomeBox, self.s_dSLineScore, colorBlack, colorWhite)

		xAwayBox = rectScore.x + (rectScore.dX / 2.0) + (dXLineGap / 2.0 )
		rectAwayBox = SRect(xAwayBox, rectScore.y, self.s_dSScore, self.s_dSScore)

		if self.page.FMatchHasResults(self.match):
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

		if self.page.FMatchHasResults(self.match):
			if self.match.scoreHomeTiebreaker != -1 or self.match.fAfterExtraTime:

				dYBelowBox = rectAll.yMax - rectHomeBox.yMax
				yExtraTime = rectHomeBox.yMax - CDayBlot.s_dSPensNudge
				dYExtraTime = dYBelowBox
				dYFontExtraTime = dYBelowBox # * 0.9

			if self.match.scoreHomeTiebreaker != -1:
				assert self.match.scoreAwayTiebreaker != -1

				# line between penalties

				dXLineScore = xLineMax - xLineMin
				uXPens = rectHomePens.dX / rectHomeBox.dX
				dXLinePens = dXLineScore * uXPens
				dXLinePensHalf = dXLinePens / 2.0
				xMid = (rectHomePens.xMax + rectAwayPens.xMin) / 2.0
				xLinePensMin = xMid - dXLinePensHalf
				xLinePensMax = xMid + dXLinePensHalf

				yLine = yExtraTime + dYExtraTime / 2.0
				self.pdf.set_line_width(self.s_dSLineScore)
				self.pdf.set_draw_color(0) # black
				self.pdf.line(xLinePensMin, yLine, xLinePensMax, yLine)

				# penalties on either side

				strHomeTiebreaker = f'({self.match.scoreHomeTiebreaker}'
				rectHomeTiebreaker = SRect(rectHomePens.xMin, yExtraTime, xLinePensMin - rectHomePens.xMin, dYExtraTime)
				oltbHomeTiebreaker = self.Oltb(rectHomeTiebreaker, self.page.Fontkey('match.score'), dYFontExtraTime)
				oltbHomeTiebreaker.DrawText(strHomeTiebreaker, colorWhite, JH.Right, JV.Bottom, haloa = haloaScore)

				strAwayTiebreaker = f'{self.match.scoreAwayTiebreaker})'
				rectAwayTiebreaker = SRect(xLinePensMax, yExtraTime, rectAwayPens.xMax - xLinePensMax, dYExtraTime)
				oltbAwayTiebreaker = self.Oltb(rectAwayTiebreaker, self.page.Fontkey('match.score'), dYFontExtraTime)
				oltbAwayTiebreaker.DrawText(strAwayTiebreaker, colorWhite, JH.Left, JV.Bottom, haloa = haloaScore)

			elif self.match.fAfterExtraTime:
				strExtraTime = self.page.StrTranslation('match.after-extra-time')
				rectExtraTime = SRect(rectHomePens.xMin, yExtraTime, rectAwayPens.xMax - rectHomePens.xMin, dYExtraTime)
				oltbExtraTime = self.Oltb(rectExtraTime, self.page.Fontkey('match.score'), dYFontExtraTime)
				oltbExtraTime.DrawText(strExtraTime, colorWhite, JH.Center, JV.Bottom, haloa = haloaScore)


			# (full) team names

			strHome = self.page.StrTeam(self.match.strTeamHome)
			rectHomeTeam = SRect(rectAll.x, rectHomeBox.y, rectHomeBox.xMin - rectAll.x, rectHomeBox.dY)
			oltbHomeTeam = self.Oltb(rectHomeTeam, self.page.Fontkey('final.team.name'), rectHomeBox.dY)
			oltbHomeTeam.DrawText(strHome, colorBlack, JH.Right)

			strAway = self.page.StrTeam(self.match.strTeamAway)
			rectAwayTeam = SRect(rectAwayBox.xMax, rectAwayBox.y, rectAll.xMax - rectAwayBox.xMax, rectAwayBox.dY)
			oltbAwayTeam = self.Oltb(rectAwayTeam, self.page.Fontkey('final.team.name'), rectAwayBox.dY)
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

		setMatchElimLeft = self.tourn.setMatchElimHalfHome if self.page.FIsLeftToRight() else self.tourn.setMatchElimHalfAway

		self.lTuXYElimb: list[tuple[float, float, CElimBlot]] = []
		mpStageLRect: dict[STAGE, list[SRect]] = {}

		for colLeft, stage in enumerate(lStage):
			setMatch = self.tourn.mpStageSetMatch[stage]
			setMatchLeft = setMatch.intersection(setMatchElimLeft)
			setMatchRight = setMatch - setMatchLeft
			tuTuColSetMatchCol = ((colLeft, setMatchLeft), (self.cCol-(1+colLeft), setMatchRight))
			for col, setMatchCol in tuTuColSetMatchCol:
				x = mpColX[col]
				for row, matchCol in enumerate(sorted(setMatchCol, key=lambda match: match.sortElim)):
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
			strStage = self.page.StrTranslation(strKey)

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
			rectStageTextDrawn = oltbStageText.RectDrawText(strStage, colorLightGrey, JH.Center)

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
