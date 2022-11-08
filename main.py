import os
import subprocess
import webbrowser

from pathlib import Path
from reportlab.lib.pagesizes import A1, A2, A3, A4, A5, B1, B2, B3, B4, B5, C1, C2, C3, C4, C5, landscape
from reportlab.lib.units import inch, cm, mm
from reportlab.lib.colors import Color, HexColor, white, pink, black, red, blue, green, skyblue
from reportlab.pdfgen.canvas import Canvas as CCanvas
from reportlab.graphics.shapes import Rect

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

class CGroup(CPoser):

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

		x, y, dX, dY = self.RectDrawWithin(x, y, dX, dY, self.s_dSLineOuter, black)
		x, y, dX, dY = self.RectDrawWithin(x, y, dX, dY, self.s_dSLineInner, self.color)
		x, y, dX, dY = self.RectDrawWithin(x, y, dX, dY, self.s_dSLineOuter, black)

		dYTitle = dY * self.s_uYTitle
		yTitle = y + dY - dYTitle

		dYHeading = dY * self.s_uYHeading
		yHeading = yTitle - dYHeading

		self.FillWithin(x, yTitle, dX, dYTitle, self.color)
		self.FillWithin(x, yHeading, dX, dYHeading, black)

		dYTeams = dY - (dYTitle + dYHeading)
		dYTeam = dYTeams / self.s_cTeam
		yTeam = yHeading - dYTeam

		for i in range(self.s_cTeam):
			color = self.color if (i & 1) else white
			self.FillWithin(x, yTeam, dX, dYTeam, color, self.s_uAlphaTeam)
			yTeam -= dYTeam

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

pathDst = Path('poster.pdf').absolute()
strPathDst = str(pathDst)

c = CCanvas(str(pathDst), pagesize=landscape(C4))

#c.drawString(100,750,'Welcome to paradise. Your lear jet is waiting.')
#coords(c)
groupA = CGroup(c, HexColor(0x94D9F5))
groupB = CGroup(c, HexColor(0xFEE289))

groupA.Draw(1*inch, 5*inch)
groupB.Draw(1*inch, 2*inch)

c.save()

#webbrowser.open(f'file://{str(pathDst)}', new=2)
#subprocess.Popen(["start", str(pathDst)], creationflags=subprocess.CREATE_NEW_CONSOLE, shell=True)
#print('waiting...')
#pass


