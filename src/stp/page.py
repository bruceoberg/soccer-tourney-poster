from __future__ import annotations  # Forward refs without quotes (eg foo: CFoo, not foo: 'CFoo')

import arrow
import babel.dates
import datetime
import sys

from babel import Locale
from typing import Optional, cast, TYPE_CHECKING
from zoneinfo import ZoneInfo

from bolay import SFontKey, CBlot
from bolay import JH, JV, SPoint, SRect
from bolay import ColorFromStr, SColor
from bolay import colorBlack, colorWhite, colorGrey

from .config import SPageArgs
from .fonts import StrTtfLookup
from .loc import g_loc, CZoneName, StrFmtBestFit, StrLangTerritoryFromLocale, StrScriptFromLocale, StrDateRange
from .versioning import g_repover
from .database import CTournamentDataBase, CMatch, STAGE
from .group import CGroupBlot, CGroupSetBlot
from .calendar import CDayBlot, CDayBlotList, CElimBlot, CCalendarBlot
from .bracket import CFinalBlot, CBracketBlot

if TYPE_CHECKING:
	from .main import CDocument

def StrPatternDateMMMMEEEEd(locale: Locale) -> str:
	# CLDR does not provide a skeleton for 'MMMMEEEEd' (for getting 'Sunday, November 1' in any language).
	# so for western languages (e.g. not arabic/farsi/japanese), we build 'MMMMEEEEd' from the pattern provided by 'MMMEd'.

	dtfMMMEd = locale.datetime_skeletons['MMMEd']

	if locale.language in ('ja', 'ar', 'fa'):
		return dtfMMMEd.pattern

	# the pattern can have single quotes denoting literals.
	# so skip those by splitting around them and reconstituting later.

	lStrPattern = dtfMMMEd.pattern.split("'")
	lStrPatternNew = []

	for iStr, str in enumerate(lStrPattern):
		# since we split, the odd chunks are literals we should leave alone.
		if not (iStr & 1):
			str = str.replace('E', 'EEEE', 1)
			str = str.replace('MMM', 'MMMM', 1)

		lStrPatternNew.append(str)

	return "'".join(lStrPatternNew)

class CTomorrowTime(datetime.time):  # tag = tmrt
    """
    datetime.time subclass expressing a post-midnight hour in extended-day notation,
    where the hour is always represented as actual_hour + 24.

    Constructed from a datetime.time whose hour must be < 24. The base stores
    the real hour; the .hour property adds 24 on read. .replace() is overridden
    to preserve CTomorrowTime identity through Babel's internal tz-attachment call.
    """

    @property
    def hour(self) -> int:  # type: ignore[override]
        return super().hour + 24

    def replace(self, **kwargs: object) -> CTomorrowTime:  # type: ignore[override]
        """
        Preserve CTomorrowTime identity through Babel's internal replace() call.
        Only tzinfo replacement is expected; anything touching hour would corrupt
        the extended-hour value.
        """
        assert set(kwargs.keys()) <= {'tzinfo'}, \
            f"CTomorrowTime.replace() called with unexpected keys: {set(kwargs.keys())}"
        return CTomorrowTime(
            super().hour,
            self.minute,
            self.second,
            self.microsecond,
            kwargs.get('tzinfo'),  # type: ignore[arg-type]
        )

