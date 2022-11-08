import arrow
import math
import yaml

from pathlib import Path

from reportlab.lib.pagesizes import A1, A2, A3, A4, A5, B1, B2, B3, B4, B5, C1, C2, C3, C4, C5, landscape
from reportlab.lib.units import inch, cm, mm
from reportlab.lib.colors import Color, HexColor, white, pink, black, red, blue, green, skyblue
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen.canvas import Canvas as CCanvas

s_ratioISO = math.sqrt(2.0)
s_ratioISOx2 = s_ratioISO * 2.0

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
		
		self.mpIdGroup: dict[str, CGroup] = {strGroup:CGroup(strGroup) for strGroup in ('A', 'B', 'C', 'D', 'E', 'F', 'G', 'H')}

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

				group = self.mpIdGroup[strSeed[:1]]
				group.AddTeam(team)

			self.mpIdMatch: dict[int, CMatch] = {mpKV['match']:CMatch(self, mpKV) for mpKV in objTop['matches']}
				

class CPoser:
	def __init__(self, c: CCanvas) -> None:
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

	def Draw(x: float, y: float) -> None:
		pass

class CGroupP(CPoser):

	s_cTeam = 4

	s_dX = 4.5*inch
	s_dY = 2.5*inch
	s_dSLineOuter = 0.02*inch
	s_dSLineInner = 0.008*inch
	s_dSLineFills = 0.01*inch

	s_uYTitle = 0.3
	s_uYHeading = 0.08
	s_uAlphaTeam = 0.5
	s_uXTeamName = 0.35

	def __init__(self, c: CCanvas, color: Color) -> None:
		super().__init__(c)
		self.color = color

	def Draw(self, x: float, y: float) -> None:
		self.c.setLineJoin(0)

		dX, dY = self.s_dX, self.s_dY

		# black/color/black borders

		x, y, dX, dY = self.RectDrawWithin(x, y, dX, dY, self.s_dSLineOuter, black)
		x, y, dX, dY = self.RectDrawWithin(x, y, dX, dY, self.s_dSLineInner, self.color)
		x, y, dX, dY = self.RectDrawWithin(x, y, dX, dY, self.s_dSLineOuter, black)

		# title and heading rects

		#dYTitle = dY * self.s_uYTitle
		dYTitle = dX / s_ratioISOx2
		yTitle = y + dY - dYTitle

		#dYHeading = dY * self.s_uYHeading
		dYHeading = dYTitle / 4.0
		yHeading = yTitle - dYHeading

		self.FillWithin(x, yTitle, dX, dYTitle, self.color)
		self.FillWithin(x, yHeading, dX, dYHeading, black)

		# team rects

		dYTeams = dY - (dYTitle + dYHeading)
		dYTeam = dYTeams / self.s_cTeam
		yTeam = yHeading - dYTeam

		for i in range(self.s_cTeam):
			color = self.color if (i & 1) else white
			self.FillWithin(x, yTeam, dX, dYTeam, color, self.s_uAlphaTeam)
			yTeam -= dYTeam

		# dividers for country/points/gf/ga

		dXTeamName = dX * self.s_uXTeamName
		xTeamName = x + dXTeamName
		dXFills = (dX - dXTeamName) / 3.0
		xFills1 = xTeamName + dXFills
		xFills2 = xFills1 + dXFills

		self.c.setLineWidth(self.s_dSLineFills)
		self.c.setStrokeColor(black)
	
		self.c.line(xTeamName, y, xTeamName, yHeading)
		self.c.line(xFills1, y, xFills1, yHeading)
		self.c.line(xFills2, y, xFills2, yHeading)

		# heading labels

		lTuXStr = (
			(x + dXTeamName / 2.0, "COUNTRY"),
			(xTeamName + dXFills / 2.0, "POINTS"),
			(xFills1 + dXFills / 2.0, "GF"),
			(xFills2 + dXFills / 2.0, "GA"),
		)

		dYDescent = pdfmetrics.getDescent('Helvetica', dYHeading)
		yHeadingText = yHeading + abs(dYDescent) / 2.0
		self.c.setFont('Helvetica', dYHeading)
		self.c.setFillColor(white)

		for xHeading, strHeading in lTuXStr:
			self.c.drawCentredString(xHeading, yHeadingText, strHeading)

db = CDataBase()

pathDst = Path('poster.pdf').absolute()
strPathDst = str(pathDst)

c = CCanvas(str(pathDst), pagesize=landscape(C4))

groupA = CGroupP(c, HexColor(0x94D9F5))
groupB = CGroupP(c, HexColor(0xFEE289))

groupA.Draw(1*inch, 5*inch)
groupB.Draw(1*inch, 2*inch)

c.save()

