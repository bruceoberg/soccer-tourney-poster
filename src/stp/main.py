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
from typing import Optional, Type, NamedTuple

from bolay import CPdf

from . import g_pathCode
from .config import PAGEK, TFmt, REGION, SPageArgs, SDocumentArgs, SWorklist, WlFromArgs, ParseArgs, DocaUnwind
from .fonts import SetStrTtfFromSetStrScript
from .loc import StrScriptFromLocale
from .profiling import Profiling, DumpTopCumulative
from .database import CTournamentDataBase
from .page import CPage, CGroupsTestPage, CDaysTestPage, CCalOnlyPage, CCalElimPage

logging.getLogger("fontTools.subset").setLevel(logging.ERROR)

def LocaleLang(locale: Locale) -> Locale:
	return Locale(locale.language, script=locale.script)

class SManifestKey(NamedTuple): # tag = mank
	strTz: str
	localeLang: Locale
	fmt: TFmt

class SPageResult(NamedTuple): # tag = pager
	strTz: str
	locale: Locale
	fmt: TFmt
	region: REGION

	def Mank(self) -> SManifestKey:
		return SManifestKey(
				self.strTz,
				LocaleLang(self.locale),
				self.fmt)
	
def PagerFromPage(page: CPage) ->SPageResult:
	return SPageResult(
			page.pagea.strTz,
			page.locale,
			page.fmt,
			page.pagea.region)

class SDocResult(NamedTuple): # tag = docr
	pathOutput: Path
	lPager: list[SPageResult]

class SManifestPage(NamedTuple): # tag = manp
	pathOutput: Path
	pager: SPageResult

class CManifest: # tag = manif
	def __init__(self, doca: Optional[SDocumentArgs], lDocr: list[SDocResult]) -> None:
		self.doca = doca
		self.setStrTz: set[str] = set()
		self.setLocaleLang: set[Locale] = set()
		self.setFmt: set[TFmt] = set()
		self.mpMankManp: dict[SManifestKey, SManifestPage] = {}

		if not self.doca:
			return

		if not self.doca.fUnwindPages:
			return

		for docr in lDocr:
			for pager in docr.lPager:
				mank = pager.Mank()

				assert mank not in self.mpMankManp
				self.mpMankManp[mank] = SManifestPage(docr.pathOutput, pager)

				self.setStrTz.add(mank.strTz)
				self.setLocaleLang.add(mank.localeLang)
				self.setFmt.add(mank.fmt)

		# self.PrintMissing()

		self.CollateUnwoundPages()

	def SetMankMissing(self) -> set[SManifestKey]:
		if not self.doca or not self.doca.fFillGrid:
			return set()
		
		setMankAll: set[SManifestKey] = set()

		for strTz in self.setStrTz:
			for localeLang in self.setLocaleLang:
				for fmt in self.setFmt:
					setMankAll.add(SManifestKey(strTz, localeLang, fmt))

		assert len(setMankAll) == len(self.setStrTz) * len(self.setLocaleLang) * len(self.setFmt)

		return setMankAll - set(self.mpMankManp.keys())
	
	def CollateUnwoundPages(self) -> None:
		assert self.doca

		# skip collated file when filling the grid

		if self.doca.fFillGrid:
			return

		pathOutput = self.doca.PathOutput(self.doca.strNameTourn)

		if not self.mpMankManp:
			# BB bruceo: SDocumentArgs.StrPath()?
			print(f"warning: no unwound documents for {pathOutput.relative_to(Path.cwd())}")
			return

		writer = PdfWriter()
		for manp in self.mpMankManp.values():
			writer.append(manp.pathOutput)

		print(f"collating to {pathOutput.relative_to(Path.cwd())}")

		pathOutput.parent.mkdir(parents=True, exist_ok=True)
		with pathOutput.open("wb") as fileDst:
			writer.write(fileDst)		

	def PrintMissing(self) -> None:
		assert self.doca

		if not self.doca.fUnwindPages:
			return

		if not self.mpMankManp:
			return
		
		setMankMissing = self.SetMankMissing()
		
		print(f"missing: {len(setMankMissing)} files from {len(self.setStrTz)} zones * {len(self.setLocaleLang)} langs * {len(self.setFmt)} sizes")
		print(f"extant: {len(self.mpMankManp)} files from total of {len(self.setStrTz) * len(self.setLocaleLang) * len(self.setFmt)}")

	def WlFillGrid(self) -> Optional[SWorklist]:
		if not self.doca:
			return None
		
		if not self.doca.fFillGrid:
			return None

		if not self.mpMankManp:
			# warn?
			return None
		
		lDoca: list[SDocumentArgs] = []
		
		for mank in self.SetMankMissing():
			# BB bruceo: need to choose a territory here
			lDoca.append(DocaUnwind(self.doca, SPageArgs(tz=mank.strTz, loc=str(mank.localeLang), format=mank.fmt)))
		
		return SWorklist(lDoca, None)

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

		lMankPages: list[SManifestKey] = [PagerFromPage(page).Mank() for page in self.lPage]

		self.pathOutput = self.doca.PathOutput(strName, lMankPages)

		self.pathOutput.parent.mkdir(parents=True, exist_ok=True)

		print(f"writing to {self.pathOutput.relative_to(Path.cwd())}")

		self.pdf.output(str(self.pathOutput))

	def Docr(self) -> Optional[SDocResult]:
		if not self.doca.fAutoFileSuffix:
			return None

		return SDocResult(self.pathOutput, [PagerFromPage(page) for page in self.lPage])

def DocrBuildDocaAsync(doca: SDocumentArgs) -> Optional[SDocResult]:
	# Top-level so ProcessPoolExecutor can pickle it.
	return CDocument(doca).Docr()

def LDocrBuildLDoca(lDoca: list[SDocumentArgs], cJob: int) -> list[SDocResult]:
	if cJob == 1 or len(lDoca) <= 1:
		return [docr for doca in lDoca if (docr := DocrBuildDocaAsync(doca))]

	cJob = min(cJob, len(lDoca))
	print(f"building {len(lDoca)} document(s) across {cJob} worker(s)")

	lDocr: list[SDocResult] = []
	with ProcessPoolExecutor(max_workers=cJob) as pool:
		lFuture = [pool.submit(DocrBuildDocaAsync, doca) for doca in lDoca]
		for future in as_completed(lFuture):
			if docr := future.result():
				lDocr.append(docr)
	return lDocr

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

		lDocr = LDocrBuildLDoca(wl.lDoca, cJob)

		manif = CManifest(wl.docaWind, lDocr)

		if wl := manif.WlFillGrid():
			assert wl.docaWind is None
			LDocrBuildLDoca(wl.lDoca, cJob)

	if fProfile:
		print(f"wrote profile to {pathProf}")

if __name__ == '__main__':
	main()
