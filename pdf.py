import arabic_reshaper
import bidi.algorithm
import colorsys
import copy
import fpdf
import unicategories
import unicodedata

from enum import Enum, auto
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

@dataclass
class SFontKey:
	strFont: str
	strStyle: str

	def Str(self) -> str:
		return self.strFont.lower() + self.strStyle

class CPdf(fpdf.FPDF):
	s_mpStrFormatWH: dict[str, tuple[float, float]] ={
		'a0': (2383.94, 3370.39),
		'a1': (1683.78, 2383.94),
		'a2': (1190.55, 1683.78),
		'a3': (841.89, 1190.55),
		'a4': (595.28, 841.89),
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
		'a5': (419.53, 595.28),
		'a6': (297.64, 419.53),
		'a7': (209.76, 297.64),
		'a8': (147.40, 209.76),
		'b0': (2834.65, 4008.19),
		'b1': (2004.09, 2834.65),
		'b2': (1417.32, 2004.09),
		'b3': (1000.63, 1417.32),
		'b4': (708.66, 1000.63),
		'b5': (498.90, 708.66),
		'b6': (354.33, 498.90),
		'b7': (249.45, 354.33),
		'b8': (175.75, 249.45),
		'b9': (124.72, 175.75),
		'b10': (87.87, 124.72),
		'c0': (2599.37, 3676.54),
		'c1': (1836.85, 2599.37),
		'c2': (1298.27, 1836.85),
		'c3': (918.43, 1298.27),
		'c4': (649.13, 918.43),
		'c5': (459.21, 649.13),
		'c6': (323.15, 459.21),
		'd0': (2185.51, 3089.76),
		'letter': (612.00, 792.00),
		'legal': (612.00, 1008.00),
		'ledger': (792.00, 1224.00),
		'tabloid': (792.00, 1224.00),
		'executive': (521.86, 756.00),
		'ansi c': (1224.57, 1584.57),
		'ansi d': (1584.57, 2449.13),
		'ansi e': (2449.13, 3169.13),
		'sra0': (2551.18, 3628.35),
		'sra1': (1814.17, 2551.18),
		'sra2': (1275.59, 1814.17),
		'sra3': (907.09, 1275.59),
		'sra4': (637.80, 907.09),
		'ra0': (2437.80, 3458.27),
		'ra1': (1729.13, 2437.80),
		'ra2': (1218.90, 1729.13),
	}

	def __init__(self):
		fpdf.fpdf.PAGE_FORMATS.update(self.s_mpStrFormatWH)

		super().__init__(unit='in')

	def AddFont(self, strFontkey: str, strStyle: str, path: Path):
		self.add_font(family=strFontkey, style=strStyle, fname=str(path))

	def TuDxDyFromOrientationFmt(self, strOrientation: str, fmt: Optional[str | tuple[float, float]]) -> tuple[float, float] | None:
		if fmt is None:
			return None

		tuDxDyPt: tuple[float, float] = fpdf.fpdf.get_page_format(fmt, self.k)
		dXPt, dYPt = tuDxDyPt

		# replicating FPDF._set_orientation()

		strOrientation = strOrientation.lower()
		if strOrientation in ("p", "portrait"):
			return (dXPt / self.k, dYPt / self.k)

		assert strOrientation in ("l", "landscape")
		return (dYPt / self.k, dXPt / self.k)

class JH(Enum):
	Left = auto()
	Center = auto()
	Right = auto()

class JV(Enum):
	Bottom = auto()
	Middle = auto()
	Top = auto()

class CFontInstance:
	"""a sized font"""
	def __init__(self, pdf: CPdf, fontkey: SFontKey, dYFont: float) -> None:
		self.pdf = pdf
		self.fontkey = fontkey
		self.dYFont = dYFont
		self.dPtFont = self.dYFont * 72.0 # inches to points

		font = pdf.fonts[self.fontkey.Str()]

		try:
			desc = font['desc']
		except TypeError:
			desc = font.desc
		
		try:
			dYCapRaw = desc['CapHeight']
		except TypeError:
			dYCapRaw = desc.cap_height
		self.dYCap = dYCapRaw * self.dYFont / 1000.0

@dataclass
class SColor: # tag = color
	r: int = 0
	g: int = 0
	b: int = 0
	a: int = 255

def ColorFromStr(strColor: str, alpha: int = 255) -> SColor:
	r, g, b = fpdf.html.color_as_decimal(strColor).colors255
	return SColor(r, g, b, alpha)

colorWhite = ColorFromStr('white')
colorGrey = ColorFromStr('grey')
colorLightGrey = ColorFromStr('lightgrey')
colorDarkgrey = ColorFromStr('darkgrey')	# NOTE (bruceo) lighter than grey!
colorDarkSlateGrey = ColorFromStr('darkslategrey')
colorBlack = ColorFromStr('black')

def ColorResaturate(color: SColor, rS: float = 1.0, dS: float = 0.0, rV: float = 1.0, dV: float = 0.0) -> SColor:
	h, s, v = colorsys.rgb_to_hsv(color.r / 255.0, color.g / 255.0, color.b / 255.0)
	s = min(1.0, max(0.0, s * rS + dS))
	v = min(1.0, max(0.0, v * rV + dV))
	r, g, b = colorsys.hsv_to_rgb(h, s, v)
	return SColor(round(r * 255), round(g * 255), round(b * 255), color.a)

