#!/usr/bin/env python3

from __future__ import annotations  # Forward refs without quotes (eg foo: CFoo, not foo: 'CFoo')

import arrow
import fpdf
import logging
import platform

from babel import Locale
from os import sep as g_chPathSeparator
from pathlib import Path
from typing import Type

from bolay import CPdf

from . import g_pathCode
from .config import PAGEK, SDocumentArgs, IterDoca, ParseArgs, StrFromFmt
from .fonts import SetStrTtfFromSetStrScript
from .loc import StrFileFromLocale, StrScriptFromLocale
from .profiling import Profiling, DumpTopCumulative
from .database import CTournamentDataBase
from .page import CPage, CGroupsTestPage, CDaysTestPage, CCalOnlyPage, CCalElimPage

logging.getLogger("fontTools.subset").setLevel(logging.ERROR)

class CDocument: # tag = doc
	s_pathDirFonts = g_pathCode / 'fonts'

	s_mpPagekClsPage: dict[PAGEK, Type[CPage]] = {
		PAGEK.GroupsTest:	CGroupsTestPage,
		PAGEK.DaysTest:		CDaysTestPage,
		PAGEK.CalOnly:		CCalOnlyPage,
		PAGEK.CalElim:		CCalElimPage,
	}

	def __init__(self, doca: SDocumentArgs) -> None:
		self.doca = doca
		self.pdf = CPdf()

		if doca.strNameTourn:
			strName = doca.strNameTourn
			self.tourn = CTournamentDataBase.TournFromStrName(strName)
			strSubject = strKeywords = ' '.join(strName.split('-'))
		else:
			strName = doca.strName
			self.tourn = None
			strSubject = 'collection'
			strKeywords = ''

		self.pdf.set_title(strName)
		self.pdf.set_author('bruce oberg')
		self.pdf.set_subject(strSubject)
		self.pdf.set_keywords(strKeywords)
		self.pdf.set_creator(f'python v{platform.python_version()}, fpdf2 v{fpdf.__version__}')
		self.pdf.set_lang('en')
		self.pdf.set_creation_date(arrow.now().datetime)

		# load fonts for referenced locales

		setLocale: set[Locale] = {Locale.parse(pagea.strLocale) for pagea in doca.tuPagea}
		setStrScript: set[str] = { StrScriptFromLocale(locale) for locale in setLocale }

		for strTtf in SetStrTtfFromSetStrScript(setStrScript):
			self.pdf.AddFont(strTtf, '', self.s_pathDirFonts / strTtf)

		self.lPage: list[CPage] = [self.s_mpPagekClsPage[pagea.pagek](self, pagea) for pagea in self.doca.tuPagea]

		self.pathDirOutput = Path.cwd()

		if self.doca.strDirOutput:
			self.pathDirOutput /= self.doca.strDirOutput

		lStrFile = [strName]

		if self.doca.strFileSuffix:
			lStrFile.append(self.doca.strFileSuffix)

		if self.doca.fAddLangTzSuffix:
			for page in self.lPage:
				lStrFile.append(page.pagea.strTz.replace(g_chPathSeparator, '#'))
				lStrFile.append(page.locale.language)
				lStrFile.append(StrFromFmt(page.fmt))

		strFile = '+'.join(lStrFile).lower()

		self.pathDirOutput.mkdir(parents=True, exist_ok=True)
		self.pathOutput = (self.pathDirOutput / strFile).with_suffix('.pdf')

		print(f"writing to {self.pathOutput.relative_to(Path.cwd())}")

		self.pdf.output(str(self.pathOutput))

def main():
	args = ParseArgs()

	if args.profile_dump:
		DumpTopCumulative(Path(args.profile_dump))
		return

	fProfile: bool = args.profile
	tNow = arrow.now()
	pathProf = Path('profiles') / f"run-{tNow.format('YYYYMMDD-HHmmss')}.prof"

	with Profiling(pathProf, fEnabled=fProfile):
		for doca in IterDoca(args):
			CDocument(doca)

	if fProfile:
		print(f"wrote profile to {pathProf}")

if __name__ == '__main__':
	main()
