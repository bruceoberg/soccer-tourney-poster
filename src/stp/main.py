#!/usr/bin/env python3

from __future__ import annotations  # Forward refs without quotes (eg foo: CFoo, not foo: 'CFoo')

import arrow
import fpdf
import logging
import os
import platform
import sys

from babel import Locale
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from pypdf import PdfWriter
from tqdm import tqdm
from typing import Optional, Type, NamedTuple, Iterator

from bolay import CPdf

from . import g_pathCode
from .config import PAGEK, TFmt, REGION, SPageArgs, SDocumentArgs, SWorklist, WlFromArgs, ParseArgs, DocaUnwind, StrFromFmt
from .fonts import SetStrTtfFromSetStrScript
from .loc import CZoneName, StrScriptFromLocale, StrLocaleFromTzLocaleLang, StrLocaleFromLocaleLang, StrLangShortFromLocale, CZoneScope
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
	zonename: CZoneName
	locale: Locale
	fmt: TFmt
	region: REGION
	lStrTzAliases: list[str]

	def IterMank(self) -> Iterator[SManifestKey]:
		for strTz in [self.strTz] + self.lStrTzAliases:
			yield SManifestKey(
					strTz,
					LocaleLang(self.locale),
					self.fmt)
	
def PagerFromPage(page: CPage) ->SPageResult:
	return SPageResult(
			page.pagea.strTz,
			page.zonename,
			page.locale,
			page.fmt,
			page.pagea.region,
			page.pagea.lStrTzAlias)

class SDocResult(NamedTuple): # tag = docr
	pathOutput: Path
	lPager: list[SPageResult]

class SManifestPage(NamedTuple): # tag = manp
	pathOutput: Path
	pager: SPageResult

