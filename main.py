import arrow
import colorsys
import copy
import re
import yaml

from aenum import Enum, AutoNumberEnum
from dataclasses import dataclass
from pathlib import Path

from reportlab.lib.pagesizes import landscape, portrait, LETTER, A1, A2, A3, A4, A5, A6, B1, B2, B3, B4, B5, B6, C1, C2, C3, C4, C5, C6
from reportlab.lib.units import inch, cm, mm
from reportlab.lib.colors import Color, HexColor, white, black, red, blue, green, grey, darkgrey, lightgrey
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

pdfmetrics.registerFont(TTFont('Consolas', 'consola.ttf'))
pdfmetrics.registerFont(TTFont('Consolas-Bold', 'consolab.ttf'))
pdfmetrics.registerFont(TTFont('Lucida-Console', 'lucon.ttf'))
pdfmetrics.registerFont(TTFont('Calibri', 'calibri.ttf'))
pdfmetrics.registerFont(TTFont('Calibri-Light-Italic', 'calibrili.ttf'))

g_lStrGroup = ('A', 'B', 'C', 'D', 'E', 'F', 'G', 'H')
g_setStrGroup = frozenset(g_lStrGroup)

g_patAlphaNum = re.compile('([a-zA-Z]+)([0-9]+)')
g_patNumAlpha = re.compile('([0-9]+)([a-zA-Z]+)')

class STAGE(AutoNumberEnum):
	Group = ()
	Round1 = ()
	Round2 = ()	# may not be used, depending on tourney size
	Round3 = () # ditto
	Quarters = ()
	Semis = ()
	Third = ()
	Final = ()

class CVenue:
	def __init__(self, mpKV: dict[str, any]) -> None:
		self.strName: str = mpKV['location']

class CTeam:
	def __init__(self, mpKV: dict[str, any]) -> None:
		self.strName: str = mpKV['team']
		self.strAbbrev: str = mpKV['abbrev']
		self.strSeed: str = None
	def SetSeed(self, strSeed: str) -> None:
		self.strSeed: str = strSeed

class CGroup:
	def __init__(self, strGroup: str) -> None:
		self.strName: str = strGroup
		self.mpStrSeedTeam: dict[str, CTeam] = {}
	def AddTeam(self, team: CTeam):
		self.mpStrSeedTeam[team.strSeed] = team

class CMatch:
	def __init__(self, db: 'CDataBase', mpKV: dict[str, any]) -> None:
		self.strName: str = str(mpKV['match'])
		self.venue: CVenue = db.mpIdVenue[mpKV['venue']]
		self.strHome: str = mpKV['home']
		self.strAway: str = mpKV['away']
		self.tStart = arrow.get(mpKV['time'])

		self.stage: STAGE = None
		self.lStrGroup: list[str] = []
		self.lIdFeeders = []

		if matHome := g_patNumAlpha.match(self.strHome):
			matAway = g_patNumAlpha.match(self.strAway)
			assert matAway
			self.stage = STAGE.Round1
			self.lStrGroup = [matHome[2], matAway[2]]
		elif matHome := g_patAlphaNum.match(self.strHome):
			matAway = g_patAlphaNum.match(self.strAway)
			assert matAway
			assert matHome[1] == matAway[1]
			
			if matHome[1] in g_setStrGroup:
				self.stage = STAGE.Group
				self.lStrGroup = [matHome[1]]
				self.strHome = db.mpStrSeedTeam[self.strHome].strAbbrev
				self.strAway = db.mpStrSeedTeam[self.strAway].strAbbrev
			elif matHome[1] == 'RU':
				assert matAway[1] == 'RU'
				self.stage = STAGE.Third
				self.lIdFeeders = [int(matHome[2]), int(matAway[2])]
			else:
				# leaving self.stage as None, but setting ids so
				# we can set it based on feeders' stages
				assert matHome[1] == 'W'
				self.lIdFeeders = [int(matHome[2]), int(matAway[2])]
		else:
			assert False

	def FTrySetStage(self, mpIdMatch: dict[int, 'CMatch'], stagePrev: STAGE, stage: STAGE):
		assert self.stage is None
		assert self.lIdFeeders

		for id in self.lIdFeeders:
			match = mpIdMatch[id]

			if match.stage != stagePrev:
				return False

		self.stage = stage

		return True

