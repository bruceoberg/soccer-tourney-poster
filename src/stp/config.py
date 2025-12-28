#!/usr/bin/env python3

# 'annotations' allow typing hints to forward reference.
#	e.g. Fn(fwd: CFwd) instead of Fn(fwd: 'CFwd')
#	when CFwd is later in file.
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Optional, Iterable

#from pydantic import BaseModel, ValidationError

#g_strNameTourn = '2018-mens-world-cup'			# 32 teams
#g_strNameTourn = '2022-mens-world-cup'			# 32 teams
#g_strNameTourn = '2023-womens-world-cup'		# 32 teams
#g_strNameTourn = '2024-mens-euro'				# 24 teams
#g_strNameTourn = '2024-mens-copa-america'		# 16 teams
#g_strNameTourn = '2025-mens-club-world-cup'	# 32 teams
g_strNameTourn = '2026-mens-world-cup'			# 48 teams


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

@dataclass
class SPageArgs: # tag - pagea

	# NOTE (bruceo) strLocale is a two letter ISO 639 language code, or
	# one combined with a two letter ISO 3166-1 alpha-2 country code (e.g. en_GB/en_US/en_AU/en_NZ)
	#	https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes
	# more importantly, it's a code honored by arrow
	#	https://arrow.readthedocs.io/en/latest/api-guide.html#module-arrow.locales

	pagek: PAGEK
	strNameTourn: str = ''
	strOrientation: str = 'landscape'
	strTz: str = 'US/Pacific'
	strLocale: str = 'en_US'
	strVariant: str = ''
	fmt: Optional[str | tuple[float, float]] = None
	fmtCrop: Optional[str | tuple[float, float]] = None
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
	strNameTourn: str = g_strNameTourn
	strDestDir: str = ''
	strFileSuffix: str = ''
	fAddLangTzSuffix: bool = False

docaDefault = SDocumentArgs(
	strDestDir = 'playground',
	strNameTourn='2026-mens-world-cup',
	iterPagea = (
		# SPageArgs(PAGEK.CalElim, strLocale='fa', strTz='Asia/Tehran', strNameTourn='2026-mens-world-cup'),
		# SPageArgs(PAGEK.CalElim, strLocale='fa', strTz='Asia/Tehran', strNameTourn='2025-mens-club-world-cup'),
		# SPageArgs(PAGEK.CalElim, strLocale='fa', strTz='Asia/Tehran', strNameTourn='2024-mens-copa-america'),
		# SPageArgs(PAGEK.CalElim, strLocale='fa', strTz='Asia/Tehran', strNameTourn='2024-mens-euro'		),
		# SPageArgs(PAGEK.CalElim, strLocale='fa', strTz='Asia/Tehran', strNameTourn='2023-womens-world-cup'),
		# SPageArgs(PAGEK.CalElim, strLocale='fa', strTz='Asia/Tehran', strNameTourn='2022-mens-world-cup'	),
		# SPageArgs(PAGEK.CalElim, strLocale='fa', strTz='Asia/Tehran', strNameTourn='2018-mens-world-cup'	),
		# SPageArgs(PAGEK.CalElim, strTz='US/Pacific'),
		# SPageArgs(PAGEK.CalElim, strTz='US/Eastern'),
		# SPageArgs(PAGEK.CalElim, strLocale='en_AU', strTz='Australia/Sydney'),
		# SPageArgs(PAGEK.CalElim, strLocale='ja', strTz='Asia/Tokyo'),
		# SPageArgs(PAGEK.CalElim, strLocale='fa', strTz='Asia/Tehran'),
		# SPageArgs(PAGEK.CalElim, strLocale='nl', strTz='Europe/Amsterdam'),
		# SPageArgs(PAGEK.CalElim, strTz='Asia/Qatar'),
		# SPageArgs(PAGEK.CalElim, strLocale='ja', strTz='Asia/Tokyo'),
		SPageArgs(PAGEK.CalElim, strLocale='fa', strTz='Asia/Tehran'),
		SPageArgs(PAGEK.CalElim, strLocale='fa', strTz='Europe/Amsterdam'),
		SPageArgs(PAGEK.CalElim, strLocale='en_GB', strTz='Europe/Amsterdam'),
		SPageArgs(PAGEK.CalElim, strLocale='nl', strTz='Europe/Amsterdam'),
		# SPageArgs(PAGEK.CalElim, strTz='Australia/Sydney'),
		# SPageArgs(PAGEK.GroupsTest, fmt='tabloid', strLocale='fa', strTz='Asia/Tehran', strNameTourn='2026-mens-world-cup'),
		# SPageArgs(PAGEK.GroupsTest, fmt='tabloid', strLocale='en_US', strTz='US/Pacific', strNameTourn='2026-mens-world-cup'),
		#SPageArgs(CCalOnlyPage, strTz='US/Eastern'),
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
		SPageArgs(PAGEK.CalOnly, strVariant = 'alpha', fMatchNumbers = True, fEliminationHints = False, fGroupDots = False),
		SPageArgs(PAGEK.CalElim, strVariant = 'beta', fEliminationBorders = False, fMatchNumbers = True, fEliminationHints = False, fGroupDots = False),
		SPageArgs(PAGEK.CalElim, strVariant = 'borderless', fMainBorders = False),
		SPageArgs(PAGEK.CalElim, strVariant = 'gold master'),
	))

