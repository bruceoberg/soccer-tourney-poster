import arrow
import colorsys
import copy
import fpdf
import logging
import re
import yaml

from aenum import Enum, AutoNumberEnum
from dataclasses import dataclass
from pathlib import Path

CPdf = fpdf.FPDF

logging.getLogger("fontTools.subset").setLevel(logging.ERROR)

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

def ColorNamed(strColor: str, alpha: int = 255) -> SColor:
	return SColor(*fpdf.html.color_as_decimal(strColor), alpha)

colorWhite = ColorNamed("white")
colorDarkgrey = ColorNamed("darkgrey")
colorBlack = ColorNamed("black")

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

@dataclass
class SRect(SPoint): # tag = rect
	dX: float = 0
	dY: float = 0

class COneLineTextBox: # tag = oltb
	"""a box with a single line of text in a particular font, sized to fit the box"""
	def __init__(self, pdf: CPdf, rect: SRect, strFont: str, dYFont: float, strStyle: str = '', dSMargin: float = None) -> None:
		self.pdf = pdf
		self.fonti = CFontInstance(pdf, strFont, dYFont, strStyle)
		self.rect = rect

		self.dYCap = self.fonti.dYCap
		self.dSMargin = dSMargin or max(0.0, (self.rect.dY - self.dYCap) / 2.0)

	def RectMargin(self) -> SRect:
		return SRect(
				self.rect.x + self.dSMargin,
				self.rect.y + self.dSMargin,
				self.rect.dX - 2.0 * self.dSMargin,
				self.rect.dY - 2.0 * self.dSMargin)

	def RectDrawText(self, strText: str, color: SColor, jh : JH = JH.Left, jv: JV = JV.Middle) -> SRect:
		self.pdf.set_font(self.fonti.strFont, style=self.fonti.strStyle, size=self.fonti.dPtFont)
		rectText = SRect(0, 0, self.pdf.get_string_width(strText), self.dYCap)
		rectMargin = self.RectMargin()

		if jh == JH.Left:
			rectText.x = rectMargin.x
		elif jh == JH.Center:
			rectText.x = rectMargin.x + (rectMargin.dX - rectText.dX) / 2.0
		else:
			assert jh == JH.Right
			rectText.x = rectMargin.x + rectMargin.dX - rectText.dX

		if jv == JV.Bottom:
			rectText.y = rectMargin.y + rectMargin.dY
		elif jv == JV.Middle:
			rectText.y = rectMargin.y + (rectMargin.dY + rectText.dY) / 2.0
		else:
			assert jv == JV.Top
			rectText.y = rectMargin.y + rectText.dY

		self.pdf.set_text_color(color.r, color.g, color.b)
		self.pdf.text(rectText.x, rectText.y, strText)

		return rectText

	DrawText = RectDrawText



class CBlot: # tag = blot
	"""something drawable at a location. some blots may contain other blots."""

	def __init__(self, pdf: CPdf) -> None:
		self.pdf = pdf

	def RectInsetDrawBox(self, rect: SRect, dSLine: float, color: SColor) -> SRect:
		x = rect.x + 0.5 * dSLine
		y = rect.y + 0.5 * dSLine
		dX = rect.dX - dSLine
		dY = rect.dY - dSLine
		self.pdf.set_fill_color(255) # white
		self.pdf.set_line_width(dSLine)
		self.pdf.set_draw_color(color.r, color.g, color.b)
		self.pdf.rect(x, y, dX, dY, style='FD')
		return SRect(x + 0.5 * dSLine, y + 0.5 * dSLine, dX - dSLine, dY - dSLine)

	def DrawBox(self, rect: SRect, dSLine: float, color: SColor) -> None:
		self.RectInsetDrawBox(rect, dSLine, color)

	def FillWithin(self, rect: SRect, color: SColor) -> None:
		self.pdf.set_fill_color(color.r, color.g, color.b)
		self.pdf.rect(rect.x, rect.y, rect.dX, rect.dY, style='F')

	def Oltb(self, rect: SRect, strFont: str, dYFont: float, strStyle: str = '', dSMargin: float = None) ->COneLineTextBox:
		return COneLineTextBox(self.pdf, rect, strFont, dYFont, strStyle, dSMargin)

	def Draw(pos: SPoint) -> None:
		pass

