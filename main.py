import colorsys
import copy
import datetime
import fpdf
import logging

from aenum import Enum, AutoNumberEnum
from dataclasses import dataclass
from dateutil import tz
from pathlib import Path
from typing import Optional

from database import *

CPdf = fpdf.FPDF

logging.getLogger("fontTools.subset").setLevel(logging.ERROR)

g_pathHere = Path(__file__).parent
g_db = CDataBase(g_pathHere / '2022-world-cup.xlsx')

class JH(AutoNumberEnum):
	Left = ()
	Center = ()
	Right = ()

class JV(AutoNumberEnum):
	Bottom = ()
	Middle = ()
	Top = ()

class CFontInstance:
	"""a sized font"""
	def __init__(self, pdf: CPdf, strFont: str, dYFont: float, strStyle: str = '') -> None:
		self.pdf = pdf
		self.strFont = strFont
		self.dYFont = dYFont
		self.strStyle = strStyle
		self.dPtFont = self.dYFont * 72.0 # inches to points

		with self.pdf.local_context():
			self.pdf.set_font(self.strFont, self.strStyle, size=self.dPtFont)
			self.dYCap = self.pdf.current_font['desc']['CapHeight'] * self.dYFont / 1000.0

@dataclass
class SColor: # tag = color
	r: int = 0
	g: int = 0
	b: int = 0
	a: int = 255

def ColorFromStr(strColor: str, alpha: int = 255) -> SColor:
	return SColor(*fpdf.html.color_as_decimal(strColor), alpha)

colorWhite = ColorFromStr("white")
colorDarkgrey = ColorFromStr("darkgrey")
colorBlack = ColorFromStr("black")

def ColorResaturate(color: SColor, rS: float = 1.0, dS: float = 0.0, rV: float = 1.0, dV: float = 0.0) -> SColor:
	h, s, v = colorsys.rgb_to_hsv(color.r / 255.0, color.g / 255.0, color.b / 255.0)
	s = min(1.0, max(0.0, s * rS + dS))
	v = min(1.0, max(0.0, v * rV + dV))
	r, g, b = colorsys.hsv_to_rgb(h, s, v)
	return SColor(round(r * 255), round(g * 255), round(b * 255), color.a)

@dataclass
class SPoint: # tag = pos
	x: float = 0
	y: float = 0

	def Shift(self, dX: float = 0, dY: float = 0) -> None:
		self.x += dX
		self.y += dY

class SRect: # tag = rect
	def __init__(self, x: float = 0, y: float = 0, dX: float = 0, dY: float = 0):
		self.posMin: SPoint = SPoint(x, y)
		self.posMax: SPoint = SPoint(x + dX, y + dY)

	def Set(self, x: Optional[float] = None, y: Optional[float] = None, dX: Optional[float] = None, dY: Optional[float] = None) -> 'SRect':
		if x is not None:
			self.x = x
		if y is not None:
			self.y = y
		if dX is not None:
			self.dX = dX
		if dY is not None:
			self.dY = dY
		return self

	def Copy(self, x: Optional[float] = None, y: Optional[float] = None, dX: Optional[float] = None, dY: Optional[float] = None) -> 'SRect':
		rectNew = copy.deepcopy(self)
		rectNew.Set(x, y, dX, dY)
		return rectNew

	def __repr__(self):
		# NOTE (bruceo) avoiding property wrappers for faster debugger perf
		strVals = ', '.join([
			# NOTE (bruceo) avoiding property wrappers for faster debugger perf
			f'_x={self.posMin.x!r}',
			f'_y={self.posMin.y!r}',
			f'dX={self.posMax.x - self.posMin.x!r}',
			f'dY={self.posMax.y - self.posMin.y!r}',
			f'x_={self.posMax.x!r}',
			f'y_={self.posMax.y!r}',
		])
		return f'{type(self).__name__}({strVals})'

	@property
	def xMin(self) -> float:
		return self.posMin.x
	@xMin.setter
	def xMin(self, xNew: float) -> None:
		self.posMin.x = xNew

	@property
	def yMin(self) -> float:
		return self.posMin.y
	@yMin.setter
	def yMin(self, yNew: float) -> None:
		self.posMin.y = yNew

	@property
	def xMax(self) -> float:
		return self.posMax.x
	@xMax.setter
	def xMax(self, xNew: float) -> None:
		self.posMax.x = xNew

	@property
	def yMax(self) -> float:
		return self.posMax.y
	@yMax.setter
	def yMax(self, yNew: float) -> None:
		self.posMax.y = yNew

	@property
	def x(self) -> float:
		return self.posMin.x
	@x.setter
	def x(self, xNew: float) -> None:
		dX = xNew - self.posMin.x
		self.Shift(dX, 0)

	@property
	def y(self) -> float:
		return self.posMin.y
	@y.setter
	def y(self, yNew: float) -> None:
		dY = yNew - self.posMin.y
		self.Shift(0, dY)

	@property
	def dX(self) -> float:
		return self.posMax.x - self.posMin.x
	@dX.setter
	def dX(self, dXNew: float) -> None:
		self.posMax.x = self.posMin.x + dXNew

	@property
	def dY(self) -> float:
		return self.posMax.y - self.posMin.y
	@dY.setter
	def dY(self, dYNew: float) -> None:
		self.posMax.y = self.posMin.y + dYNew

	def Shift(self, dX: float = 0, dY: float = 0) -> 'SRect':
		self.posMin.Shift(dX, dY)
		self.posMax.Shift(dX, dY)
		return self

	def Inset(self, dS: float) -> 'SRect':
		dSHalf = dS / 2.0
		self.posMin.Shift(dSHalf, dSHalf)
		self.posMax.Shift(-dSHalf, -dSHalf)
		return self

	def Outset(self, dS: float) -> 'SRect':
		self.Inset(-dS)
		return self

	def Stretch(self, dXLeft: float = 0, dYTop: float = 0, dXRight: float = 0, dYBottom: float = 0) -> 'SRect':
		self.posMin.Shift(dXLeft, dYTop)
		self.posMax.Shift(dXRight, dYBottom)
		return self

