#!/usr/bin/env python3

from __future__ import annotations  # Forward refs without quotes (eg foo: CFoo, not foo: 'CFoo')

from babel import Locale
from enum import auto

from bolay import IntEnum0

class FONTK(IntEnum0): # tag = fontk
	Bold = auto()
	CondensedBold = auto()
	CondensedBoldLatn = auto()
	Console = auto()
	ConsoleItalic = auto()	# may not be used, depending on tourney size
	Light = auto()
	LightItalic = auto()
	Regular = auto()
	SemiBold = auto()
	SemiCondensed = auto()

g_mpStrStyleFontk = {
	'calendar.day-of-week-broken':	FONTK.Bold,
	'calendar.day-of-week':			FONTK.LightItalic,
	'day.date':						FONTK.LightItalic,
	'elim.date':					FONTK.Regular,
	'elim.label':					FONTK.Regular,
	'elim.stage':					FONTK.Bold,
	'final.date':					FONTK.Bold,
	'final.form.label':				FONTK.Light,
	'final.team.name':				FONTK.Bold,
	'final.time':					FONTK.Light,
	'final.title':					FONTK.Bold,
	'group.heading':				FONTK.SemiCondensed,
	'group.label':					FONTK.Regular,
	'group.name':					FONTK.Console,
	'group.team.abbrev':			FONTK.Console,
	'group.team.name':				FONTK.SemiCondensed,
	'group.team.place':				FONTK.Console,
	'group.team.point-total':		FONTK.Console,
	'match.form.label-inverse':		FONTK.ConsoleItalic,
	'match.form.label':				FONTK.Console,
	'match.label':					FONTK.SemiBold,
	'match.score':					FONTK.SemiBold,
	'match.team.abbrev':			FONTK.Console,
	'match.time':					FONTK.Light,
	'page.footer':					FONTK.CondensedBoldLatn,
	'page.header.title':			FONTK.CondensedBold,
	'third.team.name':				FONTK.SemiCondensed,
}

g_mpStrScriptFontkStrTtf: dict[str, dict[FONTK,str]] = {}

g_mpStrScriptFontkStrTtf['latn'] = {
	FONTK.Console: 				'consola.ttf',
	FONTK.ConsoleItalic: 		'consolai.ttf',
	FONTK.Bold: 				'NotoSans-Bold.otf',
	FONTK.CondensedBoldLatn:	'NotoSans-CondensedBold.otf',
	FONTK.CondensedBold: 		'NotoSans-CondensedBold.otf',
	FONTK.SemiBold: 			'NotoSans-SemiBold.otf',
	FONTK.SemiCondensed: 		'NotoSans-SemiCondensed.otf',
	FONTK.Light: 				'NotoSans-Light.otf',
	FONTK.LightItalic: 			'NotoSans-LightItalic.otf',
	FONTK.Regular: 				'NotoSans-Regular.otf',
}

g_mpStrScriptFontkStrTtf['latn-orig'] = {
	FONTK.Console: 				'consola.ttf',
	FONTK.ConsoleItalic: 		'consolai.ttf',
	FONTK.Bold:					'TradeGothicLTStd-Bd2.otf',
	FONTK.CondensedBold:		'TradeGothicLTStd-BdCn20.otf',
	FONTK.CondensedBoldLatn:	'TradeGothicLTStd-BdCn20.otf',
	FONTK.SemiBold:				'TradeGothicLTStd-Bold.otf',
	FONTK.SemiCondensed:		'TradeGothicLTStd-Cn18.otf',
	FONTK.Light:				'TradeGothicLTStd-Light.otf',
	FONTK.LightItalic:			'TradeGothicLTStd-LightObl.otf',
	FONTK.Regular:				'TradeGothicLTStd.otf',
}

def MpStrScriptFontkStrTtfOverrideLatn(mpFontkStrTtf: dict[FONTK,str]) -> dict[FONTK,str]:
	return g_mpStrScriptFontkStrTtf['latn'] | mpFontkStrTtf

g_mpStrScriptFontkStrTtf['cyrl'] = MpStrScriptFontkStrTtfOverrideLatn({})
g_mpStrScriptFontkStrTtf['grek'] = MpStrScriptFontkStrTtfOverrideLatn({})

