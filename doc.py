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
from .image import CImageCache
from .page import CGroupBlot

from . import metrics
from . import g_pathCode

g_pathFonts = g_pathCode / 'fonts'

class CDocument():
	def __init__(self, db: SDatabase):
		self.db = db
		self.pdf = CPdf()
		self.imgc = CImageCache(db)
		self.cPersonMax = self.db.CPersonMax()

	def Write(self):

		self.pdf.AddFont('NotoSans', '', g_pathFonts / 'NotoSansNerdFont-Regular.ttf')
		self.pdf.AddFont('NotoSans', 'B', g_pathFonts / 'NotoSans-Bold.ttf')
		self.pdf.AddFont('NotoSans', 'I', g_pathFonts / 'NotoSans-Light.ttf')
		self.pdf.AddFont('NotoSansMono', '', g_pathFonts / 'NotoSansMono-Regular.ttf')
		self.pdf.AddFont('NotoSansMono', 'B', g_pathFonts / 'NotoSansMono-Bold.ttf')
		self.pdf.AddFont('NotoSansMono', 'I', g_pathFonts / 'NotoSansMono-Thin.ttf')

		self.pdf.set_title(strYearTitle)
		self.pdf.set_author('bruce oberg')
		self.pdf.set_subject("Roster Cheat Sheet")
		self.pdf.set_keywords('world cup soccer football rosters')
		self.pdf.set_creator(f'python v{platform.python_version()}, fpdf2 v{fpdf.__version__}')
		self.pdf.set_lang('en')
		self.pdf.set_creation_date(datetime.datetime.now())

		for strGroup, group in self.db.groups.items():

			self.pdf.add_page(orientation=metrics.page.strOrientation, format=metrics.page.strFormat)

			assert self.pdf.w == metrics.page.dX
			assert self.pdf.h == metrics.page.dY

			CGroupBlot(self, strGroup, group).Draw(SPoint(metrics.page.dXLeft, metrics.page.dYTop))

		pathDst = (Path.cwd() / "playground" / strFile).with_suffix('.pdf')
		pathDst.parent.mkdir(parents=True, exist_ok=True)

		print(f'Writing: {pathDst.relative_to(Path.cwd())}')
		self.pdf.output(str(pathDst))
