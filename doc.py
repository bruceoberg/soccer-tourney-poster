#!/usr/bin/env python3

"""
soccer tournament roster document handling
"""

from __future__ import annotations  # Forward refs without quotes

import datetime
import fpdf
import platform

from pathlib import Path

from bolay import CBlot, CPdf, SRect, SPoint, SFontKey, colorBlack, JH, JV

from .database import SDatabase
from .common import strFile, strYearTitle
from .page import CGroupBlot

from . import metrics
from . import g_pathCode

g_pathFonts = g_pathCode / 'fonts'

def DoIt(db: SDatabase):
	pdf = CPdf()

	pdf.AddFont('NotoSans', '', g_pathFonts / 'NotoSans-Regular.ttf')
	pdf.AddFont('NotoSans', 'B', g_pathFonts / 'NotoSans-Bold.ttf')
	pdf.AddFont('NotoSans', 'I', g_pathFonts / 'NotoSans-Light.ttf')

	pdf.set_title(strYearTitle)
	pdf.set_author('bruce oberg')
	pdf.set_subject("Roster Cheat Sheet")
	pdf.set_keywords('world cup soccer football rosters')
	pdf.set_creator(f'python v{platform.python_version()}, fpdf2 v{fpdf.__version__}')
	pdf.set_lang('en')
	pdf.set_creation_date(datetime.datetime.now())

	pdf.add_page(orientation="portrait", format="letter")

	assert pdf.w == metrics.page.dX
	assert pdf.h == metrics.page.dY

	CGroupBlot(pdf).Draw(SPoint(metrics.page.dXLeft, metrics.page.dYTop))

	pathDst = (Path.cwd() / "playground" / strFile).with_suffix('.pdf')
	print(f'Writing: {pathDst.relative_to(Path.cwd())}')
	pdf.output(str(pathDst))