docaAllLang = SDocumentArgs(
	strDestDir = 'playground',
	strNameTourn='2024-mens-copa-america',
	strFileSuffix = 'all',
	iterPagea = (
		SPageArgs(PAGEK.CalElim, strTz='US/Pacific'),
		SPageArgs(PAGEK.CalElim, strTz='US/Mountain'),
		SPageArgs(PAGEK.CalElim, strTz='US/Central'),
		SPageArgs(PAGEK.CalElim, strTz='US/Eastern'),
		SPageArgs(PAGEK.CalElim, strTz='Europe/London', strLocale='en_GB'),
		SPageArgs(PAGEK.CalElim, strTz='Europe/Paris', strLocale='fr'),
		SPageArgs(PAGEK.CalElim, strTz='Europe/Rome', strLocale='it'),
		SPageArgs(PAGEK.CalElim, strTz='Europe/Berlin', strLocale='de'),
		SPageArgs(PAGEK.CalElim, strTz='Europe/Madrid', strLocale='es_ES'),
		SPageArgs(PAGEK.CalElim, strTz='Europe/Amsterdam', strLocale='nl'),
		SPageArgs(PAGEK.CalElim, strTz='Europe/Amsterdam', strLocale='fa'),
		SPageArgs(PAGEK.CalElim, strTz='Asia/Tehran', strLocale='fa'),
		SPageArgs(PAGEK.CalElim, strTz='Asia/Tokyo', strLocale='ja'),
		SPageArgs(PAGEK.CalElim, strTz='Australia/Sydney', strLocale='en_AU'),
		SPageArgs(PAGEK.CalElim, strTz='Pacific/Auckland', strLocale='en_NZ'),
	))

docaRelease = SDocumentArgs(
	#strDestDir = str(Path('releases') / (g_strNameTourn + '-patch1' )),
	strDestDir = str(Path('releases') / g_strNameTourn),
	strFileSuffix = 'all',
	iterPagea = (
		SPageArgs(PAGEK.CalElim, strTz='US/Pacific'),
		SPageArgs(PAGEK.CalElim, strTz='US/Mountain'),
		SPageArgs(PAGEK.CalElim, strTz='US/Central'),
		SPageArgs(PAGEK.CalElim, strTz='US/Eastern'),
		SPageArgs(PAGEK.CalElim, strTz='Europe/London', strLocale='en_GB'),
		SPageArgs(PAGEK.CalElim, strTz='Europe/Paris', strLocale='fr'),
		SPageArgs(PAGEK.CalElim, strTz='Europe/Rome', strLocale='it'),
		SPageArgs(PAGEK.CalElim, strTz='Europe/Berlin', strLocale='de'),
		SPageArgs(PAGEK.CalElim, strTz='Europe/Madrid', strLocale='es_ES'),
		SPageArgs(PAGEK.CalElim, strTz='Europe/Amsterdam', strLocale='nl'),
		SPageArgs(PAGEK.CalElim, strTz='Europe/Amsterdam', strLocale='fa'),
		SPageArgs(PAGEK.CalElim, strTz='Asia/Tehran', strLocale='fa'),
		SPageArgs(PAGEK.CalElim, strTz='Asia/Tokyo', strLocale='ja'),
		SPageArgs(PAGEK.CalElim, strTz='Australia/Sydney', strLocale='en_AU'),
		SPageArgs(PAGEK.CalElim, strTz='Pacific/Auckland', strLocale='en_NZ'),
	))

lDocaRelease: list[SDocumentArgs] = []

for iPagea, pagea in enumerate(docaRelease.iterPagea):
	
	if iPagea == 0:
		lDocaRelease.append(SDocumentArgs(strDestDir = docaRelease.strDestDir, iterPagea=(pagea,)))

	lDocaRelease.append(SDocumentArgs(strDestDir = docaRelease.strDestDir, fAddLangTzSuffix=True, iterPagea=(pagea,)))

llDocaTodo = [
	[
		docaDefault,
		# docaTests,
		# docaDesigns,
		# docaAllLang,
		# docaRelease,
	],
	#lDocaRelease,
]

