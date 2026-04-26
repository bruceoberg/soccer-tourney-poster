#!/usr/bin/env python3

from __future__ import annotations  # Forward refs without quotes (eg foo: CFoo, not foo: 'CFoo')

import polib

from babel import Locale
from babel.core import get_global, parse_locale
from dataclasses import dataclass
from datetime import datetime

from bolay import CPdf

from . import __project__, g_pathCode

# paper sizes offered for poster printing at fedex office stores

mpStoreLFmt = {
	'fedex':
	(
		'16x20',	# 16in x 20in
		'18x24',	# 18in x 24in
		'22x28',	# 22in x 28in
		'24x36',	# 24in x 36in
		'36x48',	# 36in x 48in
	),
	'office-depot':
	(
		'16x20',	# 16in x 20in
		'18x24',	# 18in x 24in
		'24x36',	# 24in x 36in
		'36x48',	# 36in x 48in
		'40x60',	# 40in x 60in
	),
	'staples':
	(
		'12x18',	# 12in x 18in
		'16x20',	# 16in x 20in
		'18x24',	# 18in x 24in
		'24x36',	# 24in x 36in
		'36x48',	# 36in x 48in
	),
}

setFmtUS = {fmt for strStore, lFmt in mpStoreLFmt.items() for fmt in lFmt }
lFmtUS = sorted(setFmtUS)

lFmtIso = (
	'a0', 'a1', 'a2', 'a3', 'a4', 'a5', 'a6', 'a7', 'a8', 'a9', 'a10',
	'b0', 'b1', 'b2', 'b3', 'b4', 'b5', 'b6', 'b7', 'b8', 'b9', 'b10',
	'c0', 'c1', 'c2', 'c3', 'c4', 'c5', 'c6', 'c7', 'c8', 'c9', 'c10',
)

# empirical minimum heights/widths of various tourney sizes.
# see print() statement in CCalElimPage constructor.

mpCTeamSizeMin: dict[int, tuple[float, float]] ={
	16: (14.035, 19.844),
	24: (18.068, 25.750),
	32: (18.068, 25.750),
	48: (22.665, 29.969),
}

def FUsesIsoPaperSizes(locale: Locale) -> bool:
	setStrTerritoryUsLetter = {
		'us',  # United States
		'ca',  # Canada
		'mx',  # Mexico
		'cl',  # Chile
		'co',  # Colombia
		'cr',  # Costa Rica
		'gt',  # Guatemala
		'pa',  # Panama
		'ph',  # Philippines
		'pr',  # Puerto Rico
		've',  # Venezuela
		'sv',  # El Salvador
	}
  
	return not locale.territory or not locale.territory.lower() in setStrTerritoryUsLetter
	
def StrFmtBestFit(cTeam: int, locale: Locale) -> str:
	dxInMin, dYInMin = mpCTeamSizeMin[cTeam]
	dXPtMin = dxInMin * 72
	dYPtMin = dYInMin * 72
	sAreaPtMin = dXPtMin * dYPtMin
	sWastedBest = None
	strFmtBest = 'unknown'
	lStrFmt = lFmtIso if FUsesIsoPaperSizes(locale) else lFmtUS
	for strFmt in lStrFmt:
		dXPt, dYPt = CPdf.s_mpStrFormatWH[strFmt]
		if dXPt < dXPtMin or dYPt < dYPtMin:
			continue
		sWastedFmt = (dXPt * dYPt) - sAreaPtMin
		if sWastedBest is None or sWastedFmt < sWastedBest:
			sWastedBest = sWastedFmt
			strFmtBest = strFmt

	return strFmtBest

@dataclass(frozen=True)
class STZs:  # tag = tzs
	strStd: str
	strDst: str

# name for unnamed timezones (where datetime.strftime('%Z') returns a number instead of a name)
# timezones: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones

g_mpStrTzTzs: dict[str, STZs] = {
 	"America/Bogota":		STZs("EST", "EST"), # No DST
 	"America/Guayaquil":	STZs("EST", "EST"), # No DST
	"America/Buenos_Aires":	STZs("ADT", "ADT"), # Always DST
	"America/Montevideo":	STZs("ADT", "ADT"), # Always DST
	"America/Asuncion":		STZs("ADT", "ADT"), # Always DST
	"America/Sao_Paulo":	STZs("BRT", "BRT"), # No DST
	"Europe/Istanbul":		STZs("TRT", "TRT"),	# No DST
	"Atlantic/Cape_Verde":	STZs("CVT", "CVT"), # No DST
	"Africa/Casablanca":	STZs("WAT",	"WAT"), # No DST
	"Asia/Tehran":			STZs("IRST", "IRST"), # No DST
	"Asia/Riyadh":			STZs("SAST", "SAST"),	# No DST
	"Asia/Tashkent":		STZs("UZT", "UZT"),	# No DST
}

