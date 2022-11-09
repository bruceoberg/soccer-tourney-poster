import arrow
import colorsys
import copy
import yaml

from aenum import Enum, AutoNumberEnum
from dataclasses import dataclass
from pathlib import Path

from reportlab.lib.pagesizes import A1, A2, A3, A4, A5, A6, B1, B2, B3, B4, B5, B6, C1, C2, C3, C4, C5, C6, landscape, portrait
from reportlab.lib.units import inch, cm, mm
from reportlab.lib.colors import Color, HexColor, white, black, red, blue, green, grey, darkgrey, lightgrey
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

pdfmetrics.registerFont(TTFont('Consolas', 'consola.ttf'))
pdfmetrics.registerFont(TTFont('Consolas-Bold', 'consolab.ttf'))
pdfmetrics.registerFont(TTFont('Lucida-Console', 'lucon.ttf'))
pdfmetrics.registerFont(TTFont('Calibri', 'calibri.ttf'))

g_lStrGroup = ('A', 'B', 'C', 'D', 'E', 'F', 'G', 'H')

@dataclass
class Point:
	x: float = 0
	y: float = 0

@dataclass
class Rect(Point):
	dX: float = 0
	dY: float = 0

def ColorResaturate(color: Color, dS: float) -> Color:
	h, s, v = colorsys.rgb_to_hsv(color.red, color.green, color.blue)
	s = min(1.0, max(0.0, s + dS))
	r, g, b = colorsys.hsv_to_rgb(h, s, v)
	return Color(r, g, b)

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
				
g_db = CDataBase()

class JH(AutoNumberEnum):
	Left = ()
	Center = ()
	Right = ()

class JV(AutoNumberEnum):
	Bottom = ()
	Middle = ()
	Top = ()

class COneLineTextBox:
	"""a box with a single line of text in a particular font, sized to fit the box"""
	def __init__(self, strFont: str, dYFont, rect: Rect, dSMargin: float = None) -> None:
		self.strFont = strFont
		self.dYFont = dYFont
		self.rect = rect

		self.dYCap = self.DYCap()
		self.dSMargin = dSMargin or max(0.0, (self.rect.dY - self.dYCap) / 2.0)

	def RectMargin(self) -> Rect:
		return Rect(
				self.rect.x + self.dSMargin,
				self.rect.y + self.dSMargin,
				self.rect.dX - 2.0 * self.dSMargin,
				self.rect.dY - 2.0 * self.dSMargin)

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

class CBlot:
	"""something drawable at a location. some blots may contain other blots."""

	def __init__(self, c: Canvas) -> None:
		self.c = c

	def RectDrawWithin(self, rect: Rect, dSLine: float, color: Color) -> Rect:
		x = rect.x + 0.5 * dSLine
		y = rect.y + 0.5 * dSLine
		dX = rect.dX - dSLine
		dY = rect.dY - dSLine
		self.c.setLineWidth(dSLine)
		self.c.setStrokeColor(color)
		self.c.rect(x, y, dX, dY)
		return Rect(x + 0.5 * dSLine, y + 0.5 * dSLine, dX - dSLine, dY - dSLine)

	def FillWithin(self, rect: Rect, color: Color, uAlpha: float = 1.0) -> None:
		self.c.setFillColor(color, alpha=uAlpha)
		self.c.rect(rect.x, rect.y, rect.dX, rect.dY, stroke=0, fill=1)

	def RectDrawText(self, strText: str, color: Color, oltb : COneLineTextBox, jh : JH = JH.Left, jv: JV = JV.Middle) -> Rect:
		self.c.setFont(oltb.strFont, oltb.dYFont)
		rectText = Rect(0, 0, self.c.stringWidth(strText), oltb.dYCap)
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

		return rectText

	def Draw(pos: Point) -> None:
		pass