class CDataBase:
	def __init__(self) -> None:
		
		self.mpStrGroupGroup: dict[str, CGroup] = {strGroup:CGroup(strGroup) for strGroup in g_lStrGroup}

		with open('2022-world-cup.yaml') as fd:
			objTop: dict[str, dict[str, any]] = yaml.safe_load(fd)

			self.mpIdVenue: dict[int, CGroup] = {mpKV['venue']:CVenue(mpKV) for mpKV in objTop['venues']}
			self.mpRankTeam: dict[int, CTeam] = {mpKV['rank']:CTeam(mpKV) for mpKV in objTop['teams']}
			self.mpStrSeedTeam: dict[str, CTeam] = {}
			for mpKV in objTop['groups']:
				strSeed = mpKV['seed']
				rank = mpKV['rank']

				team = self.mpRankTeam[rank]
				team.SetSeed(strSeed)

				self.mpStrSeedTeam[strSeed] = team

				group = self.mpStrGroupGroup[strSeed[:1]]
				group.AddTeam(team)

			self.mpIdMatch: dict[int, CMatch] = {mpKV['match']:CMatch(self, mpKV) for mpKV in objTop['matches']}

		# map dates to matches

		self.mpDateSetMatch: dict[STAGE, set[CMatch]] = {}

		for match in self.mpIdMatch.values():
			self.mpDateSetMatch.setdefault(match.tStart.date(), set()).add(match)

		# allot matches to stages

		self.mpStageSetMatch: dict[STAGE, set[CMatch]] = {}

		for match in self.mpIdMatch.values():
			self.mpStageSetMatch.setdefault(match.stage, set()).add(match)

		stagePrev: STAGE = STAGE.Round1
		setMatchNone = self.mpStageSetMatch[None]

		while setMatchNone:
			setMatchPrev = self.mpStageSetMatch[stagePrev]

			if len(setMatchPrev) == 8:
				assert len(setMatchNone) == 7
				stageNext = STAGE.Quarters
			elif len(setMatchPrev) == 4:
				assert stagePrev == STAGE.Quarters
				assert len(setMatchNone) == 3
				stageNext = STAGE.Semis
			elif len(setMatchPrev) == 2:
				assert stagePrev == STAGE.Semis
				assert len(setMatchNone) == 1
				stageNext = STAGE.Final
			else:
				stageNext = stagePrev + 1

			setMatchNext: set[CMatch] = set()

			for match in setMatchNone:
				if match.FTrySetStage(self.mpIdMatch, stagePrev, stageNext):
					setMatchNext.add(match)
			
			assert setMatchNext

			setMatchNone -= setMatchNext
			self.mpStageSetMatch[stageNext] = setMatchNext

			stagePrev = stageNext

		del self.mpStageSetMatch[None]


g_db = CDataBase()

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
	def __init__(self, strFont: str, dYFont: float) -> None:
		self.strFont = strFont
		self.dYFont = dYFont

	def DYCap(self) -> float:
		"""font cap height. aped from pdfmetrics.getAscentDescent()"""
		font = pdfmetrics.getFont(self.strFont)
		dYCap = None
		if not dYCap:
			try:
				dYCap = font.capHeight
			except:
				pass
		if not dYCap:
			try:
				dYCap = font.face.capHeight
			except:
				pass
		if not dYCap:
			dYCap = pdfmetrics.getAscent(self.strFont, self.dYFont)

		if self.dYFont:
			norm = self.dYFont / 1000.0
			return dYCap * norm

		return dYCap

@dataclass
class SPoint: # tag = pos
	x: float = 0
	y: float = 0

@dataclass
class SRect(SPoint): # tag = rect
	dX: float = 0
	dY: float = 0

class COneLineTextBox: # tag = oltb
	"""a box with a single line of text in a particular font, sized to fit the box"""
	def __init__(self, strFont: str, dYFont: float, rect: SRect, dSMargin: float = None) -> None:
		self.fonti = CFontInstance(strFont, dYFont)
		self.rect = rect

		self.dYCap = self.fonti.DYCap()
		self.dSMargin = dSMargin or max(0.0, (self.rect.dY - self.dYCap) / 2.0)

	def RectMargin(self) -> SRect:
		return SRect(
				self.rect.x + self.dSMargin,
				self.rect.y + self.dSMargin,
				self.rect.dX - 2.0 * self.dSMargin,
				self.rect.dY - 2.0 * self.dSMargin)

def ColorResaturate(color: Color, rS: float = 1.0, dS: float = 0.0, rV: float = 1.0, dV: float = 0.0) -> Color:
	h, s, v = colorsys.rgb_to_hsv(color.red, color.green, color.blue)
	s = min(1.0, max(0.0, s * rS + dS))
	v = min(1.0, max(0.0, v * rV + dV))
	r, g, b = colorsys.hsv_to_rgb(h, s, v)
	return Color(r, g, b)