class CPage:

	s_dSLineCropMarks = 0.008
	s_colorCropMarks = colorGrey

	# "darkslategray": "#2f4f4f", (47)
	# "lightgrey": "#d3d3d3", (211)
	# (211 - 47) / 3 = 41

	s_mpStageColorBorder: dict[STAGE, SColor] = {
		STAGE.Round64: ColorFromStr("#585858"),		# 47 + 41 = 88 (0x58)
		STAGE.Round32: ColorFromStr("#585858"),
		STAGE.Round16: ColorFromStr("#585858"),
		STAGE.Quarters: ColorFromStr("#818181"),	# 88 + 41 = 129 (0x81)
		STAGE.Semis: ColorFromStr("#aaaaaa"),		# 129 + 41 = 170 (0xaa)
	}

	def __init__(self, doc: CDocument, pagea: SPageArgs):
		self.doc = doc
		self.pdf = doc.pdf
		self.pagea = pagea

		if pagea.strNameTourn:
			self.tourn = CTournamentDataBase.TournFromStrName(pagea.strNameTourn)
		else:
			if not doc.tourn:
				sys.exit("page has no tournament")
			self.tourn = cast(CTournamentDataBase, doc.tourn)

		self.strOrientation = self.pagea.strOrientation
		self.zoneinfo = ZoneInfo(self.tourn.StrTimezone() if self.FAllMatchesHaveResults() else self.pagea.strTz)
		self.locale = Locale.parse(self.pagea.strLocale)
		self.strScript = StrScriptFromLocale(self.locale)
		self.strDateMMMMEEEEd = StrPatternDateMMMMEEEEd(self.locale)
		if self.pagea.fmt is None:
			assert(self.pagea.fmtCrop == None)
			self.fmt = StrFmtBestFit(len(self.tourn.mpStrTeamGroup), self.locale)
		else:
			self.fmt = self.pagea.fmt
		self.fmtCrop = self.pagea.fmtCrop

		self.BuildDisplayDatesTimes()

		self.mpDateSetMatch: dict[datetime.date, set[CMatch]] = self.MpDateSetMatch()

		# with our dates set, we can calcucate our timezone names

		self.tMin = arrow.get(min(self.mpDateSetMatch))
		self.tMax = arrow.get(max(self.mpDateSetMatch))
		self.zonename = CZoneName(self.tMin, self.zoneinfo)

		self.strEdition = self.StrEdition()
		self.strTitle = self.StrTitle(self.strEdition)
		self.strDateRange = StrDateRange(self.tMin, self.tMax, self.locale)
		self.strLocation = self.StrTranslation(self.tourn.StrKeyHost())
		self.strZonename = self.zonename.StrUtcOnly() if self.pagea.fUtcOnly else self.zonename.StrFriendly()

		# if self.pagea.fmt is None:
		# 	print(f"{self.tourn.strName} ({str(self.locale).lower()}/{self.zoneinfo.key}): choosing {self.fmt}")

		# using "type: ignore" here because fpdf's typing stubs are known to be janky.

		self.pdf.add_page(orientation=self.strOrientation, format=self.fmt)	# type: ignore[arg-type]
		self.rect = SRect(0, 0, self.pdf.w, self.pdf.h)

		if tuDxDyCrop := self.pdf.TuDxDyFromOrientationFmt(self.strOrientation, self.fmtCrop):
			dX = min(self.rect.dX, tuDxDyCrop[0])
			dY = min(self.rect.dY, tuDxDyCrop[1])
			dXCropPerEdge = (self.rect.dX - dX) / 2
			dYCropPerEdge = (self.rect.dY - dY) / 2
			dSCropMarkPerEdge = min(dXCropPerEdge / 2, dYCropPerEdge / 2)

			self.rectInside = self.rect.Copy().Stretch(
												dXLeft = dXCropPerEdge,
												dYTop = dYCropPerEdge,
												dXRight = -dXCropPerEdge,
												dYBottom = -dYCropPerEdge)


			self.rectCropMarks = self.rectInside.Copy().Outset(dSCropMarkPerEdge)
		else:
			self.rectInside = self.rect
			self.rectCropMarks = self.rect

	def StrTranslation(self, strKey: str) -> str:
		return g_loc.StrTranslation(strKey, self.locale)

	def StrTeam(self, strKey: str) -> str:
		return self.StrTranslation(self.tourn.StrKeyTeam(strKey))
	
	def	StrEdition(self) -> str:
		strYear = self.tMin.strftime('%Y')
		strCompetition = self.StrTranslation(self.tourn.StrKeyCompetition())
		strFormatEdition = self.StrTranslation('page.format.edition')
		return strFormatEdition.format(year= strYear, competition=strCompetition)

	def StrTitle(self, strEdition: str) -> str:
		strType = self.StrTranslation('page.type.results' if self.FAllMatchesHaveResults() else 'page.type.fixtures')
		strFormatTitle = self.StrTranslation('page.format.title')
		return strFormatTitle.format(edition=strEdition, type=strType)

	def Fontkey(self, strStyle: str) -> SFontKey:
		strTtf = StrTtfLookup(strStyle, self.strScript)

		return SFontKey(strTtf, '')

	def FIsLeftToRight(self) -> bool:
		return self.locale.character_order == 'left-to-right'

	def FIsRightToLeft(self) -> bool:
		return not self.FIsLeftToRight()

	def JhStart(self) -> JH:
		return JH.Left if self.locale.character_order == 'left-to-right' else JH.Right

	def JhEnd(self) -> JH:
		return JH.Right if self.locale.character_order == 'left-to-right' else JH.Left

	def StrDateForCalendar(self, tDate: arrow.Arrow, tPrev: Optional[arrow.Arrow] = None) -> str:
		# NOTE (bruceo) only include month sometimes when it is changing
		#	these formats are CLDR patterns (https://cldr.unicode.org/translation/date-time/date-time-patterns)
		#	as supported by babel.dates.format_skeleton()

		if tPrev and tPrev.month == tDate.month:
			strFormat = "d"
		else:
			strFormat = "MMMMd"

		return babel.dates.format_skeleton(strFormat, tDate.datetime, locale=self.locale)

	def StrDateForElimination(self, match: CMatch) -> str:
		return babel.dates.format_skeleton('MMMEd', self.DateDisplay(match), locale=self.locale)

	def StrDateForFinal(self, match: CMatch) -> str:
		return babel.dates.format_date(self.DateDisplay(match), format=self.strDateMMMMEEEEd, locale=self.locale)

	def BuildDisplayDatesTimes(self):

		self.mpIdDateDisplay: dict[int, datetime.date] = {}
		self.mpIdStrTimeDisplay: dict[int, str] = {}

		# map all matches into the day that they are played in the tournament's timezone.
		# the goal here is to have same-day matches appear on the same calendar day for all
		# pages regardless of the page timezone.

		strTzTourney: str = self.tourn.StrTimezone()
		zoneinfoTourney = ZoneInfo(strTzTourney)
		assert(zoneinfoTourney)
		mpIdDateTourney: dict[int, datetime.date] = { id: match.tStart.to(zoneinfoTourney).date() for id, match in self.tourn.mpIdMatch.items() }

		# if all the matches are one day off their display dates, then reset the display dates

		fAllGroupMatchesAhead = True

		for match in self.tourn.mpIdMatch.values():
			if match.stage != STAGE.Group:
				continue
			tTimeTz = match.tStart.to(self.zoneinfo)
			dateDisplay = mpIdDateTourney[match.id]
			if dateDisplay.day == tTimeTz.day:
				fAllGroupMatchesAhead = False
				break

		if fAllGroupMatchesAhead:
			mpIdDateTourneyAdjusted: dict[int, datetime.date] = {id: dateTourney + datetime.timedelta(days=1) for id, dateTourney in mpIdDateTourney.items() }
			mpIdDateTourney = mpIdDateTourneyAdjusted

		# several language/territory combos have a 'short' format that negates the effect of our
		# CTomorrowTime hack. if any group matches would use CTomorrowTime, force a 24h aware format.

		fForceGroup24HourTime = False

		for match in self.tourn.mpIdMatch.values():
			if match.stage != STAGE.Group:
				continue
			tTimeTz = match.tStart.to(self.zoneinfo)
			dateDisplay = mpIdDateTourney[match.id]
			if dateDisplay.day != tTimeTz.day:
				fForceGroup24HourTime = True
				continue

		if fForceGroup24HourTime:
			strFmtTime = 'HH:mm'
		else:
			strFmtTime = 'short'

		for match in self.tourn.mpIdMatch.values():
			tTimeTz = match.tStart.to(self.zoneinfo)
			strTime = babel.dates.format_time(tTimeTz.time(), strFmtTime, locale=self.locale)

			if match.stage == STAGE.Group:
				dateDisplay = mpIdDateTourney[match.id]
				if dateDisplay.day != tTimeTz.day:
					ttTimeTz = CTomorrowTime(tTimeTz.hour, tTimeTz.minute, tTimeTz.second, tTimeTz.microsecond, tTimeTz.tzinfo)
					strTime = babel.dates.format_time(ttTimeTz, strFmtTime, locale=self.locale)
			else:
				dateDisplay = tTimeTz.date()

			# hacks that probably violate the CLDR

			strTime = strTime.translate({ord(ch):' ' for ch in '   '}) # some of our fonts don't have weirdo spaces

			self.mpIdDateDisplay[match.id] = dateDisplay
			self.mpIdStrTimeDisplay[match.id] = strTime

	def DateDisplay(self, match: CMatch) -> datetime.date:
		return self.mpIdDateDisplay[match.id]

	def StrTimeDisplay(self, match: CMatch) -> str:
		return self.mpIdStrTimeDisplay[match.id]

	def MpDateSetMatch(self) -> dict[datetime.date, set[CMatch]]:
		""" map dates to matches. """

		mpDateSetMatch: dict[datetime.date, set[CMatch]] = {}

		for match in self.tourn.mpIdMatch.values():
			mpDateSetMatch.setdefault(self.DateDisplay(match), set()).add(match)

		return mpDateSetMatch


	def DrawCropLines(self) -> None:
		if self.rectInside is self.rect:
			return

		self.pdf.set_line_width(self.s_dSLineCropMarks)
		self.pdf.set_draw_color(self.s_colorCropMarks.r, self.s_colorCropMarks.g, self.s_colorCropMarks.b)

		self.pdf.line(self.rect.xMin, 			self.rectInside.yMin,		self.rectCropMarks.xMin,	self.rectInside.yMin) 		# top
		self.pdf.line(self.rectCropMarks.xMax,	self.rectInside.yMin,		self.rect.xMax,				self.rectInside.yMin)

		self.pdf.line(self.rect.xMin,			self.rectInside.yMax,		self.rectCropMarks.xMin,	self.rectInside.yMax) 		# bottom
		self.pdf.line(self.rectCropMarks.xMax,	self.rectInside.yMax,		self.rect.xMax,				self.rectInside.yMax)

		self.pdf.line(self.rectInside.xMin,		self.rect.yMin, 			self.rectInside.xMin,		self.rectCropMarks.yMin)	# left
		self.pdf.line(self.rectInside.xMin,		self.rectCropMarks.yMax,	self.rectInside.xMin,		self.rect.yMax)

		self.pdf.line(self.rectInside.xMax,		self.rect.yMin, 			self.rectInside.xMax,		self.rectCropMarks.yMin)	# right
		self.pdf.line(self.rectInside.xMax,		self.rectCropMarks.yMax,	self.rectInside.xMax,		self.rect.yMax)

	def FMatchHasResults(self, match: CMatch) -> bool:
		if self.pagea.fFixturesOnly:
			return False

		return match.FHasResults()

	def FAllMatchesHaveResults(self) -> bool:
		if self.pagea.fFixturesOnly:
			return False

		return self.tourn.fHasAllResults