class CManifest: # tag = manif
	def __init__(self, doca: Optional[SDocumentArgs], lDocr: list[SDocResult]) -> None:
		self.doca = doca
		self.mpMankManp: dict[SManifestKey, SManifestPage] = {}
		self.setStrTz: set[str] = set()
		self.setLocaleLang: set[Locale] = set()
		self.setFmt: set[TFmt] = set()
		self.mpStrTzFmtDefault: dict[str, TFmt] = {}
		self.mpStrTzStrUtcOnly: dict[str, str] = {}
		self.setMankMissing: set[SManifestKey] = set()

		if not self.doca:
			return

		if not self.doca.fUnwindPages:
			return

		for docr in lDocr:
			for pager in docr.lPager:
				for mank in pager.IterMank():

					assert mank not in self.mpMankManp
					self.mpMankManp[mank] = SManifestPage(docr.pathOutput, pager)

					self.setStrTz.add(mank.strTz)
					self.setLocaleLang.add(mank.localeLang)
					self.setFmt.add(mank.fmt)

					try:
						fmtFound = self.mpStrTzFmtDefault[mank.strTz]
						if fmtFound != mank.fmt:
							sys.exit(f"error: tz {mank.strTz} specifies two page formats: {str(fmtFound)} and {str(mank.fmt)}")
					except KeyError:
						self.mpStrTzFmtDefault[mank.strTz] = mank.fmt

					strUtcOnlyPager = pager.zonename.StrUtcOnly()
					if strUtcOnlyFound := self.mpStrTzStrUtcOnly.get(mank.strTz):
						if strUtcOnlyFound != strUtcOnlyPager:
							sys.exit("error: tz {mank.strTz} maps to both {strUtcOnly} and {strUtcOnlyPager}")
					else:
						self.mpStrTzStrUtcOnly[mank.strTz] = strUtcOnlyPager

		self.setMankMissing = self.SetMankMissing()

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
		
		print(f"missing: {len(self.setMankMissing)} files from {len(self.setStrTz)} zones * {len(self.setLocaleLang)} langs * {len(self.setFmt)} sizes")
		print(f"extant: {len(self.mpMankManp)} files from total of {len(self.setStrTz) * len(self.setLocaleLang) * len(self.setFmt)}")

	def WlMissing(self) -> Optional[SWorklist]:
		if not self.doca:
			return None
		
		if not self.doca.fFillGrid:
			return None

		if not self.mpMankManp:
			# warn?
			return None
		
		lDoca: list[SDocumentArgs] = []
		mpMankUtcOnlySetMankMissing: dict[SManifestKey, set[SManifestKey]] = {}
		
		
		for mankMissing in self.setMankMissing:
			strLocale = StrLocaleFromTzLocaleLang(mankMissing.strTz, mankMissing.localeLang)

			if not strLocale:
				# timezone(city) does not natively support this language (eg french in the US).

				# fall back to a generic UTC only timezone. later we'll choose the "standard" territory
				# for that language.

				# since we're falling back to UTC only, we may map multiple missing manks to the same
				# destination file. that's good! we want this to minimize the number of PDFs we create.
				# for cities in the same timezone, whose territories don't support a language, we want
				# to map the output to the same generic language+tz file. this can reduce our PDF count
				# by 60% to 70%. instead of oodles of similar PDFs for obscure city/language combos, we
				# can have just tz/language combos and point multiple cities to each tz.

				strUtcOnly = self.mpStrTzStrUtcOnly[mankMissing.strTz]

				mankUtcOnly = SManifestKey(strUtcOnly, mankMissing.localeLang, mankMissing.fmt)
				setMankMissing = mpMankUtcOnlySetMankMissing.setdefault(mankUtcOnly, set())
				setMankMissing.add(mankMissing)

				continue

			# BB bruceo: need to choose a territory here
			lDoca.append(DocaUnwind(self.doca, SPageArgs(tz=mankMissing.strTz, loc=strLocale, format=mankMissing.fmt)))

		for mankUtcOnly, setMankMissing in mpMankUtcOnlySetMankMissing.items():
			lStrTzAlias = [mankMissing.strTz for mankMissing in setMankMissing]

			# use the "most common" locale for the given language.

			strLocale = StrLocaleFromLocaleLang(mankUtcOnly.localeLang)

			# the strTz in mankUtcOnly is a pseudo tz string of the form UTC±HHMM. we need to use one of the
			# parsable ones from our missing sets. it doesn't matter which one, since they all map to the same
			# UTC offset.

			lDoca.append(
				DocaUnwind(
					self.doca,
					SPageArgs(
						tz=lStrTzAlias[0],
						loc=strLocale,
						format=mankUtcOnly.fmt,
						# NOTE bruceo: could argue that single city UTC only entries should have city names.
						# with utc_only always true, we get more UTC names, which is what we want for the big grid.
						utc_only=True, #len(lStrTzAlias)>1,
						tz_aliases=lStrTzAlias[1:])))
		
		return SWorklist(lDoca, None)
	
	def WriteGridManifests(self, lDocr: list[SDocResult]) -> None:
		if not self.doca:
			return None
		
		if not self.doca.fFillGrid:
			return None

		if not self.mpMankManp:
			# warn?
			return None
		
		# very similar to loop in __init__
		
		for docr in lDocr:
			for pager in docr.lPager:
				for mank in pager.IterMank():

					assert mank not in self.mpMankManp
					self.mpMankManp[mank] = SManifestPage(docr.pathOutput, pager)

					assert mank.strTz in self.setStrTz
					assert mank.localeLang in self.setLocaleLang
					assert mank.fmt in self.setFmt

		# everything should be covered now

		assert not self.SetMankMissing()

		# build top level mank list ...
		# - original cities
		# - all their supported languages.
		# - only their preferred paper format

		for strTz in self.setStrTz:
			zscope = CZoneScope(strTz, self.setLocaleLang)
			fmtDefault = self.mpStrTzFmtDefault[strTz]

			lStrLangs = [StrLangShortFromLocale(locale) for locale in zscope.setLocaleLang]
			print(f"manifest: {strTz} ({zscope.strTerritory}) <{StrFromFmt(fmtDefault)}> [{'/'.join(lStrLangs)}]")


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

		self.pathOutput = self.doca.PathOutput(strName, self.lPage)

		self.pathOutput.parent.mkdir(parents=True, exist_ok=True)

		if any([page.pagea.fUtcOnly for page in self.lPage]):
			if self.pathOutput.exists():
				sys.exit(f"error: overwriting grid file {self.pathOutput.relative_to(Path.cwd())}")

		self.pdf.output(str(self.pathOutput))

	def Docr(self) -> Optional[SDocResult]:
		if not self.doca.fAutoFileSuffix:
			return None

		return SDocResult(self.pathOutput, [PagerFromPage(page) for page in self.lPage])

def DocrBuildDocaAsync(doca: SDocumentArgs) -> Optional[SDocResult]:
	# Top-level so ProcessPoolExecutor can pickle it.
	return CDocument(doca).Docr()

def LDocrBuildLDoca(lDoca: list[SDocumentArgs], cJob: int) -> list[SDocResult]:
	lDocr: list[SDocResult] = []

	if cJob == 1 or len(lDoca) <= 1:
		for doca in lDoca:
			doc = CDocument(doca)
			if docr := doc.Docr():
				lDocr.append(docr)
			print(f"writing to {doc.pathOutput.relative_to(Path.cwd())}")
		return lDocr

	cJob = min(cJob, len(lDoca))

	strBarFormat = "{desc} {n_fmt}/{total_fmt}: {percentage:3.0f}%|{bar}|"

	with tqdm(total=len(lDoca), desc="building", bar_format=strBarFormat) as pbar:
		with ProcessPoolExecutor(max_workers=cJob) as pool:
			lFuture = [pool.submit(DocrBuildDocaAsync, doca) for doca in lDoca]
			for future in as_completed(lFuture):
				if docr := future.result():
					lDocr.append(docr)
				pbar.update(1)

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

		if wl := manif.WlMissing():
			assert wl.docaWind is None
			manif.WriteGridManifests(LDocrBuildLDoca(wl.lDoca, cJob))

	if fProfile:
		print(f"wrote profile to {pathProf}")

if __name__ == '__main__':
	main()