class COneLineTextBox: # tag = oltb
	"""a box with a single line of text in a particular font, sized to fit the box"""
	def __init__(self, pdf: CPdf, rect: SRect, strFont: str, dYFont: float, strStyle: str = '', dSMargin: float = None) -> None:
		self.pdf = pdf
		self.fonti = CFontInstance(pdf, strFont, dYFont, strStyle)
		self.rect = rect

		self.dYCap = self.fonti.dYCap
		self.dSMargin = dSMargin or max(0.0, (self.rect.dY - self.dYCap) / 2.0)
		self.rectMargin = self.rect.Copy().Inset(self.dSMargin)

	def RectDrawText(self, strText: str, color: SColor, jh : JH = JH.Left, jv: JV = JV.Middle) -> SRect:
		self.pdf.set_font(self.fonti.strFont, style=self.fonti.strStyle, size=self.fonti.dPtFont)
		rectText = SRect(0, 0, self.pdf.get_string_width(strText), self.dYCap)

		if jh == JH.Left:
			rectText.x = self.rectMargin.x
		elif jh == JH.Center:
			rectText.x = self.rectMargin.x + (self.rectMargin.dX - rectText.dX) / 2.0
		else:
			assert jh == JH.Right
			rectText.x = self.rectMargin.x + self.rectMargin.dX - rectText.dX

		if jv == JV.Bottom:
			rectText.y = self.rectMargin.y + self.rectMargin.dY
		elif jv == JV.Middle:
			rectText.y = self.rectMargin.y + (self.rectMargin.dY + rectText.dY) / 2.0
		else:
			assert jv == JV.Top
			rectText.y = self.rectMargin.y + rectText.dY

		self.pdf.set_text_color(color.r, color.g, color.b)
		self.pdf.text(rectText.x, rectText.y, strText)

		return rectText

	DrawText = RectDrawText