class CGroupsTestPage(CPage): # gtp
	def __init__(self, doc: CDocument, pagea: SPageArgs):
		super().__init__(doc, pagea)

		dSMargin = 0.5

		dXGrid = CGroupBlot.s_dX + dSMargin
		dYGrid = CGroupBlot.s_dY + dSMargin

		for col in range(2):
			for row in range(4):
				try:
					strGroup = self.tourn.lStrGroup[col * 4 + row]
				except IndexError:
					continue
				group = self.tourn.mpStrGroupGroup[strGroup]
				groupb = CGroupBlot(self, group)
				pos = SPoint(
						dSMargin + col * dXGrid,
						dSMargin + row * dYGrid)
				groupb.Draw(pos)

class CDaysTestPage(CPage): # gtp
	def __init__(self, doc: CDocument, pagea: SPageArgs):
		super().__init__(doc, pagea)

		dSMargin = 0.25

		# lIdMatch = (49,57)
		# setDate: set[datetime.date] = {doc.tourn.mpIdMatch[idMatch].tStart.date() for idMatch in lIdMatch}
		setDate: set[datetime.date] = set(self.mpDateSetMatch.keys())

		daybl = CDayBlotList([CDayBlot(self, arrow.get(date), self.mpDateSetMatch.get(date)) for date in sorted(setDate)])

		dXCell = daybl.dXDayb + dSMargin
		dYCell = daybl.dYDayb + dSMargin

		for row in range(4):
			for col in range(7):
				try:
					dayb = daybl.lDayb[row * 7 + col]
				except IndexError:
					continue
				pos = SPoint(
						dSMargin + col * dXCell,
						dSMargin + row * dYCell)
				dayb.Draw(pos, daybl)

