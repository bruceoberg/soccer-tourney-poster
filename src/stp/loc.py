#!/usr/bin/env python3

from __future__ import annotations  # Forward refs without quotes (eg foo: CFoo, not foo: 'CFoo')

from babel import Locale
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

# Comprehensive mapping of IANA timezone -> abbreviations

# timezones: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones

g_mpStrTzTzs: dict[str, STZs] = {
	# # Americas

	# "America/New_York":		STZs("EST", "EDT"),
	# "America/Chicago":		STZs("CST", "CDT"),
	# "America/Denver":		STZs("MST", "MDT"),
	# "America/Los_Angeles":	STZs("PST", "PDT"),
 	# "America/Anchorage":	STZs("AKST", "AKDT"),
	# "Pacific/Honolulu":		STZs("HST", "HST"), # No DST

	# "US/Eastern":			STZs("EST", "EDT"),
	# "US/Central":			STZs("CST", "CDT"),
	# "US/Mountain":			STZs("MST", "MDT"),
	# "US/Pacific":			STZs("PST", "PDT"),

	# "America/Toronto":		STZs("EST", "EDT"),
	# "America/Edmonton":		STZs("MST", "MDT"),
	# "America/Regina":		STZs("CST", "CST"), # No DST
	# "America/Winnipeg":		STZs("CST", "CDT"),
	# "America/Vancouver":	STZs("PDT", "PDT"), # Always DST

	# "America/Tijuana":		STZs("PST", "PDT"),
	# "America/Mexico_City":	STZs("CST", "CST"), # No DST

 	# "America/Panama":		STZs("EST", "EST"), # No DST
	# "America/Port-au-Prince": STZs("EST", "EDT"),
	# "America/Curacao":		STZs("AST", "AST"), # No DST

 	"America/Bogota":		STZs("EST", "EST"), # No DST
 	"America/Guayaquil":	STZs("EST", "EST"), # No DST
	"America/Buenos_Aires":	STZs("ADT", "ADT"), # Always DST
	"America/Montevideo":	STZs("ADT", "ADT"), # Always DST
	"America/Asuncion":		STZs("ADT", "ADT"), # Always DST
	"America/Sao_Paulo":	STZs("BRT", "BRT"), # No DST

	# # Europe

	# "Europe/London":		STZs("GMT", "BST"),
	# "Europe/Lisbon":		STZs("WET", "WEST"),
	# "Europe/Paris":			STZs("CET", "CEST"),
	# "Europe/Rome":			STZs("CET", "CEST"),
	# "Europe/Berlin":		STZs("CET", "CEST"),
	# "Europe/Madrid":		STZs("CET", "CEST"),
	# "Europe/Amsterdam":		STZs("CET", "CEST"),
	# "Europe/Athens":		STZs("EET", "EEST"),
	# "Europe/Moscow":		STZs("MSK", "MSK"),	# No DST
	# "Europe/Istanbul":		STZs("TRT", "TRT"),	# No DST
	
	# # Africa

	# "Africa/Abidjan":		STZs("GMT",	"GMT"), # No DST
	# "Africa/Casablanca":	STZs("WAT",	"WAT"), # No DST
	# "Africa/Cairo":			STZs("EET",	"EEST"),
	# "Africa/Johannesburg":	STZs("SAST", "SAST"),	# No DST
	
	# # Asia
	
	"Asia/Tehran":			STZs("IRST", "IRST"), # No DST
	# "Asia/Kabul":			STZs("AFT", "AFT"),	# No DST
	# "Asia/Dubai":			STZs("GST", "GST"),	# No DST
	# "Asia/Qatar":			STZs("AST", "AST"),	# No DST
	"Asia/Riyadh":			STZs("SAST", "SAST"),	# No DST
	# "Asia/Kolkata":			STZs("IST", "IST"),	# No DST
	# "Asia/Shanghai":		STZs("CHST", "CHST"),	# No DST
	# "Asia/Taipei":			STZs("CHST", "CHST"),	# No DST
	# "Asia/Tokyo":			STZs("JST", "JST"),	# No DST
	# "Asia/Seoul":			STZs("KST", "KST"),	# No DST
	
	# # Oceania/Pacific

	# "Australia/Sydney":		STZs("AEST", "AEDT"),
	# "Australia/Perth":		STZs("AWST", "AWST"),	# No DST
	# "Pacific/Auckland":		STZs("NZST", "NZDT"),
	# "Pacific/Fiji":			STZs("FJT", "FJST"),
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
