#!/usr/bin/env python3

"""
soccer tournament roster page handling
"""

from __future__ import annotations  # Forward refs without quotes

from pathlib import Path

from bolay import CBlot, CPdf, SRect, SPoint, SFontKey, JH, JV
from bolay import colorWhite, colorBlack, colorLightGrey, colorDarkgrey


from . import metrics

class CGroupBlot(CBlot): # tag = titleb

	s_dX = metrics.page.dXLive
	s_dY = metrics.page.dYLive

	s_rSLineOuter = 0.001
	s_rSLineInner = 0.0002
	s_dSLineOuter = s_dX * s_rSLineOuter
	s_dSLineInner = s_dX * s_rSLineInner

	s_rSGroup = 10.0

	def __init__(self, pdf: CPdf) -> None:
		super().__init__(pdf)

	def Draw(self, pos: SPoint) -> None:

		rectBorder = SRect(pos.x, pos.y, self.s_dX, self.s_dY)
		rectInside = rectBorder.Copy().Inset(self.s_dSLineOuter / 2.0)

		# title

		#dYTitle = dY * self.s_uYTitle
		dYTitle = rectInside.dX / self.s_rSGroup
		rectTitle = rectInside.Copy(dY=dYTitle)

		self.FillBox(rectTitle, colorLightGrey)

		fontkey = SFontKey('NotoSans', 'B')

		dYGroupName = dYTitle * 1.3
		oltbGroupName = self.Oltb(rectTitle, fontkey, dYGroupName)
		rectGroupName = oltbGroupName.RectDrawText(
										"A",
										colorDarkgrey,
										JH.Right,
										JV.Middle)

		rectGroupLabel = rectTitle.Copy(dX=rectGroupName.x - rectTitle.x)

		uGroupLabel = 0.65
		strGroupTitle = "Group"
		oltbGroupLabel = self.Oltb(rectGroupLabel, fontkey, dYTitle * uGroupLabel, dSMargin = oltbGroupName.dSMargin)
		oltbGroupLabel.DrawText(strGroupTitle, colorWhite, JH.Right) #, JV.Top)

		self.DrawBox(rectBorder, self.s_dSLineOuter, colorBlack)
		self.DrawBox(rectBorder, self.s_dSLineInner, colorLightGrey)