class CHeaderBlot(CBlot): # tag = headerb

	s_dY = CDayBlot.s_dYMin * 0.6

	s_dYFontTitle = s_dY / 2
	s_dYFontSides = s_dYFontTitle / 2

	def __init__(self, page: CPage) -> None:
		super().__init__(page.pdf)
		self.page = page
		self.doc = page.doc

	def Draw(self, pos: SPoint) -> None:

		rectAll = SRect(pos.x, pos.y, self.page.rectInside.dX, self.s_dY)

		# fill with black, and bleed to crop marks above and to the sides

		rectBox = self.page.rectCropMarks.Copy()
		rectBox.yMax = rectAll.yMax
		self.FillBox(rectBox, colorBlack)

		# title

		oltbTitle = self.Oltb(rectAll, self.page.Fontkey('page.header.title'), self.s_dYFontTitle)
		rectTitle = oltbTitle.RectDrawText(self.page.strTitle, colorWhite, JH.Center, JV.Middle)
		dSMarginSides = rectAll.yMax - rectTitle.yMax

		# dates

		strFormatDates = self.page.StrTranslation('page.format.dates-and-location')
		strDatesLocation = strFormatDates.format(dates=self.page.strDateRange, location=self.page.strLocation)

		# time zone

		strLabelTimeZone = self.page.StrTranslation('page.timezone.label')
		strFormatTimeZone = self.page.StrTranslation('page.format.timezone')
		strTimeZone = strFormatTimeZone.format(label=strLabelTimeZone, timezone=self.page.strZonename)

		# notes left and right

		if self.page.FAllMatchesHaveResults():
			strNoteLeft = self.page.strDateRange
			strNoteRight = self.page.strLocation
		else:
			strNoteLeft = strDatesLocation
			strNoteRight = strTimeZone

		# swapping for RtL

		if not self.page.FIsLeftToRight():
			strNoteLeft, strNoteRight = strNoteRight, strNoteLeft

		rectNoteLeft = rectAll.Copy().Stretch(dXLeft = self.s_dY) # yes, using height as left space
		oltbNoteLeft = self.Oltb(rectNoteLeft, self.page.Fontkey('page.header.title'), self.s_dYFontSides, dSMargin = dSMarginSides)
		oltbNoteLeft.DrawText(strNoteLeft, colorWhite, JH.Left, JV.Bottom)

		rectNoteRight = rectAll.Copy().Stretch(dXRight = -self.s_dY) # ditto
		oltbNoteRight = self.Oltb(rectNoteRight, self.page.Fontkey('page.header.title'), self.s_dYFontSides, dSMargin = dSMarginSides)
		oltbNoteRight.DrawText(strNoteRight, colorWhite, JH.Right, JV.Bottom)