class CBlot: # tag = blot
	"""something drawable at a location. some blots may contain other blots."""

	def __init__(self, c: Canvas) -> None:
		self.c = c

	def RectInsetDrawBox(self, rect: SRect, dSLine: float, color: Color) -> SRect:
		x = rect.x + 0.5 * dSLine
		y = rect.y + 0.5 * dSLine
		dX = rect.dX - dSLine
		dY = rect.dY - dSLine
		self.c.setFillColor(white, alpha=1.0)
		self.c.setLineWidth(dSLine)
		self.c.setStrokeColor(color)
		self.c.rect(x, y, dX, dY, stroke=1, fill=1)
		return SRect(x + 0.5 * dSLine, y + 0.5 * dSLine, dX - dSLine, dY - dSLine)

	def DrawBox(self, rect: SRect, dSLine: float, color: Color) -> None:
		self.RectInsetDrawBox(rect, dSLine, color)

	def FillWithin(self, rect: SRect, color: Color, uAlpha: float = 1.0) -> None:
		self.c.setFillColor(color, alpha=uAlpha)
		self.c.rect(rect.x, rect.y, rect.dX, rect.dY, stroke=0, fill=1)

	def WhiteBox(self, rect: SRect, color: Color, uAlpha: float = 1.0) -> None:
		self.c.setFillColor(color, alpha=uAlpha)
		self.c.rect(rect.x, rect.y, rect.dX, rect.dY, stroke=0, fill=1)

	def RectDrawText(self, strText: str, color: Color, oltb : COneLineTextBox, jh : JH = JH.Left, jv: JV = JV.Middle) -> SRect:
		self.c.setFont(oltb.fonti.strFont, oltb.fonti.dYFont)
		rectText = SRect(0, 0, self.c.stringWidth(strText), oltb.dYCap)
		rectMargin = oltb.RectMargin()

		if jh == JH.Left:
			rectText.x = rectMargin.x
		elif jh == JH.Center:
			rectText.x = rectMargin.x + (rectMargin.dX - rectText.dX) / 2.0
		else:
			assert jh == JH.Right
			rectText.x = rectMargin.x + rectMargin.dX - rectText.dX

		if jv == JV.Bottom:
			rectText.y = rectMargin.y
		elif jv == JV.Middle:
			rectText.y = rectMargin.y + (rectMargin.dY - rectText.dY) / 2.0
		else:
			assert jv == JV.Top
			rectText.y = rectMargin.y + rectMargin.dY - rectText.dY

		self.c.setFillColor(color)
		self.c.drawString(rectText.x, rectText.y, strText)
		# to = self.c.beginText(rectText.x, rectText.y, direction=None)
		# to.setCharSpace(0)
		# to.textLine(strText)
		# self.c.drawText(to)

		return rectText

	def Draw(pos: SPoint) -> None:
		pass