class CGroupBlot(CBlot): # tag = groupb

	s_dX = 4.5
	s_dY = s_dX / (16.0 / 9.0) # HDTV ratio
	s_dSLineOuter = 0.02
	s_dSLineInner = 0.008
	s_dSLineStats = 0.01

	# width to height ratios

	s_rSGroup = 5.0
	s_rSTeamName = 6.0

	# colors

	# BB (bruceo) put these in the yaml

	s_mpStrGroupColor: dict[str, SColor] = {
		'A' : ColorNamed("#94d9f5"),
		'B' : ColorNamed("#fee289"),
		'C' : ColorNamed("#f79d8f"),
		'D' : ColorNamed("#c4e1b5"),
		'E' : ColorNamed("#b0d0ee"),
		'F' : ColorNamed("#c0e4df"),
		'G' : ColorNamed("#fab077"),
		'H' : ColorNamed("#eecbef"), #(0xf2e8f2),
	}
	assert(g_setStrGroup == frozenset(s_mpStrGroupColor.keys()))

	s_dSDarker = 0.5

	s_rVLighter = 1.5
	s_rSLighter = 0.5

	def __init__(self, pdf: CPdf, strGroup: str) -> None:
		super().__init__(pdf)
		self.group: CGroup = g_db.mpStrGroupGroup[strGroup]
		self.color: SColor = self.s_mpStrGroupColor[strGroup]
		self.colorDarker = ColorResaturate(self.color, dS=self.s_dSDarker)
		self.colorLighter = ColorResaturate(self.color, rV=self.s_rVLighter, rS=self.s_rSLighter)

	def Draw(self, pos: SPoint) -> None:

		rectAll = SRect(pos.x, pos.y, self.s_dX, self.s_dY)

		# black/color/black borders

		rectAll = self.RectInsetDrawBox(rectAll, self.s_dSLineOuter, colorBlack)
		rectAll = self.RectInsetDrawBox(rectAll, self.s_dSLineInner, self.color)
		rectAll = self.RectInsetDrawBox(rectAll, self.s_dSLineOuter, colorBlack)

		# title

		#dYTitle = dY * self.s_uYTitle
		dYTitle = rectAll.dX / self.s_rSGroup
		rectTitle = SRect(
						rectAll.x,
						rectAll.y,
						rectAll.dX,
						dYTitle)

		self.FillWithin(rectTitle, self.color)

		dYGroupName = dYTitle * 1.3
		oltbGroupName = self.Oltb(rectTitle, 'Consolas-Bold', dYGroupName)
		rectGroupName = oltbGroupName.RectDrawText(
										self.group.strName,
										self.colorDarker,
										JH.Right,
										JV.Middle)

		rectGroupLabel = SRect(
							rectTitle.x,
							rectTitle.y,
							rectGroupName.x - rectTitle.x,
							rectTitle.dY)

		uGroupLabel = 0.65
		oltbGroupLabel = self.Oltb(rectGroupLabel, 'Calibri', dYTitle * uGroupLabel, dSMargin=oltbGroupName.dSMargin)
		oltbGroupLabel.DrawText('Group', colorWhite, JH.Right) #, JV.Top)

		# heading

		#dYHeading = dY * self.s_uYHeading
		dYHeading = dYTitle / 4.0
		rectHeading = SRect(
						rectAll.x,
						rectTitle.y + rectTitle.dY,
						rectAll.dX,
						dYHeading)

		self.FillWithin(rectHeading, colorBlack)

		# teams

		dYTeams = rectAll.dY - (dYTitle + dYHeading)
		dYTeam = dYTeams / len(self.group.mpStrSeedTeam)
		rectTeam = SRect(rectHeading.x, 0, rectHeading.dX, dYTeam)

		for i in range(len(self.group.mpStrSeedTeam)):
			rectTeam.y = rectHeading.y + rectHeading.dY + i * dYTeam
			color = self.colorLighter if (i & 1) else colorWhite
			self.FillWithin(rectTeam, color)

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

		self.pdf.set_line_width(self.s_dSLineStats)
		self.pdf.set_draw_color(0) # black
	
		self.pdf.line(rectPoints.x, rectHeading.y + rectHeading.dY, rectPoints.x, rectAll.y + rectAll.dY)
		self.pdf.line(rectGoalsFor.x, rectHeading.y + rectHeading.dY, rectGoalsFor.x, rectAll.y + rectAll.dY)
		self.pdf.line(rectGoalsAgainst.x, rectHeading.y + rectHeading.dY, rectGoalsAgainst.x, rectAll.y + rectAll.dY)

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