def StrTzAbbrev(strTz: str, t: datetime) -> str:
	"""
	Get the timezone abbreviation for a datetime.
	
	Returns the appropriate abbreviation (e.g., "IRST" or "IRDT") based on
	whether DST is active. Falls back to system abbreviation (which may be
	an offset like "+0330") if no mapping exists.
	"""

	try:
		tzs = g_mpStrTzTzs[strTz]
		fIsDst = t.dst() and t.dst().total_seconds() > 0
		return tzs.strDst if fIsDst else tzs.strStd
	except KeyError:
		pass
	
	# Fallback to system abbreviation (might be offset like "+0330")

	strTzAbbrev = t.strftime('%Z')

	for ch in strTzAbbrev:
		if ch.isdigit():
			print(f"Warning: strTztimezone '{strTz}' abbreviated to '{strTzAbbrev}'")
			break

	return strTzAbbrev

g_mpStrSubtag = get_global('likely_subtags')

def StrScriptFromLocale(locale: Locale) -> str:
	if locale.script:
		return locale.script
	
	for strQuery in (str(locale), locale.language):
		strSubtag = g_mpStrSubtag.get(strQuery)
		if strSubtag is not None:
			_, _, strScript, *_ = parse_locale(strSubtag)
			if strScript:
				return strScript

	print(f"Warning: locale '{str(locale)}' cannot determine script, using Latn")

	return 'Latn'

def StrLocaleFromPof(pof: polib.POFile) -> str:
	return pof.metadata.get('Language', '').strip().lower()

class CLocalizationDataBase(): # tag = loc

	s_pathDir = g_pathCode / 'localization'

	def __init__(self) -> None:

		self.mpStrSectionSetStrSubkey: dict[str, set[str]] = {}
		self.mpStrKeyStrLocaleStrText: dict[str, dict[str, str]] = {}

		# pot is allowed to establish keys and sections
		# it loads text from msgids

		pathPot =  self.s_pathDir / (__project__ + '.pot')
		pof = polib.pofile(str(pathPot))
		strLocale = StrLocaleFromPof(pof)
		for entry in pof:
			if not entry.msgctxt:
				continue
			strKey = entry.msgctxt.lower()

			strSection, strSubKey = strKey.split('.', 1)
			self.mpStrSectionSetStrSubkey.setdefault(strSection, set()).add(strSubKey)

			mpStrLocaleStrText = self.mpStrKeyStrLocaleStrText.setdefault(strKey, {})
			mpStrLocaleStrText[strLocale] = entry.msgid

		# po files can only add entries to extant keys and they load text from msgstr.

		for pathPo in self.s_pathDir.glob(f'{__project__}-*.po'):
			pof = polib.pofile(str(pathPo))
			strLocale = StrLocaleFromPof(pof)
			
			for entry in pof:
				if not entry.msgctxt:
					continue
				strKey = entry.msgctxt.lower()

				if mpStrLocaleStrText := self.mpStrKeyStrLocaleStrText.get(strKey):
					mpStrLocaleStrText[strLocale] = entry.msgstr
				else:
					print(f"warning: file {pathPo} has unknown key {strKey}")

	def StrTranslation(self, strKey: str, locale: Locale) -> str:
		strKey = strKey.lower()

		mpStrLocaleStrText = self.mpStrKeyStrLocaleStrText[strKey]

		lStrLocale = [
			str(locale),		# full name... en_US or zh_Hans_CN
		]

		if locale.script:
			lStrLocale.append(f"{locale.language}_{locale.script}")

		if locale.language != 'en':
			lStrLocale.append(locale.language)

		for strLocale in lStrLocale:
			try:
				if strText := mpStrLocaleStrText[strLocale.lower()]:
					return strText
			except KeyError:
				pass

		return mpStrLocaleStrText['en']

g_loc = CLocalizationDataBase()