class CBlot: # tag = blot
	"""something drawable at a location. some blots may contain other blots."""

	def __init__(self, pdf: CPdf) -> None:
		self.pdf = pdf

	def DrawBox(self, rect: SRect, dSLine: float, color: SColor, colorFill: SColor = None) -> None:
		if colorFill is None:
			strStyle = 'D'
		else:
			strStyle = 'FD'
			self.pdf.set_fill_color(colorFill.r, colorFill.g, colorFill.b)

		self.pdf.set_line_width(dSLine)
		self.pdf.set_draw_color(color.r, color.g, color.b)

		self.pdf.rect(rect.x, rect.y, rect.dX, rect.dY, style=strStyle)

	def FillBox(self, rect: SRect, color: SColor) -> None:
		self.pdf.set_fill_color(color.r, color.g, color.b)
		self.pdf.rect(rect.x, rect.y, rect.dX, rect.dY, style='F')

	def Oltb(self, rect: SRect, strFont: str, dYFont: float, strStyle: str = '', dSMargin: float = None) ->COneLineTextBox:
		return COneLineTextBox(self.pdf, rect, strFont, dYFont, strStyle, dSMargin)

	def Draw(self, pos: SPoint) -> None:
		pass

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

	def __init__(self, pdf: CPdf, strGroup: str) -> None:
		super().__init__(pdf)
		self.group: CGroup = g_db.mpStrGroupGroup[strGroup]
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
		lStrGroup = self.match.lStrGroup if self.match.lStrGroup else g_db.lStrGroup
		lGroupb = [self.dayb.mpStrGroupGroupb[strGroup] for strGroup in lStrGroup] 
		if self.match.stage == STAGE.Group:
			lColor = [groupb.color for groupb in lGroupb]
		else:
			lColor = [groupb.colorLighter for groupb in lGroupb]

		@dataclass
		class SRectColor:
			rect: SRect = None
			color: SColor = None

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

	def __init__(self, pdf: CPdf, mpStrGroupGroupb: dict[str, CGroupBlot], lMatch: list[CMatch], datePrev: Optional[datetime.date]) -> None:
		super().__init__(pdf)
		self.mpStrGroupGroupb = mpStrGroupGroupb
		self.lMatch = lMatch
		for match in lMatch[1:]:
			assert lMatch[0].tStart.date() == match.tStart.date()
		# BB (bruceo) only include year/month sometimes
		if datePrev and datePrev.month == lMatch[0].tStart.month:
			strFormat = "D"
		else:
			strFormat = "MMMM D"
		self.strDate = lMatch[0].tStart.format(strFormat)
		self.dYTime = CFontInstance(self.pdf, self.s_strFontTime, self.s_dYFontTime).dYCap

	def Draw(self, pos: SPoint) -> None:

		rectBorder = SRect(pos.x, pos.y, self.s_dX, self.s_dY)
		rectInside = rectBorder.Copy().Inset(self.s_dSLineOuter / 2.0)

		# Date

		rectDate = rectInside.Copy(dY=self.s_dYDate)
		oltbHeading = self.Oltb(rectDate, 'Calibri', rectDate.dY, strStyle='I')
		oltbHeading.DrawText(self.strDate, colorBlack)

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

pathDst = Path('poster.pdf').absolute()
strPathDst = str(pathDst)

g_mpStrFormatWH: dict[str, tuple[float, float]] ={
	"a0": (2383.94, 3370.39),
	"a1": (1683.78, 2383.94),
	"a2": (1190.55, 1683.78),
	"a3": (841.89, 1190.55),
	"a4": (595.28, 841.89),
	# fpdf.PAGE_FORMATS is wrong about a5.
	# they list the short side as 420.94pt.
	#	(their long side is correctly listed as 595.28pt)
	# ISO std a5 short side is 148mm. this table is in pts.
	# excel tells me that 148mm / 25.4 is 5.83in.
	#	and 5.83in * 72 is 419.53pt.
	# so i have no idea where fpdf's 420.94pt comes from.
	# on github, it appears to have been this way since
	#	the original source was checked added in 2008.
	# probably doesn't matter, since the conversion rounds
	#	to the correct size in mm
	"a5": (419.53, 595.28),
	"a6": (297.64, 419.53),
	"a7": (209.76, 297.64),
	"a8": (147.40, 209.76),
	"b0": (2834.65, 4008.19),
	"b1": (2004.09, 2834.65),
	"b2": (1417.32, 2004.09),
	"b3": (1000.63, 1417.32),
	"b4": (708.66, 1000.63),
	"b5": (498.90, 708.66),
	"b6": (354.33, 498.90),
	"b7": (249.45, 354.33),
	"b8": (175.75, 249.45),
	"b9": (124.72, 175.75),
	"b10": (87.87, 124.72),
	"c2": (1298.27, 1836.85),
	"c3": (918.43, 1298.27),
	"c4": (649.13, 918.43),
	"c5": (459.21, 649.13),
	"c6": (323.15, 459.21),
	"d0": (2185.51, 3089.76),
	"letter": (612.00, 792.00),
	"legal": (612.00, 1008.00),
	"ledger": (792.00, 1224.00),
	"tabloid": (792.00, 1224.00),
	"executive": (521.86, 756.00),
	"ansi c": (1224.57, 1584.57),
	"ansi d": (1584.57, 2449.13),
	"ansi e": (2449.13, 3169.13),
	"sra0": (2551.18, 3628.35),
	"sra1": (1814.17, 2551.18),
	"sra2": (1275.59, 1814.17),
	"sra3": (907.09, 1275.59),
	"sra4": (637.80, 907.09),
	"ra0": (2437.80, 3458.27),
	"ra1": (1729.13, 2437.80),
	"ra2": (1218.90, 1729.13),
}
fpdf.fpdf.PAGE_FORMATS.update(g_mpStrFormatWH)

pdf = CPdf(unit='in')

pdf.add_font(family='Consolas', fname=r'fonts\consola.ttf')
pdf.add_font(family='Consolas', style='B', fname=r'fonts\consolab.ttf')
pdf.add_font(family='Lucida-Console', fname=r'fonts\lucon.ttf')
pdf.add_font(family='Calibri', fname=r'fonts\calibri.ttf')
pdf.add_font(family='Calibri', style='B', fname=r'fonts\calibrib.ttf')
pdf.add_font(family='Calibri', style='I', fname=r'fonts\calibrili.ttf')

