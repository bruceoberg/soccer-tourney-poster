#!/usr/bin/env python3

from __future__ import annotations  # Forward refs without quotes (eg foo: CFoo, not foo: 'CFoo')

import cProfile
import pstats

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


@contextmanager
def Profiling(pathOut: Path, fEnabled: bool = True) -> Iterator[None]:
	"""Profile the enclosed block with cProfile and dump stats to pathOut on exit.
	When fEnabled is False, yield immediately so it's cheap to leave in place."""

	if not fEnabled:
		yield
		return

	profile = cProfile.Profile()
	profile.enable()
	try:
		yield
	finally:
		profile.disable()
		pathOut.parent.mkdir(parents=True, exist_ok=True)
		profile.dump_stats(str(pathOut))


def DumpTopCumulative(pathProf: Path, cLines: int = 30) -> None:
	"""Print the top cLines entries from pathProf sorted by cumulative time."""

	stats = pstats.Stats(str(pathProf))
	stats.strip_dirs().sort_stats("cumulative").print_stats(cLines)


def DumpTopTotal(pathProf: Path, cLines: int = 30) -> None:
	"""Print the top cLines entries from pathProf sorted by total (exclusive) time.
	Surfaces the function actually burning CPU vs. the caller wrapping expensive work."""

	stats = pstats.Stats(str(pathProf))
	stats.strip_dirs().sort_stats("tottime").print_stats(cLines)


# pstats internal key is (file, line, funcname)

TKey = tuple[str, int, str]


def _MpKeyCumNcallsLoad(pathProf: Path) -> dict[TKey, tuple[float, int]]:
	"""Load a .prof file and extract {func_key: (cumtime_seconds, ncalls)}."""

	stats = pstats.Stats(str(pathProf))

	mpKeyTuCumNcalls: dict[TKey, tuple[float, int]] = {}

	# pstats.Stats.stats value tuple: (cc, nc, tt, ct, callers)
	# cc = primitive calls, nc = total calls, tt = total (exclusive) time, ct = cumulative time

	for key, tuValue in stats.stats.items():  # type: ignore[attr-defined]
		_, cNcalls, _, gCumTime, _ = tuValue
		mpKeyTuCumNcalls[key] = (gCumTime, cNcalls)

	return mpKeyTuCumNcalls


def DiffProfiles(pathBefore: Path, pathAfter: Path, cLines: int = 30) -> None:
	"""Diff two .prof files: print the top cLines functions ranked by absolute delta in cumulative time.
	Functions present in only one run still appear, with 0 for the missing side."""

	mpKeyTuCumNcallsBefore = _MpKeyCumNcallsLoad(pathBefore)
	mpKeyTuCumNcallsAfter = _MpKeyCumNcallsLoad(pathAfter)

	setKey = set(mpKeyTuCumNcallsBefore) | set(mpKeyTuCumNcallsAfter)

	# row = (key, dGCum_s, gCumBefore_s, gCumAfter_s, cCallsBefore, cCallsAfter)

	lTuRow: list[tuple[TKey, float, float, float, int, int]] = []

	for key in setKey:
		gCumBefore, cCallsBefore = mpKeyTuCumNcallsBefore.get(key, (0.0, 0))
		gCumAfter, cCallsAfter = mpKeyTuCumNcallsAfter.get(key, (0.0, 0))
		dGCum = gCumAfter - gCumBefore
		lTuRow.append((key, dGCum, gCumBefore, gCumAfter, cCallsBefore, cCallsAfter))

	lTuRow.sort(key=lambda tu: abs(tu[1]), reverse=True)

	dXName = 60
	strHeaderFmt = f"{{:<{dXName}}}  {{:>10}}  {{:>10}}  {{:>11}}  {{:>12}}  {{:>12}}"
	print(strHeaderFmt.format("function", "before_ms", "after_ms", "delta_ms", "before_calls", "after_calls"))
	print(strHeaderFmt.format("-" * dXName, "-" * 10, "-" * 10, "-" * 11, "-" * 12, "-" * 12))

	for key, dGCum, gCumBefore, gCumAfter, cCallsBefore, cCallsAfter in lTuRow[:cLines]:
		strFile, nLine, strFunc = key
		strName = f"{Path(strFile).name}:{nLine}({strFunc})"
		if len(strName) > dXName:
			strName = strName[:dXName - 3] + "..."
		print(
			f"{strName:<{dXName}}  "
			f"{gCumBefore * 1000.0:>10.2f}  "
			f"{gCumAfter * 1000.0:>10.2f}  "
			f"{dGCum * 1000.0:>+11.2f}  "
			f"{cCallsBefore:>12}  "
			f"{cCallsAfter:>12}"
		)
