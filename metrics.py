from typing import NamedTuple

# this appears to be the least gross way to create constants within a namespace

class Page(NamedTuple):
	strOrientation: str = 'landscape'
	strFormat: str = 'letter'
	dX: float = 11
	dY: float = 8.5
	dXLeft: float = 0.25
	dXRight: float = 0.25
	dYTop: float = 0.25
	dYBottom: float = 0.25

	@property
	def dXLive(self) -> float:
		return self.dX - (self.dXLeft + self.dXRight)
	@property
	def dYLive(self) -> float:
		return self.dY - (self.dYTop + self.dYBottom)

page = Page()

class Text(NamedTuple):
	strFont: str = 'NotoSans'
	ptHorizontalLine = 0.5
	ptHead: float = 22
	fHeadBold: bool = True
	ptSubhead: float = 10
	ptSubheadSpaceAfter: float = 10
	fSubheadItalic: bool = True
	ptMonth: float = 21
	ptDay: float = 14
	ptDayPrefix: float = 9
	fDayPrefixItalic: bool = True
	ptPickup: float = 11

	@property
	def strEighthptHorizontalLine(self) -> str:
		return str(int(self.ptHorizontalLine * 8))

text = Text()

class Table(NamedTuple):
	dXMonthLeft: float = 1.46
	dXMonthRight: float = 0.86
	dXCellMargin: float = 0.03
	dYCellMargin: float = 0.02

table = Table()