#!/usr/bin/env python3

from __future__ import annotations  # Forward refs without quotes (eg foo: CFoo, not foo: 'CFoo')

import arrow
import fpdf
import logging
import os
import platform

from babel import Locale
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from pypdf import PdfWriter
from typing import Optional, Type

from bolay import CPdf

from . import g_pathCode
from .config import PAGEK, TFmt, SDocKey, SDocResult, SDocumentArgs, SWorklist, WlFromArgs, ParseArgs, StrFromFmt
from .fonts import SetStrTtfFromSetStrScript
from .loc import StrScriptFromLocale
from .profiling import Profiling, DumpTopCumulative
from .database import CTournamentDataBase
from .page import CPage, CGroupsTestPage, CDaysTestPage, CCalOnlyPage, CCalElimPage

logging.getLogger("fontTools.subset").setLevel(logging.ERROR)

class CManifest: # tag = manif
	def __init__(self, doca: Optional[SDocumentArgs], lDr: list[SDocResult]) -> None:
		self.doca = doca
		self.setStrTz: set[str] = set()
		self.setStrLang: set[str] = set()
		self.setFmt: set[TFmt] = set()
		self.mpDkPath: dict[SDocKey, Path] = {}

		if not self.doca:
			return

		if not self.doca.fUnwindPages:
			return

		for dr in lDr:
			for dk in dr.lDk:
				assert dk not in self.mpDkPath
				self.mpDkPath[dk] = dr.pathOutput

				self.setStrTz.add(dk.strTz)
				self.setStrLang.add(dk.strLang)
				self.setFmt.add(dk.fmt)

		# self.PrintMissing()

		self.Wind()

	def SetDkMissing(self) -> set[SDocKey]:
		if not self.doca or not self.doca.fUnwindPages:
			return set()

		setDkAll: set[SDocKey] = set()

		for strTz in self.setStrTz:
			for strLang in self.setStrLang:
				for fmt in self.setFmt:
					setDkAll.add(SDocKey(strTz, strLang, fmt))

		assert len(setDkAll) == len(self.setStrTz) * len(self.setStrLang) * len(self.setFmt)

		return setDkAll - set(self.mpDkPath.keys())
	
	def Wind(self) -> None:
		assert self.doca

		pathOutput = self.doca.PathOutput(self.doca.strNameTourn)

		if not self.mpDkPath:
			# BB bruceo: SDocumentArgs.StrPath()?
			print(f"warning: no unwound documents for {pathOutput.relative_to(Path.cwd())}")
			return

		writer = PdfWriter()
		for path in self.mpDkPath.values():
			writer.append(path)

		print(f"collating to {pathOutput.relative_to(Path.cwd())}")

		pathOutput.parent.mkdir(parents=True, exist_ok=True)
		with pathOutput.open("wb") as fileDst:
			writer.write(fileDst)		

	def PrintMissing(self) -> None:
		assert self.doca

		if not self.doca.fUnwindPages:
			return

		if not self.mpDkPath:
			return
		
		setDkMissing = self.SetDkMissing()
		
		print(f"missing: {len(setDkMissing)} files from {len(self.setStrTz)} zones * {len(self.setStrLang)} langs * {len(self.setFmt)} sizes")
		print(f"extant: {len(self.mpDkPath)} files from total of {len(self.setStrTz) * len(self.setStrLang) * len(self.setFmt)}")

	def WlFillGrid(self) -> Optional[SWorklist]:
		if not self.doca:
			return None
		
		if not self.doca.fUnwindPages:
			return None

		if not self.doca.fFillGrid:
			return None

		if not self.mpDkPath:
			# warn?
			return None
		
		return None

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

	def Dr(self) -> Optional[SDocResult]:
		if not self.doca.fAutoFileSuffix:
			return None

		return SDocResult(self.pathOutput, [page.Dk() for page in self.lPage])

def DrBuildDocaAsync(doca: SDocumentArgs) -> Optional[SDocResult]:
	# Top-level so ProcessPoolExecutor can pickle it.
	return CDocument(doca).Dr()

def LDrBuildLDoca(lDoca: list[SDocumentArgs], cJob: int) -> list[SDocResult]:
	if cJob == 1 or len(lDoca) <= 1:
		return [dr for doca in lDoca if (dr := DrBuildDocaAsync(doca))]

	cJob = min(cJob, len(lDoca))
	print(f"building {len(lDoca)} document(s) across {cJob} worker(s)")

	lDr: list[SDocResult] = []
	with ProcessPoolExecutor(max_workers=cJob) as pool:
		lFuture = [pool.submit(DrBuildDocaAsync, doca) for doca in lDoca]
		for future in as_completed(lFuture):
			if dr := future.result():
				lDr.append(dr)
	return lDr

def main():
	args = ParseArgs()

	if args.profile_dump:
		DumpTopCumulative(Path(args.profile_dump))
		return

	fProfile: bool = args.profile
	tNow = arrow.now()
	pathProf = Path('profiles') / f"run-{tNow.format('YYYYMMDD-HHmmss')}.prof"

	# cProfile in workers would scatter stats across processes; force serial when profiling.
	cJob = 1 if fProfile else (args.jobs if args.jobs > 0 else max(1, (os.cpu_count() or 1) - 2))

	with Profiling(pathProf, fEnabled=fProfile):

		wl = WlFromArgs(args)

		for doca in wl.lDoca:
			assert not doca.fUnwindPages
			assert not doca.fFillGrid

		lDr = LDrBuildLDoca(wl.lDoca, cJob)

		manif = CManifest(wl.docaWind, lDr)

		if wl := manif.WlFillGrid():
			assert wl.docaWind is None
			LDrBuildLDoca(wl.lDoca, cJob)

	if fProfile:
		print(f"wrote profile to {pathProf}")

if __name__ == '__main__':
	main()