class CMatchBlot(CBlot): # tag = dayb
	def __init__(self, dayb: 'CDayBlot', match: CMatch, rect: SRect) -> None:
		super().__init__(dayb.pdf)
		self.dayb = dayb
		self.match = match
		self.rect = rect

		self.dYInfo = dayb.dYTime + dayb.s_dSScore
		dYGap = (self.rect.dY - self.dYInfo) / 3.0
		self.yTime = self.rect.y + dYGap
		self.yScore = self.yTime + dayb.dYTime + dYGap

	def DrawFill(self) -> None:
		lColor = [self.dayb.mpStrGroupGroupb[strGroup].color for strGroup in self.match.lStrGroup]

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
			lRc.append(SRectColor(copy.copy(self.rect), lColor[0]))
			lRc[-1].rect.dX /= 2.0

			lRc.append(SRectColor(copy.copy(self.rect), lColor[1]))
			lRc[-1].rect.dX /= 2.0
			lRc[-1].rect.x += lRc[-1].rect.dX
		else:
			lColor = [self.dayb.mpStrGroupGroupb[strGroup].colorLighter for strGroup in g_lStrGroup]
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

		rectTime = SRect(self.rect.x, self.yTime, self.rect.dX, self.dayb.dYTime)
		strTime = self.match.tStart.format('HH:mma')
		oltbTime = self.Oltb(rectTime, self.dayb.s_strFontTime, self.dayb.s_dYFontTime)
		oltbTime.DrawText(strTime, colorBlack, JH.Center)

		# dash between score boxes

		dXLineGap = self.dayb.s_dSScore / 2.0
		dXLine = dXLineGap / 2.0
		xLineMin = self.rect.x + (self.rect.dX / 2.0) - (dXLine / 2.0)
		xLineMax = xLineMin + dXLine
		yLine = self.yScore + (self.dayb.s_dSScore / 2.0)
		self.pdf.set_line_width(self.dayb.s_dSLineScore)
		self.pdf.set_draw_color(0) # black
		self.pdf.line(xLineMin, yLine, xLineMax, yLine)

		# score boxes

		xHomeBox = self.rect.x + (self.rect.dX / 2.0) - ((dXLineGap / 2.0 ) + self.dayb.s_dSScore)
		rectHomeBox = SRect(xHomeBox, self.yScore, self.dayb.s_dSScore, self.dayb.s_dSScore)
		self.DrawBox(rectHomeBox, self.dayb.s_dSLineScore, colorBlack)

		xAwayBox = self.rect.x + (self.rect.dX / 2.0) + (dXLineGap / 2.0 )
		rectAwayBox = SRect(xAwayBox, self.yScore, self.dayb.s_dSScore, self.dayb.s_dSScore)
		self.DrawBox(rectAwayBox, self.dayb.s_dSLineScore, colorBlack)

		# team labels

		dXLabels = self.rect.dX - (2 * self.dayb.s_dSScore) - dXLineGap
		dXLabel = dXLabels / 2.0

		rectHomeLabel = SRect(self.rect.x, self.yScore, dXLabel, self.dayb.s_dSScore)
		oltbHomeLabel = self.Oltb(rectHomeLabel, 'Consolas', self.dayb.s_dSScore)
		oltbHomeLabel.DrawText(self.match.strHome, colorBlack, JH.Center)

		rectAwayLabel = SRect(self.rect.x + self.rect.dX - dXLabel, self.yScore, dXLabel, self.dayb.s_dSScore)
		oltbAwayLabel = self.Oltb(rectAwayLabel, 'Consolas', self.dayb.s_dSScore)
		oltbAwayLabel.DrawText(self.match.strAway, colorBlack, JH.Center)