class CFooterBlot(CBlot): # tag = headerb

	s_dY = CDayBlot.s_dYMin * 0.2

	s_dYFont = s_dY / 4

	def __init__(self, page: CPage) -> None:
		super().__init__(page.pdf)
		self.page = page
		self.doc = page.doc

	def Draw(self, pos: SPoint) -> None:

		rectAll = SRect(pos.x, pos.y, self.page.rectInside.dX, self.s_dY)

		# fill with black, and bleed to crop marks below and to the sides

		rectBox = self.page.rectCropMarks.Copy()
		rectBox.yMin = rectAll.yMin
		self.FillBox(rectBox, colorBlack)

		# credits

		rectCredits = rectAll.Copy().Stretch(dXLeft = CHeaderBlot.s_dY, dXRight = -CHeaderBlot.s_dY) # yes, using height as left space

		lStrCreditLeft: list[str] = [
			'DESIGN/CODE BY BRUCE OBERG',
			'BRUCE@OBERG.ORG',
			'MADE IN PYTHON WITH FPDF2',
			'GITHUB.COM/BRUCEOBERG/SOCCER-TOURNEY-POSTER',
			g_repover.StrVersionShort(),
		]

		lStrCreditCenter: list[str] = []

		if not self.page.FAllMatchesHaveResults():
			strTzFooter = self.page.zonename.StrUtcOnly() if self.page.pagea.fUtcOnly else self.page.pagea.strTz
			lStrCreditCenter.append(strTzFooter)

		lStrCreditCenter += [
			StrLangTerritoryFromLocale(self.page.locale),
			str(self.page.fmt),
		]

		if self.page.pagea.strVariant:
			lStrCreditCenter.append(self.page.pagea.strVariant)

		lStrCreditRight: list[str] = [
			'ORIGINAL DESIGN BY BENJY TOCZYNSKI',
			'BTOCZYNSKI@GMAIL.COM',
		]

		strSpaceDotSpace = ' • '

		for lStrCredit, jh in ((lStrCreditLeft, JH.Left), (lStrCreditCenter, JH.Center), (lStrCreditRight, JH.Right)):
			strCredit = strSpaceDotSpace.join(lStrCredit)
			oltbCredit = self.Oltb(rectCredits, self.page.Fontkey('page.footer'), self.s_dYFont)
			oltbCredit.DrawText(strCredit, colorWhite, jh, JV.Middle)

