#!/usr/bin/env python3

from babel import Locale
from datetime import datetime
from dataclasses import dataclass

from config import mpCTeamSizeMin, lFmtIso, lFmtUS
from bolay import CPdf

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
		'sv',  # El Salvador
		've',  # Venezuela
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
g_mpStrTimezoneToAbbrevs: dict[str, STZs] = {
	# Pacific
	"Pacific/Auckland":        STZs("NZST", "NZDT"),
	"Pacific/Fiji":            STZs("FJT",  "FJST"),
	"Pacific/Honolulu":        STZs("HST",  "HDT"),
	
	# Asia
	"Asia/Tehran":             STZs("IRST", "IRDT"),
	"Asia/Dubai":              STZs("GST",  "GST"),   # No DST
	"Asia/Shanghai":           STZs("CST",  "CST"),   # No DST
	"Asia/Tokyo":              STZs("JST",  "JST"),   # No DST
	"Asia/Kolkata":            STZs("IST",  "IST"),   # No DST
	
	# Americas
	"America/New_York":        STZs("EST",  "EDT"),
	"America/Chicago":         STZs("CST",  "CDT"),
	"America/Denver":          STZs("MST",  "MDT"),
	"America/Los_Angeles":     STZs("PST",  "PDT"),
	"America/Sao_Paulo":       STZs("BRT",  "BRST"),
	
	# Europe
	"Europe/London":           STZs("GMT",  "BST"),
	"Europe/Paris":            STZs("CET",  "CEST"),
	"Europe/Athens":           STZs("EET",  "EEST"),
	"Europe/Moscow":           STZs("MSK",  "MSK"),   # No DST
	
	# Africa
	"Africa/Cairo":            STZs("EET",  "EEST"),
	"Africa/Johannesburg":     STZs("SAST", "SAST"),  # No DST
	
	# Australia
	"Australia/Sydney":        STZs("AEST", "AEDT"),
	"Australia/Perth":         STZs("AWST", "AWST"),  # No DST
}

def StrTzAbbrev(t: datetime) -> str:
	"""
	Get the timezone abbreviation for a datetime.
	
	Returns the appropriate abbreviation (e.g., "IRST" or "IRDT") based on
	whether DST is active. Falls back to system abbreviation (which may be
	an offset like "+0330") if no mapping exists.
	"""

	try:
		tzs = g_mpStrTimezoneToAbbrevs[str(t.tzinfo)]
		fIsDst = t.dst() and t.dst().total_seconds() > 0
		return tzs.strDst if fIsDst else tzs.strStd
	except KeyError:
		pass
	
	# Fallback to system abbreviation (might be offset like "+0330")
	strTz = t.strftime('%Z')

	if strTz.startswith('+'):
		strTz = f'UTC{strTz}'
	else:
		dT = t.utcoffset()
		assert(dT)
		if cSec := int(dT.total_seconds()):
			if (cSec % (60*60)) == 0:
				cHour = cSec // (60*60)
				strTz += f' (UTC{cHour:+d})'
			else:
				cHour = cSec // (60*60)
				cMin = (cSec % (60*60)) // 60
				strTz += f' (UTC{cHour:+d}:{cMin:02d})'
	
	return strTz
