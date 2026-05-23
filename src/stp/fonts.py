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
	Handwritten = auto()

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
	'handwritten':					FONTK.Handwritten,
}

g_mpStrScriptFontkStrTtf: dict[str, dict[FONTK,str]] = {}

g_mpStrScriptFontkStrTtf['latn'] = {
	FONTK.Console: 				'NotoSansMono-Regular.ttf',
	FONTK.ConsoleItalic: 		'NotoSansMono-Thin.ttf',
	FONTK.Bold: 				'NotoSans-Bold.ttf',
	FONTK.CondensedBoldLatn:	'NotoSans-CondensedBold.ttf',
	FONTK.CondensedBold: 		'NotoSans-CondensedBold.ttf',
	FONTK.SemiBold: 			'NotoSans-SemiBold.ttf',
	FONTK.SemiCondensed: 		'NotoSans-SemiCondensed.ttf',
	FONTK.Light: 				'NotoSans-Light.ttf',
	FONTK.LightItalic: 			'NotoSans-LightItalic.ttf',
	FONTK.Regular: 				'NotoSans-Regular.ttf',
	FONTK.Handwritten: 			'ArchitectsDaughter-Regular.ttf',
}
assert len(g_mpStrScriptFontkStrTtf['latn']) is len(FONTK)

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
	FONTK.Console: 				'consola.ttf',
	FONTK.ConsoleItalic: 		'consolai.ttf',
	FONTK.Bold:				'NotoSansCJKjp-Black.ttf',
	FONTK.CondensedBold:	'NotoSansCJKjp-Bold.ttf',
	FONTK.SemiBold:			'NotoSansCJKjp-Bold.ttf',
	FONTK.SemiCondensed:	'NotoSansCJKjp-Regular.ttf',
	FONTK.Light:			'NotoSansCJKjp-Light.ttf',
	FONTK.LightItalic:		'NotoSansCJKjp-Light.ttf',
	FONTK.Regular:			'NotoSansCJKjp-Regular.ttf',
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
	FONTK.Bold:				'NotoSansCJKkr-Black.ttf',
	FONTK.CondensedBold:	'NotoSansCJKkr-Bold.ttf',
	FONTK.SemiBold:			'NotoSansCJKkr-Bold.ttf',
	FONTK.SemiCondensed:	'NotoSansCJKkr-Regular.ttf',
	FONTK.Light:			'NotoSansCJKkr-Light.ttf',
	FONTK.LightItalic:		'NotoSansCJKkr-Light.ttf',
	FONTK.Regular:			'NotoSansCJKkr-Regular.ttf',
})

g_mpStrScriptFontkStrTtf['hans'] = MpStrScriptFontkStrTtfOverrideLatn({
	FONTK.Bold:				'NotoSansCJKsc-Black.ttf',
	FONTK.CondensedBold:	'NotoSansCJKsc-Bold.ttf',
	FONTK.SemiBold:			'NotoSansCJKsc-Bold.ttf',
	FONTK.SemiCondensed:	'NotoSansCJKsc-Regular.ttf',
	FONTK.Light:			'NotoSansCJKsc-Light.ttf',
	FONTK.LightItalic:		'NotoSansCJKsc-Light.ttf',
	FONTK.Regular:			'NotoSansCJKsc-Regular.ttf',
})

g_mpStrScriptFontkStrTtf['hant'] = MpStrScriptFontkStrTtfOverrideLatn({
	FONTK.Bold:				'NotoSansCJKtc-Black.ttf',
	FONTK.CondensedBold:	'NotoSansCJKtc-Bold.ttf',
	FONTK.SemiBold:			'NotoSansCJKtc-Bold.ttf',
	FONTK.SemiCondensed:	'NotoSansCJKtc-Regular.ttf',
	FONTK.Light:			'NotoSansCJKtc-Light.ttf',
	FONTK.LightItalic:		'NotoSansCJKtc-Light.ttf',
	FONTK.Regular:			'NotoSansCJKtc-Regular.ttf',
})

g_mpStrScriptFontkStrTtf['arab'] = MpStrScriptFontkStrTtfOverrideLatn({
	FONTK.Bold:				'NotoSansArabic-ExtraBold.ttf',
	FONTK.CondensedBold:	'NotoSansArabic-CondensedBold.ttf',
	FONTK.SemiBold:			'NotoSansArabic-Bold.ttf',
	FONTK.SemiCondensed:	'NotoSansArabic-SemiCondensed.ttf',
	FONTK.Light:			'NotoSansArabic-Light.ttf',
	FONTK.LightItalic:		'NotoSansArabic-Light.ttf',
	FONTK.Regular:			'NotoSansArabic-Regular.ttf',
})

def StrTtfLookup(strStyle: str, strScript: str) -> str:
	fontk = g_mpStrStyleFontk[strStyle]

	if strTtf := g_mpStrScriptFontkStrTtf[strScript.lower()].get(fontk):
		return strTtf
		
	print(f"Warning: font style '{strStyle}' cannot determine ttf from script '{strScript}'")

	return 'consola.ttf'

def SetStrTtfFromSetStrScript(setStrScript: set[str]) -> set[str]:
	return { strTtf for strScript in setStrScript for strTtf in g_mpStrScriptFontkStrTtf[strScript.lower()].values() }