class CCalOnlyPage(CPage): # tag = calonlyp
	def __init__(self, doc: CDocument, pagea: SPageArgs):
		super().__init__(doc, pagea)

		# header/footer

		headerb = CHeaderBlot(self)
		rectHeader = self.rectInside.Copy().Set(dY=headerb.s_dY)

		footerb = CFooterBlot(self)
		rectFooter = self.rectInside.Copy().Stretch(dYTop = (self.rectInside.dY - footerb.s_dY))

		rectCanvas = self.rectInside.Copy()
		rectCanvas.yMin = rectHeader.yMax
		rectCanvas.yMax = rectFooter.yMin

		# groups on either side

		cGroupHalf = len(self.tourn.lStrGroup) // 2

		lGroupbLeft = [CGroupBlot(self, self.tourn.mpStrGroupGroup[strGroup]) for strGroup in self.tourn.lStrGroup[:cGroupHalf]]
		gsetbLeft = CGroupSetBlot(doc, lGroupbLeft, rectCanvas, cCol = 1)

		lGroupbRight = [CGroupBlot(self, self.tourn.mpStrGroupGroup[strGroup]) for strGroup in self.tourn.lStrGroup[cGroupHalf:]]
		gsetbRight = CGroupSetBlot(doc, lGroupbRight, rectCanvas, cCol = 1)

		setMatchCalendar = self.tourn.setMatchGroup | self.tourn.setMatchElimination

		if self.tourn.matchThird:
			setMatchCalendar.add(self.tourn.matchThird)

		calb = CCalendarBlot(self, setMatchCalendar)
		finalb = CFinalBlot(self)

		dXUnused = rectCanvas.dX - (calb.dX + gsetbLeft.dX + gsetbRight.dX)
		dXGap = dXUnused / 4.0 # both margins and both gaps between groups and calendar. same gap vertically for calendar/final

		dYUnused = rectCanvas.dY - (calb.dY + finalb.s_dY)
		dYGap = dYUnused / 3.0

		assert gsetbLeft.dY == gsetbRight.dY
		yGroups = rectCanvas.y + (rectCanvas.dY - gsetbLeft.dY) / 2.0

		xGroupsLeft = rectCanvas.x + dXGap

		gsetbLeft.Draw(SPoint(xGroupsLeft, yGroups))

		xCalendar = xGroupsLeft + gsetbLeft.dX + dXGap
		yCalendar = rectCanvas.y + dYGap

		calb.Draw(SPoint(xCalendar, yCalendar))

		xFinal = (rectCanvas.dX - finalb.s_dX) / 2.0
		yFinal = yCalendar + calb.dY + dYGap

		finalb.Draw(SPoint(xFinal, yFinal))

		xGroupsRight = xCalendar + calb.dX + dXGap

		gsetbRight.Draw(SPoint(xGroupsRight, yGroups))

		headerb.Draw(rectHeader.posMin)
		footerb.Draw(rectFooter.posMin)

		self.DrawCropLines()

