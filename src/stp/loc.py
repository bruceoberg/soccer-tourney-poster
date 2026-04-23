#!/usr/bin/env python3

from __future__ import annotations  # Forward refs without quotes (eg foo: CFoo, not foo: 'CFoo')

from babel import Locale
from babel.core import get_global, parse_locale
from dataclasses import dataclass
from datetime import datetime

from bolay import CPdf

from .config import mpCTeamSizeMin, lFmtIso, lFmtUS

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

