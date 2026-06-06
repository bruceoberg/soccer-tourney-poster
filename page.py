#!/usr/bin/env python3

"""
soccer tournament roster page handling
"""

from __future__ import annotations  # Forward refs without quotes

from pathlib import Path

from bolay import CBlot, CPdf, SRect, SPoint, SFontKey, JH, JV
from bolay import SColor, ColorFromStr, ColorResaturate, ColorResaturateDarker, FIsSaturated
from bolay import colorWhite, colorBlack, colorLightGrey, colorDarkgrey

from .database import SGroup, SSquad
from .common import mpStrGroupStrColor

from . import metrics

class SColors: # tag = colors
	s_dSDarker = 0.5

	s_rVLighter = 1.5
	s_rSLighter = 0.5

	s_rVDarker = 0.75	# for unsaturated colors
	s_dVLighter = 0.2

	def __init__(self, strColor: str) -> None:
		self.color: SColor = ColorFromStr(strColor)
		if FIsSaturated(self.color):
			self.colorDarker: SColor = ColorResaturateDarker(self.color, dS=self.s_dSDarker)
			self.colorLighter: SColor = ColorResaturate(self.color, rV=self.s_rVLighter, rS=self.s_rSLighter)
		else:
			self.colorDarker: SColor = ColorResaturateDarker(self.color, rV=self.s_rVDarker)
			self.colorLighter: SColor = ColorResaturate(self.color, dV=self.s_dVLighter)

class CGroupBlot(CBlot): # tag = titleb

	s_dX = metrics.page.dXLive
	s_dY = metrics.page.dYLive

	s_rSLineOuter = 0.001
	s_rSLineInner = 0.0002
	s_dSLineOuter = s_dX * s_rSLineOuter
	s_dSLineInner = s_dX * s_rSLineInner

	s_rSGroup = 10.0

	def __init__(self, pdf: CPdf, strGroup: str, group: SGroup) -> None:
		super().__init__(pdf)

		assert strGroup.startswith("Group ")
		assert len(strGroup) == len("Group ") + 1
		self.strGroup = strGroup[-1]
		self.group = group
		self.colors = SColors(mpStrGroupStrColor[self.strGroup])

	def Draw(self, pos: SPoint) -> None:

		rectBorder = SRect(pos.x, pos.y, self.s_dX, self.s_dY)
		rectInside = rectBorder.Copy().Inset(self.s_dSLineOuter / 2.0)

		# title

		#dYTitle = dY * self.s_uYTitle
		dYTitle = rectInside.dX / self.s_rSGroup
		rectTitle = rectInside.Copy(dY=dYTitle)

		self.FillBox(rectTitle, self.colors.color)

		dYGroupName = dYTitle * 1.3
		oltbGroupName = self.Oltb(rectTitle, SFontKey('NotoSansMono', ''), dYGroupName)
		rectGroupName = oltbGroupName.RectDrawText(
										self.strGroup,
										self.colors.colorDarker,
										JH.Right,
										JV.Middle)

		rectGroupLabel = rectTitle.Copy(dX=rectGroupName.x - rectTitle.x)

		uGroupLabel = 0.65
		strGroupTitle = "Group"
		oltbGroupLabel = self.Oltb(rectGroupLabel, SFontKey('NotoSans', ''), dYTitle * uGroupLabel, dSMargin = oltbGroupName.dSMargin)
		oltbGroupLabel.DrawText(strGroupTitle, colorWhite, JH.Right) #, JV.Top)

		self.DrawBox(rectBorder, self.s_dSLineOuter, colorBlack)
		self.DrawBox(rectBorder, self.s_dSLineInner, self.colors.color)
