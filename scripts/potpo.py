#!/usr/bin/env python3
"""Manage .pot/.po files for the stp project using polib."""

from __future__ import annotations  # Forward refs without quotes

import argparse
import copy
import sys
from datetime import datetime
from pathlib import Path

import polib

g_pathLoc = Path(__file__).parent.parent / 'src' / 'stp' / 'localization'
g_strProject = 'stp'
g_strGenerator = 'potpo from bruce@oberg.org'

# language-specific fields preserved from the .po — everything else in the
# .pot's metadata propagates through (so unknown/new fields don't get dropped).
# POT-Creation-Date is set from the .pot file mtime (not the metadata, which
# can be stale). PO-Revision-Date and X-Generator are always set fresh.
g_lStrFieldFromLang = [
	'Language',
	'Last-Translator',
	'Language-Team',
	'Plural-Forms',
]


def StrFormatDate(t: datetime) -> str:
	return t.astimezone().strftime('%Y-%m-%d %H:%M%z')


def UpdateMetadata(
	pofOut: polib.POFile,
	pofProject: polib.POFile,
	pofLang: polib.POFile,
	strPotCreationDate: str,
) -> None:
	# every .pot field overwrites .po (propagates unknown fields), then
	# language-specific fields are restored from the .po.
	for strField, strVal in pofProject.metadata.items():
		pofOut.metadata[strField] = strVal
	for strField in g_lStrFieldFromLang:
		strVal = pofLang.metadata.get(strField)
		if strVal is not None:
			pofOut.metadata[strField] = strVal
	pofOut.metadata['POT-Creation-Date'] = strPotCreationDate
	pofOut.metadata['PO-Revision-Date'] = StrFormatDate(datetime.now())
	pofOut.metadata['X-Generator'] = g_strGenerator

# NOTE(bruce): divider entries are non-translatable section markers — every real
# entry has a msgctxt (e.g. "competition.mens-world-cup") that serves as its
# developer key, so absence of msgctxt uniquely identifies a divider. They are
# passed through verbatim from the .pot during merge — never carried forward
# from the .po, never marked fuzzy.


def FIsDivider(entry: polib.POEntry) -> bool:
	return not entry.msgctxt


def MpKeyEntryBuild(pof: polib.POFile) -> dict[tuple[str, str], polib.POEntry]:
	mpKeyEntry: dict[tuple[str, str], polib.POEntry] = {}
	for entry in pof:
		if FIsDivider(entry):
			continue
		mpKeyEntry[(entry.msgctxt or '', entry.msgid)] = entry
	return mpKeyEntry


def MpCtxEntryBuild(pof: polib.POFile) -> dict[str, polib.POEntry]:
	mpCtxEntry: dict[str, polib.POEntry] = {}
	for entry in pof:
		if FIsDivider(entry):
			continue
		if entry.msgctxt:
			mpCtxEntry[entry.msgctxt] = entry
	return mpCtxEntry


class CMergeStats:  # tag = stats
	def __init__(self) -> None:
		self.cTranslated: int = 0
		self.cFuzzy: int = 0
		self.cNew: int = 0
		self.cDropped: int = 0
		self.cUntranslated: int = 0


def MergePotIntoPo(
	pofProject: polib.POFile,
	pofLang: polib.POFile,
	strPotCreationDate: str,
) -> tuple[polib.POFile, CMergeStats]:
	"""Build a new POFile from pofProject using msgstr/flags carried forward from pofLang."""

	mpKeyEntry = MpKeyEntryBuild(pofLang)
	mpCtxEntry = MpCtxEntryBuild(pofLang)
	setKeyUsed: set[tuple[str, str]] = set()

	stats = CMergeStats()

	# build the output pof: start from the .po's metadata/header (preserves any
	# .po-only fields like translator-set X-Poedit-*), then UpdateMetadata
	# propagates .pot fields and re-pins language-specific ones.
	pofOut = polib.POFile()
	pofOut.metadata = dict(pofLang.metadata)
	pofOut.metadata_is_fuzzy = pofLang.metadata_is_fuzzy
	pofOut.header = pofLang.header
	UpdateMetadata(pofOut, pofProject, pofLang, strPotCreationDate)

	for entryPot in pofProject:
		if FIsDivider(entryPot):
			# pass through divider verbatim from the .pot — never carry over from .po.
			# deep copy so later mutations to entryPot don't leak into pofOut.
			pofOut.append(copy.deepcopy(entryPot))
			continue

		strCtx = entryPot.msgctxt or ''
		key = (strCtx, entryPot.msgid)
		entryExisting = mpKeyEntry.get(key)

		if entryExisting is not None:
			# exact match: carry msgstr + flags, refresh comments from .pot.
			setKeyUsed.add(key)
			entryNew = polib.POEntry(
				msgid=entryPot.msgid,
				msgstr=entryExisting.msgstr,
				msgctxt=entryPot.msgctxt,
				comment=entryPot.comment,
				tcomment=entryExisting.tcomment,
				flags=list(entryExisting.flags),
				occurrences=list(entryPot.occurrences),
			)
			pofOut.append(entryNew)
			if 'fuzzy' in entryNew.flags:
				stats.cFuzzy += 1
			elif entryNew.msgstr:
				stats.cTranslated += 1
			else:
				stats.cUntranslated += 1
			continue

		entryByCtx = mpCtxEntry.get(strCtx) if strCtx else None
		if entryByCtx is not None:
			# msgctxt match but msgid changed: carry msgstr, mark fuzzy.
			setKeyUsed.add((entryByCtx.msgctxt or '', entryByCtx.msgid))
			lFlags = list(entryByCtx.flags)
			if 'fuzzy' not in lFlags:
				lFlags.append('fuzzy')
			entryNew = polib.POEntry(
				msgid=entryPot.msgid,
				msgstr=entryByCtx.msgstr,
				msgctxt=entryPot.msgctxt,
				comment=entryPot.comment,
				tcomment=entryByCtx.tcomment,
				flags=lFlags,
				occurrences=list(entryPot.occurrences),
				previous_msgid=entryByCtx.msgid,
			)
			pofOut.append(entryNew)
			stats.cFuzzy += 1
			continue

		# brand new entry.
		entryNew = polib.POEntry(
			msgid=entryPot.msgid,
			msgstr='',
			msgctxt=entryPot.msgctxt,
			comment=entryPot.comment,
			flags=list(entryPot.flags),
			occurrences=list(entryPot.occurrences),
		)
		pofOut.append(entryNew)
		stats.cNew += 1
		stats.cUntranslated += 1

	# count drops: real (non-divider) entries in existing not consumed.
	for key in mpKeyEntry:
		if key not in setKeyUsed:
			stats.cDropped += 1

	return pofOut, stats


