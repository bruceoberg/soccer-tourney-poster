import arrow
import colorsys
import yaml

from pathlib import Path

from reportlab.lib.pagesizes import A1, A2, A3, A4, A5, B1, B2, B3, B4, B5, C1, C2, C3, C4, C5, landscape
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

# width to height ratios
g_ratioGroup = 5.0
g_ratioTeam = 6.0

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

class CBlot:
	"""something drawable at a location. some blots may contain other blots."""
	def __init__(self, c: Canvas) -> None:
		self.c = c

	def RectDrawWithin(self, x: float, y: float, dX: float, dY: float, dSLine: float, color: Color) -> tuple[float, float, float, float]:
		x += 0.5 * dSLine
		y += 0.5 * dSLine
		dX -= dSLine
		dY -= dSLine
		self.c.setLineWidth(dSLine)
		self.c.setStrokeColor(color)
		self.c.rect(x, y, dX, dY)
		return (x + 0.5 * dSLine, y + 0.5 * dSLine, dX - dSLine, dY - dSLine)

	def FillWithin(self, x: float, y: float, dX: float, dY: float, color: Color, uAlpha: float = 1.0) -> None:
		self.c.setFillColor(color, alpha=uAlpha)
		self.c.rect(x, y, dX, dY, stroke=0, fill=1)

	def DYFontCap(self) -> float:
		"""font cap height. aped from pdfmetrics.getAscentDescent()"""
		font = pdfmetrics.getFont(self.c._fontname)
		size = self.c._fontsize
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
			dYCap = pdfmetrics.getAscent(self.c._fontname, self.c._fontsize)
		if self.c._fontsize:
			norm = self.c._fontsize / 1000.0
			return dYCap*norm
		return dYCap

	def Draw(x: float, y: float) -> None:
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

	# unused while we experiment with ISO ratios
	# s_uYTitle = 0.3
	# s_uYHeading = 0.08
	# s_uXTeamArea = 0.35

	s_uAlphaTeam = 0.5

	def __init__(self, c: Canvas, strGroup: str) -> None:
		super().__init__(c)
		self.group: CGroup = g_db.mpStrGroupGroup[strGroup]
		self.color: Color = self.s_mpStrGroupColor[strGroup]

	def Draw(self, x: float, y: float) -> None:
		self.c.setLineJoin(0)

		dX, dY = self.s_dX, self.s_dY

		# black/color/black borders

		x, y, dX, dY = self.RectDrawWithin(x, y, dX, dY, self.s_dSLineOuter, black)
		x, y, dX, dY = self.RectDrawWithin(x, y, dX, dY, self.s_dSLineInner, self.color)
		x, y, dX, dY = self.RectDrawWithin(x, y, dX, dY, self.s_dSLineOuter, black)

		# title

		#dYTitle = dY * self.s_uYTitle
		dYTitle = dX / g_ratioGroup
		yTitle = y + dY - dYTitle

		self.FillWithin(x, yTitle, dX, dYTitle, self.color)

		dYGroupName = dYTitle * 1.3
		self.c.setFont('Consolas-Bold', dYGroupName)
		dYCap = self.DYFontCap()
		dSAdjust = max(0.0, (dYTitle - dYCap) / 2.0)

		xGroupName = x + dX - dSAdjust
		yGroupName = yTitle + dSAdjust
		self.c.setFillColor(ColorResaturate(self.color, 0.5))
		self.c.drawRightString(xGroupName, yGroupName, self.group.strName)
		dXGroupName = self.c.stringWidth(self.group.strName)

		uGroupLabel = 0.65
		dYGroupLabel = dYTitle * uGroupLabel
		self.c.setFont('Calibri', dYGroupLabel)
		dYCap = self.DYFontCap()

		xGroupLabel = xGroupName - dXGroupName # x + dSAdjust
		yGroupLabel = yTitle + dYTitle - (dYCap + dSAdjust)
		self.c.setFillColor(white) # ColorResaturate(self.color, -0.5))
		self.c.drawRightString(xGroupLabel, yGroupLabel, 'Group')

		# heading

		#dYHeading = dY * self.s_uYHeading
		dYHeading = dYTitle / 4.0
		yHeading = yTitle - dYHeading

		self.FillWithin(x, yHeading, dX, dYHeading, black)

		# teams

		dYTeams = dY - (dYTitle + dYHeading)
		dYTeam = dYTeams / len(self.group.mpStrSeedTeam)

		xTeamArea = x
		#dXTeamArea = dX * self.s_uXTeamArea
		dXTeamArea = dYTeam * g_ratioTeam
		xPoints = x + dXTeamArea

		for i in range(len(self.group.mpStrSeedTeam)):
			yTeam = yHeading - (i + 1) * dYTeam
			color = self.color if (i & 1) else white
			self.FillWithin(x, yTeam, dX, dYTeam, color, self.s_uAlphaTeam)

		for i, strSeed in enumerate(sorted(self.group.mpStrSeedTeam)):
			yTeam = yHeading - (i + 1) * dYTeam
			team = self.group.mpStrSeedTeam[strSeed]

			dYTeamAbbrev = dYTeam
			self.c.setFont('Consolas', dYTeamAbbrev)
			dYCap = self.DYFontCap()
			dSAdjust = max(0.0, (dYTeam - dYCap) / 2.0)

			xTeamAbbrev = xTeamArea + dXTeamArea - dSAdjust
			yTeamAbbrev = yTeam + dSAdjust
			self.c.setFillColor(black)
			self.c.drawRightString(xTeamAbbrev, yTeamAbbrev, team.strAbbrev)

			uTeamText = 0.75
			dYTeamText = dYTeam * uTeamText
			self.c.setFont('Calibri', dYTeamText)
			dYCap = self.DYFontCap()

			xTeamText = xTeamArea + dSAdjust
			yTeamText = yTeam + dYTeam - (dYCap + dSAdjust)
			self.c.setFillColor(darkgrey)
			self.c.drawString(xTeamText, yTeamText, team.strName)

		# dividers for country/points/gf/ga

		dXStats = (dX - dXTeamArea) / 3.0
		xGoalsFor = xPoints + dXStats
		xGoalsAgainst = xGoalsFor + dXStats

		self.c.setLineWidth(self.s_dSLineStats)
		self.c.setStrokeColor(black)
	
		self.c.line(xPoints, y, xPoints, yHeading)
		self.c.line(xGoalsFor, y, xGoalsFor, yHeading)
		self.c.line(xGoalsAgainst, y, xGoalsAgainst, yHeading)

		# heading labels

		lTuXStr = (
			#(xTeamArea + dXTeamArea / 2.0, "COUNTRY"),
			(xPoints + dXStats / 2.0, "PTS"),
			(xGoalsFor + dXStats / 2.0, "GF"),
			(xGoalsAgainst + dXStats / 2.0, "GA"),
		)

		self.c.setFont('Calibri', dYHeading)
		dYCap = self.DYFontCap()
		yHeadingText = yHeading + max(0.0, (dYHeading - dYCap) / 2.0)
		self.c.setFillColor(white)

		for xHeading, strHeading in lTuXStr:
			self.c.drawCentredString(xHeading, yHeadingText, strHeading)

pathDst = Path('poster.pdf').absolute()
strPathDst = str(pathDst)

c = Canvas(str(pathDst), pagesize=landscape(C2))

lGroupb = [CGroupBlot(c, strGroup) for strGroup in g_lStrGroup]

for col in range(2):
	for row in range(4):
		groupb = lGroupb[col * 4 + row]
		dX = CGroupBlot.s_dX + 1.0*inch
		dY = CGroupBlot.s_dY + 1.0*inch
		x = 1.0*inch + col * dX
		y = 1.0*inch + ((4 - row) * dY)
		groupb.Draw(x, y)

c.save()

