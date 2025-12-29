#!/usr/bin/env python3

from __future__ import annotations  # Forward refs without quotes (eg foo: CFoo, not foo: 'CFoo')

import sys
import yaml

from enum import StrEnum
from pathlib import Path
from typing import Optional, Iterator

from pydantic import BaseModel, Field, ConfigDict

g_pathCode = Path(__file__).parent

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

TFmt = Optional[str | tuple[float, float]]

class SPageArgs(BaseModel): # tag - pagea
	"""Page configuration arguments.
	
	NOTE (bruceo) strLocale is a two letter ISO 639 language code, or
	one combined with a two letter ISO 3166-1 alpha-2 country code (e.g. en_GB/en_US/en_AU/en_NZ)
		https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes
	more importantly, it's a code honored by arrow
		https://arrow.readthedocs.io/en/latest/api-guide.html#module-arrow.locales
	"""
	
	model_config = ConfigDict(frozen=True, populate_by_name=True)

	pagek:                  PAGEK       = Field(default=PAGEK.CalElim,	alias='page_kind')
	strNameTourn:           str         = Field(default='',				alias='tournament')
	strOrientation:         str         = Field(default='landscape',	alias='orientation')
	strTz:                  str         = Field(default='US/Pacific',	alias='tz')
	strLocale:              str         = Field(default='en_US',		alias='loc')
	strVariant:             str         = Field(default='',				alias='variant')
	fmt:                    TFmt        = Field(default=None,			alias='format')
	fmtCrop:                TFmt        = Field(default=None,			alias='crop_format')
	fMainBorders:           bool        = Field(default=True,			alias='main_borders')
	fEliminationBorders:    bool        = Field(default=True,			alias='elimination_borders')
	fMatchNumbers:          bool        = Field(default=False,			alias='match_numbers')
	fGroupHints:            bool        = Field(default=False,			alias='group_hints')
	fEliminationHints:      bool        = Field(default=True,			alias='elimination_hints')
	fGroupDots:             bool        = Field(default=True,			alias='group_dots')
	fResults:               bool        = Field(default=False,			alias='results')

TTuPagea = tuple[SPageArgs, ...]

class SDocumentArgs(BaseModel): # tag = doca
	"""Document configuration arguments."""
	
	model_config = ConfigDict(frozen=True, populate_by_name=True)
	
	tuPagea:              	TTuPagea   = Field(							alias='pages')
	strNameTourn:           str        = Field(default=g_strNameTourn,	alias='tournament')
	pathDirDest:            Path       = Field(default=Path(),			alias='destination_dir')
	strFileSuffix:          str        = Field(default='',				alias='file_suffix')
	fAddLangTzSuffix:       bool       = Field(default=False,			alias='add_lang_tz_suffix')
	fUnwindPages:           bool       = Field(default=False,			alias='unwind_pages')

def MpStrDocaLoad(pathYaml: Path) -> dict[str, SDocumentArgs]:
	"""Load all document configurations from a single YAML file."""

	with open(pathYaml, encoding='utf-8') as file:
		mpStrObjYaml = yaml.safe_load(file)
	
	return { strName: SDocumentArgs(**objYaml) for strName, objYaml in mpStrObjYaml.items() }

def IterDoca(strName: str) -> Iterator[SDocumentArgs]:

	mpStrDoca = MpStrDocaLoad(g_pathCode / 'config.yaml')

	try:
		doca = mpStrDoca[strName]

		if doca.fUnwindPages:
			assert(doca.strNameTourn)
			assert(doca.strFileSuffix)
			doca = doca.model_copy(update={'pathDirDest': doca.pathDirDest / doca.strNameTourn})

		yield doca
	except KeyError:
		sys.exit(f"unknown document {strName}")
	
	if doca.fUnwindPages:
		for iPagea, pagea in enumerate(doca.tuPagea):
			assert(not pagea.strNameTourn)
			
			if iPagea == 0:
				yield SDocumentArgs(
						tournament = doca.strNameTourn,
						destination_dir = doca.pathDirDest,
						file_suffix='',
						pages=(pagea,))

			yield SDocumentArgs(
					tournament = doca.strNameTourn,
					destination_dir = doca.pathDirDest,
					file_suffix='',
					pages=(pagea,),
					add_lang_tz_suffix=True)
