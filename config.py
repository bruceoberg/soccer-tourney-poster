#!/usr/bin/env python3

# 'annotations' allow typing hints to forward reference.
#	e.g. Fn(fwd: CFwd) instead of Fn(fwd: 'CFwd')
#	when CFwd is later in file.
from __future__ import annotations

from dataclasses import dataclass

from pathlib import Path
from typing import Optional, Type, Iterable

from babel import Locale
import arrow
from dateutil import tz

from enum import StrEnum

#from pydantic import BaseModel, ValidationError

g_pathHere = Path(__file__).parent
#g_pathTourn = g_pathHere / 'tournaments' / '2018-mens-world-cup.xlsx'
#g_pathTourn = g_pathHere / 'tournaments' / '2022-mens-world-cup.xlsx'
#g_pathTourn = g_pathHere / 'tournaments' / '2023-womens-world-cup.xlsx'
#g_pathTourn = g_pathHere / 'tournaments' / '2024-mens-euro.xlsx'
#g_pathTourn = g_pathHere / 'tournaments' / '2024-mens-copa-america.xlsx'
#g_pathTourn = g_pathHere / 'tournaments' / '2025-mens-club-world-cup.xlsx'
g_pathTourn = g_pathHere / 'tournaments' / '2026-mens-world-cup.xlsx'


class PAGEK(StrEnum): # tag = pagek
	GroupsTest = 'groups_test'
	DaysTest = 'days_test'
	CalOnly = 'cal_only'
	CalElim = 'cal_elim'

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

lFmtIso216 = (
	'a0', 'a1', 'a2', 'a3', 'a4', 'a5', 'a6', 'a7', 'a8',
	'b0', 'b1', 'b2', 'b3', 'b4', 'b5', 'b6', 'b7', 'b8', 'b9', 'b10',
	'c0', 'c1', 'c2', 'c3', 'c4', 'c5', 'c6',
	'd0',
)

@dataclass
class SPageArgs: # tag - pagea

	# NOTE (bruceo) strLocale is a two letter ISO 639 language code, or
	# one combined with a two letter ISO 3166-1 alpha-2 country code (e.g. en_GB/en_US/en_AU/en_NZ)
	#	https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes
	# more importantly, it's a code honored by arrow
	#	https://arrow.readthedocs.io/en/latest/api-guide.html#module-arrow.locales

	pagek: PAGEK
	strOrientation: str = 'landscape'
	fmt: str | tuple[float, float] = (22, 28)
	strTz: str = 'US/Pacific'
	fmtCrop: Optional[str | tuple[float, float]] = (18, 27)
	strLocale: str = 'en_US'
	strVariant: str = ''
	fMainBorders: bool = True
	fEliminationBorders: bool = True
	fMatchNumbers: bool = False
	fGroupHints: bool = False
	fEliminationHints: bool = True
	fGroupDots: bool = True
	fResults: bool = False

@dataclass
class SDocumentArgs: # tag = doca
	iterPagea: Iterable[SPageArgs]
	strDestDir: str = ''
	strFileSuffix: str = ''

docaDefault = SDocumentArgs(
	strDestDir = 'playground',
	iterPagea = (
		#SPageArgs(CCalOnlyPage, fmt=(23, 35), fmtCrop=None, strTz='US/Eastern'),
		SPageArgs(PAGEK.CalElim, fmt='arch-d', fmtCrop=None, strTz='US/Pacific'),
		SPageArgs(PAGEK.CalElim, fmt='a1', fmtCrop=None, strLocale='en_AU', strTz='Australia/Sydney'),
		# SPageArgs(PAGEK.CalElim, fmt=(23, 35), fmtCrop=None, strTz='US/Pacific'),
		# SPageArgs(PAGEK.CalElim, fmt=(23, 35), fmtCrop=None, strTz='US/Eastern'),
		# SPageArgs(PAGEK.CalElim, fmt=(23, 35), fmtCrop=None, strLocale='en_AU', strTz='Australia/Sydney'),
		# SPageArgs(PAGEK.CalElim, fmt=(23, 35), fmtCrop=None, strLocale='ja', strTz='Asia/Tokyo'),
		# SPageArgs(PAGEK.CalElim, fmt=(23, 35), fmtCrop=None, strLocale='fa', strTz='Asia/Tehran'),
		# SPageArgs(PAGEK.CalElim, fmt=(20, 27), fmtCrop=None, strLocale='nl', strTz='Europe/Amsterdam'),
		# SPageArgs(PAGEK.CalElim, fmt=(20, 27), fmtCrop=None, strTz='Asia/Qatar'),
		# SPageArgs(PAGEK.CalElim, fmt=(20, 27), fmtCrop=None, strLocale='ja', strTz='Asia/Tokyo'),
		# SPageArgs(PAGEK.CalElim, fmt=(20, 27), fmtCrop=None, strLocale='fa', strTz='Asia/Tehran'),
		# SPageArgs(PAGEK.CalElim, fmt=(20, 27), fmtCrop=None, strTz='Australia/Sydney'),
	))