class CDayBlot(CBlot): # tag = dayb

	s_dX = 2.25
	s_dY = s_dX # square
	s_dSLineOuter = CGroupBlot.s_dSLineOuter
	s_dSLineScore = CGroupBlot.s_dSLineStats

	s_uYDate = 0.06
	s_dYDate = s_dY * s_uYDate

	s_uYTime = 0.075
	s_strFontTime = 'Calibri'
	s_dYFontTime = s_dY * s_uYTime
	
	# scores are square, so we use dS

	s_uSScore = 0.147
	s_dSScore = s_dY * s_uSScore
	s_dSScoreGap = s_dSScore / 2.0

	def __init__(self, pdf: CPdf, mpStrGroupGroupb: dict[str, CGroupBlot], lMatch: list[CMatch]) -> None:
		super().__init__(pdf)
		self.mpStrGroupGroupb = mpStrGroupGroupb
		self.lMatch = lMatch
		for match in lMatch[1:]:
			assert lMatch[0].tStart.date() == match.tStart.date()
		# BB (bruceo) only include year/month sometimes
		self.strDate = lMatch[0].tStart.format("MMMM Do")
		self.dYTime = CFontInstance(self.pdf, self.s_strFontTime, self.s_dYFontTime).dYCap

	def Draw(self, pos: SPoint) -> None:

		rectAll = SRect(pos.x, pos.y, self.s_dX, self.s_dY)

		# black border

		rectAll = self.RectInsetDrawBox(rectAll, self.s_dSLineOuter, colorBlack)

		# Date

		rectDate = SRect(
						rectAll.x,
						rectAll.y,
						rectAll.dX,
						self.s_dYDate)
		oltbHeading = self.Oltb(rectDate, 'Calibri', rectDate.dY, strStyle='I')
		oltbHeading.DrawText(self.strDate, colorBlack)

		rectAll.y += rectDate.dY
		rectAll.dY -= rectDate.dY

		# count the time segments

		dYMatch = rectAll.dY / len(self.lMatch)

		# draw matches top to bottom

		lMatchb: list[CMatchBlot] = []
		yMatch = rectAll.y

		for match in self.lMatch:
			lMatchb.append(CMatchBlot(self, match, SRect(rectAll.x, yMatch, rectAll.dX, dYMatch)))
			yMatch += dYMatch

		pass

		for matchb in lMatchb:
			matchb.DrawFill()

		for matchb in lMatchb:
			matchb.DrawInfo()

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
pdf.add_font(family='Consolas-Bold', fname=r'fonts\consolab.ttf')
pdf.add_font(family='Lucida-Console', fname=r'fonts\lucon.ttf')
pdf.add_font(family='Calibri', fname=r'fonts\calibri.ttf')
pdf.add_font(family='Calibri', style='I', fname=r'fonts\calibrili.ttf')

rectPage = SRect(0, 0, pdf.w, pdf.h)

mpStrGroupGroupb = {strGroup:CGroupBlot(pdf, strGroup) for strGroup in g_lStrGroup}

def DrawGroups(pdf: CPdf):

	pdf.add_page(orientation='portrait', format='c3')

	dSMargin = 0.5

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
					dSMargin + row * dYGrid)
			groupb.Draw(pos)

def DrawDays(pdf: CPdf):

	pdf.add_page(orientation='landscape', format='c3')

	dSMargin = 0.25

	dXGrid = CDayBlot.s_dX + dSMargin
	dYGrid = CDayBlot.s_dY + dSMargin

	lDayb: list[CDayBlot] = []

	# lIdMatch = (1,2,5,9,49,51,57,59)
	# setDate: set[any] = {g_db.mpIdMatch[idMatch].tStart.date() for idMatch in lIdMatch}
	for dateMatch in sorted(g_db.mpDateSetMatch):
		setMatch = g_db.mpDateSetMatch[dateMatch]
		lMatch = sorted(setMatch, key=lambda match: match.tStart)

		lDayb.append(CDayBlot(pdf, mpStrGroupGroupb, lMatch))

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

DrawGroups(pdf)
#DrawDays(pdf)

pdf.output("poster.pdf")