class CGroupBlot(CBlot):

	# BB (bruceo) put these in the yaml

	s_mpStrGroupColor: dict[str, Color] = {
		'A' : HexColor(0x94D9F5),
		'B' : HexColor(0xFEE289),
		'C' : HexColor(0xf79d8f),
		'D' : HexColor(0xc4e1b5),
		'E' : HexColor(0xb0d0ee),
		'F' : HexColor(0xc0e4df),
		'G' : HexColor(0xfab077),
		'H' : HexColor(0xf2e8f2),
	}
	assert(set(g_lStrGroup) == set(s_mpStrGroupColor.keys()))

	s_cTeam = 4

	s_dX = 4.5*inch
	s_dY = 2.5*inch
	s_dSLineOuter = 0.02*inch
	s_dSLineInner = 0.008*inch
	s_dSLineStats = 0.01*inch

	# width to height ratios
	s_ratioGroup = 5.0
	s_ratioCountry = 6.0
	s_uAlphaTeam = 0.5

	def __init__(self, c: Canvas, strGroup: str) -> None:
		super().__init__(c)
		self.group: CGroup = g_db.mpStrGroupGroup[strGroup]
		self.color: Color = self.s_mpStrGroupColor[strGroup]

	def Draw(self, pos: Point) -> None:
		self.c.setLineJoin(0)

		rectAll = Rect(pos.x, pos.y, self.s_dX, self.s_dY)

		# black/color/black borders

		rectAll = self.RectDrawWithin(rectAll, self.s_dSLineOuter, black)
		rectAll = self.RectDrawWithin(rectAll, self.s_dSLineInner, self.color)
		rectAll = self.RectDrawWithin(rectAll, self.s_dSLineOuter, black)

		# title

		#dYTitle = dY * self.s_uYTitle
		dYTitle = rectAll.dX / self.s_ratioGroup
		rectTitle = Rect(
						rectAll.x,
						rectAll.y + rectAll.dY - dYTitle,
						rectAll.dX,
						dYTitle)

		self.FillWithin(rectTitle, self.color)

		dYGroupName = dYTitle * 1.3
		oltbGroupName = COneLineTextBox('Consolas-Bold', dYGroupName, rectTitle)
		rectGroupName = self.RectDrawText(
								self.group.strName,
								ColorResaturate(self.color, 0.5),
								oltbGroupName,
								JH.Right,
								JV.Middle)

		rectGroupLabel = Rect(
							rectTitle.x,
							rectTitle.y,
							rectGroupName.x - rectTitle.x,
							rectTitle.dY)

		uGroupLabel = 0.65
		oltbGroupLabel = COneLineTextBox('Calibri', dYTitle * uGroupLabel, rectGroupLabel, dSMargin=oltbGroupName.dSMargin)
		self.RectDrawText('Group', white, oltbGroupLabel, JH.Right, JV.Top)

		# heading

		#dYHeading = dY * self.s_uYHeading
		dYHeading = dYTitle / 4.0
		rectHeading = Rect(
						rectAll.x,
						rectTitle.y - dYHeading,
						rectAll.dX,
						dYHeading)

		self.FillWithin(rectHeading, black)

		# countries

		dYCountries = rectAll.dY - (dYTitle + dYHeading)
		dYCountry = dYCountries / len(self.group.mpStrSeedTeam)
		rectCountry = Rect(rectHeading.x, 0, dYCountry * self.s_ratioCountry, dYCountry)

		for i in range(len(self.group.mpStrSeedTeam)):
			rectCountry.y = rectHeading.y - (i + 1) * dYCountry
			color = self.color if (i & 1) else white
			self.FillWithin(rectCountry, color, self.s_uAlphaTeam)

		for i, strSeed in enumerate(sorted(self.group.mpStrSeedTeam)):
			rectCountry.y = rectHeading.y - (i + 1) * dYCountry
			team = self.group.mpStrSeedTeam[strSeed]

			oltbAbbrev = COneLineTextBox('Consolas', dYCountry, rectCountry)
			self.RectDrawText(team.strAbbrev, black, oltbAbbrev, JH.Right)

			uTeamText = 0.75
			oltbName = COneLineTextBox('Calibri', dYCountry * uTeamText, rectCountry, dSMargin=oltbAbbrev.dSMargin)
			self.RectDrawText(team.strName, darkgrey, oltbName, JH.Left, JV.Top)

		# dividers for country/points/gf/ga

		dXStats = (rectAll.dX - rectCountry.dX) / 3.0

		rectPoints = Rect(
						rectCountry.x + rectCountry.dX,
						rectHeading.y,
						dXStats,
						rectHeading.dY)
		rectGoalsFor = Rect(
						rectPoints.x + rectPoints.dX,
						rectHeading.y,
						dXStats,
						rectHeading.dY)
		rectGoalsAgainst = Rect(
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
			#(rectCountry, "COUNTRY"),
			(rectPoints,		"PTS"),
			(rectGoalsFor,		"GF"),
			(rectGoalsAgainst,	"GA"),
		)

		for rectHeading, strHeading in lTuRectStr:
			oltbHeading = COneLineTextBox('Calibri', rectHeading.dY, rectHeading)
			self.RectDrawText(strHeading, white, oltbHeading, JH.Center)

pathDst = Path('poster.pdf').absolute()
strPathDst = str(pathDst)

c = Canvas(str(pathDst), pagesize=portrait(C3))

lGroupb = [CGroupBlot(c, strGroup) for strGroup in g_lStrGroup]

dX = CGroupBlot.s_dX + 1.0*inch
dY = CGroupBlot.s_dY + 1.0*inch

for col in range(2):
	for row in range(4):
		groupb = lGroupb[col * 4 + row]
		pos = Point(0.5*inch + col * dX, 0.5*inch + ((4 - row) * dY))
		groupb.Draw(pos)

c.save()

