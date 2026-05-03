#!/usr/bin/env python3

from __future__ import annotations  # Forward refs without quotes (eg foo: CFoo, not foo: 'CFoo')

import sys
import yaml

from enum import StrEnum
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from tap import Tap
from typing import Optional, Iterator

from . import g_pathCode
from .database import CDataBase

class PAGEK(StrEnum): # tag = pagek
	GroupsTest = 'groups_test'
	DaysTest = 'days_test'
	CalOnly = 'cal_only'
	CalElim = 'cal_elim'

TFmt = Optional[str | tuple[float, float]]

class SPageArgs(BaseModel): # tag - pagea
	"""Page configuration arguments.
	
	NOTE (bruceo) strLocale is a two letter ISO 639 language code, or
	one combined with a two letter ISO 3166-1 alpha-2 country code (e.g. en_GB/en_US/en_AU/en_NZ)
		languages: https://en.wikipedia.org/wiki/List_of_ISO_639_language_codes
		countries: https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2
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
	fFixturesOnly:          bool        = Field(default=False,			alias='fixtures_only')

TTuPagea = tuple[SPageArgs, ...]

class SDocumentArgs(BaseModel): # tag = doca
	"""Document configuration arguments."""
	
	model_config = ConfigDict(frozen=True, populate_by_name=True)
	
	strName:			str			= Field(				alias='name')
	tuPagea:			TTuPagea	= Field(				alias='pages')
	strNameTourn:		str			= Field(default='',		alias='tournament')
	strDirOutput:		str			= Field(default='',		alias='output_dir')
	strFileSuffix:		str			= Field(default='',		alias='file_suffix')
	fAddLangTzSuffix:	bool		= Field(default=False,	alias='add_lang_tz_suffix')
	fUnwindPages:		bool		= Field(default=False,	alias='unwind_pages')
	fAllTournaments:	bool		= Field(default=False,	alias='all_tournaments')
	fDefault:			bool		= Field(default=False,	alias='default')

def MpStrDocaLoad(pathYaml: Path) -> dict[str, SDocumentArgs]:
	"""Load all document configurations from a single YAML file."""

	with open(pathYaml, encoding='utf-8') as file:
		mpStrObjYaml = yaml.safe_load(file)
	
	mpStrDoca = {}
	for strName, objYaml in mpStrObjYaml.items():
		objYaml['strName'] = strName  # Inject the dict key as the name
		mpStrDoca[strName] = SDocumentArgs(**objYaml)
	
	return mpStrDoca

def ParseArgs() -> Tap:
	"""Parse CLI args for the poster generator. Returned Tap exposes fields used by IterDoca and main."""

	mpStrDoca = MpStrDocaLoad(g_pathCode / 'config.yaml')

	strDocaDefault: str = ''
	for strDoca, doca in mpStrDoca.items():
		if not strDocaDefault or doca.fDefault:
			strDocaDefault = strDoca

	class ArgumentParser(Tap):
		"""Soccer Tournament Poster Generator"""
		tournament: str = 'latest' # Tournament to generate for.
		document: str = strDocaDefault  # Document to output.
		output_dir: str = 'playground'  # Destination directory.
		profile: bool = False  # Enable cProfile instrumentation; writes profiles/run-<ts>.prof.
		profile_dump: Optional[str] = None  # Dump top cumulative-time stats from this .prof file and exit.

		def configure(self):
			self.add_argument('-t', '--tournament')
			self.add_argument('-d', '--document')
			self.add_argument('-o', '--output_dir')

	return ArgumentParser().parse_args()


def IterDoca(args: Tap) -> Iterator[SDocumentArgs]:

	mpStrDoca = MpStrDocaLoad(g_pathCode / 'config.yaml')

	lStrNameTournaments = CDataBase.LStrNameTournament()

	try:
		doca = mpStrDoca[args.document]
	except KeyError:
		sys.exit(f"unknown document {args.document}")

	if not doca.strDirOutput:
		doca = doca.model_copy(update={'strDirOutput': args.output_dir })

	if doca.fAllTournaments:
		assert(not doca.strNameTourn)
		assert(not doca.fUnwindPages)

		lPagea = []
		
		for strNameTourn in lStrNameTournaments:
			for pagea in doca.tuPagea:
				assert(not pagea.strNameTourn)
				lPagea.append(pagea.model_copy(update={'strNameTourn': strNameTourn }))

		doca = doca.model_copy(update={'tuPagea': tuple(lPagea)})

		yield doca
		
		return
	
	if doca.strNameTourn == 'latest':
		doca = doca.model_copy(update={'strNameTourn': lStrNameTournaments[-1] })

	if not doca.strNameTourn:
		doca = doca.model_copy(update={'strNameTourn': args.tournament })

	if not doca.fUnwindPages:
		yield doca
	else:
		assert(doca.strNameTourn)
		assert(doca.strFileSuffix)
		pathDirOutput = Path(doca.strDirOutput) / doca.strNameTourn
		doca = doca.model_copy(update={'strDirOutput': str(pathDirOutput) })

		yield doca

		for iPagea, pagea in enumerate(doca.tuPagea):
			assert(not pagea.strNameTourn)
			
			if iPagea == 0:
				yield SDocumentArgs(
						name = doca.strName,
						tournament = doca.strNameTourn,
						output_dir = doca.strDirOutput,
						file_suffix='',
						pages=(pagea,))

			yield SDocumentArgs(
					name = doca.strName,
					tournament = doca.strNameTourn,
					output_dir = doca.strDirOutput,
					file_suffix='',
					pages=(pagea,),
					add_lang_tz_suffix=True)