def StrLangFromPo(pof: polib.POFile) -> str:
	strLang = pof.metadata.get('Language', '').strip()
	return strLang


def CmdPush(args: argparse.Namespace) -> int:
	pathPot = g_pathLoc / f'{g_strProject}.pot'
	if not pathPot.is_file():
		print(f'error: template not found: {pathPot}', file=sys.stderr)
		return 1

	pofProject = polib.pofile(str(pathPot))
	strPotCreationDate = StrFormatDate(datetime.fromtimestamp(pathPot.stat().st_mtime))

	lPathPo = sorted(p for p in g_pathLoc.glob(f'{g_strProject}-*.po'))
	if not lPathPo:
		print(f'no .po files found in {g_pathLoc}', file=sys.stderr)
		return 1

	for pathPo in lPathPo:
		strLang = pathPo.stem.split('-', 1)[1]
		pofLang = polib.pofile(str(pathPo))
		pofOut, stats = MergePotIntoPo(pofProject, pofLang, strPotCreationDate)
		pofOut.save(str(pathPo))
		print(
			f'  ✓ {strLang}  translated={stats.cTranslated}  '
			f'fuzzy={stats.cFuzzy}  new={stats.cNew}  dropped={stats.cDropped}'
		)

	return 0


def CmdAccept(args: argparse.Namespace) -> int:
	pathPot = g_pathLoc / f'{g_strProject}.pot'
	if not pathPot.is_file():
		print(f'error: template not found: {pathPot}', file=sys.stderr)
		return 1

	pofProject = polib.pofile(str(pathPot))
	strPotCreationDate = StrFormatDate(datetime.fromtimestamp(pathPot.stat().st_mtime))

	cAccepted = 0
	cRejected = 0

	for strInput in args.lInput:
		pathInput = Path(strInput).expanduser()
		print(f'Processing: {pathInput}')

		if not pathInput.is_file():
			print(f'  ✗ {pathInput} — file not found')
			cRejected += 1
			continue

		try:
			pofInput = polib.pofile(str(pathInput))
		except (OSError, IOError) as ex:
			print(f'  ✗ failed to read: {ex}')
			cRejected += 1
			continue
		except Exception as ex:
			print(f'  ✗ failed to parse: {ex}')
			cRejected += 1
			continue

		strLang = StrLangFromPo(pofInput)
		if not strLang:
			print('  ✗ could not read Language: header — skipping')
			cRejected += 1
			continue

		pofOut, stats = MergePotIntoPo(pofProject, pofInput, strPotCreationDate)
		print(
			f'  Stats: translated={stats.cTranslated}  fuzzy={stats.cFuzzy}  '
			f'untranslated={stats.cUntranslated}  new={stats.cNew}  dropped={stats.cDropped}'
		)

		pathDest = g_pathLoc / f'{g_strProject}-{strLang}.po'
		if pathDest.exists():
			print(f'  Updating existing: {pathDest}')
		else:
			print(f'  Creating new: {pathDest}')

		pofOut.save(str(pathDest))
		print(f'  ✓ {strLang} accepted → {pathDest}')
		cAccepted += 1

	print('')
	print(f'Done. {cAccepted} accepted, {cRejected} rejected.')
	return 0 if cRejected == 0 else 1


def Main(argv: list[str] | None = None) -> int:
	parser = argparse.ArgumentParser(
		prog='potpo',
		description='Manage .pot/.po files for the stp project using polib.',
	)
	subs = parser.add_subparsers(dest='strCmd', required=True)

	parserPush = subs.add_parser(
		'push',
		help='propagate .pot changes to all .po files',
		description='Propagate .pot changes to every .po in localization/.',
	)
	parserPush.set_defaults(fn=CmdPush)

	parserAccept = subs.add_parser(
		'accept',
		help='accept translated .po files from a translator',
		description='Validate and integrate translator-returned .po files.',
	)
	parserAccept.add_argument(
		'lInput',
		metavar='file',
		nargs='+',
		help='one or more .po files returned from a translator',
	)
	parserAccept.set_defaults(fn=CmdAccept)

	args = parser.parse_args(argv)
	return args.fn(args)


if __name__ == '__main__':
	sys.exit(Main())