docaTests = SDocumentArgs(
	strDestDir = 'playground',
	iterPagea = (
		SPageArgs(PAGEK.GroupsTest),
		SPageArgs(PAGEK.DaysTest),
	))

docaDesigns = SDocumentArgs(
	strDestDir = 'playground',
	strFileSuffix = 'designs',
	iterPagea = (
		SPageArgs(PAGEK.CalOnly, fmt=(18, 27), fmtCrop=None, strVariant = 'alpha', fMatchNumbers = True, fEliminationHints = False, fGroupDots = False),
		SPageArgs(PAGEK.CalElim, fmt=(18, 27), fmtCrop=None, strVariant = 'beta', fEliminationBorders = False, fMatchNumbers = True, fEliminationHints = False, fGroupDots = False),
		SPageArgs(PAGEK.CalElim, fmt=(18, 27), fmtCrop=None, strVariant = 'borderless', fMainBorders = False),
		SPageArgs(PAGEK.CalElim, fmt=(18, 27), fmtCrop=None, strVariant = 'gold master'),
	))

docaRelease = SDocumentArgs(
	#strDestDir = str(Path('releases') / (g_pathTourn.stem + '-patch1' )),
	strDestDir = str(Path('releases') / g_pathTourn.stem),
	strFileSuffix = 'all',
	iterPagea = (
		SPageArgs(PAGEK.CalElim, fmt=(20, 27), fmtCrop=None),
		SPageArgs(PAGEK.CalElim, strTz='US/Pacific'),
		SPageArgs(PAGEK.CalElim, strTz='US/Mountain'),
		SPageArgs(PAGEK.CalElim, strTz='US/Central'),
		SPageArgs(PAGEK.CalElim, strTz='US/Eastern'),
		SPageArgs(PAGEK.CalElim, fmt='a1', fmtCrop=None, strTz='Europe/London', strLocale='en'),
		SPageArgs(PAGEK.CalElim, fmt='a1', fmtCrop=None, strTz='Europe/Paris', strLocale='fr'),
		SPageArgs(PAGEK.CalElim, fmt='a1', fmtCrop=None, strTz='Europe/Rome', strLocale='it'),
		SPageArgs(PAGEK.CalElim, fmt='a1', fmtCrop=None, strTz='Europe/Berlin', strLocale='de'),
		SPageArgs(PAGEK.CalElim, fmt='a1', fmtCrop=None, strTz='Europe/Madrid', strLocale='es'),
		SPageArgs(PAGEK.CalElim, fmt='a1', fmtCrop=None, strTz='Europe/Amsterdam', strLocale='nl'),
		SPageArgs(PAGEK.CalElim, fmt='a1', fmtCrop=None, strTz='Asia/Tehran', strLocale='fa'),
		SPageArgs(PAGEK.CalElim, fmt='a1', fmtCrop=None, strTz='Asia/Tokyo', strLocale='ja'),
		SPageArgs(PAGEK.CalElim, fmt='a1', fmtCrop=None, strTz='Australia/Sydney', strLocale='en'),
	))

lDocaRelease: list[SDocumentArgs] = []

for pagea in docaRelease.iterPagea:
	
	if pagea.fmt == (20, 27) and pagea.fmtCrop == None:	# BB (bruceo) somehow glean this from the pagea more explicitly
		lStrFileSuffix = []
	else:
		lStrFileSuffix = [Locale.parse(pagea.strLocale).language.lower()]

		if pagea.strTz == 'Asia/Tehran':
			lStrFileSuffix.append('irst')	# thanks arrow for not supporting iran
		else:
			tTz = arrow.utcnow().to(tz.gettz(pagea.strTz))
			strTz = tTz.format('ZZZ') # GMT, PST, etc
			lStrFileSuffix.append(strTz.lower())


	strFileSuffix = '-'.join(lStrFileSuffix)

	lDocaRelease.append(SDocumentArgs(strDestDir = docaRelease.strDestDir, strFileSuffix = strFileSuffix, iterPagea=(pagea,)))

llDocaTodo = [
	[
		docaDefault,
		# docaTests,
		# docaDesigns,
		# docaRelease,
	],
	#lDocaRelease,
]