def FIsSaturated(color: SColor) -> bool:
	return colorsys.rgb_to_hsv(color.r / 255.0, color.g / 255.0, color.b / 255.0)[1] > 0.0

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
		self.posMin.Shift(dS, dS)
		self.posMax.Shift(-dS, -dS)
		return self

	def Outset(self, dS: float) -> 'SRect':
		self.Inset(-dS)
		return self

	def Stretch(self, dXLeft: float = 0, dYTop: float = 0, dXRight: float = 0, dYBottom: float = 0) -> 'SRect':
		self.posMin.Shift(dXLeft, dYTop)
		self.posMax.Shift(dXRight, dYBottom)
		return self

def FHasAnyRtl(strText: str) -> bool:
	for ch in strText:
		strBidi = unicodedata.bidirectional(ch)
		if strBidi in ('AL', 'R'):
			return True

	return False

@dataclass
class SHaloArgs: # tag = haloa
	color: SColor
	uPtLine: float # factor of point size for halo line

class COneLineTextBox: # tag = oltb
	"""a box with a single line of text in a particular font, sized to fit the box"""
	
	s_strControl: str = ''.join([chr(ucp) for tuMinMax in unicategories.categories['Cf'] for ucp in range(tuMinMax[0], tuMinMax[1])])
	s_transRemoveControl = str.maketrans('', '', s_strControl)

	def __init__(self, pdf: CPdf, rect: SRect, fontkey: SFontKey, dYFont: float, dSMargin: Optional[float] = None) -> None:
		self.pdf = pdf
		self.fonti = CFontInstance(pdf, fontkey, dYFont)
		self.rect = rect

		self.dYCap = self.fonti.dYCap
		self.dSMargin = dSMargin or max(0.0, (self.rect.dY - self.dYCap) / 2.0)
		self.rectMargin = self.rect.Copy().Inset(self.dSMargin)

	def RectDrawText(self, strText: str, color: SColor, jh : JH = JH.Left, jv: JV = JV.Middle, fShrinkToFit: bool = False, haloa: Optional[SHaloArgs] = None) -> SRect:
		if FHasAnyRtl(strText):
			strText = arabic_reshaper.reshape(strText)
			strText = bidi.algorithm.get_display(strText, base_dir='R')
			strText = strText.translate(self.s_transRemoveControl)

		self.pdf.set_font(self.fonti.fontkey.strFont, style=self.fonti.fontkey.strStyle, size=self.fonti.dPtFont)
		dXText = self.pdf.get_string_width(strText)

		if fShrinkToFit and dXText > self.rectMargin.dX:
			rReduce = self.rectMargin.dX / dXText
			dYFontReduced = rReduce * self.fonti.dYFont

			self.fonti = CFontInstance(self.pdf, self.fonti.fontkey, dYFontReduced)
			self.dYCap = self.fonti.dYCap

			self.pdf.set_font(self.fonti.fontkey.strFont, style=self.fonti.fontkey.strStyle, size=self.fonti.dPtFont)
			dXText = self.pdf.get_string_width(strText)

			# BB (bruceo) assert new width fits?

		rectText = SRect(0, 0, dXText, self.dYCap)

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

		if haloa:
			dSLine = self.fonti.dPtFont * haloa.uPtLine
			with self.pdf.local_context(text_mode="STROKE", line_width=dSLine):
				self.pdf.set_draw_color(haloa.color.r, haloa.color.g, haloa.color.b)
				self.pdf.text(rectText.x, rectText.y, strText)

		self.pdf.set_text_color(color.r, color.g, color.b)
		self.pdf.text(rectText.x, rectText.y, strText)

		return rectText.Copy().Shift(dY = -rectText.dY)

	DrawText = RectDrawText

class CBlot: # tag = blot
	"""something drawable at a location. some blots may contain other blots."""

	def __init__(self, pdf: CPdf) -> None:
		self.pdf = pdf

	def DrawBox(self, rect: SRect, dSLine: float, color: SColor, colorFill: Optional[SColor] = None) -> None:
		if colorFill is None:
			strFillDraw = 'D'
		else:
			strFillDraw = 'FD'
			self.pdf.set_fill_color(colorFill.r, colorFill.g, colorFill.b)

		self.pdf.set_line_width(dSLine)
		self.pdf.set_draw_color(color.r, color.g, color.b)

		self.pdf.rect(rect.x, rect.y, rect.dX, rect.dY, style=strFillDraw)

	def FillBox(self, rect: SRect, color: SColor) -> None:
		self.pdf.set_fill_color(color.r, color.g, color.b)
		self.pdf.rect(rect.x, rect.y, rect.dX, rect.dY, style='F')

	def Oltb(self, rect: SRect, fontkey: SFontKey, dYFont: float, dSMargin: Optional[float] = None) ->COneLineTextBox:
		return COneLineTextBox(self.pdf, rect, fontkey, dYFont, dSMargin)

	def Draw(self, pos: SPoint) -> None:
		pass