class CCalElimPage(CPage): # tag = calelimp
	def __init__(self, doc: CDocument, pagea: SPageArgs):
		super().__init__(doc, pagea)

		# header/footer

		headerb = CHeaderBlot(self)
		rectHeader = self.rectInside.Copy().Set(dY=headerb.s_dY)

		footerb = CFooterBlot(self)
		rectFooter = self.rectInside.Copy().Stretch(dYTop = (self.rectInside.dY - footerb.s_dY))

		rectCanvas = self.rectInside.Copy()
		rectCanvas.yMin = rectHeader.yMax
		rectCanvas.yMax = rectFooter.yMin

		# groups on either side

		assert len(self.tourn.lStrGroup) % 2 == 0
		cGroupHalf = len(self.tourn.lStrGroup) // 2

		if self.FIsLeftToRight():
			lStrGroupLeft = self.tourn.lStrGroup[:cGroupHalf]
			lStrGroupRight = self.tourn.lStrGroup[cGroupHalf:]
		else:
			lStrGroupLeft = self.tourn.lStrGroup[cGroupHalf:]
			lStrGroupRight = self.tourn.lStrGroup[:cGroupHalf]

		lGroupbLeft = [CGroupBlot(self, self.tourn.mpStrGroupGroup[strGroup]) for strGroup in lStrGroupLeft]
		gsetbLeft = CGroupSetBlot(self.doc, lGroupbLeft, rectCanvas, cCol = 1)

		lGroupbRight = [CGroupBlot(self, self.tourn.mpStrGroupGroup[strGroup]) for strGroup in lStrGroupRight]
		gsetbRight = CGroupSetBlot(self.doc, lGroupbRight, rectCanvas, cCol = 1)

		assert gsetbLeft.dY == gsetbRight.dY

		# cal vs bracket matches

		setMatchCalendar: set[CMatch] = self.tourn.mpStageSetMatch[STAGE.Group]
		lSetMatchBracket: list[set[CMatch]] = [setMatch for stage, setMatch in self.tourn.mpStageSetMatch.items() if stage != STAGE.Group]
		setMatchBracket: set[CMatch] = set().union(*lSetMatchBracket)

		calb = CCalendarBlot(self, setMatchCalendar)
		bracketb = CBracketBlot(self, setMatchBracket)

		finalb = CFinalBlot(self)

		dYUnused = rectCanvas.dY - (calb.dY + bracketb.dY + finalb.s_dY)
		dYGap = dYUnused / 4.0
		fVerticalOverflow = dYGap < 0

		if fVerticalOverflow:
			dYUnused = rectCanvas.dY - (calb.dY + bracketb.dY)
			dYGap = max(0.0, dYUnused / 3.0)
			dYGapFinal = 0.0
		else:
			dYGapFinal = dYGap

		dXColumns = max(calb.dX, bracketb.dX, finalb.s_dX) + gsetbLeft.dX + gsetbRight.dX
		dXUnused = rectCanvas.dX - dXColumns
		dXGap = dXUnused / 4.0 # both margins and both gaps between groups and calendar. same gap vertically for calendar/final
		fHorizontalOverflow = dXGap < 0

		if fHorizontalOverflow:
			# paper to narrow: slide the groups below the calendar and closer to the bracket.
			dXColumns = max(bracketb.dX, finalb.s_dX) + gsetbLeft.dX + gsetbRight.dX
			dXUnused = rectCanvas.dX - dXColumns

			dYUnused = rectCanvas.dY - (calb.dY + gsetbLeft.dY + finalb.s_dY)	# NOTE bruceo: could possibly move final's up

			if dYUnused < 0:
				# try shrinking group sets vertically
				rectLayout = rectCanvas.Copy(dY = 0) # zero height to force group sets to minimum gaps
				gsetbLeft.Layout(rectLayout, cCol = 1, fAddOuterMargin = False)
				gsetbRight.Layout(rectLayout, cCol = 1, fAddOuterMargin = False)
				dYUnused = rectCanvas.dY - (calb.dY + gsetbLeft.dY + finalb.s_dY)	# NOTE bruceo: could possibly move final's up
				dYGapFinal = 0.0

			if dXUnused < 0 and dYUnused < 0:
				sys.exit(f"{self.tourn.strName}: groups don't fit. x over by {-dXUnused:0.2f}. y over by {-dYUnused:0.2f}")
			if dXUnused < 0:
				sys.exit(f"{self.tourn.strName}: groups too wide; over by {-dXUnused:0.2f}.")
			if dYUnused < 0:
				sys.exit(f"{self.tourn.strName}: groups too tall; over by {-dYUnused:0.2f}")

			dXGap = dXUnused / 4.0
			dYGap = dYUnused / 3.0

			yGroups = rectCanvas.y + calb.dY + 2 * dYGap

		else:
			# normal: groups to either side of vertical cal/bracket/final stack

			yGroups = rectCanvas.y + (rectCanvas.dY - gsetbLeft.dY) / 2.0

		xGroupsLeft = rectCanvas.x + dXGap
		xGroupsRight = rectCanvas.xMax - (gsetbRight.dX + dXGap)

		gsetbLeft.Draw(SPoint(xGroupsLeft, yGroups))
		gsetbRight.Draw(SPoint(xGroupsRight, yGroups))

		xCalendar = rectCanvas.x + (rectCanvas.dX - calb.dX) / 2.0
		yCalendar = rectCanvas.y + dYGap

		calb.Draw(SPoint(xCalendar, yCalendar))

		xBracket = rectCanvas.x + (rectCanvas.dX - bracketb.dX) / 2.0

		if fHorizontalOverflow:
			yBracket = yGroups + (gsetbLeft.dY / 2.0) - bracketb.dYMidGrid
		else:
			yBracket = yCalendar + calb.dY + dYGap

		bracketb.Draw(SPoint(xBracket, yBracket))

		xFinal = rectCanvas.x + (rectCanvas.dX - finalb.s_dX) / 2.0

		# backwards final y calculation deals with both the /4 and /3 cases of dYUnused above.
		# when calendar + bracket are too tall, final gets skootched inside the bracket.

		yFinal = rectCanvas.yMax - (finalb.s_dY + dYGapFinal)

		finalb.Draw(SPoint(xFinal, yFinal))

		headerb.Draw(rectHeader.posMin)
		footerb.Draw(rectFooter.posMin)

		self.DrawCropLines()

		# print(' '.join([
		# 	f"cTeam: {len(self.tourn.mpStrTeamGroup)}",
		# 	f"dX2: {gsetbLeft.dX+gsetbRight.dX+max(bracketb.dX, finalb.s_dX)+1:0.3f}",
		# 	f"dX3: {gsetbLeft.dX+gsetbRight.dX+max(calb.dX, bracketb.dX, finalb.s_dX)+1:0.3f}",
		# 	f"dY2: {headerb.s_dY+footerb.s_dY+calb.dY+bracketb.dY:0.3f}",
		# 	f"dY3: {headerb.s_dY+footerb.s_dY+calb.dY+bracketb.dY+finalb.s_dY+1:0.3f}",
		# ]))

		# print(f"cTeam: {len(self.tourn.mpStrTeamGroup)} fmt: {self.StrFmtBestFit()}")
