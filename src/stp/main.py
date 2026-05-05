#!/usr/bin/env python3

from __future__ import annotations  # Forward refs without quotes (eg foo: CFoo, not foo: 'CFoo')

import arrow
import fpdf
import logging
import platform

from babel import Locale
from pathlib import Path
from pypdf import PdfWriter

from bolay import CPdf

from . import g_pathCode
from .config import PAGEK, TFmt, SDocKey, SDocumentArgs, IterDoca, ParseArgs, StrFromFmt
from .fonts import SetStrTtfFromSetStrScript
from .loc import StrFileFromLocale, StrScriptFromLocale
from .profiling import Profiling, DumpTopCumulative
from .database import CTournamentDataBase
from .page import CPage, CGroupsTestPage, CDaysTestPage, CCalOnlyPage, CCalElimPage

logging.getLogger("fontTools.subset").setLevel(logging.ERROR)

class CManifest: # tag = manif
	def __init__(self) -> None:
		self.setStrTz: set[str] = set()
		self.setStrLang: set[str] = set()
		self.setFmt: set[TFmt] = set()
		self.mpDkDoc: dict[SDocKey, CDocument] = {}

	def RegisterDk(self, dk: SDocKey) -> None:
		self.setStrTz.add(dk.strTz)
		self.setStrLang.add(dk.strLang)
		self.setFmt.add(dk.fmt)

	def RegisterDoc(self, doc: CDocument) -> None:
		if not doc.doca.fAutoFileSuffix:
			return
		
		for page in doc.lPage:
			dk = page.Dk()
			
			self.RegisterDk(dk)

			assert dk not in self.mpDkDoc
			self.mpDkDoc[dk] = doc

	def SetDkMissing(self) -> set[SDocKey]:
		setDkAll: set[SDocKey] = set()

		for strTz in self.setStrTz:
			for strLang in self.setStrLang:
				for fmt in self.setFmt:
					setDkAll.add(SDocKey(strTz, strLang, fmt))

		assert len(setDkAll) == len(self.setStrTz) * len(self.setStrLang) * len(self.setFmt)

		return setDkAll - set(self.mpDkDoc.keys())
	
	def Wind(self, doca: SDocumentArgs) -> None:

		pathOutput = doca.PathOutput(doca.strNameTourn)

		if not self.mpDkDoc:
			# BB bruceo: SDocumentArgs.StrPath()?
			print(f"warning: no unwound documents for {pathOutput.relative_to(Path.cwd())}")
			return

		writer = PdfWriter()
		for doc in self.mpDkDoc.values():
			writer.append(doc.pathOutput)

		print(f"writing to {pathOutput.relative_to(Path.cwd())}")

		pathOutput.parent.mkdir(parents=True, exist_ok=True)
		with pathOutput.open("wb") as fileDst:
			writer.write(fileDst)		

	def PrintMissing(self) -> None:
		if not self.mpDkDoc:
			return
		
		setDkMissing = self.SetDkMissing()
		
		print(f"missing: {len(setDkMissing)} files from {len(self.setStrTz)} zones * {len(self.setStrLang)} langs * {len(self.setFmt)} sizes")
		print(f"extant: {len(self.mpDkDoc)} files from total of {len(self.setStrTz) * len(self.setStrLang) * len(self.setFmt)}")

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

		if self.doca.fAutoFileSuffix:
			lDkPages: list[SDocKey] = [page.Dk() for page in self.lPage]
		else:
			lDkPages: list[SDocKey] = []

		self.pathOutput = self.doca.PathOutput(strName, lDkPages)

		self.pathOutput.parent.mkdir(parents=True, exist_ok=True)

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

	manif = CManifest()

	with Profiling(pathProf, fEnabled=fProfile):
		for doca in IterDoca(args):
			if doca.fUnwindPages:
				manif.Wind(doca)
			else:
				manif.RegisterDoc(CDocument(doca))

		# manif.PrintMissing()

	if fProfile:
		print(f"wrote profile to {pathProf}")

if __name__ == '__main__':
	main()