class CGroupBlot(CBlot): # tag = groupb

	s_dX = 4.5*inch
	s_dY = s_dX / (16.0 / 9.0) # HDTV ratio
	s_dSLineOuter = 0.02*inch
	s_dSLineInner = 0.008*inch
	s_dSLineStats = 0.01*inch

	# width to height ratios

	s_rSGroup = 5.0
	s_rSTeamName = 6.0

	# colors

	# BB (bruceo) put these in the yaml

	s_mpStrGroupColor: dict[str, Color] = {
		'A' : HexColor(0x94d9f5),
		'B' : HexColor(0xfee289),
		'C' : HexColor(0xf79d8f),
		'D' : HexColor(0xc4e1b5),
		'E' : HexColor(0xb0d0ee),
		'F' : HexColor(0xc0e4df),
		'G' : HexColor(0xfab077),
		'H' : HexColor(0xeecbef), #(0xf2e8f2),
	}
	assert(g_setStrGroup == frozenset(s_mpStrGroupColor.keys()))

	s_dSDarker = 0.5

	s_rVLighter = 1.5
	s_rSLighter = 0.5

	def __init__(self, c: Canvas, strGroup: str) -> None:
		super().__init__(c)
		self.group: CGroup = g_db.mpStrGroupGroup[strGroup]
		self.color: Color = self.s_mpStrGroupColor[strGroup]
		self.colorDarker = ColorResaturate(self.color, dS=self.s_dSDarker)
		self.colorLighter = ColorResaturate(self.color, rV=self.s_rVLighter, rS=self.s_rSLighter)

	def Draw(self, pos: SPoint) -> None:

		rectAll = SRect(pos.x, pos.y, self.s_dX, self.s_dY)

		# black/color/black borders

		rectAll = self.RectInsetDrawBox(rectAll, self.s_dSLineOuter, black)
		rectAll = self.RectInsetDrawBox(rectAll, self.s_dSLineInner, self.color)
		rectAll = self.RectInsetDrawBox(rectAll, self.s_dSLineOuter, black)

		# title

		#dYTitle = dY * self.s_uYTitle
		dYTitle = rectAll.dX / self.s_rSGroup
		rectTitle = SRect(
						rectAll.x,
						rectAll.y + rectAll.dY - dYTitle,
						rectAll.dX,
						dYTitle)

		self.FillWithin(rectTitle, self.color)

		dYGroupName = dYTitle * 1.3
		oltbGroupName = COneLineTextBox('Consolas-Bold', dYGroupName, rectTitle)
		rectGroupName = self.RectDrawText(
								self.group.strName,
								self.colorDarker,
								oltbGroupName,
								JH.Right,
								JV.Middle)

		rectGroupLabel = SRect(
							rectTitle.x,
							rectTitle.y,
							rectGroupName.x - rectTitle.x,
							rectTitle.dY)

		uGroupLabel = 0.65
		oltbGroupLabel = COneLineTextBox('Calibri', dYTitle * uGroupLabel, rectGroupLabel, dSMargin=oltbGroupName.dSMargin)
		self.RectDrawText('Group', white, oltbGroupLabel, JH.Right) #, JV.Top)

		# heading

		#dYHeading = dY * self.s_uYHeading
		dYHeading = dYTitle / 4.0
		rectHeading = SRect(
						rectAll.x,
						rectTitle.y - dYHeading,
						rectAll.dX,
						dYHeading)

		self.FillWithin(rectHeading, black)

		# teams

		dYTeams = rectAll.dY - (dYTitle + dYHeading)
		dYTeam = dYTeams / len(self.group.mpStrSeedTeam)
		rectTeam = SRect(rectHeading.x, 0, rectHeading.dX, dYTeam)

		for i in range(len(self.group.mpStrSeedTeam)):
			rectTeam.y = rectHeading.y - (i + 1) * dYTeam
			color = self.colorLighter if (i & 1) else white
			self.FillWithin(rectTeam, color)

		rectTeam.dX = dYTeam * self.s_rSTeamName

		for i, strSeed in enumerate(sorted(self.group.mpStrSeedTeam)):
			rectTeam.y = rectHeading.y - (i + 1) * dYTeam
			team = self.group.mpStrSeedTeam[strSeed]

			oltbAbbrev = COneLineTextBox('Consolas', dYTeam, rectTeam)
			self.RectDrawText(team.strAbbrev, black, oltbAbbrev, JH.Right)

			uTeamText = 0.75
			oltbName = COneLineTextBox('Calibri', dYTeam * uTeamText, rectTeam, dSMargin=oltbAbbrev.dSMargin)
			self.RectDrawText(team.strName, darkgrey, oltbName, JH.Left) #, JV.Top)

		# dividers for team/points/gf/ga

		dXStats = (rectAll.dX - rectTeam.dX) / 3.0

		rectPoints = SRect(
						rectTeam.x + rectTeam.dX,
						rectHeading.y,
						dXStats,
						rectHeading.dY)
		rectGoalsFor = SRect(
						rectPoints.x + rectPoints.dX,
						rectHeading.y,
						dXStats,
						rectHeading.dY)
		rectGoalsAgainst = SRect(
						rectGoalsFor.x + rectGoalsFor.dX,
						rectHeading.y,
						dXStats,
						rectHeading.dY)

		self.c.setLineWidth(self.s_dSLineStats)
		self.c.setStrokeColor(black)
	
		self.c.line(rectPoints.x, rectAll.y, rectPoints.x, rectHeading.y)
		self.c.line(rectGoalsFor.x, rectAll.y, rectGoalsFor.x, rectHeading.y)
		self.c.line(rectGoalsAgainst.x, rectAll.y, rectGoalsAgainst.x, rectHeading.y)

		# heading labels

		lTuRectStr = (
			#(rectTeam, "COUNTRY"),
			(rectPoints,		"PTS"),
			(rectGoalsFor,		"GF"),
			(rectGoalsAgainst,	"GA"),
		)

		for rectHeading, strHeading in lTuRectStr:
			oltbHeading = COneLineTextBox('Calibri', rectHeading.dY, rectHeading)
			self.RectDrawText(strHeading, white, oltbHeading, JH.Center)