mpStrGroupGroupb = {strGroup:CGroupBlot(pdf, strGroup) for strGroup in g_db.lStrGroup}

def DrawTestPageGroups(pdf: CPdf):

	pdf.add_page(orientation='portrait', format='c3')
	rectPage = SRect(0, 0, pdf.w, pdf.h)

	dSMargin = 0.5

	dXGrid = CGroupBlot.s_dX + dSMargin
	dYGrid = CGroupBlot.s_dY + dSMargin

	for col in range(2):
		for row in range(4):
			try:
				strGroup = g_db.lStrGroup[col * 4 + row]
			except IndexError:
				continue
			groupb = mpStrGroupGroupb[strGroup]
			pos = SPoint(
					dSMargin + col * dXGrid,
					dSMargin + row * dYGrid)
			groupb.Draw(pos)

def DrawTestPageDays(pdf: CPdf):

	pdf.add_page(orientation='landscape', format='c3')
	rectPage = SRect(0, 0, pdf.w, pdf.h)

	dSMargin = 0.25

	dXGrid = CDayBlot.s_dX + dSMargin
	dYGrid = CDayBlot.s_dY + dSMargin

	lDayb: list[CDayBlot] = []

	# lIdMatch = (49,57)
	# setDate: set[any] = {g_db.mpIdMatch[idMatch].tStart.date() for idMatch in lIdMatch}
	# for dateMatch in sorted(setDate):
	datePrev: Optional[datetime.date] = None
	for dateMatch in sorted(g_db.mpDateSetMatch):
		setMatch = g_db.mpDateSetMatch[dateMatch]
		lMatch = sorted(setMatch, key=lambda match: match.tStart)

		lDayb.append(CDayBlot(pdf, mpStrGroupGroupb, lMatch, datePrev))
		datePrev = dateMatch

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

def DrawPoster(pdf: CPdf):

	pdf.add_page(orientation='landscape', format=(22, 28))
	rectPage = SRect(0, 0, pdf.w, pdf.h)

	dYGroupsGap = 1.0
	cGroup = 4
	dXGroups = CGroupBlot.s_dX
	dYGroups = (cGroup * CGroupBlot.s_dY) + ((cGroup - 1) * dYGroupsGap)
	yGroups = (rectPage.dY - dYGroups) / 2.0
	lGroupbLeft = [mpStrGroupGroupb[strGroup] for strGroup in g_db.lStrGroup[:cGroup]]
	lGroupbRight = [mpStrGroupGroupb[strGroup] for strGroup in g_db.lStrGroup[cGroup:]]

	dateMin: datetime.date = min(g_db.mpDateSetMatch.keys())
	dateMax: datetime.date = max(g_db.mpDateSetMatch.keys())

	cDay = (dateMax - dateMin).days + 1
	cWeek = (cDay + 6) // 7
	if dateMin.weekday() != 6: # SUNDAY
		cWeek += 1

	dXCalendar = 7 * CDayBlot.s_dX
	dYCalendar = cWeek * CDayBlot.s_dY
	yCalendar = (rectPage.dY - dYCalendar) / 2.0

	dXUnused = rectPage.dX - (dXCalendar + 2 * dXGroups)
	dXGap = dXUnused / 4 # both margins and both gaps between groups and calendar

	xGroupsLeft = dXGap
	xCalendar = xGroupsLeft + dXGroups + dXGap
	xGroupsRight = xCalendar + dXCalendar + dXGap

	for xGroups, lGroupb in ((xGroupsLeft, lGroupbLeft), (xGroupsRight, lGroupbRight)):
		for iGroupb, groupb in enumerate(lGroupb):
			yGroup = yGroups + iGroupb * (CGroupBlot.s_dY + dYGroupsGap)
			groupb.Draw(SPoint(xGroups, yGroup))
		
	
	datePrev: Optional[datetime.date] = None
	for dateMatch in sorted(g_db.mpDateSetMatch):
		setMatch = g_db.mpDateSetMatch[dateMatch]
		dayb = CDayBlot(pdf, mpStrGroupGroupb, sorted(setMatch, key=lambda match: match.tStart), datePrev)
		datePrev = dateMatch
		iDay = (dateMatch.weekday() + 1) % 7 # we want sunday as 0
		iWeek = (dateMatch - dateMin).days // 7

		xDay = xCalendar + iDay * CDayBlot.s_dX
		yDay = yCalendar + iWeek * CDayBlot.s_dY

		dayb.Draw(SPoint(xDay, yDay))

#DrawTestPageGroups(pdf)
#DrawTestPageDays(pdf)
DrawPoster(pdf)

pdf.output("poster.pdf")