g_mpStrScriptFontkStrTtf['jpan'] = MpStrScriptFontkStrTtfOverrideLatn({
	FONTK.Bold:				'NotoSansCJKjp-Black.otf',
	FONTK.CondensedBold:	'NotoSansCJKjp-Bold.otf',
	FONTK.SemiBold:			'NotoSansCJKjp-Bold.otf',
	FONTK.SemiCondensed:	'NotoSansCJKjp-Regular.otf',
	FONTK.Light:			'NotoSansCJKjp-Light.otf',
	FONTK.LightItalic:		'NotoSansCJKjp-Light.otf',
	FONTK.Regular:			'NotoSansCJKjp-Regular.otf',
})

g_mpStrScriptFontkStrTtf['jpan-orig'] = MpStrScriptFontkStrTtfOverrideLatn({
	FONTK.Bold:				'YuGothB_0.ttf',
	FONTK.CondensedBold:	'YuGothB_0.ttf',
	FONTK.SemiBold:			'YuGothB_0.ttf',
	FONTK.SemiCondensed:	'YuGothR_0.ttf',
	FONTK.Light:			'YuGothL_0.ttf',
	FONTK.LightItalic:		'YuGothL_0.ttf',
	FONTK.Regular:			'YuGothR_0.ttf',
})

g_mpStrScriptFontkStrTtf['kore'] = MpStrScriptFontkStrTtfOverrideLatn({
	FONTK.Bold:				'NotoSansCJKkr-Black.otf',
	FONTK.CondensedBold:	'NotoSansCJKkr-Bold.otf',
	FONTK.SemiBold:			'NotoSansCJKkr-Bold.otf',
	FONTK.SemiCondensed:	'NotoSansCJKkr-Regular.otf',
	FONTK.Light:			'NotoSansCJKkr-Light.otf',
	FONTK.LightItalic:		'NotoSansCJKkr-Light.otf',
	FONTK.Regular:			'NotoSansCJKkr-Regular.otf',
})

g_mpStrScriptFontkStrTtf['hans'] = MpStrScriptFontkStrTtfOverrideLatn({
	FONTK.Bold:				'NotoSansCJKsc-Black.otf',
	FONTK.CondensedBold:	'NotoSansCJKsc-Bold.otf',
	FONTK.SemiBold:			'NotoSansCJKsc-Bold.otf',
	FONTK.SemiCondensed:	'NotoSansCJKsc-Regular.otf',
	FONTK.Light:			'NotoSansCJKsc-Light.otf',
	FONTK.LightItalic:		'NotoSansCJKsc-Light.otf',
	FONTK.Regular:			'NotoSansCJKsc-Regular.otf',
})

g_mpStrScriptFontkStrTtf['hant'] = MpStrScriptFontkStrTtfOverrideLatn({
	FONTK.Bold:				'NotoSansCJKtc-Black.otf',
	FONTK.CondensedBold:	'NotoSansCJKtc-Bold.otf',
	FONTK.SemiBold:			'NotoSansCJKtc-Bold.otf',
	FONTK.SemiCondensed:	'NotoSansCJKtc-Regular.otf',
	FONTK.Light:			'NotoSansCJKtc-Light.otf',
	FONTK.LightItalic:		'NotoSansCJKtc-Light.otf',
	FONTK.Regular:			'NotoSansCJKtc-Regular.otf',
})

g_mpStrScriptFontkStrTtf['arab'] = MpStrScriptFontkStrTtfOverrideLatn({
	FONTK.Bold:				'NotoSansArabic-ExtraBold.otf',
	FONTK.CondensedBold:	'NotoSansArabic-CondensedBold.otf',
	FONTK.SemiBold:			'NotoSansArabic-Bold.otf',
	FONTK.SemiCondensed:	'NotoSansArabic-SemiCondensed.otf',
	FONTK.Light:			'NotoSansArabic-Light.otf',
	FONTK.LightItalic:		'NotoSansArabic-Light.otf',
	FONTK.Regular:			'NotoSansArabic-Regular.otf',
})

def StrTtfLookup(strStyle: str, strScript: str) -> str:
	fontk = g_mpStrStyleFontk[strStyle]

	if strTtf := g_mpStrScriptFontkStrTtf[strScript.lower()].get(fontk):
		return strTtf
		
	print(f"Warning: font style '{strStyle}' cannot determine ttf from script '{strScript}'")

	return 'consola.ttf'

def SetStrTtfFromSetStrScript(setStrScript: set[str]) -> set[str]:
	return { strTtf for strScript in setStrScript for strTtf in g_mpStrScriptFontkStrTtf[strScript.lower()].values() }