class CMatchBlot(CBlot): # tag = dayb
	def __init__(self, dayb: 'CDayBlot', match: CMatch, rect: SRect) -> None:
		super().__init__(dayb.c)
		self.dayb = dayb
		self.match = match
		self.rect = rect

		self.dYInfo = dayb.s_dSScore + dayb.s_dYTime
		dYGap = (self.rect.dY - self.dYInfo) / 3.0
		self.yScore = self.rect.y + dYGap
		self.yTime = self.yScore + dayb.s_dSScore + dYGap

	def DrawFill(self) -> None:
		lColor = [self.dayb.mpStrGroupGroupb[strGroup].color for strGroup in self.match.lStrGroup]

		@dataclass
		class SRectColor:
			rect: SRect = None
			color: Color = None

		lRc: list[SRectColor] = []

		if self.match.stage == STAGE.Group:
			assert len(lColor) == 1
			lRc.append(SRectColor(self.rect, lColor[0]))
		elif self.match.stage == STAGE.Round1:
			assert len(lColor) == 2
			lRc.append(SRectColor(copy.copy(self.rect), lColor[0]))
			lRc[-1].rect.dX /= 2.0

			lRc.append(SRectColor(copy.copy(self.rect), lColor[1]))
			lRc[-1].rect.dX /= 2.0
			lRc[-1].rect.x += lRc[-1].rect.dX
		else:
			lColor = [self.dayb.mpStrGroupGroupb[strGroup].color for strGroup in g_lStrGroup]
			dXStripe = self.rect.dX / len(lColor)
			xStripe = self.rect.x
			for color in lColor:
				lRc.append(SRectColor(copy.copy(self.rect), color))
				lRc[-1].rect.x = xStripe
				lRc[-1].rect.dX = dXStripe
				xStripe += dXStripe

		for rc in lRc:
			self.FillWithin(rc.rect, rc.color)

	def DrawInfo(self) -> None:

		# time

		rectTime = SRect(self.rect.x, self.yTime, self.rect.dX, self.dayb.s_dYTime)
		oltbTime = COneLineTextBox(self.dayb.s_strFontTime, self.dayb.s_dYFontTime, rectTime)
		strTime = self.match.tStart.format('HH:mma')
		self.RectDrawText(strTime, black, oltbTime, JH.Center)

		# dash between score boxes

		dXLineGap = self.dayb.s_dSScore / 2.0
		dXLine = dXLineGap / 2.0
		xLineMin = self.rect.x + (self.rect.dX / 2.0) - (dXLine / 2.0)
		xLineMax = xLineMin + dXLine
		yLine = self.yScore + (self.dayb.s_dSScore / 2.0)
		self.c.setLineWidth(self.dayb.s_dSLineScore)
		self.c.setStrokeColor(black)
		self.c.line(xLineMin, yLine, xLineMax, yLine)

		# score boxes

		xHomeBox = self.rect.x + (self.rect.dX / 2.0) - ((dXLineGap / 2.0 ) + self.dayb.s_dSScore)
		rectHomeBox = SRect(xHomeBox, self.yScore, self.dayb.s_dSScore, self.dayb.s_dSScore)
		self.DrawBox(rectHomeBox, self.dayb.s_dSLineScore, black)

		xAwayBox = self.rect.x + (self.rect.dX / 2.0) + (dXLineGap / 2.0 )
		rectAwayBox = SRect(xAwayBox, self.yScore, self.dayb.s_dSScore, self.dayb.s_dSScore)
		self.DrawBox(rectAwayBox, self.dayb.s_dSLineScore, black)

		# team labels

		dXLabels = self.rect.dX - (2 * self.dayb.s_dSScore) - dXLineGap
		dXLabel = dXLabels / 2.0

		rectHomeLabel = SRect(self.rect.x, self.yScore, dXLabel, self.dayb.s_dSScore)
		oltbHomeLabel = COneLineTextBox('Consolas', self.dayb.s_dSScore, rectHomeLabel)
		self.RectDrawText(self.match.strHome, black, oltbHomeLabel, JH.Center)

		rectAwayLabel = SRect(self.rect.x + self.rect.dX - dXLabel, self.yScore, dXLabel, self.dayb.s_dSScore)
		oltbAwayLabel = COneLineTextBox('Consolas', self.dayb.s_dSScore, rectAwayLabel)
		self.RectDrawText(self.match.strAway, black, oltbAwayLabel, JH.Center)

class CDayBlot(CBlot): # tag = dayb

	s_dX = 2.25*inch
	s_dY = s_dX # square
	s_dSLineOuter = CGroupBlot.s_dSLineOuter
	s_dSLineScore = CGroupBlot.s_dSLineStats

	s_uYDate = 0.06
	s_dYDate = s_dY * s_uYDate

	s_uYTime = 0.075
	s_strFontTime = 'Calibri'
	s_dYFontTime = s_dY * s_uYTime
	s_dYTime = CFontInstance(s_strFontTime, s_dYFontTime).DYCap()

	# scores are square, so we use dS

	s_uSScore = 0.147
	s_dSScore = s_dY * s_uSScore
	s_dSScoreGap = s_dSScore / 2.0

	def __init__(self, c: Canvas, mpStrGroupGroupb: dict[str, CGroupBlot], lMatch: list[CMatch]) -> None:
		super().__init__(c)
		self.mpStrGroupGroupb = mpStrGroupGroupb
		self.lMatch = lMatch
		for match in lMatch[1:]:
			assert lMatch[0].tStart.date() == match.tStart.date()
		# BB (bruceo) only include year/month sometimes
		self.strDate = lMatch[0].tStart.format("MMMM Do")

	def Draw(self, pos: SPoint) -> None:

		rectAll = SRect(pos.x, pos.y, self.s_dX, self.s_dY)

		# black border

		rectAll = self.RectInsetDrawBox(rectAll, self.s_dSLineOuter, black)

		# Date

		rectDate = SRect(
						rectAll.x,
						rectAll.y + rectAll.dY - self.s_dYDate,
						rectAll.dX,
						self.s_dYDate)
		oltbHeading = COneLineTextBox('Calibri-Light-Italic', rectDate.dY, rectDate)
		self.RectDrawText(self.strDate, black, oltbHeading)

		rectAll.dY -= rectDate.dY

		# count the time segments

		dYMatch = rectAll.dY / len(self.lMatch)

		# draw matches top to bottom

		lMatchb: list[CMatchBlot] = []
		yMatch = rectAll.y + rectAll.dY - dYMatch

		for match in self.lMatch:
			lMatchb.append(CMatchBlot(self, match, SRect(rectAll.x, yMatch, rectAll.dX, dYMatch)))
			yMatch -= dYMatch

		pass

		for matchb in lMatchb:
			matchb.DrawFill()

		for matchb in lMatchb:
			matchb.DrawInfo()

pathDst = Path('poster.pdf').absolute()
strPathDst = str(pathDst)

c = Canvas(str(pathDst), pagesize=portrait(LETTER))
rectPage = SRect(0, 0, c._pagesize[0], c._pagesize[1])

mpStrGroupGroupb = {strGroup:CGroupBlot(c, strGroup) for strGroup in g_lStrGroup}

dSMargin = 0.5*inch

def DrawGroups():
	dXGrid = CGroupBlot.s_dX + dSMargin
	dYGrid = CGroupBlot.s_dY + dSMargin

	for col in range(2):
		for row in range(4):
			try:
				strGroup = g_lStrGroup[col * 4 + row]
			except IndexError:
				continue
			groupb = mpStrGroupGroupb[strGroup]
			pos = SPoint(
					dSMargin + col * dXGrid,
					rectPage.dY - ((row + 1) * dYGrid))
			groupb.Draw(pos)

def DrawDays():
	dXGrid = CDayBlot.s_dX + dSMargin
	dYGrid = CDayBlot.s_dY + dSMargin

	lDayb: list[CDayBlot] = []

	lIdMatch = (1,2,5,9)
	setDate: set[any] = {g_db.mpIdMatch[idMatch].tStart.date() for idMatch in lIdMatch}
	for dateMatch in sorted(setDate):
		lMatch = sorted(g_db.mpDateSetMatch[dateMatch], key=lambda match: match.tStart)

		lDayb.append(CDayBlot(c, mpStrGroupGroupb, lMatch))

	for row in range(2):
		for col in range(2):
			try:
				dayb = lDayb[row * 2 + col]
			except IndexError:
				continue
			pos = SPoint(
					dSMargin + col * dXGrid,
					rectPage.dY - ((row + 1) * dYGrid))
			dayb.Draw(pos)

#DrawGroups()
DrawDays()


c.save()

